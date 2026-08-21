"""Append-only trial records with a tamper-evident local hash chain."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Literal

from .bundle import Trial, canonical_json, digest

OutcomeKind = Literal[
    "pass", "artifact_failure", "timeout", "refusal", "loop_exhausted", "invalid_tool_call",
    "provider_error", "infrastructure_invalid",
]
OUTCOME_KINDS = frozenset(
    {
        "pass",
        "artifact_failure",
        "timeout",
        "refusal",
        "loop_exhausted",
        "invalid_tool_call",
        "provider_error",
        "infrastructure_invalid",
    }
)


@dataclass(frozen=True)
class TrialOutcome:
    """Reason-coded intention-to-treat outcome for one scheduled episode."""

    trial: Trial
    outcome: OutcomeKind
    model_request_made: bool
    artifact_success: bool
    detail: str = ""

    def validate(self) -> None:
        if self.outcome not in OUTCOME_KINDS:
            raise ValueError(f"unknown outcome: {self.outcome}")
        if self.outcome == "pass" and not self.artifact_success:
            raise ValueError("a pass requires a successful artifact")
        if self.outcome != "pass" and self.artifact_success:
            raise ValueError("only a pass may claim successful artifact")
        if self.outcome == "infrastructure_invalid" and self.model_request_made:
            raise ValueError("post-request failures are not infrastructure-invalid")


@dataclass(frozen=True)
class AdmissionAttempt:
    """Administrative GPU admission metadata, never a scored model outcome."""

    trial: Trial
    admitted: bool
    attempt: int
    detail: str = ""


class AdmissionLog:
    """Append-only admission attempts tied to the original scheduled episode."""

    def __init__(self, path: Path, bundle_sha256: str) -> None:
        self.path = path
        self.bundle_sha256 = bundle_sha256

    def append(self, attempt: AdmissionAttempt) -> str:
        records = self.read_verified()
        prior = [record for record in records if record["trial_sha256"] == attempt.trial.sha256]
        if attempt.attempt != len(prior) + 1:
            raise ValueError("admission attempts must be consecutive for one scheduled trial")
        if prior and prior[-1]["admitted"]:
            raise ValueError("cannot retry an admitted trial")
        previous = records[-1]["record_sha256"] if records else self.bundle_sha256
        payload = {
            "bundle_sha256": self.bundle_sha256,
            "trial_id": attempt.trial.id,
            "trial_sha256": attempt.trial.sha256,
            "trial": asdict(attempt.trial),
            "attempt": attempt.attempt,
            "admitted": attempt.admitted,
            "detail": attempt.detail,
            "previous_sha256": previous,
        }
        record = payload | {"record_sha256": digest(payload)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(canonical_json(record) + b"\n")
        return record["record_sha256"]

    def read_verified(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        previous = self.bundle_sha256
        records: list[dict[str, object]] = []
        for line_number, line in enumerate(self.path.read_bytes().splitlines(), 1):
            record = json.loads(line)
            claimed = record.pop("record_sha256", None)
            if claimed != digest(record):
                raise ValueError(f"admission record digest mismatch on line {line_number}")
            if record.get("bundle_sha256") != self.bundle_sha256 or record.get("previous_sha256") != previous:
                raise ValueError(f"admission chain mismatch on line {line_number}")
            record["record_sha256"] = claimed
            previous = claimed
            records.append(record)
        return records

    def progress_index(self, schedule: tuple[Trial, ...]) -> int:
        """Validate the recorded prefix and return the next unadmitted index."""
        index = 0
        for record in self.read_verified():
            if index >= len(schedule) or record["trial_sha256"] != schedule[index].sha256:
                raise ValueError("admission history is not a prefix of the registered schedule")
            if record["admitted"]:
                index += 1
        return index

    def finalize(self, schedule: tuple[Trial, ...]) -> Path:
        """Seal a complete admission history before finalizing outcomes."""
        if self.progress_index(schedule) != len(schedule):
            raise ValueError("cannot finalize incomplete admission history")
        records = self.read_verified()
        seal = {
            "bundle_sha256": self.bundle_sha256,
            "schedule_sha256": digest([trial.__dict__ for trial in schedule]),
            "record_tip_sha256": records[-1]["record_sha256"] if records else self.bundle_sha256,
        }
        seal_path = self.path.with_suffix(self.path.suffix + ".seal")
        seal_path.write_bytes(canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n")
        return seal_path

    def verify_finalized(self, schedule: tuple[Trial, ...]) -> None:
        """Verify the local admission seal and complete registered prefix."""
        seal = json.loads(self.path.with_suffix(self.path.suffix + ".seal").read_text())
        claimed = seal.pop("seal_sha256", None)
        if claimed != digest(seal):
            raise ValueError("admission final seal digest mismatch")
        if self.progress_index(schedule) != len(schedule):
            raise ValueError("admission final seal has incomplete schedule")
        records = self.read_verified()
        if (
            seal.get("bundle_sha256") != self.bundle_sha256
            or seal.get("schedule_sha256") != digest([trial.__dict__ for trial in schedule])
            or seal.get("record_tip_sha256") != (records[-1]["record_sha256"] if records else self.bundle_sha256)
        ):
            raise ValueError("admission final seal does not match record chain")


class ScheduledAdmission:
    """Keep the registered trial order intact across GPU admission denials."""

    def __init__(self, schedule: tuple[Trial, ...], log: AdmissionLog) -> None:
        self.schedule = schedule
        self.log = log
        self.index = log.progress_index(schedule)

    @property
    def current(self) -> Trial | None:
        return self.schedule[self.index] if self.index < len(self.schedule) else None

    def record(self, attempt: AdmissionAttempt) -> bool:
        """Record the current episode attempt and advance only after admission."""
        if attempt.trial != self.current:
            raise ValueError("must retry the current scheduled episode before advancing")
        self.log.append(attempt)
        if attempt.admitted:
            self.index += 1
        return attempt.admitted


class RecordChain:
    """JSONL chain with an explicit final seal for local tamper evidence."""

    def __init__(self, path: Path, bundle_sha256: str) -> None:
        self.path = path
        self.bundle_sha256 = bundle_sha256

    def append(self, result: TrialOutcome) -> str:
        result.validate()
        records = self.read_verified()
        if any(record["trial_sha256"] == result.trial.sha256 for record in records):
            raise ValueError(f"duplicate trial record: {result.trial.id}")
        previous = records[-1]["record_sha256"] if records else self.bundle_sha256
        payload = {
            "bundle_sha256": self.bundle_sha256,
            "trial_id": result.trial.id,
            "trial_sha256": result.trial.sha256,
            "trial": asdict(result.trial),
            "outcome": result.outcome,
            "model_request_made": result.model_request_made,
            "artifact_success": result.artifact_success,
            "detail": result.detail,
            "previous_sha256": previous,
        }
        record = payload | {"record_sha256": digest(payload)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(canonical_json(record) + b"\n")
        return record["record_sha256"]

    def read_verified(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        previous = self.bundle_sha256
        records: list[dict[str, object]] = []
        for line_number, line in enumerate(self.path.read_bytes().splitlines(), 1):
            record = json.loads(line)
            claimed = record.pop("record_sha256", None)
            if claimed != digest(record):
                raise ValueError(f"record digest mismatch on line {line_number}")
            if record.get("bundle_sha256") != self.bundle_sha256 or record.get("previous_sha256") != previous:
                raise ValueError(f"record chain mismatch on line {line_number}")
            record["record_sha256"] = claimed
            previous = claimed
            records.append(record)
        return records

    def assert_schedule_accounted_for(self, schedule: tuple[Trial, ...]) -> None:
        expected = {trial.sha256 for trial in schedule}
        seen = {str(record["trial_sha256"]) for record in self.read_verified()}
        if seen != expected:
            raise ValueError(f"scheduled-record mismatch: missing={expected - seen}, extra={seen - expected}")

    def finalize(self, schedule: tuple[Trial, ...], admission_log: AdmissionLog) -> Path:
        """Write a local seal only after every scheduled episode is accounted for."""
        self.assert_schedule_accounted_for(schedule)
        records = self.read_verified()
        admission_log.finalize(schedule)
        admission_records = admission_log.read_verified()
        admission_tip = admission_records[-1]["record_sha256"] if admission_records else admission_log.bundle_sha256
        seal = {
            "bundle_sha256": self.bundle_sha256,
            "schedule_sha256": digest([trial.__dict__ for trial in schedule]),
            "record_tip_sha256": records[-1]["record_sha256"] if records else self.bundle_sha256,
            "admission_tip_sha256": admission_tip,
        }
        seal_path = self.path.with_suffix(self.path.suffix + ".seal")
        seal_path.write_bytes(canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n")
        return seal_path

    def verify_finalized(self, schedule: tuple[Trial, ...], admission_log: AdmissionLog) -> None:
        """Verify the local final seal, schedule coverage, and record-chain tip."""
        seal_path = self.path.with_suffix(self.path.suffix + ".seal")
        seal = json.loads(seal_path.read_text())
        claimed = seal.pop("seal_sha256", None)
        if claimed != digest(seal):
            raise ValueError("final seal digest mismatch")
        self.assert_schedule_accounted_for(schedule)
        records = self.read_verified()
        if (
            seal.get("bundle_sha256") != self.bundle_sha256
            or seal.get("schedule_sha256") != digest([trial.__dict__ for trial in schedule])
            or seal.get("record_tip_sha256") != (records[-1]["record_sha256"] if records else self.bundle_sha256)
        ):
            raise ValueError("final seal does not match record chain")
        admission_log.verify_finalized(schedule)
        admission_records = admission_log.read_verified()
        expected_tip = admission_records[-1]["record_sha256"] if admission_records else admission_log.bundle_sha256
        if seal.get("admission_tip_sha256") != expected_tip:
            raise ValueError("final seal does not match admission history")
