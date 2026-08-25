"""Seal and run the retrieved-versus-handed guidance development screen."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import random
import re
import signal
import stat
import subprocess
from tempfile import TemporaryDirectory
from types import MethodType
from typing import Any

from harness.archive import archive_scripted_run
from harness.bundle import StudyBundle, Trial, atomic_write, canonical_json, digest
from harness.records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from harness.report import write_static_report
from harness.runner import RunArtifacts, _artifact_digests, _valid_trace, _write_trace
from harness.schedule import blocked_schedule


STUDY = "reach-for-instructions-validation-v7"
FIXTURE = "reach-for-instructions-reimbursement-handoff-v5.json"
RENDERED_REQUEST_DIGESTS = "rendered-request-digests.json"
WEIGHTS_SHA256 = "d797b531c527bea28a04fdb326515c43114f798a4fa2a5c1c0e0cffaeaa6fd09"
CONTEXT_LINES = {"C-low": 0, "C-medium": 900, "C-high": 3600}
CONDITION_DELIVERY = {"G01": "handed", "G02": "reached"}
CONDITIONS = tuple(CONDITION_DELIVERY)
SKILL_NAME = "reconcile-reimbursement"
SKILL_CATALOG = (
    "Available procedural guide: reconcile-reimbursement. Use it when a request asks "
    "you to consolidate reimbursement case records into a handoff."
)
PROCEDURE = (
    "For a reimbursement handoff, first inventory the workspace. Read every source "
    "record before writing. Preserve source records. Reconcile only supported facts, "
    "identify unresolved conflicts, and create one structured handoff."
)


@dataclass(frozen=True)
class TrialScore:
    """The deterministic primary score and declared process observations."""

    passed: bool
    detail: str
    first_input_tokens: int | None
    skill_loaded_before_first_read: bool


def _root_task(root: Path) -> dict[str, Any]:
    value = json.loads((root / "fixtures" / FIXTURE).read_text())
    required = {"task_id", "user_prompt", "initial_files", "oracle", "decoding"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("reach-for-instructions fixture shape is invalid")
    if not isinstance(value["task_id"], str) or not isinstance(value["user_prompt"], str):
        raise ValueError("reach-for-instructions fixture text is invalid")
    if not isinstance(value["initial_files"], dict) or not all(
        isinstance(path, str) and isinstance(text, str) for path, text in value["initial_files"].items()
    ):
        raise ValueError("reach-for-instructions fixture files are invalid")
    if not isinstance(value["oracle"], dict) or not isinstance(value["decoding"], dict):
        raise ValueError("reach-for-instructions fixture metadata is invalid")
    return value


def _conditions(root: Path) -> dict[str, dict[str, str]]:
    value = json.loads((root / "experiments" / STUDY / "conditions.json").read_text())
    if not isinstance(value, dict) or set(value) != set(CONDITIONS):
        raise ValueError("reach-for-instructions conditions are invalid")
    for condition, descriptor in value.items():
        if not isinstance(descriptor, dict) or set(descriptor) != {"delivery"} or not isinstance(descriptor["delivery"], str):
            raise ValueError(f"reach-for-instructions condition is invalid: {condition}")
    return value


def _filler(lines: int) -> str:
    """Return deterministic irrelevant declarative material without task vocabulary."""
    return "".join(
        f"Observation {index:05d}: amber shale formed beside a quiet estuary under a measured tide.\n"
        for index in range(1, lines + 1)
    )


def _system_prompt(condition: str, lines: int) -> str:
    """Render the only declared guidance-delivery difference for an episode."""
    if condition not in set(CONDITION_DELIVERY.values()) or lines < 0:
        raise ValueError("invalid reach-for-instructions prompt condition")
    base = _filler(lines) + "You work in a local workspace. " + SKILL_CATALOG
    return base + ("\n\n" + PROCEDURE if condition == "handed" else "")


def _settings(source_commit: str, assist_revision: str) -> dict[str, Any]:
    model = {
        "provider": "local OpenAI-compatible llama.cpp endpoint",
        "model_id": "Qwen_Qwen3.6-27B-Q4_K_M.gguf",
        "weights_sha256": WEIGHTS_SHA256,
        "reasoning": {"enabled": False},
        "temperature": 0.1,
        "max_tokens": 1200,
        "server_context_tokens": 131072,
        "timeout_seconds": 600,
        "cache_policy": "provider-default; no client replay",
    }
    architecture = {
        "id": "deepagents-langchain-tool-loop",
        "deepagents": "0.6.1",
        "langchain": "1.3.1",
        "langgraph": "1.2.0",
        "assist_revision": assist_revision,
        "source_commit": source_commit,
        "backend": "fresh private virtual FilesystemBackend",
        "tools": "Deep Agents default filesystem, TODO, task, and one fixed load_skill tool; no caller-provided tools or subagents",
        "recursion_limit": 20,
    }
    return {"model": model, "harness_architecture": architecture}


def _implementation_sha256(root: Path) -> str:
    paths = [root / "studies" / "reach_for_instructions" / "runner.py", root / "fixtures" / FIXTURE, root / "experiments" / STUDY / "conditions.json", root / "experiments" / STUDY / RENDERED_REQUEST_DIGESTS]
    return digest({str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})


def _schedule() -> tuple[Trial, ...]:
    """Interleave sealed context-dose blocks while preserving each condition pair."""
    blocks = []
    for offset, context in enumerate(CONTEXT_LINES):
        trials = blocked_schedule([context], CONDITIONS, 3, 20260825 + offset)
        blocks.extend(tuple(trials[index:index + len(CONDITIONS)]) for index in range(0, len(trials), len(CONDITIONS)))
    deterministic = random.Random(20260825)
    ordered = []
    while blocks:
        candidates = [block for block in blocks if not ordered or block[0].task != ordered[-1][0].task]
        choice = deterministic.choice(candidates or blocks)
        blocks.remove(choice)
        ordered.append(choice)
    return tuple(trial for block in ordered for trial in block)


def seal(root: Path, *, source_commit: str, assist_revision: str) -> StudyBundle:
    """Write the sealed pre-result bundle for the complete 18-episode schedule."""
    task = _root_task(root)
    conditions = _conditions(root)
    settings = _settings(source_commit, assist_revision)
    schedule = _schedule()
    request_digests = _request_digests(root, schedule)
    registration = {
        "kind": "retrieved_vs_handed_guidance_development",
        "hypothesis_seed": "seeds/2026-08-24-reach-for-instructions.md",
        "source_commit": source_commit,
        "registration_tag": STUDY,
        "max_turns": 20,
        "primary_outcome": "structured reimbursement handoff plus ordered workspace procedure",
        "secondary_outcome": "skill loaded before first source-record read",
        "analysis": "report all reason-coded outcomes and actual provider first-request input tokens by delivery and context cell",
        "randomization_seed": 20260825,
        "position_balance": "adjust_for_position",
        "missingness": "denied admission retries the same trial; every admitted terminal outcome remains",
        "generation_seed": "the local provider does not expose a sealed generation-seed control; trial seeds identify schedule entries only",
        "implementation_sha256": _implementation_sha256(root),
        "provider_request_sha256": request_digests,
    }
    fixture_sha = digest(task)
    bundle = StudyBundle(
        study_id=STUDY,
        registration=registration,
        conditions={name: {"sha256": digest(value)} for name, value in conditions.items()},
        fixtures={context: fixture_sha for context in CONTEXT_LINES},
        tool_schemas={"load_skill": {"name": "load_skill", "arguments": {"name": "string"}}, "deepagents_filesystem": {"mode": "default filesystem and TODO tools", "external_tools": []}},
        schedule=schedule,
        model={"id": "Qwen_Qwen3.6-27B-Q4_K_M.gguf", "revision": "2026-05-01", "configuration_sha256": digest(settings["model"])},
        harness_architecture={"id": "deepagents-langchain-tool-loop", "revision": "v1", "configuration_sha256": digest(settings["harness_architecture"])},
        settings=settings,
        runner_revision="reach-for-instructions-runner-v1",
        analysis_revision="reach-for-instructions-summary-v1",
    )
    bundle.write(root / "experiments" / STUDY / "bundle.json")
    return bundle


def _request_digests(root: Path, schedule: tuple[Trial, ...]) -> dict[str, str]:
    """Read only a complete, pre-rendered request-digest map for this schedule."""
    try:
        value = json.loads((root / "experiments" / STUDY / RENDERED_REQUEST_DIGESTS).read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("sealed provider-request digests are missing or malformed") from error
    expected = {trial.sha256 for trial in schedule}
    if not isinstance(value, dict) or set(value) != expected or not all(isinstance(item, str) and len(item) == 64 for item in value.values()):
        raise ValueError("sealed provider-request digests do not match the schedule")
    return value


def _definition(root: Path) -> tuple[StudyBundle, dict[str, Any], dict[str, dict[str, str]]]:
    bundle_path = root / "experiments" / STUDY / "bundle.json"
    bundle = StudyBundle.read_verified(bundle_path)
    task, conditions = _root_task(root), _conditions(root)
    if bundle.study_id != STUDY or bundle.fixtures != {context: digest(task) for context in CONTEXT_LINES}:
        raise ValueError("reach-for-instructions bundle fixture does not match")
    if bundle.conditions != {name: {"sha256": digest(value)} for name, value in conditions.items()}:
        raise ValueError("reach-for-instructions bundle conditions do not match")
    if bundle.registration.get("implementation_sha256") != _implementation_sha256(root):
        raise ValueError("reach-for-instructions bundle does not match runner implementation")
    tag = bundle.registration.get("registration_tag")
    if not isinstance(tag, str) or not tag:
        raise ValueError("reach-for-instructions registration tag is missing")
    tagged = subprocess.run(["git", "-C", str(root), "show", f"{tag}:experiments/{STUDY}/bundle.json"], capture_output=True)
    if tagged.returncode or tagged.stdout != bundle_path.read_bytes():
        raise ValueError("reach-for-instructions tag does not contain this bundle")
    return bundle, task, conditions


def _assert_rendered_condition_contract() -> None:
    """Prove that delivery is the sole difference within each context dose."""
    for lines in CONTEXT_LINES.values():
        reached = _system_prompt("reached", lines)
        handed = _system_prompt("handed", lines)
        if handed != reached + "\n\n" + PROCEDURE:
            raise ValueError("guidance conditions differ beyond the declared delivery body")


def _worker_command(root: Path, workspace_root: Path, assist_source: Path, assist_python: Path, descriptor: Path, result: Path, marker: Path) -> list[str]:
    """Construct the sole model-capable command, nested below shared admission."""
    return [
        str(workspace_root / "tools" / "agentic"), "resource", "run", "llm", "--",
        "sh", "-c", 'set -a; . "$1"; PYTHONPATH="$2"; export PYTHONPATH; shift 2; exec "$@"', "sh",
        str(workspace_root / "assist" / ".deploy.env"), f"{root}:{assist_source}",
        str(assist_python), "-m", "studies.reach_for_instructions.runner", "worker",
        "--descriptor", str(descriptor.resolve()), "--result", str(result.resolve()), "--request-started", str(marker.resolve()),
    ]


def _descriptor(bundle: StudyBundle, trial: Trial, task: dict[str, Any]) -> dict[str, Any]:
    return {
        "bundle_sha256": bundle.sha256,
        "trial_sha256": trial.sha256,
        "system_prompt": _system_prompt(CONDITION_DELIVERY[trial.condition], CONTEXT_LINES[trial.task]),
        "user_prompt": task["user_prompt"],
        "files": task["initial_files"],
        "skill_name": SKILL_NAME,
        "skill_body": PROCEDURE,
        "max_turns": bundle.registration["max_turns"],
        "temperature": task["decoding"]["temperature"],
        "max_tokens": task["decoding"]["max_tokens"],
        "fixture": task,
        "fixture_sha256": bundle.fixtures[trial.task],
        "provider_request_sha256": bundle.registration["provider_request_sha256"][trial.sha256],
        "tool_schema": bundle.tool_schemas["load_skill"],
        "runtime": {
            "assist_revision": bundle.settings["harness_architecture"]["assist_revision"],
            "deepagents": bundle.settings["harness_architecture"]["deepagents"],
            "langchain": bundle.settings["harness_architecture"]["langchain"],
            "langgraph": bundle.settings["harness_architecture"]["langgraph"],
            "model_id": bundle.settings["model"]["model_id"],
            "reasoning_enabled": bundle.settings["model"]["reasoning"]["enabled"],
        },
    }


def _json_value(value: Any) -> Any:
    """Return a non-secret JSON-shaped provider value or a stable type marker."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if str(key).lower() in {"api_key", "authorization", "headers", "password", "secret"} else _json_value(item)
            for key, item in value.items()
        }
    if hasattr(value, "model_dump"):
        return _json_value(value.model_dump(mode="json"))
    return {"type": f"{type(value).__module__}.{type(value).__qualname__}"}


