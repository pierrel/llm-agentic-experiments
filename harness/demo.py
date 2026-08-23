"""Command-line proof of the sealed no-model MVP schedule."""

from __future__ import annotations

import argparse
from pathlib import Path

from .manifests import mvp_definition, mvp_script
from .runner import RunArtifacts, run_scripted_study

def run(output: Path) -> RunArtifacts:
    """Run the committed fixture, denying the first administrative attempt once."""
    root = Path(__file__).resolve().parents[1]
    denied: set[str] = set()

    def admission(trial_sha256: str, _: int) -> tuple[bool, str]:
        if trial_sha256 not in denied:
            denied.add(trial_sha256)
            return False, "simulated scheduler denial"
        return True, "simulated admission"

    return run_scripted_study(mvp_definition(root), output, mvp_script(root), admission)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new or empty local artifact directory")
    arguments = parser.parse_args()
    artifacts = run(arguments.output)
    print(artifacts.report)


if __name__ == "__main__":
    main()
