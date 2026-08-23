"""Commit-safe result capsules linked to sealed local run artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .bundle import StudyBundle, atomic_write, canonical_json, digest
from .records import AdmissionLog, RecordChain
from .runner import RunArtifacts


@dataclass(frozen=True)
class ResultCapsule:
    """Tracked evidence paths for one completed sealed run."""

    root: Path
    record: Path
    learning: Path
    assist_proposal: Path


def archive_scripted_run(artifacts: RunArtifacts, destination: Path) -> ResultCapsule:
    """Create one immutable, commit-ready capsule from a finalized local run.

    The source trace bodies stay local by default.  Their sealed SHA-256 values,
    along with the complete non-secret setting and result records, are captured
    in the repository so a later learning retains its evidence context.
    """
    if destination.exists() or destination.is_symlink():
        raise ValueError("result capsule destination must be a new real directory")
    bundle = StudyBundle.read_verified(artifacts.bundle)
    outcomes = RecordChain(artifacts.outcomes, bundle.sha256)
    admissions = AdmissionLog(artifacts.admissions, bundle.sha256)
    artifact_digests = _source_artifact_digests(artifacts)
    outcomes.verify_finalized(bundle.schedule, admissions, artifact_digests)

    destination.mkdir(parents=True)
    copied = {
        "bundle.json": artifacts.bundle,
        "admissions.jsonl": artifacts.admissions,
        "admissions.jsonl.seal": artifacts.admissions.with_suffix(".jsonl.seal"),
        "outcomes.jsonl": artifacts.outcomes,
        "outcomes.jsonl.seal": artifacts.outcomes.with_suffix(".jsonl.seal"),
        "report.json": artifacts.report,
    }
    for name, source in copied.items():
        atomic_write(destination / name, source.read_bytes())
    record = {
        "schema": "result-capsule-v1",
        "bundle_sha256": bundle.sha256,
        "settings": bundle.settings,
        "tracked_files": {name: _sha256(destination / name) for name in sorted(copied)},
        "raw_trace_sha256": {
            name.removeprefix("traces/"): value
            for name, value in sorted(artifact_digests.items())
            if name.startswith("traces/")
        },
        "raw_trace_retention": "local results/raw/; not committed by default",
    }
    record_path = destination / "run.json"
    atomic_write(record_path, canonical_json(record | {"record_sha256": digest(record)}) + b"\n")
    learning_path = destination / "learning.md"
    atomic_write(learning_path, _LEARNING_TEMPLATE.encode())
    proposal_path = destination / "assist-roadmap-proposal.md"
    atomic_write(proposal_path, _ASSIST_PROPOSAL_TEMPLATE.encode())
    return ResultCapsule(destination, record_path, learning_path, proposal_path)


def _source_artifact_digests(artifacts: RunArtifacts) -> dict[str, str]:
    """Return the exact report and trace hash inventory bound by the final seal."""
    seal = json.loads(artifacts.outcomes.with_suffix(".jsonl.seal").read_text())
    claimed = seal.pop("seal_sha256", None)
    if claimed != digest(seal):
        raise ValueError("result source final seal digest mismatch")
    expected = seal.get("artifacts")
    if not isinstance(expected, dict) or not all(
        isinstance(name, str) and isinstance(value, str) for name, value in expected.items()
    ):
        raise ValueError("result source final seal lacks artifact hashes")
    actual = {"report.json": _sha256(artifacts.report)} | {
        f"traces/{path.name}": _sha256(path) for path in artifacts.traces.glob("*.json")
    }
    if actual != expected:
        raise ValueError("result source artifacts do not match final seal")
    return actual


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_LEARNING_TEMPLATE = """# Learning pending interpretation

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

No interpretation recorded yet.

## Limits

State what this run cannot establish across tests, models, architectures, or settings.

## Handoffs

When this is a genuine learning, add one private `larochelle.io/seeds/` blog seed
with this capsule as evidence context, and complete `assist-roadmap-proposal.md`.
Neither handoff authorizes an Assist change by itself.
"""


_ASSIST_PROPOSAL_TEMPLATE = """# Proposed Assist roadmap item

## Proposed outcome

No proposal recorded yet.

## Evidence and limits

Link the result capsule and state why the result is sufficient, or why it is
only exploratory. Name adjacent behavior that must remain stable.

## Product action

Describe a proposed Assist roadmap item. Do not implement or merge an Assist
change from this file without Pierre's explicit decision.
"""
