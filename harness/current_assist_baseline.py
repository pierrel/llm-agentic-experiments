"""Register and execute the one sealed current-Assist baseline episode."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from .bundle import StudyBundle, Trial, canonical_json
from .records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome


STUDY_ID = "current-assist-baseline-v4"
PROMPT = (
    'Please add the exact line "Checked by the experiment." to today\'s note, '
    "preserving what is already there."
)
RUNNER_REVISION = "current-assist-baseline-runner-v4"
ANALYSIS_REVISION = "current-assist-baseline-oracle-v1"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def study_directory(repo: Path) -> Path:
    return repo / "experiments" / STUDY_ID


def make_bundle(repo: Path) -> StudyBundle:
    """Construct the sole pre-registered episode from committed inputs."""
    fixture = study_directory(repo) / "fixtures" / "todays-note.txt"
    return StudyBundle(
        study_id=STUDY_ID,
        registration={
            "kind": "baseline",
            "hypothesis": "The current Assist baseline can preserve and update an isolated note.",
            "experimental_unit": "one fresh Deep Agents episode",
            "sample_size": 1,
            "primary_outcome": "preserved fixture plus exactly one requested line",
            "secondary_observation": "read_file precedes edit_file or write_file when a mutation occurs",
            "prompt": PROMPT,
            "missingness": "admission denial retries the same trial; every post-request result is retained",
            "position_balance": "adjust_for_position",
        },
        conditions={"current_assist": {"change": "none"}},
        model={
            "family": "Qwen3.6-27B",
            "quantization": "Q4_K_M",
            "selection": "current Assist local endpoint auto-discovery",
        },
        harness_architecture={
            "framework": "deepagents.create_deep_agent",
            "loop": "ReAct-style tool loop",
            "backend": "isolated virtual FilesystemBackend",
        },
        settings={
            "model": {"temperature": 0.1, "reasoning": {"enabled": False}},
            "episode": {"recursion_limit": 12},
        },
        fixtures={"note-edit": _sha256_file(fixture)},
        tool_schemas={
            "source": "Deep Agents default filesystem tools at the pinned runner environment",
            "required_capabilities": ["read_file", "edit_file", "write_file"],
        },
        schedule=(Trial("note-edit", 1, "current_assist", 1),),
        runner_revision=RUNNER_REVISION,
        analysis_revision=ANALYSIS_REVISION,
    )


def register(repo: Path) -> Path:
    """Write the content-addressed registration, refusing an overwrite."""
    path = study_directory(repo) / "bundle.json"
    bundle = make_bundle(repo)
    if path.exists():
        if StudyBundle.read_verified(path).sha256 != bundle.sha256:
            raise ValueError("registered bundle differs from current definition")
        return path
    bundle.write(path)
    return path


def _read_worker_result(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _next_admission_attempt(admissions: AdmissionLog, trial: Trial) -> int:
    """Continue the same scheduled episode with a consecutive attempt number."""
    return 1 + sum(record["trial_sha256"] == trial.sha256 for record in admissions.read_verified())


def run(repo: Path, raw_directory: Path) -> int:
    """Request one bounded, admitted model episode with no direct-run option."""
    bundle_path = study_directory(repo) / "bundle.json"
    bundle = StudyBundle.read_verified(bundle_path)
    if len(bundle.schedule) != 1:
        raise ValueError("the current baseline is deliberately a one-episode study")
    raw_directory.mkdir(parents=True, exist_ok=False)
    trial = bundle.schedule[0]
    admissions = AdmissionLog(repo / "results" / STUDY_ID / "admissions.jsonl", bundle.sha256)
    gate = ScheduledAdmission(bundle.schedule, admissions)
    if gate.current != trial:
        raise ValueError("the registered baseline has already been admitted")
    descriptor = raw_directory / "descriptor.json"
    worker_result = raw_directory / "worker-result.json"
    descriptor.write_bytes(canonical_json({
        "bundle_path": str(bundle_path.resolve()),
        "fixture_path": str((study_directory(repo) / "fixtures" / "todays-note.txt").resolve()),
        "raw_trace_path": str((raw_directory / "trace.json").resolve()),
        "execution_input_path": str((raw_directory / "execution-input.json").resolve()),
        "worker_result_path": str(worker_result.resolve()),
        "trial": trial.__dict__,
    }) + b"\n")
    command = [
        "/home/pierre/src/agentic/tools/agentic", "resource", "run", "llm", "--",
        "/bin/sh", "-c",
        "set -a; . /home/pierre/deploy/assist/.deploy.env; exec env AGENTIC_EXPERIMENT_ADMITTED=1 PYTHONPATH=\"$1\" \"$2\" -m harness.current_assist_baseline_worker \"$3\"",
        "admitted-current-assist-baseline",
        str(repo), "/home/pierre/deploy/assist/code/.venv/bin/python", str(descriptor),
    ]
    completed = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=900, check=False)
    result = _read_worker_result(worker_result)
    if result is None:
        detail = (completed.stderr or completed.stdout or "admission command produced no worker result").strip()
        gate.record(AdmissionAttempt(trial, False, _next_admission_attempt(admissions, trial), detail[:500]))
        return 3
    gate.record(AdmissionAttempt(trial, True, _next_admission_attempt(admissions, trial), "admitted"))
    outcome = TrialOutcome(
        trial=trial,
        outcome=result["outcome"],
        model_request_made=bool(result["model_request_made"]),
        artifact_success=bool(result["artifact_success"]),
        detail=str(result["detail"]),
    )
    records = RecordChain(repo / "results" / STUDY_ID / "outcomes.jsonl", bundle.sha256)
    records.append(outcome)
    records.finalize(bundle.schedule, admissions)
    (raw_directory / "command.json").write_bytes(canonical_json({
        "exit_code": completed.returncode,
        "bundle_sha256": bundle.sha256,
        "trace_sha256": result.get("trace_sha256"),
    }) + b"\n")
    return 0 if completed.returncode == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("register", "run"):
        command = subcommands.add_parser(name)
        command.add_argument("--repo", type=Path, required=True)
    subcommands.choices["run"].add_argument("--raw-directory", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.command == "register":
        print(register(repo))
        return 0
    return run(repo, args.raw_directory.resolve())


if __name__ == "__main__":
    sys.exit(main())
