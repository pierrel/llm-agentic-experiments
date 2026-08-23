"""Execute sealed scripted episodes without a model or external capability."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import re
from typing import Callable

from .bundle import StudyBundle, canonical_json
from .episode import Episode, EpisodeResult, ProviderReply, ScriptedProvider, ToolCall, script_sha256
from .manifests import StudyDefinition
from .oracles import evaluate
from .records import (
    AdmissionAttempt,
    AdmissionLog,
    RecordChain,
    ScheduledAdmission,
    TrialOutcome,
    recover_torn_record_tail,
)
from .report import write_static_report

AdmissionPolicy = Callable[[str, int], tuple[bool, str]]


@dataclass(frozen=True)
class RunArtifacts:
    """Local artifact paths from one fully accounted scripted schedule."""

    bundle: Path
    admissions: Path
    outcomes: Path
    report: Path
    traces: Path


def run_scripted_study(
    definition: StudyDefinition,
    output: Path,
    script: tuple[ProviderReply, ...],
    admission_policy: AdmissionPolicy,
    *,
    max_admission_attempts: int = 10,
) -> RunArtifacts:
    """Run every sealed episode with a fake provider and fresh fixture state.

    This runner is intentionally incapable of calling a model.  Its admission
    log exercises the accounting protocol only; it records no model request.
    """
    definition = deepcopy(definition)
    script = tuple(
        ProviderReply(
            content=reply.content,
            tool_calls=tuple(ToolCall(call.name, deepcopy(call.arguments)) for call in reply.tool_calls),
            final=reply.final,
        )
        for reply in script
    )
    definition.validate()
    if definition.bundle.registration.get("script_sha256") != script_sha256(script):
        raise ValueError("scripted provider behavior differs from the sealed bundle")
    max_turns = definition.bundle.registration.get("max_turns")
    if not isinstance(max_turns, int) or max_turns < 1:
        raise ValueError("sealed bundle requires a positive max_turns")
    _prepare_output(output)
    with _exclusive_output_lock(output):
        return _run_scripted_study(
            definition, output, script, admission_policy, max_turns, max_admission_attempts
        )


def _run_scripted_study(
    definition: StudyDefinition,
    output: Path,
    script: tuple[ProviderReply, ...],
    admission_policy: AdmissionPolicy,
    max_turns: int,
    max_admission_attempts: int,
) -> RunArtifacts:
    """Run under one output-directory lock so chains have a single writer."""
    bundle_path = output / "bundle.json"
    for path in (bundle_path, output / "admissions.jsonl", output / "outcomes.jsonl", output / "report.json"):
        if path.is_symlink():
            raise ValueError(f"scripted artifact cannot be a symlink: {path.name}")
    outcome_seal = (output / "outcomes.jsonl").with_suffix(".jsonl.seal")
    if not outcome_seal.exists():
        recover_torn_record_tail(output / "admissions.jsonl")
        recover_torn_record_tail(output / "outcomes.jsonl")
    if bundle_path.exists():
        bundle = StudyBundle.read_verified(bundle_path)
        if bundle.sha256 != definition.bundle.sha256:
            raise ValueError("existing output belongs to a different bundle")
    else:
        if any(path.name != ".runner.lock" for path in output.iterdir()):
            raise ValueError("existing scripted output lacks a bundle")
        definition.bundle.write(bundle_path)
        bundle = StudyBundle.read_verified(bundle_path)
    admissions = AdmissionLog(output / "admissions.jsonl", bundle.sha256)
    gate = ScheduledAdmission(bundle.schedule, admissions)
    outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256)
    trace_dir = output / "traces"
    if trace_dir.is_symlink():
        raise ValueError("trace directory cannot be a symlink")
    if trace_dir.exists() and not trace_dir.is_dir():
        raise ValueError("trace path must be a real directory")
    _discard_stale_trace_temps(trace_dir)
    _recover_interrupted_admission(bundle, outcomes, gate, trace_dir)
    completed = outcomes.read_verified()
    _assert_completed_prefix(bundle, completed, gate.index)
    if gate.current is None:
        return _finalize_or_verify(bundle_path, outcomes, admissions, trace_dir)
    admission_attempts = {
        trial_sha256: sum(record["trial_sha256"] == trial_sha256 for record in admissions.read_verified())
        for trial_sha256 in (trial.sha256 for trial in bundle.schedule)
    }
    while gate.current is not None:
        trial = gate.current
        admitted = False
        previous_attempts = admission_attempts[trial.sha256]
        for attempt in range(previous_attempts + 1, previous_attempts + max_admission_attempts + 1):
            allowed, detail = admission_policy(trial.sha256, attempt)
            if not isinstance(allowed, bool) or not isinstance(detail, str):
                raise ValueError("admission policy must return a boolean and text detail")
            gate.record(AdmissionAttempt(trial, allowed, attempt, detail))
            admission_attempts[trial.sha256] += 1
            if allowed:
                admitted = True
                break
        if not admitted:
            raise RuntimeError(f"scripted admission never allowed trial: {trial.id}")
        task = definition.tasks[trial.task]
        condition = definition.conditions[trial.condition]
        inputs = definition.episode_inputs(task, condition)
        episode = Episode(
            system_prompt=inputs["system_prompt"],
            user_prompt=inputs["user_prompt"],
            decoding=inputs["decoding"],
            workspace=inputs["workspace"],
            provider=ScriptedProvider(script),
            max_turns=max_turns,
            episode_id=trial.sha256,
        )
        result = episode.run()
        _assert_first_request(definition, trial.sha256, task.task_id, condition.condition_id, result)
        trace_path = trace_dir / f"{trial.sha256}.json"
        if trace_path.exists():
            raise ValueError(f"trace already exists for unrecorded trial: {trial.id}")
        _write_trace(trace_path, {"trial_sha256": trial.sha256, "trace": result.trace})
        if result.provider_error:
            outcome = TrialOutcome(trial, "provider_error", False, False, result.provider_error)
        elif result.invalid_tool_call:
            outcome = TrialOutcome(trial, "invalid_tool_call", False, False, "virtual tool call was invalid")
        elif result.loop_exhausted:
            outcome = TrialOutcome(trial, "loop_exhausted", False, False, "scripted loop budget exhausted")
        else:
            score = evaluate(task, result)
            outcome = TrialOutcome(
                trial,
                "pass" if score.passed else "artifact_failure",
                False,
                score.passed,
                score.detail,
            )
        outcomes.append(outcome)
    return _finalize_or_verify(bundle_path, outcomes, admissions, trace_dir)


def _assert_completed_prefix(
    bundle: StudyBundle, completed: list[dict[str, object]], admitted_count: int
) -> None:
    if len(completed) != admitted_count:
        raise ValueError("admitted and completed episode counts differ; cannot safely resume")
    expected = [trial.sha256 for trial in bundle.schedule[: len(completed)]]
    actual = [record["trial_sha256"] for record in completed]
    if actual != expected:
        raise ValueError("completed records are not a prefix of the sealed schedule")


def _recover_interrupted_admission(
    bundle: StudyBundle, outcomes: RecordChain, gate: ScheduledAdmission, trace_dir: Path
) -> None:
    """Account for the sole recoverable crash point in the no-model runner.

    A scripted episode cannot have issued a model request. If an earlier process
    was admitted but died before writing its outcome, record that episode as an
    infrastructure-invalid failure instead of silently rerunning it.
    """
    completed = outcomes.read_verified()
    if gate.index == len(completed):
        return
    if gate.index != len(completed) + 1:
        raise ValueError("admission history is too far ahead of completed scripted episodes")
    trial = bundle.schedule[len(completed)]
    trace_path = trace_dir / f"{trial.sha256}.json"
    if trace_path.exists():
        if not _valid_trace(trace_path, trial.sha256):
            raise ValueError("interrupted trace is malformed or belongs to another trial")
    else:
        _write_trace(trace_path, {"trial_sha256": trial.sha256, "trace": [], "interrupted": True})
    outcomes.append(
        TrialOutcome(
            trial,
            "infrastructure_invalid",
            False,
            False,
            "scripted episode interrupted after admission before an outcome was recorded",
        )
    )


def _finalize_or_verify(
    bundle_path: Path, outcomes: RecordChain, admissions: AdmissionLog, trace_dir: Path
) -> RunArtifacts:
    bundle = StudyBundle.read_verified(bundle_path)
    report = bundle_path.parent / "report.json"
    seal_path = outcomes.path.with_suffix(outcomes.path.suffix + ".seal")
    if seal_path.exists():
        outcomes.verify_finalized(bundle.schedule, admissions, _artifact_digests(bundle, trace_dir, report))
        return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, trace_dir)
    # Condition IDs are deliberately opaque and are not human treatment labels.
    write_static_report(bundle, outcomes, report)
    artifacts = _artifact_digests(bundle, trace_dir, report)
    outcomes.finalize(bundle.schedule, admissions, artifacts)
    outcomes.verify_finalized(bundle.schedule, admissions, artifacts)
    return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, trace_dir)


def _artifact_digests(bundle: StudyBundle, trace_dir: Path, report: Path) -> dict[str, str]:
    expected_traces = {f"traces/{trial.sha256}.json" for trial in bundle.schedule}
    actual_traces = {f"traces/{path.name}" for path in trace_dir.iterdir()} if trace_dir.exists() else set()
    if actual_traces != expected_traces:
        raise ValueError("trace artifacts do not cover exactly the sealed schedule")
    paths = {"report.json": report} | {
        f"traces/{trial.sha256}.json": trace_dir / f"{trial.sha256}.json" for trial in bundle.schedule
    }
    if any(path.is_symlink() for path in paths.values()):
        raise ValueError("sealed artifact cannot be a symlink")
    for trial in bundle.schedule:
        if not _valid_trace(trace_dir / f"{trial.sha256}.json", trial.sha256):
            raise ValueError("trace artifact is malformed or belongs to another trial")
    try:
        return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sorted(paths.items())}
    except FileNotFoundError as error:
        raise ValueError("sealed artifact is missing") from error


_TRACE_TEMP_PATTERN = re.compile(r"\.[0-9a-f]{64}\.json\.[0-9]+\.tmp")


def _discard_stale_trace_temps(trace_dir: Path) -> None:
    """Discard only interrupted atomic-write temps from the private trace directory."""
    if not trace_dir.exists():
        return
    for path in trace_dir.iterdir():
        if not _TRACE_TEMP_PATTERN.fullmatch(path.name):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError("trace temporary artifact must be a regular file")
        path.unlink()


@contextmanager
def _exclusive_output_lock(output: Path):
    """Serialize one local writer without retaining a lock after a crash."""
    with (output / ".runner.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _prepare_output(output: Path) -> None:
    """Create or accept only a private real directory for local artifacts."""
    try:
        output.mkdir(mode=0o700, parents=True)
    except FileExistsError:
        pass
    if output.is_symlink() or not output.is_dir():
        raise ValueError("scripted output must be a real directory")
    info = output.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("scripted output directory must be private to this user")


def _write_trace(path: Path, payload: dict[str, object]) -> None:
    """Atomically publish one complete trace inside the private output directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(canonical_json(payload) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _valid_trace(path: Path, trial_sha256: str) -> bool:
    try:
        import json

        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    return isinstance(value, dict) and value.get("trial_sha256") == trial_sha256 and isinstance(value.get("trace"), list)


def _assert_first_request(
    definition: StudyDefinition, trial_sha256: str, task_id: str, condition_id: str, result: EpisodeResult
) -> None:
    if not result.trace:
        raise ValueError("episode emitted no provider request")
    actual = result.trace[0]["request"]
    expected = definition.initial_request(definition.tasks[task_id], definition.conditions[condition_id]) | {
        "request_id": f"{trial_sha256}:t1"
    }
    if canonical_json(actual) != canonical_json(expected):
        raise ValueError("first provider request diverged from the sealed manifest")
