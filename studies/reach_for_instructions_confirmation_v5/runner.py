"""Seal and run V5 with its schedule seed bound in its registration."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator

from harness.bundle import digest
from studies.reach_for_instructions_confirmation_v4 import runner as base


STUDY = "reach-for-instructions-confirmation-v5-qwen38"
RANDOMIZATION_SEED = 20260905


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
    with _configured():
        base.main()


if __name__ == "__main__":
    main()
