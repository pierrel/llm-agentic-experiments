"""Shared admission/event integrity checks for the exact V8-r3 reproduction."""

from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
import re
from typing import Any

from harness.bundle import digest
from harness.records import OUTCOME_KINDS


DENIAL_RETRY_SECONDS = 600
BATCH_EPISODES = 24
BATCH_PAUSE_SECONDS = 900
DENIAL = re.compile(
    r"^agentic: production is busy \(.+\); not starting (?:llm|real-llm) work\. "
    r"Run `tools/agentic production status --attempt N`, set its next-probe timer, "
    r"and continue other work\.$"
)


def verify_event_interval(record: Any) -> list[dict[str, Any]]:
    """Return ordered event records that fall inside their parent invocation."""
    expected = {
        "admissions_after", "admissions_before", "events", "finished_at",
        "batch_cooldown_mtime_ns", "next_batch_not_before_unix",
        "next_denial_not_before_unix",
        "outcomes_after", "outcomes_before", "started_at",
    }
    if not isinstance(record, dict) or set(record) != expected:
        raise ValueError("runtime event attestation is malformed")
    counts = tuple(
        record[name]
        for name in (
            "admissions_before", "admissions_after", "outcomes_before", "outcomes_after"
        )
    )
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        raise ValueError("runtime event attestation progress is malformed")
    if record["admissions_before"] > record["admissions_after"] or record["outcomes_before"] > record["outcomes_after"]:
        raise ValueError("runtime event attestation progress is reversed")
    for key in ("next_batch_not_before_unix", "next_denial_not_before_unix"):
        not_before = record[key]
        if not_before is not None and (
            not isinstance(not_before, (int, float))
            or isinstance(not_before, bool)
            or not math.isfinite(not_before)
        ):
            raise ValueError("runtime event attestation cadence is malformed")
    cooldown_mtime = record["batch_cooldown_mtime_ns"]
    if cooldown_mtime is not None and (
        not isinstance(cooldown_mtime, int)
        or isinstance(cooldown_mtime, bool)
        or cooldown_mtime < 0
    ):
        raise ValueError("runtime event attestation cooldown identity is malformed")
    events = record["events"]
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        raise ValueError("runtime event attestation is malformed")
    try:
        started = datetime.fromisoformat(record["started_at"])
        finished = datetime.fromisoformat(record["finished_at"])
        times = [datetime.fromisoformat(event["at"]) for event in events]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("runtime event timestamps are malformed") from error
    event_start = started.replace(microsecond=0)
    event_finish = finished.replace(microsecond=0)
    if (
        started.tzinfo is None or finished.tzinfo is None
        or any(value.tzinfo is None for value in times)
        or started > finished or times != sorted(times)
        or any(value < event_start or value > event_finish for value in times)
    ):
        raise ValueError("runtime events fall outside their ordered invocation interval")
    return events


def events_match_admissions(
    *,
    new_admissions: list[dict[str, Any]],
    new_outcomes: list[dict[str, Any]],
    new_events: list[dict[str, Any]],
    thread_id: str,
) -> bool:
    """Require one complete shared-resource transaction per admitted episode."""
    relevant = [
        event for event in new_events
        if event.get("thread") == thread_id and event.get("resource") == "llm"
        and event.get("event") in {
            "production_admission_denied", "resource_started", "resource_finished"
        }
    ]
    terminal = iter(new_outcomes)
    position = 0
    for admission in new_admissions:
        if admission.get("admitted") is False:
            if position >= len(relevant) or relevant[position]["event"] != "production_admission_denied":
                return False
            position += 1
            continue
        if admission.get("admitted") is not True or position >= len(relevant):
            return False
        if relevant[position]["event"] != "resource_started":
            return False
        position += 1
        try:
            outcome = next(terminal)
        except StopIteration:
            return False
        if position < len(relevant) and relevant[position]["event"] == "resource_finished":
            if (
                not isinstance(relevant[position].get("exit_code"), int)
                or isinstance(relevant[position]["exit_code"], bool)
            ):
                return False
            position += 1
        elif outcome.get("outcome") != "timeout":
            return False
    try:
        next(terminal)
    except StopIteration:
        pass
    else:
        return False
    return position == len(relevant)


