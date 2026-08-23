"""Hermetic, in-memory agent episodes and their complete provider traces."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Protocol

from .bundle import canonical_json, digest


@dataclass(frozen=True)
class ToolCall:
    """One structured virtual-tool request from a provider reply."""

    name: str
    arguments: dict[str, Any]

    def validate(self) -> None:
        if not isinstance(self.name, str) or not isinstance(self.arguments, dict):
            raise ValueError("tool call name and arguments must be typed")

    def payload(self) -> dict[str, Any]:
        self.validate()
        return {"name": self.name, "arguments": self.arguments}


@dataclass(frozen=True)
class ProviderReply:
    """A provider response containing either tool calls or a final answer."""

    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    final: bool = False

    def validate(self) -> None:
        if not isinstance(self.content, str) or not isinstance(self.final, bool):
            raise ValueError("provider reply content and final flag must be typed")
        if self.final == bool(self.tool_calls):
            raise ValueError("provider reply must be exactly final or tool-calling")
        for call in self.tool_calls:
            if not isinstance(call, ToolCall):
                raise ValueError("provider reply contains an invalid tool call")
            call.validate()

    def payload(self) -> dict[str, Any]:
        self.validate()
        return {
            "content": self.content,
            "final": self.final,
            "tool_calls": [call.payload() for call in self.tool_calls],
        }


class Provider(Protocol):
    """The deliberately narrow provider boundary used by one episode."""

    def respond(self, request: dict[str, Any]) -> ProviderReply:
        """Return one reply for the already-rendered provider request."""


class VirtualWorkspace:
    """A per-episode workspace with no path to the host filesystem."""

    def __init__(self, files: dict[str, str], skills: dict[str, str]) -> None:
        if not isinstance(files, dict) or not isinstance(skills, dict):
            raise ValueError("virtual files and skills must be objects")
        self._files = {self._path(path): content for path, content in files.items()}
        self._skills = dict(skills)
        if not all(isinstance(content, str) for content in self._files.values()):
            raise ValueError("virtual file contents must be text")
        if not all(isinstance(body, str) for body in self._skills.values()):
            raise ValueError("skill bodies must be text")

    @staticmethod
    def _path(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("virtual path must be text")
        path = PurePosixPath(value)
        if (
            not value
            or path.as_posix() == "."
            or path.is_absolute()
            or any(part in {".", ".."} for part in path.parts)
            or path.as_posix() != value
        ):
            raise ValueError(f"invalid virtual path: {value!r}")
        return path.as_posix()

    @staticmethod
    def schemas() -> dict[str, dict[str, Any]]:
        """Return the canonical schemas used to render every episode request."""
        string = {"type": "string"}
        return {
            "list_files": {"parameters": {"type": "object", "properties": {}, "required": []}},
            "read_file": {
                "parameters": {"type": "object", "properties": {"path": string}, "required": ["path"]}
            },
            "write_file": {
                "parameters": {
                    "type": "object",
                    "properties": {"path": string, "content": string},
                    "required": ["path", "content"],
                }
            },
            "load_skill": {
                "parameters": {"type": "object", "properties": {"name": string}, "required": ["name"]}
            },
        }

    def execute(self, call: ToolCall) -> dict[str, Any]:
        """Apply one typed virtual operation and return its deterministic result."""
        arguments = call.arguments
        if call.name == "list_files":
            if not isinstance(arguments, dict) or arguments:
                raise ValueError("list_files takes no arguments")
            return {"files": sorted(self._files)}
        if call.name == "read_file":
            path = self._path(self._required(arguments, "path", {"path"}))
            if path not in self._files:
                raise ValueError(f"virtual file does not exist: {path}")
            return {"path": path, "content": self._files[path]}
        if call.name == "write_file":
            path = self._path(self._required(arguments, "path", {"path", "content"}))
            content = self._required(arguments, "content", {"path", "content"})
            if not isinstance(content, str):
                raise ValueError("virtual file content must be text")
            self._files[path] = content
            return {"path": path, "written": True}
        if call.name == "load_skill":
            name = self._required(arguments, "name", {"name"})
            if name not in self._skills:
                raise ValueError(f"unknown skill: {name}")
            return {"name": name, "body": self._skills[name]}
        raise ValueError(f"unknown virtual tool: {call.name}")

    @staticmethod
    def _required(arguments: dict[str, Any], name: str, allowed: set[str]) -> Any:
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise ValueError("unexpected virtual tool argument")
        if name not in arguments:
            raise ValueError(f"missing virtual tool argument: {name}")
        return arguments[name]

    def snapshot(self) -> dict[str, str]:
        """Return a stable copy used only by a deterministic fixture oracle."""
        return dict(sorted(self._files.items()))


@dataclass(frozen=True)
class EpisodeResult:
    """The terminal in-memory state and complete chronological trace."""

    final_response: str
    files: dict[str, str]
    trace: tuple[dict[str, Any], ...]
    loop_exhausted: bool
    invalid_tool_call: bool
    provider_error: str | None


class Episode:
    """Run one fresh provider conversation against one fresh virtual workspace."""

    def __init__(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        decoding: dict[str, Any],
        workspace: VirtualWorkspace,
        provider: Provider,
        max_turns: int,
        episode_id: str = "episode",
    ) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        if not episode_id:
            raise ValueError("episode_id is required")
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.decoding = deepcopy(decoding)
        self.workspace = workspace
        self.provider = provider
        self.max_turns = max_turns
        self.episode_id = episode_id

    def run(self) -> EpisodeResult:
        """Capture every exact request, reply, call, and virtual-tool result."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]
        trace: list[dict[str, Any]] = []
        invalid_tool_call = False
        for turn in range(1, self.max_turns + 1):
            request = {
                "request_id": f"{self.episode_id}:t{turn}",
                "messages": deepcopy(messages),
                "tools": VirtualWorkspace.schemas(),
                "decoding": deepcopy(self.decoding),
            }
            try:
                reply = self.provider.respond(deepcopy(request))
                payload = reply.payload()
            except Exception as error:
                trace.append(
                    {
                        "turn": turn,
                        "request": request,
                        "provider_error": type(error).__name__,
                        "tools": [],
                    }
                )
                return EpisodeResult(
                    "", self.workspace.snapshot(), tuple(trace), False, invalid_tool_call, type(error).__name__
                )
            event: dict[str, Any] = {"turn": turn, "request": request, "reply": payload, "tools": []}
            if reply.final:
                trace.append(event)
                return EpisodeResult(reply.content, self.workspace.snapshot(), tuple(trace), False, invalid_tool_call, None)
            messages.append(
                {
                    "role": "assistant",
                    "content": reply.content,
                    "tool_calls": payload["tool_calls"],
                }
            )
            for call in reply.tool_calls:
                try:
                    result = self.workspace.execute(call)
                except (TypeError, ValueError) as error:
                    invalid_tool_call = True
                    result = {"error": str(error)}
                event["tools"].append({"call": call.payload(), "result": result})
                messages.append(
                    {
                        "role": "tool",
                        "name": call.name,
                        "content": canonical_json(result).decode(),
                    }
                )
            trace.append(event)
        return EpisodeResult("", self.workspace.snapshot(), tuple(trace), True, invalid_tool_call, None)


