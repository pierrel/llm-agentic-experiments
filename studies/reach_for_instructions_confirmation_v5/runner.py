"""Seal and run V5 with its schedule seed bound in its registration."""

from __future__ import annotations

import argparse
import hashlib
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import threading
from typing import Any, Iterator

from harness.bundle import digest
from harness.runner import RunArtifacts
from studies.reach_for_instructions_confirmation_v4 import runner as base


STUDY = "reach-for-instructions-confirmation-v5-qwen38"
RANDOMIZATION_SEED = 20260905
_LOCK = threading.RLock()


def _implementation_sha256(root: Path) -> str:
    paths = [
        root / "studies" / "reach_for_instructions_confirmation_v5" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v4" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v3" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v2" / "runner.py",
        root / "studies" / "access_transition_oracle_calibration.py",
        root / "fixtures" / base.base.base.FIXTURE,
        root / "experiments" / STUDY / "conditions.json",
        root / "experiments" / STUDY / base.base.base.RENDERED_REQUEST_DIGESTS,
        root / "experiments" / "access-transition-oracle-calibration-v1" / "corpus.json",
    ]
    return digest({str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})


def _worker_command(*args: Any) -> list[str]:
    command = _BASE_WORKER_COMMAND(*args)
    return [
        "studies.reach_for_instructions_confirmation_v5.runner"
        if value == "studies.reach_for_instructions_confirmation_v4.runner"
        else value
        for value in command
    ]


_BASE_WORKER_COMMAND = base._worker_command


@contextmanager
def _configured() -> Iterator[None]:
    replacements = {
        "STUDY": STUDY,
        "RANDOMIZATION_SEED": RANDOMIZATION_SEED,
        "_implementation_sha256": _implementation_sha256,
        "_worker_command": _worker_command,
    }
    with _LOCK:
        originals = {name: getattr(base, name) for name in replacements}
        try:
            for name, value in replacements.items():
                setattr(base, name, value)
            with base._configured():
                yield
        finally:
            for name, value in originals.items():
                setattr(base, name, value)


def preflight(root: Path) -> None:
    with _configured():
        base.preflight(root)


def render_request_digests(root: Path) -> None:
    with _configured():
        base.render_request_digests(root)


def seal(root: Path, *, source_commit: str, assist_revision: str) -> Any:
    with _configured():
        sealed = base.seal(root, source_commit=source_commit, assist_revision=assist_revision)
        bundle = replace(sealed, registration=sealed.registration | {"randomization_seed": RANDOMIZATION_SEED})
        bundle.write(root / "experiments" / STUDY / "bundle.json")
        return bundle


def run(root: Path, output: Path, *, workspace_root: Path, assist_source: Path, assist_python: Path) -> Any:
    with _configured():
        return base.run(root, output, workspace_root=workspace_root, assist_source=assist_source, assist_python=assist_python)


def archive(artifacts: Any, destination: Path) -> None:
    with _configured():
        base.archive(artifacts, destination)


def run_worker(descriptor_path: Path, result_path: Path, marker: Path) -> None:
    with _configured():
        base.run_worker(descriptor_path, result_path, marker)


def main() -> None:
    """Expose V5's wrappers so sealing cannot bypass the seed correction."""
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
            raise SystemExit("worker requires --descriptor, --result, and --request-started")
        run_worker(args.descriptor, args.result, args.request_started)


if __name__ == "__main__":
    main()
