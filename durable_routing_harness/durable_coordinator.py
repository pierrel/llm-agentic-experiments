"""One-admission sealed coordinator for the durable-routing study."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
from typing import Callable, Sequence

from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from .durable_routing import DurableRoutingResult, DurableRoutingTask, read_tasks, score
from harness.records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from harness.runner import RunArtifacts, _artifact_digests, _exclusive_output_lock, _prepare_output, _write_trace


_DESCRIPTION_FIELD = "grounding_description"
_STUDY_PREFIX = "durable-promise-routing-v"


@dataclass(frozen=True)
class DurableRoutingDefinition:
    """The closed task bank and one-factor condition pair for this study."""

    bundle: StudyBundle
    tasks: dict[str, DurableRoutingTask]
    descriptions: dict[str, str]

    def validate(self, root: Path) -> None:
        """Reject source, schedule, or condition drift before worker admission."""
        self.bundle.assert_complete()
        registration = self.bundle.registration
        if registration.get("kind") != "durable_routing_web_main":
            raise ValueError("durable-routing bundle has the wrong registration kind")
        if set(self.tasks) != set(self.bundle.fixtures):
            raise ValueError("durable-routing fixtures do not match the task bank")
        if set(self.descriptions) != set(self.bundle.conditions):
            raise ValueError("durable-routing conditions do not match the bundle")
        if set(self.descriptions) != {"C0", "C1"}:
            raise ValueError("durable-routing study requires exactly two opaque conditions")
        for task_id, task in self.tasks.items():
            if self.bundle.fixtures[task_id] != digest(task.payload()):
                raise ValueError(f"durable-routing fixture digest mismatch: {task_id}")
        for condition_id, description in self.descriptions.items():
            if self.bundle.conditions[condition_id] != {"sha256": digest({_DESCRIPTION_FIELD: description})}:
                raise ValueError(f"durable-routing condition digest mismatch: {condition_id}")
        declared = registration.get("allowed_condition_difference")
        if declared != _DESCRIPTION_FIELD:
            raise ValueError("durable-routing must declare its sole condition difference")
        if registration.get("implementation_sha256") != durable_implementation_sha256(root):
            raise ValueError("durable-routing bundle does not match committed implementation")


@dataclass(frozen=True)
class DurableRoutingProgress:
    """The next safe action after at most one shared-model admission attempt."""

    status: str
    artifacts: RunArtifacts | None = None


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def durable_definition(root: Path, study_id: str = "durable-promise-routing-v5") -> DurableRoutingDefinition:
    """Read only the immutable task, condition, and bundle declarations."""
    if not study_id.startswith(_STUDY_PREFIX) or not study_id[len(_STUDY_PREFIX):].isdigit():
        raise ValueError("durable-routing study id must use the registered version form")
    study_dir = root / "experiments" / study_id
    tasks = read_tasks(study_dir / "tasks.json")
    raw_conditions = json.loads((study_dir / "conditions.json").read_text())
    if not isinstance(raw_conditions, dict):
        raise ValueError("durable-routing conditions must be an object")
    descriptions: dict[str, str] = {}
    for condition_id, value in raw_conditions.items():
        if (not isinstance(condition_id, str) or not isinstance(value, dict)
                or set(value) != {_DESCRIPTION_FIELD}
                or not isinstance(value[_DESCRIPTION_FIELD], str)):
            raise ValueError("durable-routing conditions have an invalid shape")
        descriptions[condition_id] = value[_DESCRIPTION_FIELD]
    bundle = StudyBundle.read_verified(study_dir / "bundle.json")
    if bundle.study_id != study_id:
        raise ValueError("durable-routing bundle identity does not match its directory")
    definition = DurableRoutingDefinition(bundle, tasks, descriptions)
    definition.validate(root)
    return definition


def durable_implementation_sha256(root: Path) -> str:
    """Hash every harness module imported by the coordinator and private worker."""
    modules = (
        "__init__.py", "durable_coordinator.py", "durable_routing.py", "durable_worker.py",
        "run_development.py",
    )
    return digest({
        f"durable_routing_harness/{name}": hashlib.sha256(
            (root / "durable_routing_harness" / name).read_bytes()).hexdigest()
        for name in modules
    })


def assist_runtime_sha256(root: Path) -> str:
    """Digest the complete local Assist and EDD closure used by this adapter."""
    paths = ("assist", "manage", "edd/eval/utils.py", "edd/eval/test_async_subagents.py")
    files: dict[str, str] = {}
    for relative in paths:
        path = root / relative
        if path.is_dir():
            candidates = path.rglob("*")
        else:
            candidates = (path,)
        for candidate in candidates:
            if not candidate.is_file() or "__pycache__" in candidate.parts:
                continue
            if candidate.is_symlink():
                raise ValueError("durable-routing runtime source cannot contain a symlink")
            files[str(candidate.relative_to(root))] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if not files:
        raise ValueError("durable-routing runtime source is empty")
    return digest(dict(sorted(files.items())))


def durable_worker_command(
    root: Path, workspace_root: Path, assist_root: Path, assist_python: Path, assist_env: Path,
    descriptor: Path, result: Path, request_started: Path,
) -> list[str]:
    """Build the sole model-capable command, nested in shared LLM admission."""
    return [
        str(workspace_root / "tools" / "agentic"), "resource", "run", "llm", "--",
        "sh", "-c", 'set -a; . "$1"; shift; exec "$@"', "sh", str(assist_env), "env",
        f"PYTHONPATH={root.resolve()}:{assist_root.resolve()}",
        str(assist_python), "-m", "durable_routing_harness.durable_worker",
        "--descriptor", str(descriptor), "--result", str(result),
        "--request-started", str(request_started),
    ]


def run_durable_routing_once(
    root: Path, output: Path, *, workspace_root: Path, assist_root: Path, assist_python: Path,
    assist_env: Path, study_id: str = "durable-promise-routing-v5",
    command_runner: CommandRunner | None = None,
) -> DurableRoutingProgress:
    """Make at most one admitted model episode and preserve all terminal outcomes."""
    root, output = root.resolve(), output.resolve()
    definition = durable_definition(root, study_id)
    _prepare_output(output)
    if command_runner is None:
        _validate_runtime_inputs(definition, assist_root, assist_env)
    with _exclusive_output_lock(output):
        return _run_once(
            definition, root, output, workspace_root.resolve(), assist_root.resolve(), assist_python.absolute(),
            assist_env.resolve(), command_runner or (lambda command: _run_command(command, _timeout(definition))),
        )


def _run_once(
    definition: DurableRoutingDefinition, root: Path, output: Path, workspace_root: Path, assist_root: Path,
    assist_python: Path, assist_env: Path, command_runner: CommandRunner,
) -> DurableRoutingProgress:
    bundle_path = output / "bundle.json"
    _prepare_bundle(bundle_path, definition.bundle)
    bundle = StudyBundle.read_verified(bundle_path)
    admissions = AdmissionLog(output / "admissions.jsonl", bundle.sha256)
    outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256)
    traces = output / "traces"
    if traces.is_symlink():
        raise ValueError("durable-routing trace directory cannot be a symlink")
    if traces.exists() and not traces.is_dir():
        raise ValueError("durable-routing trace path must be a real directory")
    gate = ScheduledAdmission(bundle.schedule, admissions)
    if gate.index < len(outcomes.read_verified()):
        raise ValueError("durable-routing outcomes cannot exceed admissions")
    if gate.current is not None and gate.index == len(outcomes.read_verified()):
        started = output / f".{gate.current.sha256}.lifecycle.json"
        if started.exists():
            attempt = len([record for record in admissions.read_verified()
                           if record["trial_sha256"] == gate.current.sha256]) + 1
            gate.record(AdmissionAttempt(
                gate.current, True, attempt, "recovered worker that crossed the provider boundary",
            ))
            return DurableRoutingProgress("worker_still_running" if _worker_is_running(started) else "recover_worker")
    if gate.current is None:
        return _progress_or_finalize(bundle_path, outcomes, admissions, traces)
    completed = outcomes.read_verified()
    if gate.index != len(completed):
        return _recover_interrupted_worker(bundle_path, outcomes, admissions, traces, definition, output)
    trial = gate.current
    descriptor = output / f".{trial.sha256}.descriptor.json"
    result_path = output / f".{trial.sha256}.result.json"
    started = output / f".{trial.sha256}.lifecycle.json"
    atomic_write(started, canonical_json({"state": "launch-intent"}) + b"\n")
    task = definition.tasks[trial.task]
    atomic_write(descriptor, canonical_json({
        "bundle_sha256": bundle.sha256,
        "trial_sha256": trial.sha256,
        "task": task.payload(),
        _DESCRIPTION_FIELD: definition.descriptions[trial.condition],
        "model_settings": bundle.settings["model"],
    }) + b"\n")
    attempt = len([record for record in admissions.read_verified() if record["trial_sha256"] == trial.sha256]) + 1
    command = durable_worker_command(
        root, workspace_root, assist_root, assist_python, assist_env, descriptor, result_path, started,
    )
    try:
        completed = command_runner(command)
    except subprocess.TimeoutExpired:
        return _record_terminal(
            bundle_path, outcomes, admissions, traces, trial, attempt, started,
            "timeout", "worker exceeded sealed timeout",
        )
    if completed.returncode:
        if _is_admission_denial(completed):
            gate.record(AdmissionAttempt(trial, False, attempt, "production reserved the GPU"))
            return DurableRoutingProgress("retry_in_10_minutes" if attempt < 10 else "blocked_after_60_minutes")
        return _record_terminal(
            bundle_path, outcomes, admissions, traces, trial, attempt, started,
            "provider_error" if _request_started(started) else "infrastructure_invalid",
            _command_detail(completed),
        )
    gate.record(AdmissionAttempt(trial, True, attempt, "worker command admitted through GPU admission gate"))
    try:
        payload = _read_worker_result(result_path, bundle.sha256, trial.sha256)
        result = DurableRoutingResult(
            initial_response=payload["initial_response"], completion_response=payload["completion_response"],
            calls=tuple(payload["calls"]), memory=payload["memory"],
            messages=tuple(payload["messages"]), provider_requests=tuple(payload["provider_requests"]),
            workspace_sha256=payload["workspace_sha256"], memory_sha256=payload["memory_sha256"],
        )
        scored = score(task, result)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        _write_trace(traces / f"{trial.sha256}.json", {
            "trial_sha256": trial.sha256, "trace": [], "worker_error": str(error)[:500],
        })
        outcomes.append(TrialOutcome(trial, "provider_error", _request_started(started), False, "worker result was malformed"))
        return _progress_or_finalize(bundle_path, outcomes, admissions, traces)
    _write_trace(traces / f"{trial.sha256}.json", {
        "trial_sha256": trial.sha256, "trace": [], "result": result.payload(),
        "score": {
            "routing": scored.routing, "persistence": scored.persistence,
            "answer_and_honesty": scored.answer_and_honesty, "full": scored.full,
            "failed_predicates": list(scored.failed_predicates),
        },
    })
    outcomes.append(TrialOutcome(
        trial, "pass" if scored.full else "artifact_failure", _request_started(started),
        scored.full, "; ".join(scored.failed_predicates) or "all durable-routing predicates passed",
    ))
    return _progress_or_finalize(bundle_path, outcomes, admissions, traces)


def _record_terminal(
    bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, traces: Path,
    trial, attempt: int, started: Path, outcome: str, detail: str,
) -> DurableRoutingProgress:
    _write_trace(traces / f"{trial.sha256}.json", {
        "trial_sha256": trial.sha256, "trace": [], "worker_error": detail[:500],
    })
    admissions.append(AdmissionAttempt(trial, True, attempt, "worker command admitted through GPU admission gate"))
    outcomes.append(TrialOutcome(trial, outcome, _request_started(started), False, detail[:500]))
    return _progress_or_finalize(bundle_path, outcomes, admissions, traces)


def _prepare_bundle(path: Path, bundle: StudyBundle) -> None:
    if path.exists():
        if StudyBundle.read_verified(path).sha256 != bundle.sha256:
            raise ValueError("existing durable-routing output belongs to another bundle")
        return
    if any(item.name != ".runner.lock" for item in path.parent.iterdir()):
        raise ValueError("existing durable-routing output lacks a bundle")
    bundle.write(path)


def _progress_or_finalize(
    bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, traces: Path,
) -> DurableRoutingProgress:
    """Finalize only after every sealed scheduled unit has an outcome."""
    bundle = StudyBundle.read_verified(bundle_path)
    if len(outcomes.read_verified()) < len(bundle.schedule):
        return DurableRoutingProgress("next_trial")
    return DurableRoutingProgress("complete", _finalize(bundle_path, outcomes, admissions, traces))


def _finalize(bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, traces: Path) -> RunArtifacts:
    bundle = StudyBundle.read_verified(bundle_path)
    report = bundle_path.parent / "report.json"
    if outcomes.path.with_suffix(".jsonl.seal").exists():
        outcomes.verify_finalized(bundle.schedule, admissions, _artifact_digests(bundle, traces, report))
    else:
        _write_pilot_report(bundle, outcomes, traces, report)
        outcomes.finalize(bundle.schedule, admissions, _artifact_digests(bundle, traces, report))
    return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, traces)


def _write_pilot_report(bundle: StudyBundle, outcomes: RecordChain, traces: Path, report: Path) -> None:
    """Write the preregistered count-only pilot analysis from sealed trace predicates."""
    dimensions = ("routing", "persistence", "answer_and_honesty", "full")
    counts = {condition: {dimension: 0 for dimension in dimensions} for condition in bundle.conditions}
    by_task = {
        task: {condition: {dimension: 0 for dimension in dimensions} for condition in bundle.conditions}
        for task in bundle.fixtures
    }
    completed = outcomes.read_verified()
    for record in completed:
        trial = record["trial"]
        if not isinstance(trial, dict):
            raise ValueError("durable-routing outcome lacks trial metadata")
        task, condition = trial.get("task"), trial.get("condition")
        if not isinstance(task, str) or not isinstance(condition, str):
            raise ValueError("durable-routing outcome has malformed trial metadata")
        trace = json.loads((traces / f"{record['trial_sha256']}.json").read_text())
        score_data = trace.get("score") if isinstance(trace, dict) else None
        for dimension in dimensions:
            passed = isinstance(score_data, dict) and score_data.get(dimension) is True
            if passed:
                counts[condition][dimension] += 1
                by_task[task][condition][dimension] += 1
    low_conflict = bundle.registration.get("low_conflict_tasks")
    if not isinstance(low_conflict, list) or not all(isinstance(task, str) for task in low_conflict):
        raise ValueError("durable-routing bundle lacks low-conflict pilot task ids")
    advance = (
        counts["C1"]["routing"] >= counts["C0"]["routing"] + 2
        and counts["C1"]["full"] >= counts["C0"]["full"] + 2
        and all(
            by_task[task]["C1"][dimension] >= by_task[task]["C0"][dimension]
            for task in low_conflict for dimension in ("persistence", "answer_and_honesty")
        )
    )
    atomic_write(report, canonical_json({
        "bundle_sha256": bundle.sha256,
        "analysis": "durable-routing-pilot-counts-v1",
        "condition_counts": counts,
        "task_condition_counts": by_task,
        "advance_to_fresh_confirmation": advance,
        "advance_rule": "C1 has >=2 more R and F successes; no low-conflict P/A decrease",
    }) + b"\n")


def _read_worker_result(path: Path, bundle_sha256: str, trial_sha256: str) -> dict[str, object]:
    if path.is_symlink():
        raise ValueError("durable-routing worker result cannot be a symlink")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("durable-routing worker result must be an object")
    if value.get("bundle_sha256") != bundle_sha256 or value.get("trial_sha256") != trial_sha256:
        raise ValueError("durable-routing worker result belongs to another trial")
    result = value.get("result")
    if not isinstance(result, dict):
        raise ValueError("durable-routing worker result is malformed")
    required = {
        "initial_response", "completion_response", "calls", "memory", "messages", "provider_requests",
        "workspace_sha256", "memory_sha256",
    }
    if set(result) != required:
        raise ValueError("durable-routing worker result has an invalid shape")
    if not all(isinstance(result[key], str) for key in (
        "initial_response", "completion_response", "memory", "workspace_sha256", "memory_sha256",
    )):
        raise ValueError("durable-routing worker result has invalid text evidence")
    if not all(isinstance(result[key], list) for key in ("calls", "messages", "provider_requests")):
        raise ValueError("durable-routing worker result has invalid list evidence")
    if not all(
        isinstance(item, dict)
        for key in ("calls", "messages", "provider_requests") for item in result[key]
    ):
        raise ValueError("durable-routing worker result has non-object trace evidence")
    if not result["provider_requests"]:
        raise ValueError("durable-routing worker result lacks provider request evidence")
    return result


def _request_started(path: Path) -> bool:
    if path.is_symlink():
        raise ValueError("durable-routing request marker cannot be a symlink")
    if not path.exists():
        return False
    try:
        marker = json.loads(path.read_text())
        if not isinstance(marker, dict):
            raise ValueError("durable-routing request marker is malformed")
    except json.JSONDecodeError as error:
        raise ValueError("durable-routing request marker is malformed") from error
    return marker.get("state") == "model-invoke-started" and isinstance(marker.get("pid"), int)


def _timeout(definition: DurableRoutingDefinition) -> int:
    model = definition.bundle.settings.get("model")
    timeout = model.get("timeout_seconds") if isinstance(model, dict) else None
    if not isinstance(timeout, int) or timeout < 1:
        raise ValueError("durable-routing bundle requires positive sealed timeout")
    return timeout


def _run_command(command: Sequence[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        _terminate_process_group(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process.pid, signal.SIGKILL)
            process.communicate()
        raise subprocess.TimeoutExpired(command, timeout_seconds, error.output, error.stderr) from error
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _terminate_process_group(pid: int, signal_number: signal.Signals) -> None:
    """Terminate the admitted wrapper and every child without racing an exited group."""
    try:
        os.killpg(pid, signal_number)
    except ProcessLookupError:
        pass


def _recover_interrupted_worker(
    bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, traces: Path,
    definition: DurableRoutingDefinition, output: Path,
) -> DurableRoutingProgress:
    """Never rerun a trial after its worker reached the first provider request."""
    completed = outcomes.read_verified()
    trial = definition.bundle.schedule[len(completed)]
    started = output / f".{trial.sha256}.lifecycle.json"
    result_path = output / f".{trial.sha256}.result.json"
    if _request_started(started) and _worker_is_running(started):
        return DurableRoutingProgress("worker_still_running")
    if result_path.exists():
        return _record_recovered_result(bundle_path, outcomes, admissions, traces, definition, trial, result_path)
    return _record_recovered_failure(
        bundle_path, outcomes, admissions, traces, trial, started,
        "provider_error" if _request_started(started) else "infrastructure_invalid",
        "worker ended after coordinator interruption without a complete result",
    )


def _record_recovered_result(
    bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, traces: Path,
    definition: DurableRoutingDefinition, trial, result_path: Path,
) -> DurableRoutingProgress:
    """Preserve a completed worker result discovered after coordinator restart."""
    bundle = StudyBundle.read_verified(bundle_path)
    try:
        payload = _read_worker_result(result_path, bundle.sha256, trial.sha256)
        result = DurableRoutingResult(
            initial_response=payload["initial_response"], completion_response=payload["completion_response"],
            calls=tuple(payload["calls"]), memory=payload["memory"],
            messages=tuple(payload["messages"]), provider_requests=tuple(payload["provider_requests"]),
            workspace_sha256=payload["workspace_sha256"], memory_sha256=payload["memory_sha256"],
        )
        scored = score(definition.tasks[trial.task], result)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return _record_recovered_failure(bundle_path, outcomes, admissions, traces, trial,
                                         result_path.with_name(f".{trial.sha256}.lifecycle.json"),
                                         "provider_error", str(error))
    _write_trace(traces / f"{trial.sha256}.json", {
        "trial_sha256": trial.sha256, "trace": [], "result": result.payload(),
        "score": {"routing": scored.routing, "persistence": scored.persistence,
                  "answer_and_honesty": scored.answer_and_honesty, "full": scored.full,
                  "failed_predicates": list(scored.failed_predicates)},
    })
    outcomes.append(TrialOutcome(trial, "pass" if scored.full else "artifact_failure", True, scored.full,
                                 "; ".join(scored.failed_predicates) or "all durable-routing predicates passed"))
    return _progress_or_finalize(bundle_path, outcomes, admissions, traces)


def _record_recovered_failure(
    bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, traces: Path,
    trial, started: Path, outcome: str, detail: str,
) -> DurableRoutingProgress:
    """Account for an admitted trial without replaying its unknown model work."""
    _write_trace(traces / f"{trial.sha256}.json", {
        "trial_sha256": trial.sha256, "trace": [], "worker_error": detail[:500],
    })
    outcomes.append(TrialOutcome(trial, outcome, _request_started(started), False, detail[:500]))
    return _progress_or_finalize(bundle_path, outcomes, admissions, traces)


def _worker_is_running(path: Path) -> bool:
    """Return whether the worker that crossed the model boundary is still alive."""
    try:
        marker = json.loads(path.read_text())
        if not isinstance(marker, dict):
            return False
        pid = marker.get("pid")
        if not isinstance(pid, int) or pid < 1:
            return False
        os.kill(pid, 0)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return True


def _validate_runtime_inputs(definition: DurableRoutingDefinition, assist_root: Path, assist_env: Path) -> None:
    """Bind a real admission to the registered Assist source and private config path."""
    expected = definition.bundle.settings["harness_architecture"].get("assist_source_commit")
    if not isinstance(expected, str):
        raise ValueError("durable-routing bundle lacks an Assist source commit")
    actual = subprocess.run(
        ["git", "-C", str(assist_root), "merge-base", "HEAD", expected],
        check=False, text=True, capture_output=True,
    )
    if actual.returncode or actual.stdout.strip() != expected:
        raise ValueError("durable-routing Assist source does not contain the registered baseline")
    expected_runtime = definition.bundle.settings["harness_architecture"].get("assist_runtime_sha256")
    if not isinstance(expected_runtime, str) or assist_runtime_sha256(assist_root) != expected_runtime:
        raise ValueError("durable-routing Assist runtime differs from the sealed source closure")
    if assist_env.is_symlink() or not assist_env.is_file():
        raise ValueError("durable-routing Assist environment must be a regular file")


def _is_admission_denial(result: subprocess.CompletedProcess[str]) -> bool:
    detail = (result.stderr or "") + (result.stdout or "")
    return "production is busy" in detail or "resource is busy: resource-llm" in detail


def _command_detail(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip().replace("\n", " ")
    return text[-500:] or f"worker exited {result.returncode}"
