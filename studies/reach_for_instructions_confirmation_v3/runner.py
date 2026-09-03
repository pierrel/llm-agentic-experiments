"""Seal and run the Qwen3.8 guidance confirmation without altering V2."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import random
from tempfile import TemporaryDirectory
import threading
from typing import Any, Iterator

from harness.bundle import StudyBundle, Trial, digest
from harness.schedule import blocked_schedule
from studies import access_transition_oracle_calibration as calibration
from studies.reach_for_instructions_confirmation_v2 import runner as base


STUDY = "reach-for-instructions-confirmation-v3-qwen38"
MODEL_ID = "Qwen3.8-27B-UD-Q4_K_XL.gguf"
WEIGHTS_SHA256 = "3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e"
RANDOMIZATION_SEED = 20260903
_LOCK = threading.RLock()
_BASE_SETTINGS = base._settings
_BASE_WORKER_COMMAND = base._worker_command


def _schedule() -> tuple[Trial, ...]:
    """Interleave a fresh randomization of the same three context doses."""
    blocks = []
    for offset, context in enumerate(base.CONTEXT_LINES):
        trials = blocked_schedule([context], base.CONDITIONS, 12, RANDOMIZATION_SEED + offset)
        blocks.extend(tuple(trials[index:index + len(base.CONDITIONS)]) for index in range(0, len(trials), len(base.CONDITIONS)))
    deterministic = random.Random(RANDOMIZATION_SEED)
    ordered: list[tuple[Trial, ...]] = []
    while blocks:
        candidates = [block for block in blocks if not ordered or block[0].task != ordered[-1][0].task]
        choice = deterministic.choice(candidates or blocks)
        blocks.remove(choice)
        ordered.append(choice)
    return tuple(trial for block in ordered for trial in block)


def oracle_preflight(root: Path, task: dict[str, Any] | None = None) -> dict[str, Any]:
    """Require the independent, condition-blind calibration corpus to pass."""
    calibration.verify(root)
    value = json.loads((root / "experiments" / calibration.STUDY / "corpus.json").read_text())
    if task is not None and task != base._root_task(root):
        raise ValueError("oracle calibration task differs from the fixed fixture")
    return value


def _settings(source_commit: str, assist_revision: str) -> dict[str, Any]:
    """Preserve V2's harness while recording the new model identity exactly."""
    settings = _BASE_SETTINGS(source_commit, assist_revision)
    model = settings["model"] | {
        "model_id": MODEL_ID,
        "weights_sha256": WEIGHTS_SHA256,
    }
    return settings | {"model": model}


def _implementation_sha256(root: Path) -> str:
    """Bind the reused harness and the independent calibration gate."""
    paths = [
        root / "studies" / "reach_for_instructions_confirmation_v3" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v2" / "runner.py",
        root / "studies" / "access_transition_oracle_calibration.py",
        root / "fixtures" / base.FIXTURE,
        root / "experiments" / STUDY / "conditions.json",
        root / "experiments" / STUDY / base.RENDERED_REQUEST_DIGESTS,
        root / "experiments" / calibration.STUDY / "corpus.json",
    ]
    return digest({str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})


def _worker_command(
    root: Path, workspace_root: Path, assist_source: Path, assist_python: Path,
    descriptor: Path, result: Path, marker: Path,
) -> list[str]:
    command = _BASE_WORKER_COMMAND(root, workspace_root, assist_source, assist_python, descriptor, result, marker)
    return [
        "studies.reach_for_instructions_confirmation_v3.runner"
        if value == "studies.reach_for_instructions_confirmation_v2.runner"
        else value
        for value in command
    ]


@contextmanager
def _configured() -> Iterator[None]:
    """Temporarily parameterize the reviewed V2 harness for this new study."""
    replacements = {
        "STUDY": STUDY,
        "WEIGHTS_SHA256": WEIGHTS_SHA256,
        "_schedule": _schedule,
        "_settings": _settings,
        "_implementation_sha256": _implementation_sha256,
        "_worker_command": _worker_command,
        "oracle_preflight": oracle_preflight,
        "_handoff_is_grounded": calibration.handoff_is_grounded,
        "run_worker": run_worker,
    }
    with _LOCK:
        originals = {name: getattr(base, name) for name in replacements}
        try:
            for name, value in replacements.items():
                setattr(base, name, value)
            yield
        finally:
            for name, value in originals.items():
                setattr(base, name, value)


def preflight(root: Path) -> None:
    with _configured():
        base.oracle_preflight(root)


def render_request_digests(root: Path) -> None:
    with _configured():
        base.render_request_digests(root)


def seal(root: Path, *, source_commit: str, assist_revision: str) -> StudyBundle:
    with _configured():
        sealed = base.seal(root, source_commit=source_commit, assist_revision=assist_revision)
        bundle = replace(
            sealed,
            model={
                "id": MODEL_ID,
                "revision": "2026-09-03",
                "configuration_sha256": digest(sealed.settings["model"]),
            },
            runner_revision="reach-for-instructions-qwen38-runner-v1",
            analysis_revision="reach-for-instructions-qwen38-summary-v1",
        )
        bundle.write(root / "experiments" / STUDY / "bundle.json")
        return bundle