def verify_records(
    schedule: tuple[Any, ...],
    admissions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
) -> None:
    """Require exact persisted admission and outcome record schemas and semantics."""
    admission_keys = {
        "admitted", "attempt", "bundle_sha256", "detail", "previous_sha256",
        "record_sha256", "trial", "trial_id", "trial_sha256",
    }
    position = 0
    attempts = 0
    for record in admissions:
        if not isinstance(record, dict) or set(record) != admission_keys or position >= len(schedule):
            raise ValueError("admission record schema differs from the parent harness")
        trial = schedule[position]
        if (
            record["trial"] != trial.__dict__
            or record["trial_id"] != trial.id
            or record["trial_sha256"] != trial.sha256
            or not isinstance(record["admitted"], bool)
            or not isinstance(record["attempt"], int)
            or isinstance(record["attempt"], bool)
            or record["attempt"] != attempts + 1
            or not isinstance(record["detail"], str)
            or (not record["admitted"] and DENIAL.fullmatch(record["detail"]) is None)
        ):
            raise ValueError("admission record differs from the scheduled trial")
        attempts += 1
        if record["admitted"]:
            position += 1
            attempts = 0

    outcome_keys = {
        "artifact_success", "bundle_sha256", "detail", "model_request_made",
        "outcome", "previous_sha256", "record_sha256", "trial", "trial_id",
        "trial_sha256",
    }
    for index, record in enumerate(outcomes):
        if not isinstance(record, dict) or set(record) != outcome_keys or index >= len(schedule):
            raise ValueError("outcome record schema differs from the parent harness")
        trial = schedule[index]
        if (
            record["trial"] != trial.__dict__
            or record["trial_id"] != trial.id
            or record["trial_sha256"] != trial.sha256
            or not isinstance(record["outcome"], str)
            or record["outcome"] not in OUTCOME_KINDS
            or not isinstance(record["model_request_made"], bool)
            or not isinstance(record["artifact_success"], bool)
            or not isinstance(record["detail"], str)
            or (record["outcome"] == "pass") is not record["artifact_success"]
            or record["model_request_made"]
            is not (record["outcome"] != "infrastructure_invalid")
        ):
            raise ValueError("outcome record differs from the scheduled trial contract")


def verify_execution_intervals(
    intervals: list[dict[str, Any]],
    *,
    admissions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    thread_id: str,
    schedule_size: int,
) -> list[dict[str, Any]]:
    """Bind each invocation's event slice to its exact progress transition."""
    admission_position = 0
    outcome_position = 0
    all_events: list[dict[str, Any]] = []
    for interval in intervals:
        events = verify_event_interval(interval)
        if (
            interval["admissions_before"] != admission_position
            or interval["outcomes_before"] != outcome_position
            or interval["admissions_after"] > len(admissions)
            or interval["outcomes_after"] > len(outcomes)
        ):
            raise ValueError("runtime event attestation does not form a progress chain")
        new_admissions = admissions[admission_position:interval["admissions_after"]]
        new_outcomes = outcomes[outcome_position:interval["outcomes_after"]]
        denials = [record for record in new_admissions if record.get("admitted") is False]
        if len(denials) > 1 or (denials and new_admissions[-1].get("admitted") is not False):
            raise ValueError("runtime invocation contains an impossible denial sequence")
        if any(
            event.get("thread") != thread_id
            or event.get("resource") != "llm"
            or event.get("event") not in {
                "production_admission_denied", "resource_started", "resource_finished"
            }
            for event in events
        ):
            raise ValueError("runtime invocation contains an unrelated coordination event")
        if len(new_outcomes) > BATCH_EPISODES or not events_match_admissions(
            new_admissions=new_admissions,
            new_outcomes=new_outcomes,
            new_events=events,
            thread_id=thread_id,
        ):
            raise ValueError("runtime event attestation does not match its progress transition")
        admission_position = interval["admissions_after"]
        outcome_position = interval["outcomes_after"]
        all_events.extend(events)
    if admission_position != len(admissions) or outcome_position != len(outcomes):
        raise ValueError("runtime event attestations do not cover complete progress")
    for index, current in enumerate(intervals):
        new_admissions = admissions[
            current["admissions_before"]:current["admissions_after"]
        ]
        denied = bool(new_admissions) and new_admissions[-1]["admitted"] is False
        denial_not_before = current["next_denial_not_before_unix"]
        if denied != (denial_not_before is not None):
            raise ValueError("denial attestation differs from its registered cadence")
        started = datetime.fromisoformat(current["started_at"]).timestamp()
        finished = datetime.fromisoformat(current["finished_at"]).timestamp()
        if denied:
            if denial_not_before < finished + DENIAL_RETRY_SECONDS - 1:
                raise ValueError("production-denial cooldown is shorter than registered")
            if index + 1 < len(intervals):
                resumed = datetime.fromisoformat(intervals[index + 1]["started_at"]).timestamp()
                if resumed < denial_not_before:
                    raise ValueError("production-denial retry occurred before its registered cadence")
        completed = current["outcomes_after"] - current["outcomes_before"]
        requires_pause = completed == BATCH_EPISODES and current["outcomes_after"] < schedule_size
        not_before = current["next_batch_not_before_unix"]
        cooldown_mtime_ns = current["batch_cooldown_mtime_ns"]
        if requires_pause != (not_before is not None) or requires_pause != (
            cooldown_mtime_ns is not None
        ):
            raise ValueError("terminal-batch attestation differs from its registered cadence")
        if not requires_pause:
            continue
        recorded = not_before - BATCH_PAUSE_SECONDS
        cooldown_mtime = cooldown_mtime_ns / 1_000_000_000
        if (
            recorded < started
            or recorded > cooldown_mtime
            or cooldown_mtime > finished
            or cooldown_mtime - recorded > 1
        ):
            raise ValueError("terminal-batch cooldown is not the registered 900 seconds")
        if index + 1 >= len(intervals):
            continue
        resumed = datetime.fromisoformat(intervals[index + 1]["started_at"]).timestamp()
        if resumed < not_before:
            raise ValueError("terminal-batch retry occurred before its registered cadence")
    return all_events


