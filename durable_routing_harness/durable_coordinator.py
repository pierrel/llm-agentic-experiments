"""One-admission sealed coordinator for the durable-routing study."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Callable, Sequence

from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from .durable_routing import DurableRoutingResult, DurableRoutingTask, read_tasks, score
from harness.records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from harness.report import write_static_report
from harness.runner import RunArtifacts, _artifact_digests, _exclusive_output_lock, _prepare_output, _write_trace


_DESCRIPTION_FIELD = "grounding_description"


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


def durable_definition(root: Path) -> DurableRoutingDefinition:
    """Read only the immutable task, condition, and bundle declarations."""
    study_dir = root / "experiments" / "durable-promise-routing-v1"
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
    assist_env: Path, command_runner: CommandRunner | None = None,
) -> DurableRoutingProgress:
    """Make at most one admitted model episode and preserve all terminal outcomes."""
    root, output = root.resolve(), output.resolve()
    definition = durable_definition(root)
    _prepare_output(output)
    with _exclusive_output_lock(output):
        return _run_once(
            definition, root, output, workspace_root.resolve(), assist_root.resolve(), assist_python.resolve(),
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
    if gate.current is None:
        return _progress_or_finalize(bundle_path, outcomes, admissions, traces)
    if gate.index != len(outcomes.read_verified()):
        raise ValueError("durable-routing interrupted admitted worker needs explicit recovery")
    trial = gate.current
    descriptor = output / f".{trial.sha256}.descriptor.json"
    result_path = output / f".{trial.sha256}.result.json"
    started = output / f".{trial.sha256}.request-started"
    task = definition.tasks[trial.task]
    atomic_write(descriptor, canonical_json({
        "bundle_sha256": bundle.sha256,
        "trial_sha256": trial.sha256,
        "task": task.payload(),
        _DESCRIPTION_FIELD: definition.descriptions[trial.condition],
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
            return DurableRoutingProgress("retry_in_10_minutes" if attempt <= 6 else "blocked_after_60_minutes")
        return _record_terminal(
            bundle_path, outcomes, admissions, traces, trial, attempt, started,
            "provider_error", _command_detail(completed),
        )
    gate.record(AdmissionAttempt(trial, True, attempt, "worker started through GPU admission gate"))
    try:
        payload = _read_worker_result(result_path, bundle.sha256, trial.sha256)
        result = DurableRoutingResult(
            initial_response=payload["initial_response"], completion_response=payload["completion_response"],
            calls=tuple(payload["calls"]), memory=payload["memory"],
            messages=tuple(payload["messages"]), provider_requests=tuple(payload["provider_requests"]),
        )
        scored = score(task, result)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        _write_trace(traces / f"{trial.sha256}.json", {
            "trial_sha256": trial.sha256, "trace": [], "worker_error": str(error)[:500],
        })
        outcomes.append(TrialOutcome(trial, "provider_error", _request_started(started), False, "worker result was malformed"))
        return DurableRoutingProgress("complete", _finalize(bundle_path, outcomes, admissions, traces))
    _write_trace(traces / f"{trial.sha256}.json", {
        "trial_sha256": trial.sha256, "result": result.payload(),
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
    admissions.append(AdmissionAttempt(trial, True, attempt, "worker started through GPU admission gate"))
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
        write_static_report(bundle, outcomes, report)
        outcomes.finalize(bundle.schedule, admissions, _artifact_digests(bundle, traces, report))
    return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, traces)


def _read_worker_result(path: Path, bundle_sha256: str, trial_sha256: str) -> dict[str, object]:
    if path.is_symlink():
        raise ValueError("durable-routing worker result cannot be a symlink")
    value = json.loads(path.read_text())
    if value.get("bundle_sha256") != bundle_sha256 or value.get("trial_sha256") != trial_sha256:
        raise ValueError("durable-routing worker result belongs to another trial")
    result = value.get("result")
    if not isinstance(result, dict):
        raise ValueError("durable-routing worker result is malformed")
    return result


def _request_started(path: Path) -> bool:
    if path.is_symlink():
        raise ValueError("durable-routing request marker cannot be a symlink")
    return path.read_bytes() == b"model-invoke-started\n" if path.exists() else False


def _timeout(definition: DurableRoutingDefinition) -> int:
    model = definition.bundle.settings.get("model")
    timeout = model.get("timeout_seconds") if isinstance(model, dict) else None
    if not isinstance(timeout, int) or timeout < 1:
        raise ValueError("durable-routing bundle requires positive sealed timeout")
    return timeout


def _run_command(command: Sequence[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout_seconds)


def _is_admission_denial(result: subprocess.CompletedProcess[str]) -> bool:
    detail = (result.stderr or "") + (result.stdout or "")
    return "production is busy" in detail or "resource is busy: resource-llm" in detail


def _command_detail(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip().replace("\n", " ")
    return text[:500] or f"worker exited {result.returncode}"
