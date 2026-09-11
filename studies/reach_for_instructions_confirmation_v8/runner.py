"""Fresh held-out confirmation after V7's approval-status oracle boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import random
import threading
from typing import Any, Iterator

from harness.bundle import StudyBundle, Trial, atomic_write, canonical_json, digest
from harness.runner import RunArtifacts
from harness.schedule import blocked_schedule
from studies import equipment_return_oracle_calibration_v8 as calibration
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v6 import runner as delivery
from studies.reach_for_instructions_confirmation_v7 import runner as prior


STUDY = "reach-for-instructions-confirmation-v8-qwen38-current"
MODEL_ID = "Qwen3.8-27B-UD-Q4_K_XL.gguf"
WEIGHTS_SHA256 = "3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e"
RANDOMIZATION_SEED = 20260913
REGISTRATION_TAG = "reach-for-instructions-confirmation-v8-qwen38-current-r1"
FIXTURE = calibration.FIXTURE
_LOCK = threading.RLock()
_PRIOR_WORKER_COMMAND = prior._worker_command


def _schedule() -> tuple[Trial, ...]:
    """Interleave fresh context blocks from V8's declared randomization seed."""
    blocks = []
    for offset, context in enumerate(core.CONTEXT_LINES):
        trials = blocked_schedule([context], core.CONDITIONS, 12, RANDOMIZATION_SEED + offset)
        blocks.extend(tuple(trials[index:index + len(core.CONDITIONS)]) for index in range(0, len(trials), len(core.CONDITIONS)))
    deterministic = random.Random(RANDOMIZATION_SEED)
    ordered: list[tuple[Trial, ...]] = []
    while blocks:
        candidates = [block for block in blocks if not ordered or block[0].task != ordered[-1][0].task]
        choice = deterministic.choice(candidates or blocks)
        blocks.remove(choice)
        ordered.append(choice)
    return tuple(trial for block in ordered for trial in block)


def _implementation_sha256(root: Path) -> str:
    """Bind V8, inherited layers, the fresh fixture, and its oracle calibration."""
    paths = [
        root / "studies" / "reach_for_instructions_confirmation_v8" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v7" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v6" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v5" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v4" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v3" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v2" / "runner.py",
        root / "harness" / "report.py",
        root / "studies" / "equipment_return_oracle_calibration_v8.py",
        root / "fixtures" / FIXTURE,
        root / "experiments" / STUDY / "conditions.json",
        root / "experiments" / STUDY / core.RENDERED_REQUEST_DIGESTS,
        root / "experiments" / calibration.STUDY / "corpus.json",
    ]
    return digest({str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})


def _settings(source_commit: str, assist_revision: str) -> dict[str, Any]:
    """Retain the current Assist Qwen profile, including reasoning and no output cap."""
    return prior._settings(source_commit, assist_revision)


def oracle_preflight(root: Path, task: dict[str, Any] | None = None) -> dict[str, Any]:
    """Require direct and compact source-grounded forms before any model admission."""
    calibration.verify(root)
    value = json.loads((root / "experiments" / calibration.STUDY / "corpus.json").read_text())
    if task is not None and task != core._root_task(root):
        raise ValueError("V8 calibration task differs from the fixed held-out fixture")
    return value


def _worker_command(*args: Any) -> list[str]:
    """Route every inherited live worker entry through V8's sealed configuration."""
    command = _PRIOR_WORKER_COMMAND(*args)
    names = {
        "studies.reach_for_instructions_confirmation_v2.runner",
        "studies.reach_for_instructions_confirmation_v3.runner",
        "studies.reach_for_instructions_confirmation_v4.runner",
        "studies.reach_for_instructions_confirmation_v5.runner",
        "studies.reach_for_instructions_confirmation_v6.runner",
        "studies.reach_for_instructions_confirmation_v7.runner",
    }
    return ["studies.reach_for_instructions_confirmation_v8.runner" if value in names else value for value in command]


