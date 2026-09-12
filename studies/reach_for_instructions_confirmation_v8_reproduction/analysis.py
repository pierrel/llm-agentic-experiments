"""Verify and summarize two separately sealed V8-r3 executions."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from harness.records import AdmissionLog, OUTCOME_KINDS, RecordChain
from studies.reach_for_instructions_confirmation_v8_reproduction.integrity import (
    verify_attestation_inventory,
    verify_execution_intervals,
    verify_records,
)


CONTEXT_LINES = {"C-low": 0, "C-medium": 900, "C-high": 3600}
CONDITIONS = ("G01", "G02")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON: {path}") from error


def _verify_capsule(
    capsule: Path,
    *,
    bundle_sha256: str,
    expected_run_sha256: str | None = None,
    expected_hashes: dict[str, str] | None = None,
) -> tuple[
    StudyBundle,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Return verified outcomes and metadata from one complete archived run."""
    if capsule.is_symlink() or not capsule.is_dir():
        raise ValueError("capsule must be a real directory")
    run_path = capsule / "run.json"
    if expected_run_sha256 is not None and _sha256(run_path) != expected_run_sha256:
        raise ValueError("historical capsule run record differs from registration")
    run = _json(run_path)
    if not isinstance(run, dict):
        raise ValueError("capsule run record must be an object")
    claimed = run.pop("record_sha256", None)
    if claimed != digest(run):
        raise ValueError("capsule run record digest mismatch")
    if expected_hashes is not None and claimed != expected_hashes["run_record_sha256"]:
        raise ValueError("historical capsule record identity differs from registration")
    if run.get("bundle_sha256") != bundle_sha256:
        raise ValueError("capsule belongs to another bundle")
    tracked = run.get("tracked_files")
    required_tracked = {
        "admissions.jsonl", "admissions.jsonl.seal", "bundle.json",
        "outcomes.jsonl", "outcomes.jsonl.seal", "report.json",
    }
    if not isinstance(tracked, dict) or set(tracked) != required_tracked:
        raise ValueError("capsule tracked-file inventory is missing")
    for name, expected in tracked.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError("capsule tracked-file inventory is malformed")
        path = Path(name)
        if path.is_absolute() or len(path.parts) != 1:
            raise ValueError("capsule tracked-file inventory is malformed")
        if _sha256(capsule / path) != expected:
            raise ValueError(f"capsule tracked file differs: {name}")
    metadata_path = capsule / "trial-metadata.json"
    if run.get("trial_metadata_sha256") != _sha256(metadata_path):
        raise ValueError("capsule trial metadata is not bound by its run record")
    if expected_hashes is not None:
        fixed = {
            "trial_metadata_file_sha256": metadata_path,
            "admissions_seal_file_sha256": capsule / "admissions.jsonl.seal",
            "outcomes_seal_file_sha256": capsule / "outcomes.jsonl.seal",
            "report_file_sha256": capsule / "report.json",
        }
        for key, path in fixed.items():
            if _sha256(path) != expected_hashes[key]:
                raise ValueError(f"historical capsule differs from registration: {key}")

    bundle = StudyBundle.read_verified(capsule / "bundle.json")
    if bundle.sha256 != bundle_sha256 or len(bundle.schedule) != 72:
        raise ValueError("capsule does not contain the exact complete parent bundle")
    if run.get("schema") != "result-capsule-v1" or run.get("settings") != bundle.settings:
        raise ValueError("capsule run settings differ from its bundle")
    admissions = AdmissionLog(capsule / "admissions.jsonl", bundle.sha256)
    outcomes = RecordChain(capsule / "outcomes.jsonl", bundle.sha256)
    seal = _json(capsule / "outcomes.jsonl.seal")
    if not isinstance(seal, dict):
        raise ValueError("outcome seal must be an object")
    seal_payload = dict(seal)
    seal_claimed = seal_payload.pop("seal_sha256", None)
    if seal_claimed != digest(seal_payload):
        raise ValueError("outcome seal digest mismatch")
    artifacts = seal_payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("outcome seal artifact inventory is missing")
    raw_hashes = run.get("raw_trace_sha256")
    if not isinstance(raw_hashes, dict):
        raise ValueError("capsule raw-trace inventory is missing")
    expected_artifacts = {"report.json": _sha256(capsule / "report.json")} | {
        f"traces/{name}": value for name, value in raw_hashes.items()
    }
    if artifacts != expected_artifacts:
        raise ValueError("capsule trace/report hashes differ from the final seal")
    outcomes.verify_finalized(bundle.schedule, admissions, artifacts)
    admission_records = admissions.read_verified()
    outcome_records = outcomes.read_verified()
    verify_records(bundle.schedule, admission_records, outcome_records)
    metadata = _json(metadata_path)
    if not isinstance(metadata, list) or len(metadata) != len(bundle.schedule):
        raise ValueError("capsule trial metadata is incomplete")
    by_trial = {str(record["trial_sha256"]): record for record in outcome_records}
    for trial, item in zip(bundle.schedule, metadata, strict=True):
        if not isinstance(item, dict) or item.get("trial") != trial.__dict__:
            raise ValueError("trial metadata is not in the sealed schedule order")
        record = by_trial.get(trial.sha256)
        if record is None or item.get("outcome") != record["outcome"] or item.get("detail") != record["detail"]:
            raise ValueError("trial metadata differs from the sealed outcome")
        if item.get("context_lines") != CONTEXT_LINES[trial.task]:
            raise ValueError("trial metadata context dose differs from the bundle")
        token_count = item.get("first_prompt_tokens")
        if token_count is not None and (
            not isinstance(token_count, int)
            or isinstance(token_count, bool)
            or token_count < 0
        ):
            raise ValueError("trial metadata token count is invalid")
        if item.get("skill_loaded_before_first_read") is not None and not isinstance(item["skill_loaded_before_first_read"], bool):
            raise ValueError("trial metadata process measure is invalid")
    return bundle, admission_records, outcome_records, metadata


