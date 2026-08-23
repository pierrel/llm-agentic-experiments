"""One bounded current-Assist-model episode over a hermetic Deep Agents backend."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from .bundle import canonical_json
from .manifests import TaskManifest


@dataclass(frozen=True)
class CurrentAssistResult:
    """The non-secret evidence retained from one actual model episode."""

    final_response: str
    files: dict[str, str]
    messages: list[dict[str, Any]]


def run_current_assist_episode(
    task: TaskManifest,
    *,
    max_turns: int,
    model_factory: Callable[[float], Any] | None = None,
) -> CurrentAssistResult:
    """Run the production-selected model in the current Deep Agents tool loop.

    Imports occur only inside this function. Unit tests can validate the
    surrounding coordinator without installing Assist or touching its model.
    The only production factory is Assist's ``select_assistant_model``; this
    module deliberately exposes no command-line entry point or model URL.
    """
    if max_turns < 1:
        raise ValueError("current Assist episode requires a positive turn limit")
    _validate_initial_files(task.initial_files)
    if model_factory is None:
        from assist.model_manager import select_assistant_model

        model_factory = select_assistant_model
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from deepagents.middleware.filesystem import FilesystemPermission

    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        for relative_path, content in task.initial_files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        agent = create_deep_agent(
            model=model_factory(float(task.decoding.get("temperature", 0))),
            backend=FilesystemBackend(root_dir=str(root), virtual_mode=True),
            tools=[],
            subagents=[],
            system_prompt=task.system_prompt,
            permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"])],
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content": task.user_prompt}]},
            {"recursion_limit": max_turns},
        )
        messages = [_message_payload(message) for message in result["messages"]]
        return CurrentAssistResult(
            final_response=_message_text(result["messages"][-1]),
            files={path.relative_to(root).as_posix(): path.read_text() for path in root.rglob("*") if path.is_file()},
            messages=messages,
        )


def result_payload(result: CurrentAssistResult) -> dict[str, Any]:
    """Return the deterministic JSON form the coordinator commits to its trace."""
    return {
        "final_response": result.final_response,
        "files": dict(sorted(result.files.items())),
        "messages": result.messages,
    }


def result_bytes(result: CurrentAssistResult) -> bytes:
    """Serialize one result exactly once for the sealed worker boundary."""
    return canonical_json(result_payload(result)) + b"\n"


def _message_payload(message: Any) -> dict[str, Any]:
    """Retain only JSON-compatible message evidence, never a model object."""
    if hasattr(message, "model_dump"):
        payload = message.model_dump(mode="json")
    elif isinstance(message, dict):
        payload = dict(message)
    else:
        raise ValueError("current Assist message is not serializable")
    if not isinstance(payload, dict):
        raise ValueError("current Assist message payload is not an object")
    json.dumps(payload, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return payload


def _message_text(message: Any) -> str:
    """Extract the terminal text without silently accepting structured output."""
    content = getattr(message, "content", message.get("content") if isinstance(message, dict) else None)
    if not isinstance(content, str):
        raise ValueError("current Assist terminal response must be text")
    return content


def _validate_initial_files(files: dict[str, str]) -> None:
    """Keep the virtual fixture inside its temporary root even for a bad descriptor."""
    if not isinstance(files, dict):
        raise ValueError("current Assist initial files must be an object")
    for relative_path, content in files.items():
        path = Path(relative_path)
        if not isinstance(relative_path, str) or not isinstance(content, str):
            raise ValueError("current Assist initial files must map text paths to text")
        if path.is_absolute() or ".." in path.parts or not relative_path:
            raise ValueError("current Assist initial file path escapes the virtual root")
