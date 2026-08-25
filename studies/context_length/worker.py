"""One isolated Deep Agents case-handoff episode, entered only through admission."""

from __future__ import annotations

import argparse
import importlib.metadata
import inspect
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Any

from harness.bundle import atomic_write, canonical_json


def run_descriptor(descriptor_path: Path, result_path: Path, request_started_path: Path) -> None:
    """Run exactly the sealed descriptor and retain serializable trace evidence."""
    descriptor = json.loads(descriptor_path.read_text())
    required = {"bundle_sha256", "trial_sha256", "system_prompt", "user_prompt", "files", "max_turns", "temperature", "max_tokens", "runtime"}
    if not isinstance(descriptor, dict) or set(descriptor) != required:
        raise ValueError("context-length worker received an invalid descriptor")
    if not isinstance(descriptor["files"], dict) or not all(isinstance(path, str) and isinstance(text, str) for path, text in descriptor["files"].items()):
        raise ValueError("context-length worker files are invalid")
    if not isinstance(descriptor["max_turns"], int) or descriptor["max_turns"] < 1:
        raise ValueError("context-length worker turn limit is invalid")
    if not isinstance(descriptor["max_tokens"], int) or descriptor["max_tokens"] < 1:
        raise ValueError("context-length worker max_tokens is invalid")
    if not isinstance(descriptor["temperature"], (int, float)) or isinstance(descriptor["temperature"], bool) or descriptor["temperature"] < 0:
        raise ValueError("context-length worker temperature is invalid")
    from assist.model_manager import select_assistant_model
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from deepagents.middleware.filesystem import FilesystemPermission

    _verify_runtime(descriptor["runtime"], select_assistant_model)

    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        for relative, content in descriptor["files"].items():
            path = root / relative
            if path.is_absolute() or ".." in path.parts or not relative:
                raise ValueError("context-length worker file path escapes fixture")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        model = select_assistant_model(float(descriptor["temperature"]))
        _verify_selected_model(model, descriptor["runtime"])
        try:
            model.max_tokens = descriptor["max_tokens"]
        except (AttributeError, ValueError) as error:
            raise ValueError("current Assist model cannot apply the sealed max_tokens") from error
        agent = create_deep_agent(
            model=model,
            backend=FilesystemBackend(root_dir=str(root), virtual_mode=True),
            tools=[], subagents=[], system_prompt=descriptor["system_prompt"],
            permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"])],
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content": descriptor["user_prompt"]}]},
            {"recursion_limit": descriptor["max_turns"], "callbacks": [_request_started_callback(request_started_path)]},
        )
        payload = {
            "bundle_sha256": descriptor["bundle_sha256"],
            "trial_sha256": descriptor["trial_sha256"],
            "messages": [_message_payload(message) for message in result["messages"]],
            "files": {path.relative_to(root).as_posix(): path.read_text() for path in root.rglob("*") if path.is_file()},
        }
        atomic_write(result_path, canonical_json(payload) + b"\n")


def _message_payload(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        value = message.model_dump(mode="json")
    elif isinstance(message, dict):
        value = dict(message)
    else:
        raise ValueError("context-length message is not serializable")
    if not isinstance(value, dict):
        raise ValueError("context-length message payload is invalid")
    json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return value


def _verify_runtime(expected: Any, select_assistant_model: Any) -> None:
    """Reject a changed Assist/model stack before the worker invokes a model."""
    required = {"assist_revision", "deepagents", "langchain", "langgraph", "model_id", "reasoning_enabled"}
    if not isinstance(expected, dict) or set(expected) != required:
        raise ValueError("context-length worker runtime contract is invalid")
    package_versions = {
        name: importlib.metadata.version(name)
        for name in ("deepagents", "langchain", "langgraph")
    }
    if {name: package_versions[name] for name in package_versions} != {
        "deepagents": expected["deepagents"], "langchain": expected["langchain"], "langgraph": expected["langgraph"],
    }:
        raise ValueError("context-length dependency versions differ from the sealed runtime")
    assist_root = Path(inspect.getfile(select_assistant_model)).resolve().parents[1]
    revision = subprocess.run(["git", "-C", str(assist_root), "rev-parse", "HEAD"], capture_output=True, text=True)
    if revision.returncode or revision.stdout.strip() != expected["assist_revision"]:
        raise ValueError("context-length Assist revision differs from the sealed runtime")


def _verify_selected_model(model: Any, expected: dict[str, Any]) -> None:
    """Confirm the discovered endpoint model and reasoning switch before invoke."""
    if getattr(model, "model_name", None) != expected["model_id"]:
        raise ValueError("context-length served model differs from the sealed runtime")
    expected_extra = {"chat_template_kwargs": {"enable_thinking": False}} if not expected["reasoning_enabled"] else None
    if getattr(model, "extra_body", None) != expected_extra:
        raise ValueError("context-length reasoning setting differs from the sealed runtime")


def _request_started_callback(path: Path) -> Any:
    """Create a callback that marks a chat-model lifecycle start, not agent setup."""
    from langchain_core.callbacks import BaseCallbackHandler

    class RequestStarted(BaseCallbackHandler):
        def on_llm_start(self, *args: Any, **kwargs: Any) -> None:
            atomic_write(path, b"model-request-started\n")

        def on_chat_model_start(self, *args: Any, **kwargs: Any) -> None:
            atomic_write(path, b"model-request-started\n")

    return RequestStarted()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--request-started", type=Path, required=True)
    args = parser.parse_args()
    run_descriptor(args.descriptor, args.result, args.request_started)


if __name__ == "__main__":
    main()