class ScriptedProvider:
    """A deterministic provider used to prove the harness without a model."""

    def __init__(self, replies: tuple[ProviderReply, ...]) -> None:
        self._replies = replies
        self._index = 0
        self.requests: list[dict[str, Any]] = []

    def respond(self, request: dict[str, Any]) -> ProviderReply:
        if self._index == len(self._replies):
            raise ValueError("scripted provider exhausted")
        self.requests.append(deepcopy(request))
        reply = self._replies[self._index]
        self._index += 1
        return reply


def read_script(path: str) -> tuple[ProviderReply, ...]:
    """Decode a committed scripted-provider sequence without executing it."""
    import json
    from pathlib import Path

    value = json.loads(Path(path).read_text())
    if not isinstance(value, list) or not value:
        raise ValueError("script must be a non-empty JSON array")
    replies: list[ProviderReply] = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"content", "final", "tool_calls"}:
            raise ValueError("invalid scripted provider reply")
        calls = entry["tool_calls"]
        if not isinstance(calls, list):
            raise ValueError("scripted tool calls must be an array")
        try:
            reply = ProviderReply(
                content=entry["content"],
                final=entry["final"],
                tool_calls=tuple(ToolCall(**call) for call in calls),
            )
            reply.payload()
        except (TypeError, ValueError) as error:
            raise ValueError("invalid scripted provider reply") from error
        replies.append(reply)
    return tuple(replies)


def script_sha256(replies: tuple[ProviderReply, ...]) -> str:
    """Hash exactly the provider behavior permitted by a sealed scripted run."""
    return digest([reply.payload() for reply in replies])
