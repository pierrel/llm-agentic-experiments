"""Seal and run a bounded context-length development sweep through shared admission."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import subprocess
from typing import Any

from harness.archive import archive_scripted_run
from harness.bundle import StudyBundle, Trial, atomic_write, canonical_json, digest
from harness.manifests import TaskManifest
from harness.records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from harness.report import write_static_report
from harness.runner import RunArtifacts, _artifact_digests, _exclusive_output_lock, _prepare_output, _valid_trace, _write_trace


STUDY = "context-length-dev-v2"
MODEL_WEIGHTS = "d797b531c527bea28a04fdb326515c43114f798a4fa2a5c1c0e0cffaeaa6fd09"


@dataclass(frozen=True)
class ContextCondition:
    """One sealed amount of inert declarative context before the procedure."""

    condition_id: str
    filler_lines: int

    @property
    def sha256(self) -> str:
        return digest({"condition_id": self.condition_id, "filler_lines": self.filler_lines})


def _conditions(path: Path) -> dict[str, ContextCondition]:
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict) or not raw:
        raise ValueError("context-length conditions must be a nonempty object")
    result: dict[str, ContextCondition] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not isinstance(value, dict) or set(value) != {"filler_lines"}:
            raise ValueError("context-length condition shape is invalid")
        count = value["filler_lines"]
        if not isinstance(count, int) or count < 0:
            raise ValueError("context-length filler_lines must be nonnegative")
        result[name] = ContextCondition(name, count)
    return result


def _filler(lines: int) -> str:
    """Return inert synthetic facts with no instruction, case, or file vocabulary."""
    return "".join(
        f"Item {index:05d} described an amber horizon, a quiet tide, and a basalt sample with a measured grain pattern.\n"
        for index in range(1, lines + 1)
    )


def _task(root: Path) -> TaskManifest:
    return TaskManifest.read(root / "fixtures" / "context-length-complex-case-handoff.json")


def _settings(source_commit: str, assist_revision: str) -> dict[str, Any]:
    model = {
        "provider": "local OpenAI-compatible llama.cpp endpoint",
        "model_id": "Qwen_Qwen3.6-27B-Q4_K_M.gguf",
        "weights_sha256": MODEL_WEIGHTS,
        "reasoning": {"enabled": False},
        "temperature": 0.1,
        "max_tokens": 1200,
        "server_context_tokens": 131072,
        "timeout_seconds": 600,
        "cache_policy": "provider-default; no client replay",
    }
    architecture = {
        "id": "deepagents-langchain-tool-loop",
        "deepagents": "0.6.1",
        "langchain": "1.3.1",
        "langgraph": "1.2.0",
        "assist_revision": assist_revision,
        "source_commit": source_commit,
        "backend": "fresh private virtual FilesystemBackend",
        "tools": "Deep Agents default filesystem, TODO, and general-purpose task capability profile; no caller-provided tools or subagents",
        "recursion_limit": 20,
    }
    return {"model": model, "harness_architecture": architecture}


def _source_hash(root: Path) -> str:
    paths = list(sorted((root / "harness").glob("*.py"))) + list(sorted((root / "studies" / "context_length").glob("*.py")))
    return digest({str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})


def seal(root: Path, *, source_commit: str, assist_revision: str) -> StudyBundle:
    """Create the committed bundle before any model command can be admitted."""
    task = _task(root)
    conditions = _conditions(root / "experiments" / STUDY / "conditions.json")
    settings = _settings(source_commit, assist_revision)
    order = list(conditions)
    random.Random(20260826).shuffle(order)
    schedule = tuple(Trial(task.task_id, 1, condition, 7000 + index) for index, condition in enumerate(order))
    registration = {
        "kind": "context_length_development",
        "hypothesis_seed": "seeds/2026-08-24-context-length-instruction-following.md",
        "source_commit": source_commit,
        "registration_tag": "context-length-dev-v2",
        "max_turns": 20,
        "primary_outcome": "procedure-plus-artifact case-handoff success",
        "analysis": "compare all scheduled reason-coded outcomes and provider-reported first-request input tokens",
        "development_series": "v2 higher-complexity handoff after the flat v1 screen",
        "randomization_seed": 20260826,
        "position_balance": "adjust_for_position",
        "missingness": "denied admission retries the same trial; every admitted terminal outcome remains",
        "implementation_sha256": _source_hash(root),
    }
    bundle = StudyBundle(
        study_id=STUDY,
        registration=registration,
        conditions={name: {"sha256": item.sha256} for name, item in conditions.items()},
        fixtures={task.task_id: task.sha256},
        tool_schemas={"deepagents_filesystem": {"mode": "default filesystem and TODO tools", "external_tools": []}},
        schedule=schedule,
        model={"id": "Qwen_Qwen3.6-27B-Q4_K_M.gguf", "revision": "2026-05-01", "configuration_sha256": digest(settings["model"])},
        harness_architecture={"id": "deepagents-langchain-tool-loop", "revision": "v1", "configuration_sha256": digest(settings["harness_architecture"])},
        settings=settings,
        runner_revision="context-length-runner-v1",
        analysis_revision="context-length-summary-v1",
    )
    bundle.write(root / "experiments" / STUDY / "bundle.json")
    return bundle


def _definition(root: Path) -> tuple[StudyBundle, TaskManifest, dict[str, ContextCondition]]:
    bundle = StudyBundle.read_verified(root / "experiments" / STUDY / "bundle.json")
    task = _task(root)
    conditions = _conditions(root / "experiments" / STUDY / "conditions.json")
    if bundle.study_id != STUDY or bundle.fixtures != {task.task_id: task.sha256}:
        raise ValueError("context-length bundle fixture does not match")
    if bundle.conditions != {name: {"sha256": item.sha256} for name, item in conditions.items()}:
        raise ValueError("context-length bundle conditions do not match")
    if bundle.registration.get("implementation_sha256") != _source_hash(root):
        raise ValueError("context-length bundle does not match runner implementation")
    if bundle.settings["model"].get("weights_sha256") != MODEL_WEIGHTS:
        raise ValueError("context-length bundle weights do not match the pinned model")
    tag = bundle.registration.get("registration_tag")
    if not isinstance(tag, str) or not tag:
        raise ValueError("context-length bundle requires a registration tag")
    tagged = subprocess.run(
        ["git", "-C", str(root), "show", f"{tag}:experiments/{STUDY}/bundle.json"],
        capture_output=True,
    )
    if tagged.returncode or tagged.stdout != (root / "experiments" / STUDY / "bundle.json").read_bytes():
        raise ValueError("context-length registration tag does not contain this bundle")
    return bundle, task, conditions


def _worker_command(
    root: Path, workspace_root: Path, assist_source: Path, assist_python: Path, descriptor: Path, result: Path, marker: Path
) -> list[str]:
    """Build the sole model-capable command, nested beneath the shared gate."""
    return [
        str(workspace_root / "tools" / "agentic"), "resource", "run", "llm", "--",
        "sh", "-c", 'set -a; . "$1"; shift; exec "$@"', "sh",
        str(workspace_root / "assist" / ".deploy.env"), "env", f"PYTHONPATH={root}:{assist_source}",
        str(assist_python), "-m", "studies.context_length.worker",
        "--descriptor", str(descriptor), "--result", str(result), "--request-started", str(marker),
    ]


def _score(task: TaskManifest, payload: dict[str, Any]) -> tuple[bool, str, int | None]:
    oracle = task.oracle
    files = payload.get("files")
    messages = payload.get("messages")
    if not isinstance(files, dict) or not isinstance(messages, list):
        return False, "worker result is malformed", None
    output_path = oracle["output_path"]
    output = files.get(output_path)
    if not isinstance(output, str):
        return False, "required handoff was not written", _first_input_tokens(messages)
    if any(files.get(path) != content for path, content in task.initial_files.items()):
        return False, "a source record changed", _first_input_tokens(messages)
    if any(phrase.lower() not in output.lower() for phrase in oracle["required_phrases"]):
        return False, "handoff omitted a required fact or section", _first_input_tokens(messages)
    if oracle["uncertainty_phrase"].lower() not in output.lower():
        return False, "handoff did not preserve the unresolved discrepancy", _first_input_tokens(messages)
    reads: set[str] = set()
    saw_inventory = False
    wrote = False
    for message in messages:
        for call in message.get("tool_calls", []) if isinstance(message, dict) else []:
            name, args = call.get("name"), call.get("args", {})
            path = args.get("file_path", args.get("path")) if isinstance(args, dict) else None
            if name in {"glob", "ls"}:
                saw_inventory = True
            if name == "read_file" and isinstance(path, str):
                if not saw_inventory:
                    return False, "a read occurred before workspace inventory", _first_input_tokens(messages)
                reads.add(path.lstrip("/"))
            if name in {"write_file", "edit_file"}:
                if not saw_inventory:
                    return False, "a write occurred before workspace inventory", _first_input_tokens(messages)
                wrote = True
                if not set(oracle["required_reads"]).issubset(reads):
                    return False, "a write occurred before all required reads", _first_input_tokens(messages)
    if not saw_inventory or not wrote or not set(oracle["required_reads"]).issubset(reads):
        return False, "trace lacks required inventory, reads, or write", _first_input_tokens(messages)
    return True, "handoff and ordered procedure both passed", _first_input_tokens(messages)


def _first_input_tokens(messages: list[dict[str, Any]]) -> int | None:
    for message in messages:
        usage = message.get("usage_metadata", {}) if isinstance(message, dict) else {}
        value = usage.get("input_tokens") if isinstance(usage, dict) else None
        if isinstance(value, int):
            return value
    return None


def run(root: Path, output: Path, *, workspace_root: Path, assist_source: Path, assist_python: Path) -> RunArtifacts:
    """Run each fresh registered episode once, with a separate admission gate."""
    root = root.resolve()
    bundle, task, conditions = _definition(root)
    _prepare_output(output)
    with _exclusive_output_lock(output):
        bundle_path = output / "bundle.json"
        if bundle_path.exists():
            if StudyBundle.read_verified(bundle_path).sha256 != bundle.sha256:
                raise ValueError("output belongs to a different bundle")
        else:
            bundle.write(bundle_path)
        admissions = AdmissionLog(output / "admissions.jsonl", bundle.sha256)
        outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256)
        trace_dir = output / "traces"
        if trace_dir.is_symlink() or (trace_dir.exists() and not trace_dir.is_dir()):
            raise ValueError("context-length traces must be a real directory")
        trace_dir.mkdir(mode=0o700, exist_ok=True)
        completed = {item["trial_sha256"] for item in outcomes.read_verified()}
        gate = ScheduledAdmission(bundle.schedule, admissions)
        _recover_interrupted_admission(bundle, gate, outcomes, trace_dir, output)
        completed = {item["trial_sha256"] for item in outcomes.read_verified()}
        while gate.current is not None:
            trial = gate.current
            if trial.sha256 in completed:
                raise ValueError("completed outcome is not an admission prefix")
            condition = conditions[trial.condition]
            descriptor = output / f".{trial.sha256}.descriptor.json"
            result_path = output / f".{trial.sha256}.result.json"
            marker = output / f".{trial.sha256}.request-started"
            atomic_write(descriptor, canonical_json({
                "bundle_sha256": bundle.sha256, "trial_sha256": trial.sha256,
                "system_prompt": _filler(condition.filler_lines) + task.system_prompt,
                "user_prompt": task.user_prompt, "files": task.initial_files,
                "max_turns": bundle.registration["max_turns"], "temperature": task.decoding["temperature"],
                "max_tokens": task.decoding["max_tokens"],
                "runtime": {
                    "assist_revision": bundle.settings["harness_architecture"]["assist_revision"],
                    "deepagents": bundle.settings["harness_architecture"]["deepagents"],
                    "langchain": bundle.settings["harness_architecture"]["langchain"],
                    "langgraph": bundle.settings["harness_architecture"]["langgraph"],
                    "model_id": bundle.settings["model"]["model_id"],
                    "reasoning_enabled": bundle.settings["model"]["reasoning"]["enabled"],
                },
            }) + b"\n")
            attempt = len([entry for entry in admissions.read_verified() if entry["trial_sha256"] == trial.sha256]) + 1
            try:
                process = subprocess.run(_worker_command(root, workspace_root, assist_source, assist_python, descriptor, result_path, marker), text=True, capture_output=True, timeout=bundle.settings["model"]["timeout_seconds"])
            except subprocess.TimeoutExpired:
                gate.record(AdmissionAttempt(trial, True, attempt, "worker entered shared admission"))
                _write_trace(trace_dir / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "timeout": True, "trace": []})
                outcomes.append(TrialOutcome(trial, "timeout", marker.exists(), False, "sealed worker timeout"))
                continue
            detail = (process.stderr or process.stdout or "").strip().replace("\n", " ")[-2000:]
            if process.returncode and not marker.exists():
                gate.record(AdmissionAttempt(trial, False, attempt, detail or "worker failed before model invocation"))
                return RunArtifacts(bundle_path, admissions.path, outcomes.path, output / "report.json", trace_dir)
            gate.record(AdmissionAttempt(trial, True, attempt, "worker entered shared admission"))
            if process.returncode:
                _write_trace(trace_dir / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "worker_error": detail, "trace": []})
                outcome = "provider_error" if marker.exists() else "infrastructure_invalid"
                outcomes.append(TrialOutcome(trial, outcome, marker.exists(), False, detail or "worker failed"))
                continue
            try:
                payload = json.loads(result_path.read_text())
                if payload.get("bundle_sha256") != bundle.sha256 or payload.get("trial_sha256") != trial.sha256:
                    raise ValueError("worker result identity mismatch")
                passed, score_detail, prompt_tokens = _score(task, payload)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                payload, passed, score_detail, prompt_tokens = {"trace": []}, False, f"malformed worker result: {error}", None
            _write_trace(trace_dir / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "trace": payload.get("messages", []), "result": {"files": payload.get("files", {}), "first_prompt_tokens": prompt_tokens}})
            outcomes.append(TrialOutcome(trial, "pass" if passed else "artifact_failure", marker.exists(), passed, score_detail))
        report = output / "report.json"
        write_static_report(bundle, outcomes, report)
        metadata_path = output / "trial-metadata.json"
        atomic_write(metadata_path, canonical_json(_trial_metadata(bundle, conditions, outcomes, trace_dir)) + b"\n")
        artifacts = _artifact_digests(bundle, trace_dir, report)
        outcomes.finalize(bundle.schedule, admissions, artifacts)
        return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, trace_dir)


def _recover_interrupted_admission(
    bundle: StudyBundle, gate: ScheduledAdmission, outcomes: RecordChain, trace_dir: Path, output: Path
) -> None:
    """Account for the sole admitted-but-unrecorded episode before resuming."""
    completed = outcomes.read_verified()
    if gate.index == len(completed):
        return
    if gate.index != len(completed) + 1:
        raise ValueError("admission history is not at most one trial ahead of outcomes")
    trial = bundle.schedule[len(completed)]
    trace_path = trace_dir / f"{trial.sha256}.json"
    if trace_path.exists():
        if trace_path.is_symlink() or not _valid_trace(trace_path, trial.sha256):
            raise ValueError("interrupted trial trace is malformed")
    else:
        _write_trace(trace_path, {"trial_sha256": trial.sha256, "trace": [], "interrupted": True})
    marker = output / f".{trial.sha256}.request-started"
    outcomes.append(TrialOutcome(
        trial,
        "provider_error" if marker.exists() else "infrastructure_invalid",
        marker.exists(),
        False,
        "worker was interrupted after shared admission before recording an outcome",
    ))


def _trial_metadata(
    bundle: StudyBundle, conditions: dict[str, ContextCondition], outcomes: RecordChain, trace_dir: Path
) -> list[dict[str, Any]]:
    """Derive durable dose metadata from all sealed traces, including resumed trials."""
    outcome_by_trial = {record["trial_sha256"]: record for record in outcomes.read_verified()}
    metadata: list[dict[str, Any]] = []
    for trial in bundle.schedule:
        trace = json.loads((trace_dir / f"{trial.sha256}.json").read_text())
        result = trace.get("result", {}) if isinstance(trace, dict) else {}
        tokens = result.get("first_prompt_tokens") if isinstance(result, dict) else None
        outcome = outcome_by_trial[trial.sha256]
        metadata.append({
            "trial": trial.__dict__,
            "filler_lines": conditions[trial.condition].filler_lines,
            "first_prompt_tokens": tokens if isinstance(tokens, int) else None,
            "score": outcome["detail"],
        })
    return metadata


def archive(artifacts: RunArtifacts, destination: Path) -> None:
    """Archive the standard capsule plus token-dose metadata without raw traces."""
    capsule = archive_scripted_run(artifacts, destination)
    source_metadata = artifacts.bundle.parent / "trial-metadata.json"
    atomic_write(destination / "trial-metadata.json", source_metadata.read_bytes())
    run = json.loads(capsule.record.read_text())
    run["trial_metadata_sha256"] = hashlib.sha256((destination / "trial-metadata.json").read_bytes()).hexdigest()
    run.pop("record_sha256")
    atomic_write(capsule.record, canonical_json(run | {"record_sha256": digest(run)}) + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seal", "run", "archive"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--assist-revision")
    parser.add_argument("--workspace-root", type=Path, default=Path("/home/pierre/src/agentic"))
    parser.add_argument("--assist-source", type=Path)
    parser.add_argument("--assist-python", type=Path, default=Path("/home/pierre/deploy/assist/code/.venv/bin/python"))
    args = parser.parse_args()
    if args.command == "seal":
        if not args.source_commit or not args.assist_revision:
            raise SystemExit("seal requires --source-commit and --assist-revision")
        seal(args.root, source_commit=args.source_commit, assist_revision=args.assist_revision)
    elif args.command == "run":
        if args.output is None or args.assist_source is None:
            raise SystemExit("run requires --output and --assist-source")
        run(args.root, args.output, workspace_root=args.workspace_root, assist_source=args.assist_source, assist_python=args.assist_python)
    else:
        if args.output is None or args.archive is None:
            raise SystemExit("archive requires --output and --archive")
        archive(RunArtifacts(args.output / "bundle.json", args.output / "admissions.jsonl", args.output / "outcomes.jsonl", args.output / "report.json", args.output / "traces"), args.archive)


if __name__ == "__main__":
    main()
