"""Machine-readable task and condition manifests bound to a StudyBundle."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .bundle import StudyBundle, canonical_json, digest
from .episode import ProviderReply, VirtualWorkspace, read_script
from .invariants import assert_equal_except


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return value


@dataclass(frozen=True)
class TaskManifest:
    """A hermetic fixture and deterministic-oracle declaration."""

    task_id: str
    system_prompt: str
    user_prompt: str
    initial_files: dict[str, str]
    skills: dict[str, str]
    decoding: dict[str, Any]
    oracle: dict[str, Any]

    @classmethod
    def read(cls, path: Path) -> "TaskManifest":
        value = _read_object(path)
        required = {
            "task_id", "system_prompt", "user_prompt", "initial_files", "skills", "decoding", "oracle"
        }
        if set(value) != required:
            raise ValueError(f"unexpected task manifest fields: {path}")
        task = cls(**value)
        if not task.task_id or not isinstance(task.system_prompt, str) or not isinstance(task.user_prompt, str):
            raise ValueError("task identity and prompts must be non-empty text")
        if not isinstance(task.initial_files, dict) or not isinstance(task.skills, dict):
            raise ValueError("task files and skills must be objects")
        VirtualWorkspace(task.initial_files, task.skills)
        if not isinstance(task.decoding, dict) or not isinstance(task.oracle, dict):
            raise ValueError("task decoding and oracle must be objects")
        return task

    def payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "initial_files": self.initial_files,
            "skills": self.skills,
            "decoding": self.decoding,
            "oracle": self.oracle,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


@dataclass(frozen=True)
class ConditionManifest:
    """The only declared condition-specific input for an episode."""

    condition_id: str
    system_suffix: str
    skill_overrides: dict[str, str]
    decoding_overrides: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "system_suffix": self.system_suffix,
            "skill_overrides": self.skill_overrides,
            "decoding_overrides": self.decoding_overrides,
        }

    @property
    def sha256(self) -> str:
        return digest(self.payload())


def read_conditions(path: Path) -> dict[str, ConditionManifest]:
    """Load a closed mapping of opaque condition IDs to declared differences."""
    raw = _read_object(path)
    conditions: dict[str, ConditionManifest] = {}
    required = {"system_suffix", "skill_overrides", "decoding_overrides"}
    for condition_id, value in raw.items():
        if not condition_id or not isinstance(value, dict) or set(value) != required:
            raise ValueError(f"invalid condition manifest: {condition_id}")
        condition = ConditionManifest(condition_id=condition_id, **value)
        if not isinstance(condition.system_suffix, str):
            raise ValueError("condition system suffix must be text")
        if not isinstance(condition.skill_overrides, dict) or not isinstance(condition.decoding_overrides, dict):
            raise ValueError("condition overrides must be objects")
        if not all(isinstance(name, str) and isinstance(body, str) for name, body in condition.skill_overrides.items()):
            raise ValueError("condition skill overrides must map text names to text bodies")
        conditions[condition_id] = condition
    if not conditions:
        raise ValueError("at least one condition is required")
    return conditions


@dataclass(frozen=True)
class StudyDefinition:
    """Executable manifests plus the independent content-addressed bundle."""

    bundle: StudyBundle
    tasks: dict[str, TaskManifest]
    conditions: dict[str, ConditionManifest]

    def initial_request(self, task: TaskManifest, condition: ConditionManifest) -> dict[str, Any]:
        """Render the exact first provider request before an episode starts."""
        inputs = self.episode_inputs(task, condition)
        return {
            "messages": [
                {"role": "system", "content": inputs["system_prompt"]},
                {"role": "user", "content": inputs["user_prompt"]},
            ],
            "tools": VirtualWorkspace.schemas(),
            "decoding": inputs["decoding"],
        }

    def episode_inputs(self, task: TaskManifest, condition: ConditionManifest) -> dict[str, Any]:
        """Create the one fresh workspace and prompt configuration for an episode."""
        return {
            "system_prompt": task.system_prompt + condition.system_suffix,
            "user_prompt": task.user_prompt,
            "decoding": task.decoding | condition.decoding_overrides,
            "workspace": VirtualWorkspace(task.initial_files, task.skills | condition.skill_overrides),
        }

    def validate(self) -> None:
        """Reject any manifest or initial request outside the sealed declaration."""
        self.bundle.assert_complete()
        if set(self.tasks) != set(self.bundle.fixtures):
            raise ValueError("bundle and task manifests differ")
        if set(self.conditions) != set(self.bundle.conditions):
            raise ValueError("bundle and condition manifests differ")
        if canonical_json(self.bundle.tool_schemas) != canonical_json(VirtualWorkspace.schemas()):
            raise ValueError("bundle tool schemas differ from virtual tool schemas")
        for task_id, task in self.tasks.items():
            if self.bundle.fixtures[task_id] != task.sha256:
                raise ValueError(f"fixture digest mismatch: {task_id}")
        for condition_id, condition in self.conditions.items():
            if self.bundle.conditions[condition_id] != {"sha256": condition.sha256}:
                raise ValueError(f"condition digest mismatch: {condition_id}")
        allowed = self.bundle.registration.get("allowed_initial_request_fields", [])
        if not isinstance(allowed, list) or not all(isinstance(field, str) for field in allowed):
            raise ValueError("bundle request-difference declaration must be a list of fields")
        for task in self.tasks.values():
            requests = [self.initial_request(task, condition) for condition in self.conditions.values()]
            for request in requests[1:]:
                assert_equal_except(requests[0], request, set(allowed))
        allowed_skills = self.bundle.registration.get("allowed_loaded_skill_names", [])
        if not isinstance(allowed_skills, list) or not all(isinstance(name, str) for name in allowed_skills):
            raise ValueError("bundle loaded-skill declaration must be a list of names")
        for task in self.tasks.values():
            for name in set(task.skills) | set().union(*(condition.skill_overrides for condition in self.conditions.values())):
                bodies = [condition.skill_overrides.get(name, task.skills.get(name)) for condition in self.conditions.values()]
                if any(body != bodies[0] for body in bodies[1:]) and name not in allowed_skills:
                    raise ValueError(f"undeclared condition difference: loaded skill {name}")


def mvp_definition(root: Path) -> StudyDefinition:
    """Load the committed no-model fixture used by the MVP smoke runner."""
    task = TaskManifest.read(root / "fixtures" / "read-before-edit.json")
    conditions = read_conditions(root / "experiments" / "mvp-scripted" / "conditions.json")
    bundle = StudyBundle.read_verified(root / "experiments" / "mvp-scripted" / "bundle.json")
    if bundle.registration.get("implementation_sha256") != mvp_implementation_sha256(root):
        raise ValueError("MVP bundle does not match the committed harness implementation")
    return StudyDefinition(bundle, {task.task_id: task}, conditions)


def mvp_script(root: Path) -> tuple[ProviderReply, ...]:
    """Load the committed scripted behavior bound by the MVP bundle."""
    return read_script(str(root / "experiments" / "mvp-scripted" / "script.json"))


def mvp_implementation_sha256(root: Path) -> str:
    """Hash the executable MVP module set bound by the committed bundle."""
    sources = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((root / "harness").glob("*.py"))
    }
    return digest(sources)
