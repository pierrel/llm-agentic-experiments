"""Run exactly one pre-registered durable-routing development episode."""

from __future__ import annotations

import argparse
from pathlib import Path

from .durable_coordinator import run_durable_routing_once


def main() -> None:
    """Expose no direct-model option and leave scheduling to the coordinator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="private local directory for raw sealed evidence")
    parser.add_argument("--workspace-root", type=Path, required=True,
                        help="agentic workspace containing tools/agentic")
    parser.add_argument("--assist-root", type=Path, required=True,
                        help="registered Assist lane worktree to evaluate")
    parser.add_argument("--assist-python", type=Path, required=True,
                        help="Assist evaluation virtualenv Python")
    parser.add_argument("--assist-env", type=Path, required=True,
                        help="ignored Assist model configuration file")
    parser.add_argument("--study-id", default="durable-promise-routing-v5",
                        help="registered study version to run; never reuse an invalidated output")
    args = parser.parse_args()
    progress = run_durable_routing_once(
        Path(__file__).resolve().parents[1], args.output,
        workspace_root=args.workspace_root, assist_root=args.assist_root,
        assist_python=args.assist_python, assist_env=args.assist_env,
        study_id=args.study_id,
    )
    print(progress.status)


if __name__ == "__main__":
    main()
