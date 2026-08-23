"""Content-addressed study definitions that fail closed on undeclared change."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    """Return the one serialization used for manifests and chain records."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True, order=True)
class Trial:
    """One planned fresh episode, before a model request is admitted."""

    task: str
    replicate: int
    condition: str
    generation_seed: int

    @property
    def id(self) -> str:
        return f"{self.task}:r{self.replicate}:{self.condition}:s{self.generation_seed}"

    @property
    def sha256(self) -> str:
        """Collision-safe identity used for accounting; ``id`` is display-only."""
        return digest(self.__dict__)


@dataclass(frozen=True)
class StudyBundle:
    """The complete inputs for one sealed test, model, and architecture run."""

    study_id: str
    registration: dict[str, Any]
    conditions: dict[str, dict[str, Any]]
    fixtures: dict[str, str]
    tool_schemas: dict[str, Any]
    schedule: tuple[Trial, ...]
    model: dict[str, str]
    harness_architecture: dict[str, str]
    settings: dict[str, Any]
    runner_revision: str
    analysis_revision: str

    def payload(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "registration": self.registration,
            "conditions": self.conditions,
            "fixtures": self.fixtures,
            "tool_schemas": self.tool_schemas,
            "schedule": [trial.__dict__ for trial in self.schedule],
            "model": self.model,
            "harness_architecture": self.harness_architecture,
            "settings": self.settings,
            "runner_revision": self.runner_revision,
            "analysis_revision": self.analysis_revision,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())

    def write(self, path: Path) -> None:
        """Write a self-verifying bundle; callers must not hand-edit it later."""
        self.assert_complete()
        contents = {"sha256": self.sha256, "bundle": self.payload()}
        atomic_write(path, canonical_json(contents) + b"\n")

    @classmethod
    def read_verified(cls, path: Path) -> "StudyBundle":
        """Load only a byte-valid bundle with a matching recorded digest."""
        stored = json.loads(path.read_text())
        payload = stored["bundle"]
        if stored.get("sha256") != digest(payload):
            raise ValueError(f"bundle digest mismatch: {path}")
        schedule = tuple(Trial(**trial) for trial in payload["schedule"])
        bundle = cls(
            study_id=payload["study_id"],
            registration=payload["registration"],
            conditions=payload["conditions"],
            fixtures=payload["fixtures"],
            tool_schemas=payload["tool_schemas"],
            schedule=schedule,
            model=payload["model"],
            harness_architecture=payload["harness_architecture"],
            settings=payload["settings"],
            runner_revision=payload["runner_revision"],
            analysis_revision=payload["analysis_revision"],
        )
        if bundle.sha256 != stored["sha256"]:
            raise ValueError(f"bundle normalization mismatch: {path}")
        bundle.assert_complete()
        return bundle

    def assert_complete(self) -> None:
        """Reject omissions that would create hidden researcher discretion."""
        if not self.study_id or not self.registration:
            raise ValueError("study_id is required")
        if not self.conditions or not self.schedule or not self.fixtures or not self.tool_schemas:
            raise ValueError("conditions, fixtures, schemas, and scheduled trials are required")
        if not self.runner_revision or not self.analysis_revision:
            raise ValueError("runner and analysis revisions are required")
        _assert_axis(self.model, "model")
        _assert_axis(self.harness_architecture, "harness architecture")
        _assert_settings(self.settings, self.model, self.harness_architecture)
        seen: set[str] = set()
        blocks: dict[tuple[str, int], set[str]] = {}
        positions: dict[tuple[str, int], dict[str, int]] = {}
        for trial in self.schedule:
            if trial.condition not in self.conditions:
                raise ValueError(f"unknown condition in schedule: {trial.condition}")
            if trial.task not in self.fixtures:
                raise ValueError(f"scheduled task lacks fixture: {trial.task}")
            if trial.sha256 in seen:
                raise ValueError(f"duplicate trial: {trial.id}")
            seen.add(trial.sha256)
            block = blocks.setdefault((trial.task, trial.replicate), set())
            if trial.condition in block:
                raise ValueError(f"duplicate condition in block: {trial.task}:r{trial.replicate}")
            positions.setdefault((trial.task, trial.replicate), {})[trial.condition] = len(block)
            block.add(trial.condition)
        condition_count = len(self.conditions)
        replicates_by_task: dict[str, int] = {}
        for (task, _replicate), block in blocks.items():
            if block != set(self.conditions):
                raise ValueError(f"task has incomplete condition blocks: {task}")
            replicates_by_task[task] = replicates_by_task.get(task, 0) + 1
        for task, replicates in replicates_by_task.items():
            if replicates % condition_count and self.registration.get("position_balance") != "adjust_for_position":
                raise ValueError(f"partial position cycle requires adjustment: {task}")
            if replicates % condition_count == 0:
                expected_per_position = replicates // condition_count
                for condition in self.conditions:
                    counts = [
                        0 for _ in range(condition_count)
                    ]
                    for (block_task, _replicate), block_positions in positions.items():
                        if block_task == task:
                            counts[block_positions[condition]] += 1
                    if counts != [expected_per_position] * condition_count:
                        raise ValueError(f"unbalanced condition positions: {task}:{condition}")


def _assert_axis(value: dict[str, str], name: str) -> None:
    """Require one precise, reusable identity for a between-run axis."""
    if set(value) != {"id", "revision", "configuration_sha256"}:
        raise ValueError(f"{name} identity must name id, revision, and configuration digest")
    if not all(isinstance(item, str) and item for item in value.values()):
        raise ValueError(f"{name} identity values must be non-empty text")
    digest_value = value["configuration_sha256"]
    if len(digest_value) != 64 or any(character not in "0123456789abcdef" for character in digest_value):
        raise ValueError(f"{name} configuration digest must be lowercase SHA-256")


def _assert_settings(
    settings: dict[str, Any], model: dict[str, str], harness_architecture: dict[str, str]
) -> None:
    """Seal arbitrary runtime settings while binding each axis to its subtree."""
    if not isinstance(settings, dict):
        raise ValueError("settings must be an object")
    try:
        canonical_json(settings)
    except (TypeError, ValueError) as error:
        raise ValueError("settings must contain JSON-safe values") from error
    for key, axis in (("model", model), ("harness_architecture", harness_architecture)):
        if key not in settings:
            raise ValueError(f"settings must include {key}")
        if digest(settings[key]) != axis["configuration_sha256"]:
            raise ValueError(f"{key} settings do not match its configuration digest")


def atomic_write(path: Path, data: bytes) -> None:
    """Durably replace one local artifact only after its complete bytes exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if os.write(descriptor, data) != len(data):
            raise OSError("short atomic artifact write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
