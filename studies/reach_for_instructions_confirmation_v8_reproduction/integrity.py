"""Shared admission/event integrity checks for the exact V8-r3 reproduction."""

from __future__ import annotations

from datetime import datetime
from typing import Any


DENIAL_RETRY_SECONDS = 600


def verify_event_interval(record: Any) -> list[dict[str, Any]]:
    """Return ordered event records that fall inside their parent invocation."""
    if not isinstance(record, dict) or set(record) != {"events", "finished_at", "started_at"}:
        raise ValueError("runtime event attestation is malformed")
    events = record["events"]
    if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
        raise ValueError("runtime event attestation is malformed")
    try:
        started = datetime.fromisoformat(record["started_at"])
        finished = datetime.fromisoformat(record["finished_at"])
        times = [datetime.fromisoformat(event["at"]) for event in events]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("runtime event timestamps are malformed") from error
    if (
        started.tzinfo is None or finished.tzinfo is None
        or any(value.tzinfo is None for value in times)
        or started > finished or times != sorted(times)
        or any(value < started or value > finished for value in times)
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
            if not isinstance(relevant[position].get("exit_code"), int):
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


def verify_denial_retry_cadence(
    intervals: list[dict[str, Any]], seconds: int = DENIAL_RETRY_SECONDS
) -> None:
    """Require the fixed delay between a denial and its next invocation."""
    for current, following in zip(intervals, intervals[1:]):
        events = verify_event_interval(current)
        if not events or events[-1].get("event") != "production_admission_denied":
            continue
        denied_at = datetime.fromisoformat(current["finished_at"])
        retried_at = datetime.fromisoformat(following["started_at"])
        if (retried_at - denied_at).total_seconds() < seconds:
            raise ValueError("production-denial retry occurred before its registered cadence")
