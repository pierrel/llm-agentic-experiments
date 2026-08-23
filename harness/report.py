"""Static aggregate reports from sealed deterministic outcomes."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from .bundle import StudyBundle, atomic_write, canonical_json
from .records import RecordChain


def write_static_report(bundle: StudyBundle, chain: RecordChain, output: Path) -> Path:
    """Write a compact report before the caller seals it with the raw artifacts."""
    counts: dict[str, Counter[str]] = {}
    for record in chain.read_verified():
        condition = str(record["trial"]["condition"])
        counts.setdefault(condition, Counter())[str(record["outcome"])] += 1
    report = {
        "bundle_sha256": chain.bundle_sha256,
        "tests": bundle.fixtures,
        "model": bundle.model,
        "harness_architecture": bundle.harness_architecture,
        "settings": bundle.settings,
        "conditions": {
            condition: {outcome: count for outcome, count in sorted(counter.items())}
            for condition, counter in sorted(counts.items())
        },
    }
    atomic_write(output, canonical_json(report) + b"\n")
    return output
