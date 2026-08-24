"""The admitted-only worker for the current-Assist baseline."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from .bundle import StudyBundle, canonical_json
from .current_assist_baseline import artifact_matches


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_json(value) + b"\n")


def _tool_names(messages: list[Any]) -> list[str]:
    names: list[str] = []
    for message in messages:
        for call in getattr(message, "tool_calls", []) or []:
            name = call.get("name") if isinstance(call, dict) else None
            if isinstance(name, str):
                names.append(name)
    return names


def _json_value(value: Any) -> Any:
    """Convert callback payloads into local raw evidence without secrets."""
    if hasattr(value, "model_dump"):
        return _json_value(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if str(key).lower() in {"api_key", "authorization"} else _json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


class ProviderRequestCapture(BaseCallbackHandler):
    """Persist every actual request at LangChain's pre-provider boundary."""

    raise_error = True

    def __init__(self, path: Path, bundle: StudyBundle, marker_path: Path) -> None:
        self.path = path
        self.bundle = bundle
        self.marker_path = marker_path
        self.requests: list[dict[str, Any]] = []

    def on_chat_model_start(self, serialized, messages, *, invocation_params, **kwargs) -> None:
        parameters = _json_value(invocation_params)
        tools = parameters.get("tools", []) if isinstance(parameters, dict) else []
        names = {tool.get("function", {}).get("name") for tool in tools if isinstance(tool, dict)}
        required = set(self.bundle.tool_schemas["required_capabilities"])
        if not self.requests and not required.issubset(names):
            raise RuntimeError("actual provider request lacks a sealed filesystem capability")
        if parameters.get("temperature") != self.bundle.settings["model"]["temperature"]:
            raise RuntimeError("actual provider request differs from sealed temperature")
        self.requests.append({"messages": _json_value(messages), "invocation_params": parameters})
        _write(self.path, {"bundle_sha256": self.bundle.sha256, "requests": self.requests})
        self.marker_path.write_bytes(b"request captured\n")


def main() -> int:
    if os.environ.get("AGENTIC_EXPERIMENT_ADMITTED") != "1":
        raise RuntimeError("the current-Assist worker requires shared llm admission")
    descriptor = json.loads(Path(sys.argv[1]).read_text())
    result_path = Path(descriptor["worker_result_path"])
    trace_path = Path(descriptor["raw_trace_path"])
    execution_input_path = Path(descriptor["execution_input_path"])
    request_marker_path = Path(descriptor["request_marker_path"])
    bundle = StudyBundle.read_verified(Path(descriptor["bundle_path"]))
    fixture = Path(descriptor["fixture_path"])
    initial = fixture.read_text()
    model_request_made = False
    try:
        from assist.agent import create_agent
        from assist.model_manager import current_model_config, select_assistant_model
        from assist.spec import AgentSpec
        from deepagents.backends import FilesystemBackend

        runtime_model = current_model_config()
        model = select_assistant_model(
            bundle.settings["model"]["temperature"],
            enable_thinking=bundle.settings["model"]["reasoning"]["enabled"],
        )
        capture = ProviderRequestCapture(execution_input_path, bundle, request_marker_path)
        model.callbacks = [*(model.callbacks or []), capture]
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            note = root / "notes" / "today.txt"
            note.parent.mkdir()
            note.write_text(initial)
            backend = FilesystemBackend(root_dir=str(root), virtual_mode=True)
            expected_fixture = bundle.fixtures["note-edit"]
            fixture_sha256 = hashlib.sha256(initial.encode()).hexdigest()
            if fixture_sha256 != expected_fixture:
                raise ValueError("fixture digest differs from the sealed bundle")
            agent = create_agent(
                model=model,
                working_dir=str(root),
                spec=AgentSpec(default_backend=backend, async_subagent_tools=()),
            )
            response = agent.invoke(
                {"messages": [{"role": "user", "content": bundle.registration["prompt"]}]},
                {
                    "recursion_limit": bundle.settings["episode"]["recursion_limit"],
                    "configurable": {"thread_id": f"experiment:{bundle.study_id}"},
                },
            )
            messages = response["messages"]
            trace = [message.model_dump(mode="json") for message in messages]
            trace_path.write_bytes(canonical_json(trace) + b"\n")
            final = note.read_text() if note.exists() else ""
            requested = "Checked by the experiment."
            artifact_success = artifact_matches(initial, final, requested)
            tools = _tool_names(messages)
            detail = "artifact matched" if artifact_success else "artifact did not preserve the fixture and one requested line"
            _write(result_path, {
                "outcome": "pass" if artifact_success else "artifact_failure",
                "model_request_made": request_marker_path.exists(),
                "artifact_success": artifact_success,
                "detail": detail,
                "runtime_model": {"id": runtime_model.model, "context_len": runtime_model.context_len},
                "tool_calls": tools,
                "read_before_mutation": "read_file" in tools and (
                    min(index for index, name in enumerate(tools) if name == "read_file")
                    < min((index for index, name in enumerate(tools) if name in {"edit_file", "write_file"}), default=len(tools))
                ),
                "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                "execution_input_sha256": hashlib.sha256(execution_input_path.read_bytes()).hexdigest(),
            })
        return 0
    except Exception as error:
        _write(result_path, {
            "outcome": "provider_error" if request_marker_path.exists() else "infrastructure_invalid",
            "model_request_made": request_marker_path.exists(),
            "artifact_success": False,
            "detail": f"{type(error).__name__}: {error}",
        })
        return 1


if __name__ == "__main__":
    sys.exit(main())