def _verify_provider_request(descriptor: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Reject a post-admission result whose captured provider request drifted."""
    requests = payload.get("provider_requests")
    if not isinstance(requests, list) or not requests:
        return "provider request capture is missing"
    expected = payload.get("expected_provider_request")
    if not isinstance(expected, dict) or requests[0] != expected:
        return "captured first provider request differs from the sealed request"
    if digest(expected) != descriptor["provider_request_sha256"]:
        return "worker rendered provider request differs from the sealed digest"
    if payload.get("provider_request_error") is not None:
        return "provider request capture reported a contract error"
    if payload.get("fixture_sha256") != descriptor["fixture_sha256"]:
        return "worker fixture identity differs from the sealed request"
    return None


def _provider_request(model: Any, messages: list[Any], stop: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Capture the exact request arguments at ChatOpenAI's provider boundary."""
    if not isinstance(messages, list):
        raise ValueError("provider request messages must be a list")
    return {
        "messages": [_message_payload(message) for message in messages],
        "invocation_params": _json_value(model._get_invocation_params(stop=stop, **kwargs)),
    }


def _rendered_provider_request(*, system_prompt: str, user_prompt: str, files: dict[str, str], skill_name: str, skill_body: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    """Render Deep Agents' first post-middleware provider request without calling it."""
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
        root = Path(temporary)
        for relative, text in files.items():
            path = _fixture_path(root, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        model = select_assistant_model(temperature)
        model.max_tokens = max_tokens
        agent = create_deep_agent(model=model, backend=FilesystemBackend(root_dir=str(root), virtual_mode=True), tools=[load_skill], subagents=[], system_prompt=system_prompt, permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"])])
        captured: dict[str, Any] = {}
        original = model._generate

        def render(self: Any, messages: list[Any], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> Any:
            captured.update(_provider_request(self, messages, stop, kwargs))
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
    """Render every first request locally and store only its pre-seal digest."""
    task = _root_task(root)
    values = {}
    for trial in _schedule():
        request = _rendered_provider_request(system_prompt=_system_prompt(CONDITION_DELIVERY[trial.condition], CONTEXT_LINES[trial.task]), user_prompt=task["user_prompt"], files=task["initial_files"], skill_name=SKILL_NAME, skill_body=PROCEDURE, temperature=task["decoding"]["temperature"], max_tokens=task["decoding"]["max_tokens"])
        values[trial.sha256] = digest(request)
    atomic_write(root / "experiments" / STUDY / RENDERED_REQUEST_DIGESTS, canonical_json(values) + b"\n")


def _terminate_process_group(process: subprocess.Popen[str], signal_number: int) -> None:
    """Signal a dedicated worker group; an already-exited group needs no action."""
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        pass


def _first_input_tokens(messages: list[dict[str, Any]]) -> int | None:
    for message in messages:
        usage = message.get("usage_metadata")
        value = usage.get("input_tokens") if isinstance(usage, dict) else None
        if isinstance(value, int):
            return value
    return None


def _amount_cents(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value == 214.60:
        return 21460
    if isinstance(value, str):
        digits = re.sub(r"[^0-9.]", "", value)
        if digits in {"21460", "214.60"}:
            return 21460
    return None


def _text_contains(value: object, *needles: str) -> bool:
    return isinstance(value, str) and all(needle in value.lower() for needle in needles)


def _payment_not_issued(value: object) -> bool:
    """Accept the two direct, fixture-grounded forms of a non-issued payment."""
    if not isinstance(value, str):
        return False
    normalized = value.lower()
    return (
        "not issued" in normalized
        or ("no payment" in normalized and "issued" in normalized)
        or normalized.strip() in {"not_paid", "not_issued", "no_payment_issued"}
    )


def _score(task: dict[str, Any], payload: dict[str, Any]) -> TrialScore:
    files, messages = payload.get("files"), payload.get("messages")
    if not isinstance(files, dict) or not isinstance(messages, list):
        return TrialScore(False, "worker result is malformed", None, False)
    first_tokens = _first_input_tokens(messages)
    initial = task["initial_files"]
    if any(files.get(path) != text for path, text in initial.items()):
        return TrialScore(False, "a source record changed", first_tokens, False)
    outputs = [path for path in files if path not in initial and path.endswith(".json")]
    if len(outputs) != 1:
        return TrialScore(False, "expected exactly one new JSON handoff", first_tokens, False)
    try:
        handoff = json.loads(files[outputs[0]])
    except (TypeError, json.JSONDecodeError):
        return TrialScore(False, "handoff is not valid JSON", first_tokens, False)
    required = set(task["oracle"]["required_keys"])
    if not isinstance(handoff, dict) or not required.issubset(handoff):
        return TrialScore(False, "handoff lacks required structured fields", first_tokens, False)
    expected = task["oracle"]["expected"]
    amount = handoff.get("amount_cents", handoff.get("verified_amount_cents"))
    uncertainty = handoff.get("uncertainty", handoff.get("remaining_uncertainty"))
    semantic_checks = (
        handoff.get("case_id") == expected["case_id"],
        _amount_cents(amount) == expected["amount_cents"],
        handoff.get("receipt_id") == expected["receipt_id"],
        _payment_not_issued(handoff.get("payment_status")),
        handoff.get("next_owner") == expected["next_owner"],
        _text_contains(handoff.get("next_action"), "select", "receipt") and _text_contains(handoff.get("next_action"), "approve", "return"),
        _text_contains(uncertainty, "receipt", "image") and (_text_contains(uncertainty, "retain") or _text_contains(uncertainty, "select")),
    )
    if not all(semantic_checks):
        return TrialScore(False, "handoff has an unsupported or incomplete fact", first_tokens, False)
    reads, inventory, wrote, loaded, first_source_read = set(), False, False, False, False
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
            elif name == "load_skill" and isinstance(args, dict) and args.get("name") == SKILL_NAME and not first_source_read:
                loaded = True
            elif name == "read_file" and isinstance(path, str):
                first_source_read = True
                if not inventory:
                    return TrialScore(False, "a source read occurred before inventory", first_tokens, loaded)
                reads.add(path.lstrip("/"))
            elif name in {"write_file", "edit_file"}:
                if not inventory or not set(task["oracle"]["required_reads"]).issubset(reads):
                    return TrialScore(False, "a handoff write occurred before all source reads", first_tokens, loaded)
                wrote = True
    if not inventory or not wrote or not set(task["oracle"]["required_reads"]).issubset(reads):
        return TrialScore(False, "trace lacks required inventory, reads, or handoff write", first_tokens, loaded)
    return TrialScore(True, "structured handoff and ordered procedure passed", first_tokens, loaded)


@contextmanager
def _output_lock(output: Path):
    try:
        output.mkdir(parents=True, mode=0o700)
    except FileExistsError:
        pass
    if output.is_symlink() or not output.is_dir():
        raise ValueError("run output must be a real directory")
    if stat.S_IMODE(output.stat().st_mode) != 0o700:
        raise ValueError("run output must be private mode 0700")
    lock = output / ".runner.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        import fcntl
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _recover(bundle: StudyBundle, gate: ScheduledAdmission, outcomes: RecordChain, traces: Path, output: Path) -> None:
    completed = outcomes.read_verified()
    if gate.index == len(completed):
        return
    if gate.index != len(completed) + 1:
        raise ValueError("admission history is not at most one trial ahead of outcomes")
    trial = bundle.schedule[len(completed)]
    trace = traces / f"{trial.sha256}.json"
    if trace.exists() and (trace.is_symlink() or not _valid_trace(trace, trial.sha256)):
        raise ValueError("interrupted trial trace is malformed")
    if not trace.exists():
        _write_trace(trace, {"trial_sha256": trial.sha256, "trace": [], "interrupted": True})
    marker = output / f".{trial.sha256}.request-started"
    outcomes.append(TrialOutcome(
        trial,
        "provider_error" if marker.exists() else "infrastructure_invalid",
        marker.exists(),
        False,
        "worker interrupted after shared admission before recording an outcome",
    ))


def run(root: Path, output: Path, *, workspace_root: Path, assist_source: Path, assist_python: Path) -> RunArtifacts:
    """Run as much of the sealed schedule as shared admission currently permits."""
    root = root.resolve()
    bundle, task, _ = _definition(root)
    _assert_rendered_condition_contract()
    with _output_lock(output):
        bundle_path = output / "bundle.json"
        if bundle_path.exists():
            if StudyBundle.read_verified(bundle_path).sha256 != bundle.sha256:
                raise ValueError("run output belongs to a different bundle")
        elif any(path.name != ".runner.lock" for path in output.iterdir()):
            raise ValueError("new run output is not empty")
        else:
            bundle.write(bundle_path)
        admissions, outcomes = AdmissionLog(output / "admissions.jsonl", bundle.sha256), RecordChain(output / "outcomes.jsonl", bundle.sha256)
        traces = output / "traces"
        if traces.is_symlink() or (traces.exists() and not traces.is_dir()):
            raise ValueError("run traces must be a real directory")
        traces.mkdir(mode=0o700, exist_ok=True)
        gate = ScheduledAdmission(bundle.schedule, admissions)
        _recover(bundle, gate, outcomes, traces, output)
        if gate.current is None:
            report = output / "report.json"
            artifacts = _artifact_digests(bundle, traces, report)
            outcomes.verify_finalized(bundle.schedule, admissions, artifacts)
            return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, traces)
        while gate.current is not None:
            trial = gate.current
            descriptor, result, marker = output / f".{trial.sha256}.descriptor.json", output / f".{trial.sha256}.result.json", output / f".{trial.sha256}.request-started"
            atomic_write(descriptor, canonical_json(_descriptor(bundle, trial, task)) + b"\n")
            attempt = len([record for record in admissions.read_verified() if record["trial_sha256"] == trial.sha256]) + 1
            process = subprocess.Popen(
                _worker_command(root, workspace_root, assist_source, assist_python, descriptor, result, marker),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=bundle.settings["model"]["timeout_seconds"])
            except subprocess.TimeoutExpired:
                _terminate_process_group(process, signal.SIGTERM)
                try:
                    stdout, stderr = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    _terminate_process_group(process, signal.SIGKILL)
                    stdout, stderr = process.communicate()
                if not marker.exists():
                    gate.record(AdmissionAttempt(trial, False, attempt, "worker timed out before model request"))
                    return RunArtifacts(bundle_path, admissions.path, outcomes.path, output / "report.json", traces)
                gate.record(AdmissionAttempt(trial, True, attempt, "worker entered shared admission"))
                _write_trace(traces / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "timeout": True, "trace": []})
                outcomes.append(TrialOutcome(trial, "timeout", True, False, "sealed worker timeout"))
                continue
            detail = (stderr or stdout or "").strip().replace("\n", " ")[-2000:]
            if process.returncode and not marker.exists():
                gate.record(AdmissionAttempt(trial, False, attempt, detail or "worker failed before model invocation"))
                return RunArtifacts(bundle_path, admissions.path, outcomes.path, output / "report.json", traces)
            gate.record(AdmissionAttempt(trial, True, attempt, "worker entered shared admission"))
            if process.returncode:
                _write_trace(traces / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "worker_error": detail, "trace": []})
                outcomes.append(TrialOutcome(trial, "provider_error", True, False, detail or "worker failed"))
                continue
            contract_error = None
            try:
                payload = json.loads(result.read_text())
                if payload.get("bundle_sha256") != bundle.sha256 or payload.get("trial_sha256") != trial.sha256:
                    raise ValueError("worker result identity mismatch")
                contract_error = _verify_provider_request(json.loads(descriptor.read_text()), payload)
                score = TrialScore(False, contract_error, None, False) if contract_error else _score(task, payload)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                contract_error = f"malformed worker result: {error}"
                payload, score = {"messages": [], "files": {}}, TrialScore(False, contract_error, None, False)
            _write_trace(traces / f"{trial.sha256}.json", {"trial_sha256": trial.sha256, "provider_requests": payload.get("provider_requests", []), "trace": payload.get("messages", []), "result": {"files": payload.get("files", {}), "first_prompt_tokens": score.first_input_tokens, "skill_loaded_before_first_read": score.skill_loaded_before_first_read}})
            outcomes.append(TrialOutcome(trial, "pass" if score.passed else ("provider_error" if contract_error else "artifact_failure"), marker.exists(), score.passed, score.detail))
            if contract_error:
                return RunArtifacts(bundle_path, admissions.path, outcomes.path, output / "report.json", traces)
        report = output / "report.json"
        write_static_report(bundle, outcomes, report)
        metadata = []
        by_trial = {record["trial_sha256"]: record for record in outcomes.read_verified()}
        for trial in bundle.schedule:
            trace = json.loads((traces / f"{trial.sha256}.json").read_text())
            result = trace.get("result", {}) if isinstance(trace, dict) else {}
            metadata.append({"trial": trial.__dict__, "context_lines": CONTEXT_LINES[trial.task], "first_prompt_tokens": result.get("first_prompt_tokens") if isinstance(result, dict) else None, "skill_loaded_before_first_read": result.get("skill_loaded_before_first_read") if isinstance(result, dict) else None, "outcome": by_trial[trial.sha256]["outcome"], "detail": by_trial[trial.sha256]["detail"]})
        atomic_write(output / "trial-metadata.json", canonical_json(metadata) + b"\n")
        artifacts = _artifact_digests(bundle, traces, report)
        outcomes.finalize(bundle.schedule, admissions, artifacts)
        return RunArtifacts(bundle_path, admissions.path, outcomes.path, report, traces)


def archive(artifacts: RunArtifacts, destination: Path) -> None:
    """Create the commit-safe capsule and add non-secret cell metadata."""
    capsule = archive_scripted_run(artifacts, destination)
    metadata = artifacts.bundle.parent / "trial-metadata.json"
    atomic_write(destination / "trial-metadata.json", metadata.read_bytes())
    record = json.loads(capsule.record.read_text())
    record.pop("record_sha256")
    record["trial_metadata_sha256"] = hashlib.sha256((destination / "trial-metadata.json").read_bytes()).hexdigest()
    atomic_write(capsule.record, canonical_json(record | {"record_sha256": digest(record)}) + b"\n")


def _fixture_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("fixture path escapes the private workspace")
    return root / candidate


def _message_payload(message: Any) -> dict[str, Any]:
    value = message.model_dump(mode="json") if hasattr(message, "model_dump") else dict(message)
    if not isinstance(value, dict):
        raise ValueError("model message is not serializable")
    json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return value


def _verify_runtime(expected: dict[str, Any], select_assistant_model: Any) -> None:
    import importlib.metadata
    import inspect
    expected_keys = {"assist_revision", "deepagents", "langchain", "langgraph", "model_id", "reasoning_enabled"}
    if set(expected) != expected_keys:
        raise ValueError("worker runtime contract is invalid")
    actual = {name: importlib.metadata.version(name) for name in ("deepagents", "langchain", "langgraph")}
    if actual != {name: expected[name] for name in actual}:
        raise ValueError("runtime dependency versions differ from sealed configuration")
    assist_root = Path(inspect.getfile(select_assistant_model)).resolve().parents[1]
    status = subprocess.run(["git", "-C", str(assist_root), "status", "--porcelain"], capture_output=True, text=True)
    revision = subprocess.run(["git", "-C", str(assist_root), "rev-parse", "HEAD"], capture_output=True, text=True)
    if status.returncode or status.stdout or revision.returncode or revision.stdout.strip() != expected["assist_revision"]:
        raise ValueError("Assist source differs from sealed runtime")


@contextmanager
def _capture_provider_requests(model: Any, path: Path, expected: dict[str, Any]):
    """Capture actual ChatOpenAI provider calls and restore the model afterward."""
    class Capture:
        def __init__(self) -> None:
            self.requests: list[dict[str, Any]] = []
            self.error: str | None = None

    capture = Capture()
    original = model._generate

    def capture_generate(self: Any, messages: list[Any], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> Any:
        atomic_write(path, b"model-request-started\n")
        try:
            request = _provider_request(self, messages, stop, kwargs)
        except (TypeError, ValueError) as error:
            capture.error = str(error)
        else:
            capture.requests.append(request)
            if len(capture.requests) == 1 and request != expected:
                capture.error = "first provider request differs from the sealed request"
        return original(messages, stop=stop, run_manager=run_manager, **kwargs)

    object.__setattr__(model, "_generate", MethodType(capture_generate, model))
    try:
        yield capture
    finally:
        object.__setattr__(model, "_generate", original)


def run_worker(descriptor_path: Path, result_path: Path, marker: Path) -> None:
    """Run one fresh sealed Deep Agents episode after the parent entered admission."""
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
    _verify_runtime(descriptor["runtime"], select_assistant_model)
    @tool("load_skill")
    def load_skill(name: str) -> str:
        """Load a listed procedural guide by exact name."""
        if name != descriptor["skill_name"]:
            return "No guide exists under that name."
        return descriptor["skill_body"]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        for relative, text in descriptor["files"].items():
            path = _fixture_path(root, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        model = select_assistant_model(float(descriptor["temperature"]))
        if getattr(model, "model_name", None) != descriptor["runtime"]["model_id"]:
            raise ValueError("served model differs from sealed configuration")
        expected_extra = {"chat_template_kwargs": {"enable_thinking": False}} if not descriptor["runtime"]["reasoning_enabled"] else None
        if getattr(model, "extra_body", None) != expected_extra:
            raise ValueError("reasoning configuration differs from sealed configuration")
        model.max_tokens = descriptor["max_tokens"]
        agent = create_deep_agent(model=model, backend=FilesystemBackend(root_dir=str(root), virtual_mode=True), tools=[load_skill], subagents=[], system_prompt=descriptor["system_prompt"], permissions=[FilesystemPermission(operations=["read", "write"], paths=["/**"])])
        expected_request = _rendered_provider_request(system_prompt=descriptor["system_prompt"], user_prompt=descriptor["user_prompt"], files=descriptor["files"], skill_name=descriptor["skill_name"], skill_body=descriptor["skill_body"], temperature=float(descriptor["temperature"]), max_tokens=descriptor["max_tokens"])
        if digest(expected_request) != descriptor["provider_request_sha256"]:
            raise ValueError("post-middleware provider request differs from the sealed request")
        with _capture_provider_requests(model, marker, expected_request) as capture:
            response = agent.invoke({"messages": [{"role": "user", "content": descriptor["user_prompt"]}]}, {"recursion_limit": descriptor["max_turns"]})
        payload = {"bundle_sha256": descriptor["bundle_sha256"], "trial_sha256": descriptor["trial_sha256"], "fixture_sha256": descriptor["fixture_sha256"], "expected_provider_request": expected_request, "provider_request_error": capture.error, "messages": [_message_payload(message) for message in response["messages"]], "provider_requests": capture.requests, "files": {path.relative_to(root).as_posix(): path.read_text() for path in root.rglob("*") if path.is_file()}}
        atomic_write(result_path, canonical_json(payload) + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("render", "seal", "run", "archive", "worker"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--assist-revision")
    parser.add_argument("--workspace-root", type=Path, default=Path("/home/pierre/src/agentic"))
    parser.add_argument("--assist-source", type=Path)
    parser.add_argument("--assist-python", type=Path, default=Path("/home/pierre/deploy/assist/code/.venv/bin/python"))
    parser.add_argument("--descriptor", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--request-started", type=Path)
    args = parser.parse_args()
    if args.command == "render":
        render_request_digests(args.root)
    elif args.command == "seal":
        if not args.source_commit or not args.assist_revision:
            raise SystemExit("seal requires --source-commit and --assist-revision")
        seal(args.root, source_commit=args.source_commit, assist_revision=args.assist_revision)
    elif args.command == "run":
        if args.output is None or args.assist_source is None:
            raise SystemExit("run requires --output and --assist-source")
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
