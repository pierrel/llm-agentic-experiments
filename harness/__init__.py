"""Small, deterministic building blocks for preregistered agent experiments."""

from .bundle import StudyBundle, Trial
from .invariants import assert_equal_except, assert_no_condition_label
from .records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from .schedule import blocked_schedule

__all__ = [
    "RecordChain",
    "AdmissionAttempt",
    "AdmissionLog",
    "ScheduledAdmission",
    "StudyBundle",
    "Trial",
    "TrialOutcome",
    "assert_equal_except",
    "assert_no_condition_label",
    "blocked_schedule",
]