def _cell_summary(bundle: StudyBundle, metadata: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce the preregistered descriptive six-cell summary."""
    positions: dict[str, int] = {}
    for index in range(0, len(bundle.schedule), 2):
        pair = bundle.schedule[index:index + 2]
        if len(pair) != 2 or pair[0].task != pair[1].task or pair[0].replicate != pair[1].replicate:
            raise ValueError("parent schedule no longer consists of intact condition pairs")
        for position, trial in enumerate(pair, 1):
            positions[trial.sha256] = position

    cells: dict[str, Any] = {}
    for task in CONTEXT_LINES:
        for condition in CONDITIONS:
            entries = [
                item for item in metadata
                if item["trial"]["task"] == task and item["trial"]["condition"] == condition
            ]
            if len(entries) != 12:
                raise ValueError(f"cell does not contain 12 episodes: {task}:{condition}")
            reasons = Counter(str(item["outcome"]) for item in entries)
            request_fidelity_observed = sum(
                item["outcome"] in {"pass", "artifact_failure"} for item in entries
            )
            process = sum(item["skill_loaded_before_first_read"] is True for item in entries)
            process_observed = sum(isinstance(item["skill_loaded_before_first_read"], bool) for item in entries)
            tokens = [item["first_prompt_tokens"] for item in entries if isinstance(item["first_prompt_tokens"], int)]
            position_counts = {
                str(position): Counter(
                    str(item["outcome"])
                    for item in entries
                    if positions[digest(item["trial"])] == position
                )
                for position in (1, 2)
            }
            if any(sum(counter.values()) != 6 for counter in position_counts.values()):
                raise ValueError("condition positions are not balanced within a dose")
            cells[f"{task}:{condition}"] = {
                "context_lines": CONTEXT_LINES[task],
                "condition": condition,
                "denominator": 12,
                "pass": reasons.get("pass", 0),
                "pass_rate": reasons.get("pass", 0) / 12,
                "reason_codes": {
                    outcome: reasons.get(outcome, 0) for outcome in sorted(OUTCOME_KINDS)
                },
                "request_fidelity_observed": request_fidelity_observed,
                "request_fidelity_unobserved": 12 - request_fidelity_observed,
                "skill_loaded_before_first_read": process,
                "skill_loaded_rate": process / process_observed if process_observed else None,
                "skill_loaded_observed": process_observed,
                "skill_loaded_missing": 12 - process_observed,
                "first_prompt_tokens": {
                    "count": len(tokens),
                    "min": min(tokens) if tokens else None,
                    "max": max(tokens) if tokens else None,
                    "values": sorted(tokens),
                },
                "position_outcomes": {
                    position: dict(sorted(counter.items()))
                    for position, counter in position_counts.items()
                },
            }
    contrasts = {}
    for task in CONTEXT_LINES:
        g01 = cells[f"{task}:G01"]["pass_rate"]
        g02 = cells[f"{task}:G02"]["pass_rate"]
        contrasts[task] = {
            "G02_minus_G01_pass_rate": g02 - g01,
            "percentage_points": (g02 - g01) * 100,
        }
    return {"cells": cells, "contrasts": contrasts}


def _verify_reproduction_provenance(
    manifest: dict[str, Any],
    capsule: Path,
    admissions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    registration: dict[str, str],
) -> None:
    """Require the wrapper-produced capsule and attestation binding before analysis."""
    if capsule.name != manifest["execution"]["capsule_id"]:
        raise ValueError("reproduction capsule identity differs from registration")
    path = capsule / "reproduction-provenance.json"
    provenance = _json(path)
    if not isinstance(provenance, dict):
        raise ValueError("reproduction provenance is malformed")
    claimed = provenance.pop("record_sha256", None)
    if claimed != digest(provenance):
        raise ValueError("reproduction provenance digest mismatch")
    attestations = capsule / "runtime-attestations"
    if attestations.is_symlink() or not attestations.is_dir():
        raise ValueError("reproduction runtime attestations are missing")
    paths, intervals = verify_attestation_inventory(
        attestations, manifest=manifest, registration=registration
    )
    thread_id = manifest["execution"]["coordination_thread_id"]
    execution_events = verify_execution_intervals(
        intervals,
        admissions=admissions,
        outcomes=outcomes,
        thread_id=thread_id,
        schedule_size=72,
    )
    files = {
        item.name: _sha256(item) for item in paths
    }
    witness = {
        "admission_count": len(admissions),
        "admissions_file_sha256": _sha256(capsule / "admissions.jsonl"),
        "event_count": len(execution_events),
        "events_sha256": digest(execution_events),
        "outcome_count": len(outcomes),
        "outcomes_file_sha256": _sha256(capsule / "outcomes.jsonl"),
    }
    expected = {
        "attestation_files": files,
        "capsule_run_sha256": _sha256(capsule / "run.json"),
        "coordination_thread_id": thread_id,
        "execution_witness": witness,
        "manifest_sha256": digest(manifest),
        "registration": registration,
        "schema": "reach-v8-exact-reproduction-provenance-v1",
    }
    if provenance != expected or not files:
        raise ValueError("reproduction provenance differs from its evidence")


def _analysis_value(
    manifest: dict[str, Any],
    reproduction_capsule: Path,
    historical_capsule: Path,
    registration: dict[str, str],
) -> dict[str, Any]:
    """Build the locked, separate descriptive reproduction comparison."""
    if reproduction_capsule.resolve() == historical_capsule.resolve():
        raise ValueError("historical capsule cannot substitute for the reproduction")
    parent = manifest["parent"]
    historical = manifest["historical_comparator"]
    reproduction_bundle, reproduction_admissions, reproduction_outcomes, reproduction_metadata = _verify_capsule(
        reproduction_capsule, bundle_sha256=parent["bundle_sha256"]
    )
    _verify_reproduction_provenance(
        manifest,
        reproduction_capsule,
        reproduction_admissions,
        reproduction_outcomes,
        registration,
    )
    historical_bundle, _, _, historical_metadata = _verify_capsule(
        historical_capsule,
        bundle_sha256=parent["bundle_sha256"],
        expected_run_sha256=historical["run_file_sha256"],
        expected_hashes=historical,
    )
    if historical_bundle.payload() != reproduction_bundle.payload():
        raise ValueError("historical and reproduction capsules use different bundles")
    return {
        "analysis": "descriptive exact reproduction; no pooling or binary replication threshold",
        "bundle_sha256": parent["bundle_sha256"],
        "reproduction": _cell_summary(reproduction_bundle, reproduction_metadata),
        "historical": _cell_summary(historical_bundle, historical_metadata),
    }


def analyze(
    manifest: dict[str, Any],
    reproduction_capsule: Path,
    historical_capsule: Path,
    output: Path,
    registration: dict[str, str],
) -> Path:
    """Write the locked, separate descriptive reproduction comparison."""
    value = _analysis_value(
        manifest, reproduction_capsule, historical_capsule, registration
    )
    atomic_write(output, canonical_json(value) + b"\n")
    return output


def verify_existing_analysis(
    manifest: dict[str, Any],
    reproduction_capsule: Path,
    historical_capsule: Path,
    output: Path,
    registration: dict[str, str],
) -> None:
    """Verify that a prior archive contains the exact locked analysis."""
    expected = _analysis_value(
        manifest, reproduction_capsule, historical_capsule, registration
    )
    if _json(output) != expected:
        raise ValueError("sealed reproduction analysis differs from locked analysis")
