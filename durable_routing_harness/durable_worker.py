"""Private model worker for one sealed durable-routing episode."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from harness.bundle import atomic_write, canonical_json
from .durable_routing import DurableRoutingTask, run_episode


def run_descriptor(descriptor_path: Path, result_path: Path, request_started_path: Path) -> None:
    """Run one coordinator-built descriptor and publish its complete result."""
    descriptor = json.loads(descriptor_path.read_text())
    required = {"bundle_sha256", "condition_field", "condition_value", "model_settings", "task", "trial_sha256"}
    if not isinstance(descriptor, dict) or set(descriptor) != required:
        raise ValueError("durable-routing worker received an invalid descriptor")
    if not all(isinstance(descriptor[key], str) for key in (
            "bundle_sha256", "trial_sha256", "condition_field",
    )):
        raise ValueError("durable-routing worker descriptor requires text identities")
    _write_lifecycle(request_started_path, "descriptor-validated")
    task = DurableRoutingTask.from_payload(descriptor["task"])
    _write_lifecycle(request_started_path, "task-validated")
    _verify_model_settings(descriptor["model_settings"])
    _write_lifecycle(request_started_path, "model-verified")

    def mark_first_provider_request() -> None:
        """Record the actual model boundary, after setup and immediately before send."""
        _write_lifecycle(request_started_path, "model-invoke-started")

    condition_field, condition_value = descriptor["condition_field"], descriptor["condition_value"]
    if condition_field == "grounding_description" and isinstance(condition_value, str):
        treatment = {"grounding_description": condition_value}
    elif condition_field == "memory_guidance" and isinstance(condition_value, dict):
        treatment = {"memory_guidance": condition_value}
    elif condition_field == "outcome_checklist" and isinstance(condition_value, bool):
        treatment = {"outcome_checklist": condition_value}
    else:
        raise ValueError("durable-routing worker descriptor has an invalid prompt treatment")
    result = run_episode(
        task, model_settings=descriptor["model_settings"],
        on_first_provider_request=mark_first_provider_request, **treatment,
    )
    atomic_write(result_path, canonical_json({
        "bundle_sha256": descriptor["bundle_sha256"],
        "trial_sha256": descriptor["trial_sha256"],
        "result": result.payload(),
    }) + b"\n")


def _write_lifecycle(path: Path, state: str) -> None:
    """Publish a non-sensitive pre-model checkpoint or the provider boundary."""
    atomic_write(path, canonical_json({
        "state": state, "pid": os.getpid(), "process_identity": _process_identity(os.getpid()),
    }) + b"\n")


def _process_identity(pid: int) -> dict[str, str]:
    """Bind a recovery marker to one Linux process incarnation, not merely its PID."""
    stat = Path(f"/proc/{pid}/stat").read_text()
    closing = stat.rfind(")")
    fields = stat[closing + 2:].split()
    if closing < 0 or len(fields) <= 19:
        raise ValueError("process stat lacks a start time")
    command = Path(f"/proc/{pid}/cmdline").read_bytes()
    return {
        "start_time": fields[19],
        "command_sha256": hashlib.sha256(command).hexdigest(),
    }


def _verify_model_settings(value: object) -> None:
    """Check the served model before the graph can issue its first generation."""
    if not isinstance(value, dict):
        raise ValueError("durable-routing worker requires sealed model settings")
    expected_id, expected_context = value.get("model_id"), value.get("context_limit")
    expected_url = value.get("provider_url_sha256")
    if (not isinstance(expected_id, str) or not isinstance(expected_context, int)
            or not isinstance(expected_url, str) or len(expected_url) != 64):
        raise ValueError("durable-routing worker model settings are malformed")
    from assist.model_manager import current_model_config

    actual = current_model_config()
    actual_url = hashlib.sha256(actual.url.encode()).hexdigest()
    if (actual.model != expected_id or actual.context_len != expected_context
            or actual_url != expected_url):
        raise ValueError("durable-routing served model differs from sealed settings")


def main() -> None:
    """Accept descriptor/result paths only from the sealed coordinator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--request-started", type=Path, required=True)
    args = parser.parse_args()
    run_descriptor(args.descriptor, args.result, args.request_started)


if __name__ == "__main__":
    main()
