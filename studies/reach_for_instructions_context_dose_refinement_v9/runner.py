"""Map V8's retrieved-guidance contrast across the high-context region."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import random
import subprocess
import threading
from typing import Any, Iterator

from harness.bundle import StudyBundle, Trial, atomic_write, canonical_json, digest
from harness.runner import RunArtifacts
from harness.schedule import blocked_schedule
from studies import equipment_return_oracle_calibration_v8 as calibration
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v6 import runner as delivery
from studies.reach_for_instructions_confirmation_v8 import runner as v8


STUDY = "reach-for-instructions-context-dose-refinement-v9-qwen38-current"
RANDOMIZATION_SEED = 20260914
REGISTRATION_TAG = "reach-for-instructions-context-dose-refinement-v9-qwen38-current-r1"
FIXTURE = calibration.FIXTURE
CONTEXT_LINES = {
    "C-1800": 1800,
    "C-2700": 2700,
    "C-3600": 3600,
    "C-4500": 4500,
}
_LOCK = threading.RLock()


def _schedule() -> tuple[Trial, ...]:
    """Interleave fresh paired episodes across the preregistered V9 doses."""
    blocks = []
    for offset, context in enumerate(CONTEXT_LINES):
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


def _sealed_paths(root: Path) -> list[Path]:
    """Bind V9 and every inherited file that can affect an admission."""
    inherited = v8._sealed_paths(root)
    return inherited + [
        root / "studies" / "reach_for_instructions_context_dose_refinement_v9" / "runner.py",
        root / "experiments" / STUDY / "conditions.json",
        root / "experiments" / STUDY / "registration.md",
        root / "experiments" / STUDY / core.RENDERED_REQUEST_DIGESTS,
    ]


def _implementation_sha256(root: Path) -> str:
    """Hash every sealed study and shared runner input."""
    return digest({str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in _sealed_paths(root)})


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _definition(root: Path) -> tuple[StudyBundle, dict[str, Any], dict[str, dict[str, str]]]:
    """Require the immutable tag to preserve every V9 definition input."""
    bundle, task, conditions = v8._CORE_DEFINITION(root)
    registration = bundle.registration
    if registration.get("registration_sha256") != _file_sha256(root / "experiments" / STUDY / "registration.md"):
        raise ValueError("V9 bundle registration does not match")
    if registration.get("analysis_sha256") != _file_sha256(root / "harness" / "report.py"):
        raise ValueError("V9 bundle analysis does not match")
    tag = registration.get("registration_tag")
    if not isinstance(tag, str) or not tag:
        raise ValueError("V9 registration tag is missing")
    for path in _sealed_paths(root):
        relative = path.relative_to(root).as_posix()
        tagged = subprocess.run(["git", "-C", str(root), "show", f"{tag}:{relative}"], capture_output=True)
        if tagged.returncode or tagged.stdout != path.read_bytes():
            raise ValueError(f"V9 registration tag does not retain sealed input: {relative}")
    return bundle, task, conditions


def _worker_command(*args: Any) -> list[str]:
    """Route the sole model-capable worker through V9's configuration."""
    command = v8._worker_command(*args)
    return [
        "studies.reach_for_instructions_context_dose_refinement_v9.runner"
        if value == "studies.reach_for_instructions_confirmation_v8.runner"
        else value
        for value in command
    ]


@contextmanager
def _configured() -> Iterator[None]:
    """Hold the V8 task and measurement path fixed while replacing only doses."""
    with _LOCK:
        with v8._configured():
            overrides = {
                "STUDY": STUDY,
                "CONTEXT_LINES": CONTEXT_LINES,
                "_schedule": _schedule,
                "_implementation_sha256": _implementation_sha256,
                "_definition": _definition,
                "_worker_command": _worker_command,
            }
            originals = {name: getattr(core, name) for name in overrides}
            try:
                for name, value in overrides.items():
                    setattr(core, name, value)
                yield
            finally:
                for name, value in originals.items():
                    setattr(core, name, value)


def preflight(root: Path) -> None:
    with _configured():
        v8.oracle_preflight(root)


def render_request_digests(root: Path) -> None:
    """Write V9's sealed post-middleware request map without model calls."""
    with _configured():
        task = core._root_task(root)
        values = {}
        for trial in core._schedule():
            values[trial.sha256] = digest(delivery._rendered_provider_request(
                system_prompt=delivery._system_prompt(core.CONDITION_DELIVERY[trial.condition], core.CONTEXT_LINES[trial.task]),
                user_prompt=task["user_prompt"],
                files=task["initial_files"],
                skill_name=delivery.SKILL_NAME,
                skill_body=delivery.PROCEDURE,
                temperature=task["decoding"]["temperature"],
                max_tokens=task["decoding"]["max_tokens"],
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
                "registration_sha256": _file_sha256(root / "experiments" / STUDY / "registration.md"),
                "analysis_sha256": _file_sha256(root / "harness" / "report.py"),
            },
            runner_revision="reach-for-instructions-context-dose-refinement-v9",
            analysis_revision="harness/report.py",
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
    """Expose V9 through the ordinary sealed-study command interface."""
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