def _score(task: dict[str, Any], payload: dict[str, Any]) -> core.TrialScore:
    """Score V8's artifact while retaining an independent pre-read skill-use measure."""
    files, messages = payload.get("files"), payload.get("messages")
    process_loaded = delivery._process_skill_load(messages, set(task["oracle"]["required_reads"]))
    if not isinstance(files, dict) or not isinstance(messages, list):
        return core.TrialScore(False, "worker result is malformed", None, process_loaded)
    first_tokens = core._first_input_tokens(messages)
    initial = task["initial_files"]
    if any(files.get(path) != text for path, text in initial.items()):
        return core.TrialScore(False, "a source record changed", first_tokens, process_loaded)
    outputs = [path for path in files if path not in initial and path.endswith(".json")]
    if len(outputs) != 1:
        return core.TrialScore(False, "expected exactly one new JSON handoff", first_tokens, process_loaded)
    try:
        handoff = json.loads(files[outputs[0]])
    except (TypeError, json.JSONDecodeError):
        return core.TrialScore(False, "handoff is not valid JSON", first_tokens, process_loaded)
    required = {"case_id", "return_status", "approval_status", "next_owner", "next_action"}
    if not isinstance(handoff, dict) or not required.issubset(handoff) or not ({"equipment_id", "verified_equipment_id"} & set(handoff)):
        return core.TrialScore(False, "handoff lacks required structured fields", first_tokens, process_loaded)
    if not calibration.handoff_is_grounded(task, handoff):
        return core.TrialScore(False, "handoff has an unsupported or incomplete fact", first_tokens, process_loaded)
    reads: set[str] = set()
    inventory = wrote = False
    for message in messages:
        calls = message.get("tool_calls", []) if isinstance(message, dict) else []
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, dict):
                continue
            name = call.get("name")
            args = call.get("args", call.get("arguments", {}))
            path = args.get("file_path", args.get("path")) if isinstance(args, dict) else None
            if name in {"glob", "ls", "list_files"}:
                inventory = True
            elif name == "read_file" and isinstance(path, str):
                if not inventory:
                    return core.TrialScore(False, "a source read occurred before inventory", first_tokens, process_loaded)
                reads.add(path.lstrip("/"))
            elif name in {"write_file", "edit_file"}:
                is_handoff = isinstance(path, str) and path.lstrip("/") in outputs
                if not inventory or not set(task["oracle"]["required_reads"]).issubset(reads):
                    return core.TrialScore(False, "a write occurred before all source reads", first_tokens, process_loaded)
                if is_handoff:
                    wrote = True
    if not inventory or not wrote or not set(task["oracle"]["required_reads"]).issubset(reads):
        return core.TrialScore(False, "trace lacks required inventory, reads, or handoff write", first_tokens, process_loaded)
    return core.TrialScore(True, "structured handoff and ordered procedure passed", first_tokens, process_loaded)


@contextmanager
def _configured() -> Iterator[None]:
    """Layer the fresh V8 fixture and oracle over V7's sealed delivery stack."""
    outer = {
        "STUDY": STUDY,
        "RANDOMIZATION_SEED": RANDOMIZATION_SEED,
        "_implementation_sha256": _implementation_sha256,
        "_worker_command": _worker_command,
    }
    with _LOCK:
        outer_originals = {name: getattr(prior, name) for name in outer}
        try:
            for name, value in outer.items():
                setattr(prior, name, value)
            with prior._configured():
                inner = {
                    "FIXTURE": FIXTURE,
                    "_schedule": _schedule,
                    "_settings": _settings,
                    "_implementation_sha256": _implementation_sha256,
                    "_worker_command": _worker_command,
                    "oracle_preflight": oracle_preflight,
                    "_handoff_is_grounded": calibration.handoff_is_grounded,
                    "_score": _score,
                    "run_worker": delivery._run_worker,
                }
                originals = {name: getattr(core, name) for name in inner}
                try:
                    for name, value in inner.items():
                        setattr(core, name, value)
                    yield
                finally:
                    for name, value in originals.items():
                        setattr(core, name, value)
        finally:
            for name, value in outer_originals.items():
                setattr(prior, name, value)


