"""Sealed, one-episode coordinator for the current Assist execution-path pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Callable, Sequence

from .bundle import StudyBundle, atomic_write, canonical_json, digest
from .current_assist import CurrentAssistResult, result_payload
from .manifests import TaskManifest, read_conditions
from .records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from .report import write_static_report
from .runner import RunArtifacts, _artifact_digests, _exclusive_output_lock, _prepare_output, _valid_trace, _write_trace


@dataclass(frozen=True)
class CurrentPilotDefinition:
    """The one task and content-addressed bundle permitted by this pilot."""

    bundle: StudyBundle
    task: TaskManifest

    def validate(self, root: Path) -> None:
        """Reject an undeclared model, test, architecture, or setting change."""
        self.bundle.assert_complete()
        registration = self.bundle.registration
        if registration.get("kind") != "current_assist_pilot":
            raise ValueError("current Assist bundle has the wrong registration kind")
        if not isinstance(registration.get("git_tag"), str) or not registration["git_tag"]:
            raise ValueError("current Assist bundle requires an immutable git tag")
        if not isinstance(registration.get("max_turns"), int) or registration["max_turns"] < 1:
            raise ValueError("current Assist bundle requires a positive turn limit")
        if len(self.bundle.schedule) != 1 or set(self.bundle.fixtures) != {self.task.task_id}:
            raise ValueError("current Assist pilot requires exactly one scheduled fixture")
        if self.bundle.fixtures[self.task.task_id] != self.task.sha256:
            raise ValueError("current Assist fixture does not match its bundle")
        if self.bundle.schedule[0].task != self.task.task_id:
            raise ValueError("current Assist schedule names the wrong task")
        if set(self.bundle.conditions) != {self.bundle.schedule[0].condition}:
            raise ValueError("current Assist pilot requires exactly one neutral condition")
        conditions = read_conditions(root / "experiments" / "current-assist-pilot" / "conditions.json")
        if set(conditions) != set(self.bundle.conditions):
            raise ValueError("current Assist conditions do not match the bundle")
        for condition in conditions.values():
            if condition.system_suffix or condition.skill_overrides or condition.decoding_overrides:
                raise ValueError("current Assist pilot condition must be neutral")
        if self.bundle.conditions != {name: {"sha256": condition.sha256} for name, condition in conditions.items()}:
            raise ValueError("current Assist condition digest mismatch")
        model_settings = self.bundle.settings["model"]
        weights = model_settings.get("weights_sha256") if isinstance(model_settings, dict) else None
        if not _sha256(weights):
            raise ValueError("current Assist bundle requires a model weights SHA-256")
        if model_settings.get("reasoning") != {"enabled": False}:
            raise ValueError("current Assist pilot must pin reasoning off")
        if not isinstance(model_settings.get("timeout_seconds"), int) or model_settings["timeout_seconds"] < 1:
            raise ValueError("current Assist pilot requires a positive sealed timeout")
        if registration.get("implementation_sha256") != current_pilot_implementation_sha256(root):
            raise ValueError("current Assist bundle does not match the committed pilot implementation")


@dataclass(frozen=True)
class PilotProgress:
    """The explicit next action after one non-blocking coordinator invocation."""

    status: str
    artifacts: RunArtifacts | None = None


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def current_pilot_definition(root: Path) -> CurrentPilotDefinition:
    """Load the sole registered current-Assist smoke test."""
    task = TaskManifest.read(root / "fixtures" / "current-assist-read-before-edit.json")
    bundle = StudyBundle.read_verified(root / "experiments" / "current-assist-pilot" / "bundle.json")
    definition = CurrentPilotDefinition(bundle, task)
    definition.validate(root)
    return definition


def run_current_assist_pilot(
    root: Path,
    output: Path,
    *,
    workspace_root: Path,
    assist_python: Path,
    command_runner: CommandRunner | None = None,
) -> PilotProgress:
    """Make at most one admission attempt; never sleep, poll, or bypass the GPU gate."""
    root = root.resolve()
    output = output.resolve()
    workspace_root = workspace_root.resolve()
    assist_python = assist_python.resolve()
    definition = current_pilot_definition(root)
    _verify_git_tag(root, definition.bundle.registration["git_tag"], root / "experiments" / "current-assist-pilot" / "bundle.json")
    _prepare_output(output)
    with _exclusive_output_lock(output):
        return _run_current_assist_pilot(
            definition, root, output, workspace_root, assist_python,
            command_runner or (lambda command: _run_command(command, definition.bundle.settings["model"]["timeout_seconds"])),
        )


def current_worker_command(
    root: Path, workspace_root: Path, assist_python: Path, descriptor: Path, result: Path, request_started: Path
) -> list[str]:
    """Build the only model-capable command, nested under the workspace admission gate."""
    deployment_root = assist_python.parents[2] if len(assist_python.parents) > 2 else assist_python.parent
    return [
        str(workspace_root / "tools" / "agentic"), "resource", "run", "llm", "--",
        "sh", "-c", 'set -a; . "$1"; shift; exec "$@"', "sh",
        str(deployment_root / ".deploy.env"), "env", f"PYTHONPATH={root.resolve()}",
        str(assist_python), "-m", "harness.current_worker",
        "--descriptor", str(descriptor), "--result", str(result), "--request-started", str(request_started),
    ]


def current_pilot_implementation_sha256(root: Path) -> str:
    """Bind the complete imported harness package to the worker's sealed execution path."""
    modules = (
        "__init__.py", "archive.py", "bundle.py", "current_assist.py", "current_pilot.py",
        "current_worker.py", "episode.py", "invariants.py", "manifests.py", "oracles.py",
        "records.py", "report.py", "runner.py", "schedule.py",
    )
    return digest({
        f"harness/{name}": hashlib.sha256((root / "harness" / name).read_bytes()).hexdigest()
        for name in modules
    })


