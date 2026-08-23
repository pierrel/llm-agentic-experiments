"""Private worker entered only through the current-Assist pilot coordinator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bundle import atomic_write, canonical_json
from .current_assist import result_payload, run_current_assist_episode
from .manifests import TaskManifest


def run_descriptor(descriptor_path: Path, result_path: Path) -> None:
    """Execute the one sealed task described by the coordinator."""
    descriptor = json.loads(descriptor_path.read_text())
    if set(descriptor) != {"bundle_sha256", "max_turns", "task", "trial_sha256"}:
        raise ValueError("current Assist worker received an invalid descriptor")
    task = TaskManifest(**descriptor["task"])
    if not isinstance(descriptor["max_turns"], int):
        raise ValueError("current Assist worker requires an integer turn limit")
    result = run_current_assist_episode(task, max_turns=descriptor["max_turns"])
    atomic_write(
        result_path,
        canonical_json({
            "bundle_sha256": descriptor["bundle_sha256"],
            "trial_sha256": descriptor["trial_sha256"],
            "result": result_payload(result),
        }) + b"\n",
    )


def main() -> None:
    """Accept only coordinator-produced descriptor and result locations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    run_descriptor(args.descriptor, args.result)


if __name__ == "__main__":
    main()