def preflight(root: Path) -> None:
    with _configured():
        oracle_preflight(root)


def render_request_digests(root: Path) -> None:
    """Write per-trial current-profile request digests before this study is sealed."""
    with _configured():
        task = core._root_task(root)
        values = {}
        for trial in core._schedule():
            values[trial.sha256] = digest(delivery._rendered_provider_request(
                system_prompt=delivery._system_prompt(core.CONDITION_DELIVERY[trial.condition], core.CONTEXT_LINES[trial.task]),
                user_prompt=task["user_prompt"], files=task["initial_files"], skill_name=delivery.SKILL_NAME,
                skill_body=delivery.PROCEDURE, temperature=task["decoding"]["temperature"], max_tokens=task["decoding"]["max_tokens"],
            ))
    atomic_write(root / "experiments" / STUDY / core.RENDERED_REQUEST_DIGESTS, canonical_json(values) + b"\n")


def seal(root: Path, *, source_commit: str, assist_revision: str) -> StudyBundle:
    with _configured():
        sealed = core.seal(root, source_commit=source_commit, assist_revision=assist_revision)
        bundle = replace(
            sealed,
            registration=sealed.registration | {
                "randomization_seed": RANDOMIZATION_SEED,
                "registration_tag": REGISTRATION_TAG,
                "primary_outcome": "structured equipment-return handoff plus ordered workspace procedure",
            },
            model={"id": MODEL_ID, "revision": "2026-09-11", "configuration_sha256": digest(sealed.settings["model"])},
            runner_revision="reach-for-instructions-qwen38-current-runner-v8",
            analysis_revision="reach-for-instructions-qwen38-current-summary-v8",
        )
        bundle.write(root / "experiments" / STUDY / "bundle.json")
        return bundle


def run(root: Path, output: Path, *, workspace_root: Path, assist_source: Path, assist_python: Path) -> RunArtifacts:
    with _configured():
        return core.run(root, output, workspace_root=workspace_root, assist_source=assist_source, assist_python=assist_python)


def archive(artifacts: RunArtifacts, destination: Path) -> None:
    with _configured():
        core.archive(artifacts, destination)


def run_worker(descriptor_path: Path, result_path: Path, marker: Path) -> None:
    with _configured():
        delivery._run_worker(descriptor_path, result_path, marker)


def main() -> None:
    """Expose the V8 wrappers through the normal study command interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "render", "seal", "run", "archive", "worker"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--assist-revision")
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--assist-source", type=Path)
    parser.add_argument("--assist-python", type=Path)
    parser.add_argument("--descriptor", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--request-started", type=Path)
    args = parser.parse_args()
    if args.command == "preflight":
        preflight(args.root)
    elif args.command == "render":
        render_request_digests(args.root)
    elif args.command == "seal":
        if not args.source_commit or not args.assist_revision:
            raise SystemExit("seal requires --source-commit and --assist-revision")
        seal(args.root, source_commit=args.source_commit, assist_revision=args.assist_revision)
    elif args.command == "run":
        if args.output is None or args.workspace_root is None or args.assist_source is None or args.assist_python is None:
            raise SystemExit("run requires --output, --workspace-root, --assist-source, and --assist-python")
        run(args.root, args.output, workspace_root=args.workspace_root, assist_source=args.assist_source, assist_python=args.assist_python)
    elif args.command == "archive":
        if args.output is None or args.archive is None:
            raise SystemExit("archive requires --output and --archive")
        archive(RunArtifacts(args.output / "bundle.json", args.output / "admissions.jsonl", args.output / "outcomes.jsonl", args.output / "report.json", args.output / "traces"), args.archive)
    else:
        if args.descriptor is None or args.result is None or args.request_started is None:
            raise SystemExit("worker requires descriptor, result, and request-started")
        run_worker(args.descriptor, args.result, args.request_started)


if __name__ == "__main__":
    main()
