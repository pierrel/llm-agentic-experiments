"""One-admission sealed coordinator for the durable-routing study."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
from typing import Callable, Sequence

from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from .durable_routing import DurableRoutingResult, DurableRoutingTask, read_tasks, score
from harness.records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from harness.runner import RunArtifacts, _artifact_digests, _exclusive_output_lock, _prepare_output, _write_trace


_STUDY_PREFIXES = (
    "durable-promise-routing-v", "durable-promise-outcome-v",
    "durable-promise-orchestration-v",
)
_CONDITION_FIELDS = {
    "grounding_description", "memory_guidance", "outcome_checklist",
    "async_outcome_reconciliation",
}


@dataclass(frozen=True)
class DurableRoutingDefinition:
    """The closed task bank and one-factor condition pair for this study."""

    bundle: StudyBundle
    tasks: dict[str, DurableRoutingTask]
    condition_field: str
    condition_values: dict[str, object]

    def validate(self, root: Path) -> None:
        """Reject source, schedule, or condition drift before worker admission."""
        self.bundle.assert_complete()
        registration = self.bundle.registration
        if registration.get("kind") != "durable_routing_web_main":
            raise ValueError("durable-routing bundle has the wrong registration kind")
        expected_registration = registration.get("registration_markdown_sha256")
        registration_path = root / "experiments" / self.bundle.study_id / "registration.md"
        if (not isinstance(expected_registration, str) or registration_path.is_symlink()
                or not registration_path.is_file()
                or hashlib.sha256(registration_path.read_bytes()).hexdigest() != expected_registration):
            raise ValueError("durable-routing registration prose differs from the sealed bundle")
        if set(self.tasks) != set(self.bundle.fixtures):
            raise ValueError("durable-routing fixtures do not match the task bank")
        if set(self.condition_values) != set(self.bundle.conditions):
            raise ValueError("durable-routing conditions do not match the bundle")
        if set(self.condition_values) != {"C0", "C1"}:
            raise ValueError("durable-routing study requires exactly two opaque conditions")
        for task_id, task in self.tasks.items():
            if self.bundle.fixtures[task_id] != digest(task.payload()):
                raise ValueError(f"durable-routing fixture digest mismatch: {task_id}")
        for condition_id, value in self.condition_values.items():
            if self.bundle.conditions[condition_id] != {"sha256": digest({self.condition_field: value})}:
                raise ValueError(f"durable-routing condition digest mismatch: {condition_id}")
        declared = registration.get("allowed_condition_difference")
        if declared != self.condition_field:
            raise ValueError("durable-routing must declare its sole condition difference")
        if registration.get("implementation_sha256") != durable_implementation_sha256(root):
            raise ValueError("durable-routing bundle does not match committed implementation")


@dataclass(frozen=True)
class DurableRoutingProgress:
    """The next safe action after at most one shared-model admission attempt."""

    status: str
    artifacts: RunArtifacts | None = None


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def durable_definition(root: Path, study_id: str = "durable-promise-outcome-v2") -> DurableRoutingDefinition:
    """Read only the immutable task, condition, and bundle declarations."""
    prefix = next((prefix for prefix in _STUDY_PREFIXES if study_id.startswith(prefix)), None)
    if prefix is None or not study_id[len(prefix):].isdigit():
        raise ValueError("durable-routing study id must use the registered version form")
    study_dir = root / "experiments" / study_id
    tasks = read_tasks(study_dir / "tasks.json")
    raw_conditions = json.loads((study_dir / "conditions.json").read_text())
    if not isinstance(raw_conditions, dict):
        raise ValueError("durable-routing conditions must be an object")
    condition_field = None
    condition_values: dict[str, object] = {}
    bundle = StudyBundle.read_verified(study_dir / "bundle.json")
    declared = bundle.registration.get("allowed_condition_difference")
    if not isinstance(declared, str) or declared not in _CONDITION_FIELDS:
        raise ValueError("durable-routing has an unsupported condition difference")
    condition_field = declared
    for condition_id, value in raw_conditions.items():
        if not isinstance(condition_id, str) or not isinstance(value, dict):
            raise ValueError("durable-routing conditions have an invalid shape")
        if set(value) != {condition_field}:
            if set(value) != {"memory_guidance_from"} or condition_field != "memory_guidance":
                raise ValueError("durable-routing conditions have an invalid shape")
            condition_value = _referenced_memory_guidance(root, value["memory_guidance_from"])
        else:
            condition_value = value[condition_field]
        if condition_field == "grounding_description":
            valid = isinstance(condition_value, str) and bool(condition_value)
        elif condition_field == "memory_guidance":
            valid = (isinstance(condition_value, dict)
                     and set(condition_value) == {"repository_memory_prompt", "thread_memory_prompt"}
                     and all(isinstance(text, str) and text for text in condition_value.values()))
        else:
            valid = isinstance(condition_value, bool)
        if not valid:
            raise ValueError("durable-routing condition value is invalid")
        condition_values[condition_id] = condition_value
    if bundle.study_id != study_id:
        raise ValueError("durable-routing bundle identity does not match its directory")
    definition = DurableRoutingDefinition(bundle, tasks, condition_field, condition_values)
    definition.validate(root)
    return definition


def _referenced_memory_guidance(root: Path, value: object) -> dict[str, str]:
    """Reuse a hash-pinned prompt pair without copying its long immutable prose."""
    if not isinstance(value, dict) or set(value) != {"study_id", "condition", "sha256"}:
        raise ValueError("durable-routing memory guidance reference is malformed")
    study_id, condition, expected_digest = value["study_id"], value["condition"], value["sha256"]
    if (not isinstance(study_id, str) or not study_id.startswith("durable-promise-outcome-v")
            or not study_id[len("durable-promise-outcome-v"):].isdigit()
            or not isinstance(condition, str) or not isinstance(expected_digest, str)):
        raise ValueError("durable-routing memory guidance reference is invalid")
    path = root / "experiments" / study_id / "conditions.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("durable-routing memory guidance source is unavailable")
    contents = path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != expected_digest:
        raise ValueError("durable-routing memory guidance source digest differs")
    source = json.loads(contents)
    candidate = source.get(condition) if isinstance(source, dict) else None
    guidance = candidate.get("memory_guidance") if isinstance(candidate, dict) else None
    if not (isinstance(guidance, dict) and set(guidance) == {"repository_memory_prompt", "thread_memory_prompt"}
            and all(isinstance(text, str) and text for text in guidance.values())):
        raise ValueError("durable-routing memory guidance source has an invalid shape")
    return guidance


def durable_implementation_sha256(root: Path) -> str:
    """Hash every local module that implements this runner's evidence contract."""
    files: dict[str, str] = {}
    for directory in (root / "durable_routing_harness", root / "harness"):
        for path in directory.rglob("*.py"):
            if path.is_symlink():
                raise ValueError("durable-routing implementation source cannot contain a symlink")
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not files:
        raise ValueError("durable-routing implementation source is empty")
    return digest(dict(sorted(files.items())))


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
    assist_env: Path, study_id: str = "durable-promise-outcome-v2",
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
    if (gate.current is not None and gate.index == len(outcomes.read_verified())
            and _request_started(output / f".{gate.current.sha256}.lifecycle.json")):
        started = output / f".{gate.current.sha256}.lifecycle.json"
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
        "condition_field": definition.condition_field,
        "condition_value": definition.condition_values[trial.condition],
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
            todos=tuple(payload["todos"]),
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
            "todo_used": scored.todo_used, "todo_reconciled": scored.todo_reconciled,
            "failed_predicates": list(scored.failed_predicates),
        },
    })
    outcomes.append(TrialOutcome(
        trial, "pass" if scored.full else "behavioral_failure", _request_started(started),
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
    dimensions = (
        "routing", "persistence", "answer_and_honesty", "full",
        "todo_used", "todo_reconciled",
    )
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
    if bundle.registration.get("analysis_phase") == "development_screen":
        _write_development_screen_report(bundle, counts, by_task, report)
        return
    low_conflict = bundle.registration.get("low_conflict_tasks")
    if not isinstance(low_conflict, list) or not all(isinstance(task, str) for task in low_conflict):
        raise ValueError("durable-routing bundle lacks low-conflict pilot task ids")
    primary_dimensions, guard_dimensions, minimum_delta, max_sign_p, max_guard_drop = _advance_plan(
        bundle.registration
    )
    paired = _paired_sign_tests(bundle, completed, traces, primary_dimensions)
    advance = (
        all(counts["C1"][dimension] >= counts["C0"][dimension] + minimum_delta
            for dimension in primary_dimensions)
        and all(paired[dimension]["p_one_sided"] <= max_sign_p for dimension in primary_dimensions)
        and all(
            by_task[task]["C1"][dimension] >= by_task[task]["C0"][dimension] - max_guard_drop
            for task in low_conflict for dimension in guard_dimensions
        )
        and all(counts["C1"][dimension] >= counts["C0"][dimension] - max_guard_drop
                for dimension in guard_dimensions)
    )
    atomic_write(report, canonical_json({
        "bundle_sha256": bundle.sha256,
        "analysis": bundle.analysis_revision,
        "condition_counts": counts,
        "task_condition_counts": by_task,
        "paired_sign_tests": paired,
        "advance_to_fresh_confirmation": advance,
        "advance_rule": (
            f"C1 has >={minimum_delta} more {'/'.join(primary_dimensions)} successes; "
            f"paired p<={max_sign_p}; no {'/'.join(guard_dimensions)} decrease >{max_guard_drop}"
        ),
    }) + b"\n")


def _write_development_screen_report(
    bundle: StudyBundle, counts: dict[str, dict[str, int]],
    by_task: dict[str, dict[str, dict[str, int]]], report: Path,
) -> None:
    """Apply the sealed exploratory screen without presenting it as confirmation."""
    registration = bundle.registration
    minimum_full = registration.get("development_minimum_full_passes")
    minimum_full_delta = registration.get("development_minimum_full_delta", 0)
    maximum_row_deficit = registration.get("development_maximum_row_deficit")
    minimum_todo_use = registration.get("development_minimum_todo_use")
    guard_dimensions = registration.get("development_non_regression_dimensions", [])
    dimensions = {
        "routing", "persistence", "answer_and_honesty", "full",
        "todo_used", "todo_reconciled",
    }
    if not all(isinstance(value, int) and value >= 0 for value in (
        minimum_full, minimum_full_delta, maximum_row_deficit,
    )) or (minimum_todo_use is not None and (
        not isinstance(minimum_todo_use, int) or minimum_todo_use < 0
    )) or not (isinstance(guard_dimensions, list)
               and all(dimension in dimensions for dimension in guard_dimensions)):
        raise ValueError("durable-routing development screen is incomplete")
    no_material_row_loss = all(
        by_task[task]["C1"]["full"] >= by_task[task]["C0"]["full"] - maximum_row_deficit
        for task in bundle.fixtures
    )
    no_guard_regression = all(
        counts["C1"][dimension] >= counts["C0"][dimension]
        for dimension in guard_dimensions
    )
    advance = (
        counts["C1"]["full"] >= minimum_full
        and counts["C1"]["full"] >= counts["C0"]["full"] + minimum_full_delta
        and no_material_row_loss
        and no_guard_regression
        and (minimum_todo_use is None or counts["C1"]["todo_used"] >= minimum_todo_use)
    )
    atomic_write(report, canonical_json({
        "bundle_sha256": bundle.sha256,
        "analysis": bundle.analysis_revision,
        "phase": "exploratory_development_screen",
        "condition_counts": counts,
        "task_condition_counts": by_task,
        "advance_to_fresh_confirmation": advance,
        "advance_rule": "; ".join(filter(None, (
            f"C1 full>={minimum_full}",
            f"C1-C0 full>={minimum_full_delta}",
            (f"C1 todo_used>={minimum_todo_use}"
             if minimum_todo_use is not None else None),
            f"no task C1 full deficit>{maximum_row_deficit}",
            ("no aggregate C1 regression on " + "/".join(guard_dimensions)
             if guard_dimensions else None),
        ))),
    }) + b"\n")


def _advance_plan(
    registration: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...], int, float, int]:
    """Read every quantitative advancement decision from the sealed registration."""
    primary = registration.get("advance_primary_dimensions")
    guards = registration.get("sentinel_non_regression_dimensions")
    minimum_delta = registration.get("advance_minimum_delta")
    max_sign_p = registration.get("paired_sign_test_max_p")
    max_guard_drop = registration.get("guard_maximum_decrease")
    dimensions = {
        "routing", "persistence", "answer_and_honesty", "full",
        "todo_used", "todo_reconciled",
    }
    if not (isinstance(primary, list) and primary and isinstance(guards, list)
            and primary and all(isinstance(value, str) and value in dimensions for value in primary + guards)
            and isinstance(minimum_delta, int) and minimum_delta > 0
            and isinstance(max_sign_p, (int, float)) and 0 < max_sign_p <= 1
            and isinstance(max_guard_drop, int) and max_guard_drop >= 0):
        raise ValueError("durable-routing bundle lacks a complete advance plan")
    return tuple(primary), tuple(guards), minimum_delta, float(max_sign_p), max_guard_drop


def _paired_sign_tests(
    bundle: StudyBundle, completed: list[dict[str, object]], traces: Path, dimensions: tuple[str, ...],
) -> dict[str, dict[str, float | int]]:
    """Compute preregistered one-sided paired sign tests from sealed block outcomes."""
    scores: dict[tuple[str, int, str], dict[str, bool]] = {}
    for record in completed:
        trial = record["trial"]
        if not isinstance(trial, dict):
            raise ValueError("durable-routing outcome lacks trial metadata")
        task, replicate, condition = trial.get("task"), trial.get("replicate"), trial.get("condition")
        if not isinstance(task, str) or not isinstance(replicate, int) or not isinstance(condition, str):
            raise ValueError("durable-routing outcome has malformed trial metadata")
        trace = json.loads((traces / f"{record['trial_sha256']}.json").read_text())
        score_data = trace.get("score") if isinstance(trace, dict) else None
        if not isinstance(score_data, dict):
            raise ValueError("durable-routing outcome lacks deterministic score")
        scores[(task, replicate, condition)] = {
            dimension: score_data.get(dimension) is True for dimension in dimensions
        }
    paired: dict[str, dict[str, float | int]] = {}
    for dimension in dimensions:
        favored = against = 0
        blocks = {(trial.task, trial.replicate) for trial in bundle.schedule}
        for task, replicate in blocks:
            control = scores.get((task, replicate, "C0"))
            treatment = scores.get((task, replicate, "C1"))
            if control is None or treatment is None:
                raise ValueError("durable-routing paired sign test lacks a condition outcome")
            if treatment[dimension] and not control[dimension]:
                favored += 1
            elif control[dimension] and not treatment[dimension]:
                against += 1
        paired[dimension] = {
            "C1_only": favored,
            "C0_only": against,
            "discordant": favored + against,
            "p_one_sided": _one_sided_sign_p(favored, against),
        }
    return paired


def _one_sided_sign_p(favored: int, against: int) -> float:
    """Exact probability of at least this many C1-favored discordant blocks under no effect."""
    trials = favored + against
    if trials == 0:
        return 1.0
    return sum(math.comb(trials, count) for count in range(favored, trials + 1)) / (2 ** trials)


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
        "initial_response", "completion_response", "calls", "memory", "messages", "provider_requests", "todos",
        "workspace_sha256", "memory_sha256",
    }
    if set(result) != required:
        raise ValueError("durable-routing worker result has an invalid shape")
    if not all(isinstance(result[key], str) for key in (
        "initial_response", "completion_response", "memory", "workspace_sha256", "memory_sha256",
    )):
        raise ValueError("durable-routing worker result has invalid text evidence")
    if not all(isinstance(result[key], list) for key in ("calls", "messages", "provider_requests", "todos")):
        raise ValueError("durable-routing worker result has invalid list evidence")
    if not all(
        isinstance(item, dict)
        for key in ("calls", "messages", "provider_requests", "todos") for item in result[key]
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
        return _record_recovered_result(
            bundle_path, outcomes, admissions, traces, definition, trial, result_path, started,
        )
    return _record_recovered_failure(
        bundle_path, outcomes, admissions, traces, trial, started,
        "provider_error" if _request_started(started) else "infrastructure_invalid",
        "worker ended after coordinator interruption without a complete result",
    )


def _record_recovered_result(
    bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, traces: Path,
    definition: DurableRoutingDefinition, trial, result_path: Path, started: Path,
) -> DurableRoutingProgress:
    """Preserve a completed worker result discovered after coordinator restart."""
    if not _request_started(started):
        return _record_recovered_failure(
            bundle_path, outcomes, admissions, traces, trial, started,
            "infrastructure_invalid", "recovered result lacks provider-boundary evidence",
        )
    bundle = StudyBundle.read_verified(bundle_path)
    try:
        payload = _read_worker_result(result_path, bundle.sha256, trial.sha256)
        result = DurableRoutingResult(
            initial_response=payload["initial_response"], completion_response=payload["completion_response"],
            calls=tuple(payload["calls"]), memory=payload["memory"],
            messages=tuple(payload["messages"]), provider_requests=tuple(payload["provider_requests"]),
            todos=tuple(payload["todos"]),
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
                  "todo_used": scored.todo_used, "todo_reconciled": scored.todo_reconciled,
                  "failed_predicates": list(scored.failed_predicates)},
    })
    outcomes.append(TrialOutcome(trial, "pass" if scored.full else "behavioral_failure", True, scored.full,
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
        identity = marker.get("process_identity")
        if not isinstance(pid, int) or pid < 1 or not isinstance(identity, dict):
            return False
        return _process_identity(pid) == identity
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _process_identity(pid: int) -> dict[str, str]:
    """Return Linux process identity strong enough to reject PID reuse on recovery."""
    stat = Path(f"/proc/{pid}/stat").read_text()
    closing = stat.rfind(")")
    fields = stat[closing + 2:].split()
    if closing < 0 or len(fields) <= 19:
        raise ValueError("process stat lacks a start time")
    command = Path(f"/proc/{pid}/cmdline").read_bytes()
    return {
        "start_time": fields[19],
        "command_sha256": hashlib.sha256(command).hexdigest(),
    }


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
