"""Fresh current-profile confirmation of retrieved versus handed guidance."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import threading
from tempfile import TemporaryDirectory
from types import MethodType
from typing import Any, Iterator

from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from harness.runner import RunArtifacts
from studies import equipment_return_oracle_calibration as calibration
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v5 import runner as base


STUDY = "reach-for-instructions-confirmation-v6-qwen38-current"
MODEL_ID = "Qwen3.8-27B-UD-Q4_K_XL.gguf"
WEIGHTS_SHA256 = "3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e"
RANDOMIZATION_SEED = 20260911
REGISTRATION_TAG = "reach-for-instructions-confirmation-v6-qwen38-current-r1"
FIXTURE = calibration.FIXTURE
SKILL_NAME = "prepare-equipment-return"
SKILL_CATALOG = (
    "Available procedural guide: prepare-equipment-return. Use it when a request asks "
    "you to consolidate an equipment-return case into a handoff."
)
PROCEDURE = (
    "For an equipment-return handoff, first inventory the workspace. Read every source "
    "record before writing. Preserve source records. Reconcile only supported facts, "
    "identify unresolved conflicts, and create one structured handoff."
)
_LOCK = threading.RLock()
_CORE_SETTINGS = core._settings
_CORE_WORKER_COMMAND = core._worker_command


def _implementation_sha256(root: Path) -> str:
    """Bind every reused runner layer and every V6-specific design input."""
    paths = [
        root / "studies" / "reach_for_instructions_confirmation_v6" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v5" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v4" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v3" / "runner.py",
        root / "studies" / "reach_for_instructions_confirmation_v2" / "runner.py",
        root / "studies" / "equipment_return_oracle_calibration.py",
        root / "fixtures" / FIXTURE,
        root / "experiments" / STUDY / "conditions.json",
        root / "experiments" / STUDY / core.RENDERED_REQUEST_DIGESTS,
        root / "experiments" / calibration.STUDY / "corpus.json",
    ]
    return digest({str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})


def _settings(source_commit: str, assist_revision: str) -> dict[str, Any]:
    """Record the current Assist Qwen profile, including omitted output limit."""
    settings = _CORE_SETTINGS(source_commit, assist_revision)
    model = settings["model"] | {
        "model_id": MODEL_ID,
        "weights_sha256": WEIGHTS_SHA256,
        "reasoning": {"enabled": True},
        "max_tokens": None,
        "output_token_policy": "omit max_tokens; use the provider default as current Assist does",
    }
    return settings | {"model": model}


def _system_prompt(condition: str, lines: int) -> str:
    """Expose exactly one delivery surface while retaining the same loader schema."""
    if condition not in {"handed", "reached"} or lines < 0:
        raise ValueError("invalid V6 prompt condition")
    common = core._filler(lines) + "You work in a local workspace."
    if condition == "handed":
        return common + "\n\n" + PROCEDURE
    return common + "\n\n" + SKILL_CATALOG


def _assert_rendered_condition_contract() -> None:
    """Prove common task context and one declared delivery difference per dose."""
    for lines in core.CONTEXT_LINES.values():
        common = core._filler(lines) + "You work in a local workspace."
        handed, reached = _system_prompt("handed", lines), _system_prompt("reached", lines)
        if not handed.startswith(common) or not reached.startswith(common):
            raise ValueError("V6 conditions do not share the common system context")
        if PROCEDURE not in handed or PROCEDURE in reached:
            raise ValueError("V6 procedure delivery differs from the declared conditions")
        if SKILL_CATALOG in handed or SKILL_CATALOG not in reached:
            raise ValueError("V6 guide discovery differs from the declared conditions")


def oracle_preflight(root: Path, task: dict[str, Any] | None = None) -> dict[str, Any]:
    """Require independent acceptance and rejection cases before model admission."""
    calibration.verify(root)
    value = json.loads((root / "experiments" / calibration.STUDY / "corpus.json").read_text())
    if task is not None and task != core._root_task(root):
        raise ValueError("V6 calibration task differs from the fixed fixture")
    return value


def _worker_command(*args: Any) -> list[str]:
    """Route every live worker through V6, regardless of inherited layer."""
    command = _CORE_WORKER_COMMAND(*args)
    names = {
        "studies.reach_for_instructions_confirmation_v2.runner",
        "studies.reach_for_instructions_confirmation_v3.runner",
        "studies.reach_for_instructions_confirmation_v4.runner",
        "studies.reach_for_instructions_confirmation_v5.runner",
    }
    return ["studies.reach_for_instructions_confirmation_v6.runner" if value in names else value for value in command]


def _process_skill_load(messages: object) -> bool:
    """Measure guide use independently of the primary artifact outcome."""
    if not isinstance(messages, list):
        return False
    first_source_read = False
    for message in messages:
        calls = message.get("tool_calls", []) if isinstance(message, dict) else []
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, dict):
                continue
            name = call.get("name")
            arguments = call.get("args", call.get("arguments", {}))
            if name == "read_file":
                first_source_read = True
            elif name == "load_skill" and isinstance(arguments, dict) and arguments.get("name") == SKILL_NAME and not first_source_read:
                return True
    return False


def _score(task: dict[str, Any], payload: dict[str, Any]) -> core.TrialScore:
    """Score the equipment handoff while retaining process evidence on failure."""
    files, messages = payload.get("files"), payload.get("messages")
    process_loaded = _process_skill_load(messages)
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
    required = {"case_id", "return_status", "next_owner", "next_action"}
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
                if not inventory or not set(task["oracle"]["required_reads"]).issubset(reads):
                    return core.TrialScore(False, "a handoff write occurred before all source reads", first_tokens, process_loaded)
                wrote = True
    if not inventory or not wrote or not set(task["oracle"]["required_reads"]).issubset(reads):
        return core.TrialScore(False, "trace lacks required inventory, reads, or handoff write", first_tokens, process_loaded)
    return core.TrialScore(True, "structured handoff and ordered procedure passed", first_tokens, process_loaded)


def _rendered_provider_request(*, system_prompt: str, user_prompt: str, files: dict[str, str], skill_name: str, skill_body: str, temperature: float, max_tokens: object) -> dict[str, Any]:
    """Capture the current-Assist request shape with reasoning on and no output cap."""
    if max_tokens is not None:
        raise ValueError("V6 must omit max_tokens")
    from assist.model_manager import select_assistant_model
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from deepagents.middleware.filesystem import FilesystemPermission
    from langchain_core.tools import tool

    class Rendered(Exception):
        pass

    @tool("load_skill")
    def load_skill(name: str) -> str:
        """Load a listed procedural guide by exact name."""
        return skill_body if name == skill_name else "No guide exists under that name."

    with TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        for relative, text in files.items():
            path = core._fixture_path(workspace, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        model = select_assistant_model(temperature, enable_thinking=True)
        if getattr(model, "extra_body", None) is not None or getattr(model, "max_tokens", None) is not None:
            raise ValueError("current Assist model profile differs from V6")
        agent = create_deep_agent(model=model, backend=FilesystemBackend(root_dir=str(workspace), virtual_mode=True), tools=[load_skill], subagents=[], system_prompt=system_prompt, permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"])])
        captured: dict[str, Any] = {}
        original = model._generate

        def render(self: Any, messages: list[Any], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> Any:
            captured.update(core._provider_request(self, messages, stop, kwargs))
            raise Rendered()

        object.__setattr__(model, "_generate", MethodType(render, model))
        try:
            agent.invoke({"messages": [{"role": "user", "content": user_prompt}]})
        except Rendered:
            pass
        finally:
            object.__setattr__(model, "_generate", original)
    if set(captured) != {"messages", "invocation_params"}:
        raise ValueError("Deep Agents did not render a provider request")
    return captured


def render_request_digests(root: Path) -> None:
    """Write the full current-profile request-digest map before sealing."""
    with _configured():
        task = core._root_task(root)
        values = {}
        for trial in core._schedule():
            values[trial.sha256] = digest(_rendered_provider_request(
                system_prompt=_system_prompt(core.CONDITION_DELIVERY[trial.condition], core.CONTEXT_LINES[trial.task]),
                user_prompt=task["user_prompt"], files=task["initial_files"], skill_name=SKILL_NAME,
                skill_body=PROCEDURE, temperature=task["decoding"]["temperature"],
                max_tokens=task["decoding"]["max_tokens"],
            ))
    atomic_write(root / "experiments" / STUDY / core.RENDERED_REQUEST_DIGESTS, canonical_json(values) + b"\n")


def _run_worker(descriptor_path: Path, result_path: Path, marker: Path) -> None:
    """Run one current-profile episode and enforce the captured request contract."""
    descriptor = json.loads(descriptor_path.read_text())
    required = {"bundle_sha256", "trial_sha256", "system_prompt", "user_prompt", "files", "skill_name", "skill_body", "max_turns", "temperature", "max_tokens", "fixture", "fixture_sha256", "provider_request_sha256", "tool_schema", "runtime"}
    if not isinstance(descriptor, dict) or set(descriptor) != required:
        raise ValueError("V6 worker descriptor is invalid")
    if not all(isinstance(descriptor[name], str) and descriptor[name] for name in ("bundle_sha256", "trial_sha256", "system_prompt", "user_prompt", "skill_name", "skill_body")):
        raise ValueError("V6 worker descriptor text is invalid")
    if not isinstance(descriptor["files"], dict) or not all(isinstance(path, str) and isinstance(text, str) for path, text in descriptor["files"].items()):
        raise ValueError("V6 worker files are invalid")
    if not isinstance(descriptor["fixture"], dict) or digest(descriptor["fixture"]) != descriptor["fixture_sha256"]:
        raise ValueError("V6 worker fixture differs from the sealed descriptor")
    if descriptor["fixture"].get("decoding") != {"temperature": descriptor["temperature"], "max_tokens": None} or descriptor["max_tokens"] is not None:
        raise ValueError("V6 worker output-token policy differs from the fixture")
    if not isinstance(descriptor["max_turns"], int) or descriptor["max_turns"] < 1 or not isinstance(descriptor["temperature"], (int, float)):
        raise ValueError("V6 worker limits are invalid")
    from assist.model_manager import select_assistant_model
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from deepagents.middleware.filesystem import FilesystemPermission
    from langchain_core.tools import tool

    core._verify_runtime(descriptor["runtime"], select_assistant_model)

    @tool("load_skill")
    def load_skill(name: str) -> str:
        """Load a listed procedural guide by exact name."""
        return descriptor["skill_body"] if name == descriptor["skill_name"] else "No guide exists under that name."

    with TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        for relative, text in descriptor["files"].items():
            path = core._fixture_path(workspace, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        model = select_assistant_model(float(descriptor["temperature"]), enable_thinking=True)
        if not str(getattr(model, "model_name", "")).endswith(descriptor["runtime"]["model_id"]):
            raise ValueError("served model differs from sealed configuration")
        if getattr(model, "extra_body", None) is not None or getattr(model, "max_tokens", None) is not None:
            raise ValueError("reasoning or output-token policy differs from V6")
        agent = create_deep_agent(model=model, backend=FilesystemBackend(root_dir=str(workspace), virtual_mode=True), tools=[load_skill], subagents=[], system_prompt=descriptor["system_prompt"], permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"])])
        expected_request = _rendered_provider_request(system_prompt=descriptor["system_prompt"], user_prompt=descriptor["user_prompt"], files=descriptor["files"], skill_name=descriptor["skill_name"], skill_body=descriptor["skill_body"], temperature=float(descriptor["temperature"]), max_tokens=descriptor["max_tokens"])
        if digest(expected_request) != descriptor["provider_request_sha256"]:
            raise ValueError("post-middleware provider request differs from the sealed request")
        with core._capture_provider_requests(model, marker, expected_request) as capture:
            response = agent.invoke({"messages": [{"role": "user", "content": descriptor["user_prompt"]}]}, {"recursion_limit": descriptor["max_turns"]})
        payload = {"bundle_sha256": descriptor["bundle_sha256"], "trial_sha256": descriptor["trial_sha256"], "fixture_sha256": descriptor["fixture_sha256"], "expected_provider_request": expected_request, "provider_request_error": capture.error, "messages": [core._message_payload(message) for message in response["messages"]], "provider_requests": capture.requests, "files": {path.relative_to(workspace).as_posix(): path.read_text() for path in workspace.rglob("*") if path.is_file()}}
        atomic_write(result_path, canonical_json(payload) + b"\n")


@contextmanager
def _configured() -> Iterator[None]:
    """Layer V6's new study inputs over the reviewed V5/V2 runner stack."""
    outer = {"STUDY": STUDY, "RANDOMIZATION_SEED": RANDOMIZATION_SEED, "_implementation_sha256": _implementation_sha256, "_worker_command": _worker_command}
    inner = {"FIXTURE": FIXTURE, "SKILL_NAME": SKILL_NAME, "SKILL_CATALOG": SKILL_CATALOG, "PROCEDURE": PROCEDURE, "_system_prompt": _system_prompt, "_settings": _settings, "_implementation_sha256": _implementation_sha256, "_worker_command": _worker_command, "oracle_preflight": oracle_preflight, "_handoff_is_grounded": calibration.handoff_is_grounded, "_score": _score, "_rendered_provider_request": _rendered_provider_request, "_assert_rendered_condition_contract": _assert_rendered_condition_contract, "run_worker": _run_worker}
    with _LOCK:
        outer_originals = {name: getattr(base, name) for name in outer}
        try:
            for name, value in outer.items():
                setattr(base, name, value)
            with base._configured():
                inner_originals = {name: getattr(core, name) for name in inner}
                try:
                    for name, value in inner.items():
                        setattr(core, name, value)
                    yield
                finally:
                    for name, value in inner_originals.items():
                        setattr(core, name, value)
        finally:
            for name, value in outer_originals.items():
                setattr(base, name, value)


def preflight(root: Path) -> None:
    with _configured():
        oracle_preflight(root)


def seal(root: Path, *, source_commit: str, assist_revision: str) -> StudyBundle:
    with _configured():
        sealed = core.seal(root, source_commit=source_commit, assist_revision=assist_revision)
        bundle = replace(
            sealed,
            registration=sealed.registration | {"randomization_seed": RANDOMIZATION_SEED, "registration_tag": REGISTRATION_TAG},
            model={"id": MODEL_ID, "revision": "2026-09-11", "configuration_sha256": digest(sealed.settings["model"])},
            runner_revision="reach-for-instructions-qwen38-current-runner-v1",
            analysis_revision="reach-for-instructions-qwen38-current-summary-v1",
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
        _run_worker(descriptor_path, result_path, marker)


def main() -> None:
    """Expose V6's sealed wrappers through the normal study command interface."""
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