def verify_attestation_inventory(
    attestations: Path,
    *,
    manifest: dict[str, Any],
    registration: dict[str, str],
) -> tuple[list[Path], list[dict[str, Any]]]:
    """Verify one complete attestation inventory and its exact runtime identity."""
    if (
        not isinstance(registration, dict)
        or set(registration) != {"commit", "tag_object", "tree"}
        or any(
            not isinstance(value, str)
            or len(value) != 40
            or any(character not in "0123456789abcdef" for character in value)
            for value in registration.values()
        )
        or registration["commit"] == manifest["parent"]["commit"]
        or registration["tag_object"] == registration["commit"]
    ):
        raise ValueError("reproduction registration identity is malformed")
    paths = sorted(attestations.iterdir())
    if not paths:
        raise ValueError("runtime attestations are missing")
    if any(path.is_symlink() or not path.is_file() or path.suffix != ".json" for path in paths):
        raise ValueError("runtime attestation inventory contains an unexpected entry")
    names = {path.name for path in paths}
    invocations = len(paths) // 3
    expected_names = {
        f"{index:03d}-{suffix}.json"
        for index in range(invocations)
        for suffix in ("events", "identity-after", "identity-before")
    }
    if names != expected_names:
        raise ValueError("runtime attestation inventory is incomplete or unexpected")
    identity_bytes = (attestations / "000-identity-before.json").read_bytes()
    if any(path.read_bytes() != identity_bytes for path in paths if "-identity-" in path.name):
        raise ValueError("runtime identity differs across attestations")
    try:
        identity = json.loads(identity_bytes)
    except json.JSONDecodeError as error:
        raise ValueError("runtime identity attestation is malformed") from error
    expected_runtime = manifest["runtime"]["expected_attestation"]
    expected_identity = {
        "assist": {
            "commit": manifest["runtime"]["assist_commit"],
            "status": "",
            "tree": manifest["runtime"]["assist_tree"],
        },
        "deployment_environment": expected_runtime["deployment_environment"],
        "environment": {
            key: expected_runtime[key]
            for key in ("distributions", "environment", "modules", "python")
        },
        "python_environment": expected_runtime["python_environment"],
        "execution": {
            "commit": manifest["parent"]["commit"],
            "status": "",
            "tree": manifest["parent"]["tree"],
        },
        "manifest_sha256": digest(manifest),
        "publication": {
            "manifest_sha256": digest(manifest),
            "publication_branch": manifest["registration"]["publication_branch"],
            "publication_remote": manifest["registration"]["publication_remote"],
            "registration": registration,
        },
        "registered_model": manifest["runtime"]["model"],
        "registration": registration,
        "process_scope": expected_runtime["process_scope"],
        "shared_gate": expected_runtime["shared_gate"],
    }
    if not isinstance(identity, dict) or set(identity) != set(expected_identity) | {"server"}:
        raise ValueError("runtime identity attestation shape differs from registration")
    if any(identity[key] != value for key, value in expected_identity.items()):
        raise ValueError("runtime identity attestation differs from registration")
    server = identity["server"]
    expected_server = expected_runtime["server"]
    if (
        not isinstance(server, dict)
        or set(server) != set(expected_server) | {"pid", "start_ticks"}
        or not isinstance(server["pid"], int)
        or isinstance(server["pid"], bool)
        or server["pid"] <= 0
        or not isinstance(server["start_ticks"], str)
        or not server["start_ticks"].isdigit()
        or any(server[key] != value for key, value in expected_server.items())
    ):
        raise ValueError("runtime server attestation differs from registration")
    intervals = [
        json.loads((attestations / f"{index:03d}-events.json").read_text())
        for index in range(invocations)
    ]
    return paths, intervals