def _run_current_assist_pilot(
    definition: CurrentPilotDefinition, root: Path, output: Path, workspace_root: Path,
    assist_python: Path, command_runner: CommandRunner,
) -> PilotProgress:
    bundle_path = output / "bundle.json"
    _prepare_bundle(bundle_path, definition.bundle)
    bundle = StudyBundle.read_verified(bundle_path)
    admissions = AdmissionLog(output / "admissions.jsonl", bundle.sha256)
    outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256)
    trace_dir = output / "traces"
    if trace_dir.is_symlink():
        raise ValueError("trace directory cannot be a symlink")
    if trace_dir.exists() and not trace_dir.is_dir():
        raise ValueError("trace path must be a real directory")
    trial = bundle.schedule[0]
    request_started = output / f".{trial.sha256}.request-started"
    gate = ScheduledAdmission(bundle.schedule, admissions)
    completed = outcomes.read_verified()
    if gate.index == 1 and not completed:
        _write_trace(trace_dir / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "trace": [], "interrupted": True})
        outcomes.append(TrialOutcome(trial, "provider_error", _request_started(request_started), False, "coordinator interrupted after worker admission"))
        return PilotProgress("complete", _finalize(bundle_path, outcomes, admissions, trace_dir))
    if gate.current is None:
        return PilotProgress("complete", _finalize(bundle_path, outcomes, admissions, trace_dir))
    if completed:
        raise ValueError("current Assist pilot outcomes do not match its admission prefix")
    descriptor = output / f".{trial.sha256}.descriptor.json"
    result = output / f".{trial.sha256}.result.json"
    attempt = len([record for record in admissions.read_verified() if record["trial_sha256"] == trial.sha256]) + 1
    atomic_write(descriptor, canonical_json({
        "bundle_sha256": bundle.sha256, "trial_sha256": trial.sha256,
        "max_turns": bundle.registration["max_turns"], "task": definition.task.payload(),
    }) + b"\n")
    try:
        completed_process = command_runner(current_worker_command(root, workspace_root, assist_python, descriptor, result, request_started))
    except subprocess.TimeoutExpired:
        _write_trace(trace_dir / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "trace": [], "timeout": True})
        gate.record(AdmissionAttempt(trial, True, attempt, "worker started through GPU admission gate"))
        outcomes.append(TrialOutcome(trial, "timeout", _request_started(request_started), False, "worker exceeded the sealed timeout"))
        return PilotProgress("complete", _finalize(bundle_path, outcomes, admissions, trace_dir))
    if completed_process.returncode != 0:
        if _is_admission_denial(completed_process):
            gate.record(AdmissionAttempt(trial, False, attempt, "production reserved the GPU"))
            return PilotProgress("retry_in_10_minutes" if attempt <= 6 else "blocked_after_60_minutes")
        _write_trace(trace_dir / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "trace": [], "worker_error": _command_detail(completed_process)})
        gate.record(AdmissionAttempt(trial, True, attempt, "worker started through GPU admission gate"))
        outcomes.append(TrialOutcome(trial, "provider_error", _request_started(request_started), False, _command_detail(completed_process)))
        return PilotProgress("complete", _finalize(bundle_path, outcomes, admissions, trace_dir))
    gate.record(AdmissionAttempt(trial, True, attempt, "worker started through GPU admission gate"))
    try:
        worker = _read_worker_result(result, bundle.sha256, trial.sha256)
        current_result = CurrentAssistResult(**worker["result"])
        score = _evaluate_current(definition.task, current_result)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        _write_trace(trace_dir / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "trace": [], "worker_error": str(error)[:500]})
        outcomes.append(TrialOutcome(trial, "provider_error", True, False, "worker result was malformed"))
        return PilotProgress("complete", _finalize(bundle_path, outcomes, admissions, trace_dir))
    _write_trace(trace_dir / f"{trial.sha256}.json", {
        "trial_sha256": trial.sha256, "trace": current_result.messages, "result": result_payload(current_result),
    })
    outcomes.append(TrialOutcome(trial, "pass" if score.passed else "artifact_failure", True, score.passed, score.detail))
    return PilotProgress("complete", _finalize(bundle_path, outcomes, admissions, trace_dir))