def run(root: Path, output: Path, *, workspace_root: Path, assist_source: Path, assist_python: Path) -> Any:
    with _configured():
        return base.run(root, output, workspace_root=workspace_root, assist_source=assist_source, assist_python=assist_python)


def archive(artifacts: Any, destination: Path) -> None:
    with _configured():
        base.archive(artifacts, destination)


def run_worker(descriptor_path: Path, result_path: Path, marker: Path) -> None:
    """Run one V3 worker while allowing the endpoint's local model-path prefix."""
    with _configured():
        descriptor = json.loads(descriptor_path.read_text())
        required = {"bundle_sha256", "trial_sha256", "system_prompt", "user_prompt", "files", "skill_name", "skill_body", "max_turns", "temperature", "max_tokens", "fixture", "fixture_sha256", "provider_request_sha256", "tool_schema", "runtime"}
        if not isinstance(descriptor, dict) or set(descriptor) != required:
            raise ValueError("worker descriptor is invalid")
        if not all(isinstance(descriptor[name], str) and descriptor[name] for name in ("bundle_sha256", "trial_sha256", "system_prompt", "user_prompt", "skill_name", "skill_body")):
            raise ValueError("worker descriptor text is invalid")
        if not isinstance(descriptor["files"], dict) or not all(isinstance(path, str) and isinstance(text, str) for path, text in descriptor["files"].items()):
            raise ValueError("worker descriptor files are invalid")
        if not isinstance(descriptor["fixture_sha256"], str) or not isinstance(descriptor["provider_request_sha256"], str) or not isinstance(descriptor["tool_schema"], dict):
            raise ValueError("worker descriptor fidelity contract is invalid")
        if not isinstance(descriptor["fixture"], dict) or digest(descriptor["fixture"]) != descriptor["fixture_sha256"]:
            raise ValueError("worker fixture digest differs from the sealed request")
        if descriptor["fixture"].get("user_prompt") != descriptor["user_prompt"] or descriptor["fixture"].get("initial_files") != descriptor["files"]:
            raise ValueError("worker fixture contents differ from the sealed request")
        if descriptor["fixture"].get("decoding") != {"temperature": descriptor["temperature"], "max_tokens": descriptor["max_tokens"]}:
            raise ValueError("worker fixture decoding differs from the sealed request")
        if not isinstance(descriptor["max_turns"], int) or descriptor["max_turns"] < 1 or not isinstance(descriptor["max_tokens"], int) or descriptor["max_tokens"] < 1:
            raise ValueError("worker limits are invalid")
        from assist.model_manager import select_assistant_model
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        from deepagents.middleware.filesystem import FilesystemPermission
        from langchain_core.tools import tool
        base._verify_runtime(descriptor["runtime"], select_assistant_model)

        @tool("load_skill")
        def load_skill(name: str) -> str:
            """Load the single listed procedural guide by exact name."""
            return descriptor["skill_body"] if name == descriptor["skill_name"] else "No guide exists under that name."

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative, text in descriptor["files"].items():
                path = base._fixture_path(root, relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            model = select_assistant_model(float(descriptor["temperature"]))
            if not str(getattr(model, "model_name", "")).endswith(descriptor["runtime"]["model_id"]):
                raise ValueError("served model differs from sealed configuration")
            expected_extra = {"chat_template_kwargs": {"enable_thinking": False}} if not descriptor["runtime"]["reasoning_enabled"] else None
            if getattr(model, "extra_body", None) != expected_extra:
                raise ValueError("reasoning configuration differs from sealed configuration")
            model.max_tokens = descriptor["max_tokens"]
            agent = create_deep_agent(model=model, backend=FilesystemBackend(root_dir=str(root), virtual_mode=True), tools=[load_skill], subagents=[], system_prompt=descriptor["system_prompt"], permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"])])
            expected_request = base._rendered_provider_request(system_prompt=descriptor["system_prompt"], user_prompt=descriptor["user_prompt"], files=descriptor["files"], skill_name=descriptor["skill_name"], skill_body=descriptor["skill_body"], temperature=float(descriptor["temperature"]), max_tokens=descriptor["max_tokens"])
            if digest(expected_request) != descriptor["provider_request_sha256"]:
                raise ValueError("post-middleware provider request differs from the sealed request")
            with base._capture_provider_requests(model, marker, expected_request) as capture:
                response = agent.invoke({"messages": [{"role": "user", "content": descriptor["user_prompt"]}]}, {"recursion_limit": descriptor["max_turns"]})
            payload = {"bundle_sha256": descriptor["bundle_sha256"], "trial_sha256": descriptor["trial_sha256"], "fixture_sha256": descriptor["fixture_sha256"], "expected_provider_request": expected_request, "provider_request_error": capture.error, "messages": [base._message_payload(message) for message in response["messages"]], "provider_requests": capture.requests, "files": {path.relative_to(root).as_posix(): path.read_text() for path in root.rglob("*") if path.is_file()}}
            base.atomic_write(result_path, base.canonical_json(payload) + b"\n")


def main() -> None:
    """Expose V2's reviewed command interface under the V3 configuration."""
    with _configured():
        base.main()


if __name__ == "__main__":
    main()
