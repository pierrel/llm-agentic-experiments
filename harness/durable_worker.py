"""Private model worker for one sealed durable-routing episode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bundle import atomic_write, canonical_json
from .durable_routing import DurableRoutingTask, run_episode


def run_descriptor(descriptor_path: Path, result_path: Path, request_started_path: Path) -> None:
    """Run only a coordinator-authenticated descriptor and publish one result."""
    descriptor = json.loads(descriptor_path.read_text())
    required = {"bundle_sha256", "grounding_description", "task", "trial_sha256"}
    if not isinstance(descriptor, dict) or set(descriptor) != required:
        raise ValueError("durable-routing worker received an invalid descriptor")
    if not all(isinstance(descriptor[key], str) for key in (
        "bundle_sha256", "trial_sha256", "grounding_description",
    )):
        raise ValueError("durable-routing worker descriptor requires text identities")
    task = DurableRoutingTask.from_payload(descriptor["task"])
    # The marker distinguishes a failed worker setup from an episode whose real
    # graph reached the provider boundary. It is written immediately before the
    # only operation that can reach Assist's selected model.
    atomic_write(request_started_path, b"model-invoke-started\n")
    result = run_episode(task, grounding_description=descriptor["grounding_description"])
    atomic_write(result_path, canonical_json({
        "bundle_sha256": descriptor["bundle_sha256"],
        "trial_sha256": descriptor["trial_sha256"],
        "result": result.payload(),
    }) + b"\n")


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
