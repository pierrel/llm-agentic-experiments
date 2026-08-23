"""Small, deterministic building blocks for preregistered agent experiments."""

from .bundle import StudyBundle, Trial
from .archive import ResultCapsule, archive_scripted_run
from .episode import Episode, ProviderReply, ScriptedProvider, ToolCall, VirtualWorkspace, read_script, script_sha256
from .invariants import assert_equal_except, assert_no_condition_label
from .manifests import (
    ConditionManifest,
    StudyDefinition,
    TaskManifest,
    mvp_definition,
    mvp_implementation_sha256,
    mvp_script,
)
from .oracles import OracleResult, evaluate
from .records import AdmissionAttempt, AdmissionLog, RecordChain, ScheduledAdmission, TrialOutcome
from .runner import RunArtifacts, run_scripted_study
from .schedule import blocked_schedule

__all__ = [
    "RecordChain",
    "AdmissionAttempt",
    "AdmissionLog",
    "ResultCapsule",
    "ScheduledAdmission",
    "StudyBundle",
    "Trial",
    "TrialOutcome",
    "ConditionManifest",
    "Episode",
    "OracleResult",
    "ProviderReply",
    "RunArtifacts",
    "ScriptedProvider",
    "StudyDefinition",
    "TaskManifest",
    "ToolCall",
    "VirtualWorkspace",
    "assert_equal_except",
    "assert_no_condition_label",
    "archive_scripted_run",
    "blocked_schedule",
    "evaluate",
    "mvp_definition",
    "mvp_implementation_sha256",
    "mvp_script",
    "read_script",
    "run_scripted_study",
    "script_sha256",
]
