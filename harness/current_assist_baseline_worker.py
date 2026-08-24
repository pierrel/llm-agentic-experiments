"""The admitted-only worker for the current-Assist baseline."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

from .bundle import StudyBundle, canonical_json


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


def main() -> int:
    if os.environ.get("AGENTIC_EXPERIMENT_ADMITTED") != "1":
        raise RuntimeError("the current-Assist worker requires shared llm admission")
    descriptor = json.loads(Path(sys.argv[1]).read_text())
    result_path = Path(descriptor["worker_result_path"])
    trace_path = Path(descriptor["raw_trace_path"])
    bundle = StudyBundle.read_verified(Path(descriptor["bundle_path"]))
    fixture = Path(descriptor["fixture_path"])
    initial = fixture.read_text()
    model_request_made = False
    try:
        from assist.model_manager import current_model_config, select_assistant_model
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend

        runtime_model = current_model_config()
        model = select_assistant_model(bundle.settings["model"]["temperature"])
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            note = root / "notes" / "today.txt"
            note.parent.mkdir()
            note.write_text(initial)
            agent = create_deep_agent(
                model=model,
                backend=FilesystemBackend(root_dir=str(root), virtual_mode=True),
            )
            model_request_made = True
            response = agent.invoke(
                {"messages": [{"role": "user", "content": bundle.registration["prompt"]}]},
                {"recursion_limit": bundle.settings["episode"]["recursion_limit"]},
            )
            messages = response["messages"]
            trace = [message.model_dump(mode="json") for message in messages]
            trace_path.write_bytes(canonical_json(trace) + b"\n")
            final = note.read_text() if note.exists() else ""
            requested = "Checked by the experiment."
            artifact_success = final.startswith(initial) and final.count(requested) == 1
            tools = _tool_names(messages)
            detail = "artifact matched" if artifact_success else "artifact did not preserve the fixture and one requested line"
            _write(result_path, {
                "outcome": "pass" if artifact_success else "artifact_failure",
                "model_request_made": True,
                "artifact_success": artifact_success,
                "detail": detail,
                "runtime_model": {"id": runtime_model.model, "context_len": runtime_model.context_len},
                "tool_calls": tools,
                "read_before_mutation": "read_file" in tools and (
                    min(index for index, name in enumerate(tools) if name == "read_file")
                    < min((index for index, name in enumerate(tools) if name in {"edit_file", "write_file"}), default=len(tools))
                ),
                "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            })
        return 0
    except Exception as error:
        _write(result_path, {
            "outcome": "provider_error" if model_request_made else "infrastructure_invalid",
            "model_request_made": model_request_made,
            "artifact_success": False,
            "detail": f"{type(error).__name__}: {error}",
        })
        return 1


if __name__ == "__main__":
    sys.exit(main())