@dataclass(frozen=True)
class _Score:
    passed: bool
    detail: str


def _evaluate_current(task: TaskManifest, result: CurrentAssistResult) -> _Score:
    """Apply the existing read-before-edit predicate to a Deep Agents message trace."""
    if task.oracle.get("kind") != "read_before_edit":
        raise ValueError("current Assist pilot supports only read_before_edit")
    path, expected = task.oracle.get("path"), task.oracle.get("expected_content")
    if result.files.get(path) != expected:
        return _Score(False, "final virtual file does not match the requested artifact")
    read_seen = False
    for message in result.messages:
        for call in message.get("tool_calls", []):
            if call.get("name") == "read_file" and call.get("args", {}).get("path") == path:
                read_seen = True
            if call.get("name") == "write_file" and call.get("args", {}).get("path") == path:
                if read_seen:
                    return _Score(True, "target artifact was read, then written correctly")
                return _Score(False, "target file was written before it was read")
    return _Score(False, "trace does not show a read followed by a write")


def _prepare_bundle(path: Path, bundle: StudyBundle) -> None:
    if path.exists():
        if StudyBundle.read_verified(path).sha256 != bundle.sha256:
            raise ValueError("existing output belongs to a different bundle")
        return
    if any(item.name != ".runner.lock" for item in path.parent.iterdir()):
        raise ValueError("existing current Assist output lacks a bundle")
    bundle.write(path)


def _finalize(bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, trace_dir: Path) -> RunArtifacts:
    bundle = StudyBundle.read_verified(bundle_path)
    report = bundle_path.parent / "report.json"
    artifacts = _artifact_digests(bundle, trace_dir, report) if report.exists() else None
    if outcomes.path.with_suffix(".jsonl.seal").exists():
        if artifacts is None:
            raise ValueError("sealed current Assist output lacks a report")
        outcomes.verify_finalized(bundle.schedule, admissions, artifacts)
    else:
        write_static_report(bundle, outcomes, report)
        outcomes.finalize(bundle.schedule, admissions, _artifact_digests(bundle, trace_dir, report))
    return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, trace_dir)


def _read_worker_result(path: Path, bundle_sha256: str, trial_sha256: str) -> dict[str, object]:
    if path.is_symlink():
        raise ValueError("current Assist worker result cannot be a symlink")
    value = json.loads(path.read_text())
    if value.get("bundle_sha256") != bundle_sha256 or value.get("trial_sha256") != trial_sha256:
        raise ValueError("current Assist worker result belongs to another trial")
    if not isinstance(value.get("result"), dict):
        raise ValueError("current Assist worker result is malformed")
    return value


def _request_started(path: Path) -> bool:
    if path.is_symlink():
        raise ValueError("current Assist request marker cannot be a symlink")
    return path.read_bytes() == b"model-invoke-started\n" if path.exists() else False


def _verify_git_tag(root: Path, tag: str, bundle_path: Path) -> None:
    resolved = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", f"{tag}^{{commit}}"], capture_output=True, text=True)
    if resolved.returncode:
        raise ValueError("current Assist pilot tag is not available locally")
    content = subprocess.run(["git", "-C", str(root), "show", f"{tag}:{bundle_path.relative_to(root)}"], capture_output=True)
    if content.returncode or content.stdout != bundle_path.read_bytes():
        raise ValueError("current Assist pilot tag does not contain this sealed bundle")


def _run_command(command: Sequence[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout_seconds)


def _is_admission_denial(result: subprocess.CompletedProcess[str]) -> bool:
    return "production is busy" in ((result.stderr or "") + (result.stdout or ""))


def _command_detail(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip().replace("\n", " ")
    return text[:500] or f"worker exited {result.returncode}"


def _sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)
