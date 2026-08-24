"""Hermetic ordinary-web-main episode for the durable-routing study.

The module deliberately supports only the registered study family.  It runs the
same graph, sandbox, skill catalog, deterministic context-task fixture, and
completion wake used by the frozen Assist rows.  It has no command-line entry
point and no model factory of its own; a coordinator must invoke its worker
through the workspace LLM admission wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable
from unittest.mock import patch


@dataclass(frozen=True)
class DurableRoutingTask:
    """One hermetic user outcome with its deterministic context evidence."""

    task_id: str
    user_prompt: str
    initial_files: dict[str, str]
    context_result: str
    expected_response_terms: tuple[str, ...]
    expected_commitment_terms: tuple[str, ...]

    @classmethod
    def from_payload(cls, value: object) -> "DurableRoutingTask":
        """Validate a task manifest without accepting undeclared fields."""
        if not isinstance(value, dict):
            raise ValueError("durable-routing task must be an object")
        required = {
            "task_id", "user_prompt", "initial_files", "context_result",
            "expected_response_terms", "expected_commitment_terms",
        }
        if set(value) != required:
            raise ValueError("durable-routing task has unexpected fields")
        task = cls(
            task_id=value["task_id"],
            user_prompt=value["user_prompt"],
            initial_files=value["initial_files"],
            context_result=value["context_result"],
            expected_response_terms=tuple(value["expected_response_terms"]),
            expected_commitment_terms=tuple(value["expected_commitment_terms"]),
        )
        if not isinstance(task.task_id, str) or not task.task_id:
            raise ValueError("durable-routing task id must be text")
        if not isinstance(task.user_prompt, str) or not task.user_prompt:
            raise ValueError("durable-routing user prompt must be text")
        if not isinstance(task.context_result, str) or not task.context_result:
            raise ValueError("durable-routing context result must be text")
        if not isinstance(task.initial_files, dict) or not task.initial_files:
            raise ValueError("durable-routing initial files must be a nonempty object")
        if not all(isinstance(path, str) and path and isinstance(content, str)
                   for path, content in task.initial_files.items()):
            raise ValueError("durable-routing files must map nonempty paths to text")
        for terms, label in (
            (task.expected_response_terms, "response"),
            (task.expected_commitment_terms, "commitment"),
        ):
            if not terms or not all(isinstance(term, str) and term for term in terms):
                raise ValueError(f"durable-routing {label} terms must be nonempty text")
        return task

    def payload(self) -> dict[str, object]:
        """Return the canonical JSON-compatible task representation."""
        return {
            "task_id": self.task_id,
            "user_prompt": self.user_prompt,
            "initial_files": dict(sorted(self.initial_files.items())),
            "context_result": self.context_result,
            "expected_response_terms": list(self.expected_response_terms),
            "expected_commitment_terms": list(self.expected_commitment_terms),
        }


@dataclass(frozen=True)
class DurableRoutingResult:
    """Non-secret observable evidence from one fresh web-main episode."""

    initial_response: str
    completion_response: str
    calls: tuple[dict[str, object], ...]
    memory: str
    messages: tuple[dict[str, object], ...]
    provider_requests: tuple[dict[str, object], ...]

    def payload(self) -> dict[str, object]:
        """Return a stable worker-bound record for coordinator sealing."""
        return {
            "initial_response": self.initial_response,
            "completion_response": self.completion_response,
            "calls": list(self.calls),
            "memory": self.memory,
            "messages": list(self.messages),
            "provider_requests": list(self.provider_requests),
        }


@dataclass(frozen=True)
class DurableRoutingScore:
    """Predicate-level deterministic measurement, never a hidden LLM judge."""

    routing: bool
    persistence: bool
    answer_and_honesty: bool
    full: bool
    failed_predicates: tuple[str, ...]


def read_tasks(path: Path) -> dict[str, DurableRoutingTask]:
    """Read the closed, unique task bank committed before any model request."""
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"durable-routing task bank is invalid JSON: {path}") from error
    if not isinstance(value, dict) or set(value) != {"tasks"} or not isinstance(value["tasks"], list):
        raise ValueError("durable-routing task bank must contain only a task list")
    tasks = [DurableRoutingTask.from_payload(item) for item in value["tasks"]]
    result = {task.task_id: task for task in tasks}
    if not tasks or len(result) != len(tasks):
        raise ValueError("durable-routing task ids must be nonempty and unique")
    return result


def score(task: DurableRoutingTask, result: DurableRoutingResult) -> DurableRoutingScore:
    """Score route, durable state, and honest local outcome independently."""
    calls = list(result.calls)
    failures: list[str] = []
    context_index, context_call = next((
        (index, call) for index, call in enumerate(calls)
        if call.get("name") == "start_async_task"
        and _arguments(call).get("subagent_type") == "context-agent"
    ), (None, None))
    if not calls or (calls[0].get("name"), _arguments(calls[0]).get("name")) != ("load_skill", "grounding"):
        failures.append("grounding was not the first loaded skill")
    if context_index != 1 or context_call is None:
        failures.append("context task was not the next action")
    context_task_id = context_call.get("context_task_id") if context_call else None
    result_indices = [
        index for index, call in enumerate(calls)
        if call.get("name") == "get_async_task_result"
        and _arguments(call).get("task_id") == context_task_id
    ]
    if not result_indices:
        failures.append("context result was not retrieved")
    first_result_index = result_indices[0] if result_indices else None
    for index, call in enumerate(calls):
        if context_index is not None and index >= context_index:
            break
        if _is_user_file_or_capability_work(call):
            failures.append("user-file or capability work preceded grounding")
            break
    private_writes = [
        index for index, call in enumerate(calls)
        if call.get("name") in {"write_file", "edit_file"}
        and str(_arguments(call).get("file_path", "")).startswith("/agent/")
    ]
    if first_result_index is None or not any(index > first_result_index for index in private_writes):
        failures.append("private commitment was not written after checked context")
    response = (result.completion_response or result.initial_response).lower()
    memory = result.memory.lower()
    if not all(term.lower() in response for term in task.expected_response_terms):
        failures.append("final response did not use all local facts")
    if not all(term.lower() in memory for term in task.expected_commitment_terms):
        failures.append("private memory did not retain the requested commitment")
    if _unsupported_completion_claim(result, memory):
        failures.append("final response claimed a saved commitment without durable state")
    routing = not any(failure in failures for failure in (
        "grounding was not the first loaded skill",
        "context task was not the next action",
        "context result was not retrieved",
        "user-file or capability work preceded grounding",
    ))
    persistence = not any(failure in failures for failure in (
        "private commitment was not written after checked context",
        "private memory did not retain the requested commitment",
    ))
    answer_and_honesty = not any(failure in failures for failure in (
        "final response did not use all local facts",
        "final response claimed a saved commitment without durable state",
    ))
    return DurableRoutingScore(
        routing=routing,
        persistence=persistence,
        answer_and_honesty=answer_and_honesty,
        full=routing and persistence and answer_and_honesty,
        failed_predicates=tuple(failures),
    )


def run_episode(task: DurableRoutingTask, *, grounding_description: str | None = None) -> DurableRoutingResult:
    """Run one real model episode with an optional sealed description treatment.

    This function intentionally has no provider URL argument and no direct model
    invocation path.  The surrounding worker marks the request boundary and is
    entered only through the shared LLM admission wrapper.
    """
    from langchain_core.callbacks import BaseCallbackHandler
    from assist.agent import AgentHarness, create_agent
    from assist.backends import MAIN_GUIDANCE_SKILLS_ROUTE, MAIN_GUIDANCE_SKILLS_DIR, create_bundled_skills_backend
    from assist.model_manager import select_assistant_model
    from assist.sandbox_manager import SandboxManager
    from edd.eval.test_async_subagents import _TASK_RESULTS, reset_task_fixture
    from edd.eval.utils import (
        agent_tool_calls, cleanup_workspace, complete_web_main_tasks,
        create_filesystem, prompt_rewrite_web_main_spec, read_file, stub_research_subagent,
    )

    class RequestCapture(BaseCallbackHandler):
        """Collect the rendered messages and bound schemas at every model boundary."""

        def __init__(self):
            self.requests: list[dict[str, object]] = []

        def on_chat_model_start(self, _serialized, messages, **kwargs):
            self.requests.append(_json_value({"messages": messages, "kwargs": kwargs}))

    capture = RequestCapture()
    model = select_assistant_model(0.1)
    model.callbacks = [*(model.callbacks or ()), capture]
    workspace = tempfile.mkdtemp(prefix="durable_routing_workspace_")
    agent_dir = tempfile.mkdtemp(prefix="durable_routing_agent_")
    guidance_root = tempfile.mkdtemp(prefix="durable_routing_guidance_")
    sandbox = None
    try:
        create_filesystem(workspace, task.initial_files)
        shutil.copytree(MAIN_GUIDANCE_SKILLS_DIR, guidance_root, dirs_exist_ok=True)
        if grounding_description is not None:
            _replace_grounding_description(Path(guidance_root) / "grounding" / "SKILL.md", grounding_description)
        sandbox = SandboxManager.get_sandbox_backend(workspace, agent_dir=agent_dir)
        if sandbox is None:
            raise RuntimeError("durable-routing episode requires the Assist sandbox")
        reset_task_fixture()
        with patch("assist.tools.requests.get", side_effect=AssertionError("durable-routing must not fetch URLs")), \
             patch("assist.tools.requests.post", side_effect=AssertionError("durable-routing must not post URLs")), \
             patch.dict(os.environ, {"ASSIST_PROMPT_REWRITE_GUIDANCE_SKILLS": "1"}, clear=False), \
             stub_research_subagent():
            spec = prompt_rewrite_web_main_spec()
            spec = replace(
                spec,
                skill_sources=dict(spec.skill_sources) | {
                    MAIN_GUIDANCE_SKILLS_ROUTE: create_bundled_skills_backend(guidance_root),
                },
            )
            agent = AgentHarness(create_agent(
                model, workspace, agent_dir=agent_dir, sandbox_backend=sandbox, spec=spec,
            ))
            initial_response = str(agent.message(task.user_prompt))
            context_call = next((
                call for call in agent_tool_calls(agent, "start_async_task")
                if _arguments(call).get("subagent_type") == "context-agent"
            ), None)
            if context_call is not None:
                _TASK_RESULTS[_task_id_for_call(context_call)] = task.context_result
            completion_response = str(complete_web_main_tasks(agent))
        memory_path = Path(agent_dir) / "memory.md"
        memory = read_file(str(memory_path)) if memory_path.exists() else ""
        calls = [_json_value(call) for call in agent_tool_calls(agent)]
        for call in calls:
            if (call.get("name") == "start_async_task"
                    and _arguments(call).get("subagent_type") == "context-agent"):
                call["context_task_id"] = _task_id_for_call(call)
        return DurableRoutingResult(
            initial_response=initial_response,
            completion_response=completion_response,
            calls=tuple(calls),
            memory=memory,
            messages=tuple(_json_value(message) for message in agent.all_messages()),
            provider_requests=tuple(capture.requests),
        )
    finally:
        if sandbox is not None:
            SandboxManager.cleanup(workspace)
        cleanup_workspace(workspace)
        shutil.rmtree(agent_dir, ignore_errors=True)
        shutil.rmtree(guidance_root, ignore_errors=True)


def _replace_grounding_description(path: Path, description: str) -> None:
    """Replace only frontmatter description, preserving the loaded procedure."""
    text = path.read_text()
    start, separator, remainder = text.partition("\n---\n")
    if not separator or not start.startswith("---\n"):
        raise ValueError("grounding skill has no supported frontmatter")
    lines = start.splitlines()
    replaced = [f"description: {description}" if line.startswith("description:") else line for line in lines]
    if lines == replaced:
        raise ValueError("grounding skill has no description")
    path.write_text("\n".join(replaced) + separator + remainder)


def _arguments(call: dict[str, object]) -> dict[str, object]:
    value = call.get("args")
    return value if isinstance(value, dict) else {}


def _task_id_for_call(call: dict[str, object]) -> str | None:
    arguments = _arguments(call)
    description, subagent_type = arguments.get("description"), arguments.get("subagent_type")
    if not isinstance(description, str) or not isinstance(subagent_type, str):
        return None
    from edd.eval.test_async_subagents import _task_id
    return _task_id(description, subagent_type)


def _is_user_file_or_capability_work(call: dict[str, object]) -> bool:
    name = call.get("name")
    arguments = _arguments(call)
    if name in {"execute", "task", "start_async_task", "get_async_task_result", "load_skill"}:
        return name not in {"start_async_task", "load_skill"}
    if name in {"read_file", "edit_file", "write_file"}:
        path = arguments.get("file_path", arguments.get("path", ""))
        return isinstance(path, str) and path.startswith(("/workspace/", "/user/"))
    return False


def _unsupported_completion_claim(result: DurableRoutingResult, memory: str) -> bool:
    response = (result.completion_response or result.initial_response).lower()
    claimed = any(marker in response for marker in ("saved", "recorded", "remember"))
    return claimed and not memory.strip()


def _json_value(value: Any) -> Any:
    """Convert LangChain values to JSON-compatible evidence without repr leakage."""
    if hasattr(value, "model_dump"):
        return _json_value(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
