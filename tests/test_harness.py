from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from harness import (
    RecordChain,
    AdmissionAttempt,
    AdmissionLog,
    ScheduledAdmission,
    StudyBundle,
    Trial,
    TrialOutcome,
    assert_equal_except,
    assert_no_condition_label,
    blocked_schedule,
)
from harness.bundle import digest


def bundle() -> StudyBundle:
    schedule = blocked_schedule(["read-before-edit"], ["A", "B", "C", "D"], 2, seed=7)
    return StudyBundle(
        study_id="study-a-v1",
        registration={"primary": "artifact", "position_balance": "adjust_for_position"},
        conditions={name: {"system": name} for name in "ABCD"},
        fixtures={"read-before-edit": "fixture-sha"},
        tool_schemas={"read_file": {"type": "object"}},
        schedule=schedule,
        model={"id": "scripted-provider", "revision": "v1", "configuration_sha256": digest({"script": "v1"})},
        harness_architecture={"id": "direct-tool-loop", "revision": "v1", "configuration_sha256": digest({"loop": "v1"})},
        settings={"model": {"script": "v1"}, "harness_architecture": {"loop": "v1"}},
        runner_revision="abc",
        analysis_revision="def",
    )


class HarnessTest(unittest.TestCase):
    def test_bundle_fails_closed_after_edit(self):
        with self.subTest("initial bundle"):
            original = bundle()
            original.assert_complete()
        with self.subTest("tampered bundle"):
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as temporary:
                path = Path(temporary) / "bundle.json"
                original.write(path)
                self.assertEqual(StudyBundle.read_verified(path).sha256, original.sha256)
                stored = json.loads(path.read_text())
                stored["bundle"]["conditions"]["A"]["system"] = "tampered"
                path.write_text(json.dumps(stored))
                with self.assertRaisesRegex(ValueError, "digest mismatch"):
                    StudyBundle.read_verified(path)

    def test_bundle_requires_position_policy_for_partial_cycle(self):
        study = bundle()
        with self.assertRaisesRegex(ValueError, "partial position cycle"):
            StudyBundle(
                study_id=study.study_id,
                registration={"primary": "artifact"},
                conditions=study.conditions,
                fixtures=study.fixtures,
                tool_schemas=study.tool_schemas,
                schedule=study.schedule,
                model=study.model,
                harness_architecture=study.harness_architecture,
                settings=study.settings,
                runner_revision=study.runner_revision,
                analysis_revision=study.analysis_revision,
            ).assert_complete()

    def test_bundle_seals_generic_settings_without_one_off_setting_fields(self):
        study = bundle()
        settings = {
            "model": {
                "reasoning": {"enabled": False},
                "temperature": 0,
                "stop": [],
                "provider_metadata": None,
            },
            "harness_architecture": {
                "middleware": ["todo", "filesystem", "skills"],
                "subagents": {"enabled": True},
            },
            "future_setting_type": ["nested", {"values": [1, True, None]}],
        }
        configured = replace(
            study,
            model=study.model | {"configuration_sha256": digest(settings["model"])},
            harness_architecture=study.harness_architecture | {
                "configuration_sha256": digest(settings["harness_architecture"])
            },
            settings=settings,
        )
        configured.assert_complete()
        with self.assertRaisesRegex(ValueError, "JSON-safe"):
            replace(
                configured,
                settings=configured.settings | {"invalid": float("nan")},
            ).assert_complete()

    def test_bundle_rejects_full_cycle_with_unbalanced_positions(self):
        study = bundle()
        unbalanced = tuple(
            Trial("read-before-edit", replicate, condition, replicate)
            for replicate in range(1, 5)
            for condition in "ABCD"
        )
        with self.assertRaisesRegex(ValueError, "unbalanced condition positions"):
            StudyBundle(
                study_id=study.study_id,
                registration={"primary": "artifact"},
                conditions=study.conditions,
                fixtures=study.fixtures,
                tool_schemas=study.tool_schemas,
                schedule=unbalanced,
                model=study.model,
                harness_architecture=study.harness_architecture,
                settings=study.settings,
                runner_revision=study.runner_revision,
                analysis_revision=study.analysis_revision,
            ).assert_complete()

    def test_schedule_interleaves_and_counterbalances_full_condition_blocks(self):
        schedule = blocked_schedule(["one", "two"], ["A", "B", "C"], 3, seed=4)
        positions: dict[str, set[int]] = {condition: set() for condition in "ABC"}
        for offset in range(0, len(schedule), 3):
            block = schedule[offset : offset + 3]
            self.assertEqual({trial.condition for trial in block}, {"A", "B", "C"})
            self.assertEqual(len({trial.generation_seed for trial in block}), 3)
            for position, trial in enumerate(block):
                positions[trial.condition].add(position)
        self.assertEqual(positions, {condition: {0, 1, 2} for condition in "ABC"})

    def test_schedule_reuses_generation_seed_only_when_explicit(self):
        schedule = blocked_schedule(
            ["one"], ["A", "B", "C"], 1, seed=4, reuse_generation_seed_across_conditions=True
        )
        self.assertEqual(len({trial.generation_seed for trial in schedule}), 1)

    def test_invariant_and_label_checks_fail_closed(self):
        baseline = {"prompt": "same", "schema": {"read": True}, "fixture": "one", "decode": 0}
        candidate = baseline | {"prompt": "declared treatment"}
        assert_equal_except(baseline, candidate, {"prompt"})
        with self.assertRaisesRegex(ValueError, "undeclared"):
            assert_equal_except(baseline, candidate | {"fixture": "other"}, {"prompt"})
        with self.assertRaisesRegex(ValueError, "label leaked"):
            assert_no_condition_label("Repeated condition trace", {"Repeated", "System-only"})
        with self.assertRaisesRegex(ValueError, "label leaked"):
            assert_no_condition_label("SYSTEM ONLY condition trace", {"System-only"})

    def test_chain_rejects_tampering_and_missing_trials(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            study = bundle()
            path = Path(temporary) / "records.jsonl"
            chain = RecordChain(path, study.sha256)
            for trial in study.schedule:
                chain.append(TrialOutcome(trial, "pass", True, True))
            chain.assert_schedule_accounted_for(study.schedule)
            path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
            with self.assertRaisesRegex(ValueError, "scheduled-record mismatch"):
                chain.assert_schedule_accounted_for(study.schedule)

    def test_chain_rejects_an_edited_record(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "records.jsonl"
            chain = RecordChain(path, "bundle")
            chain.append(TrialOutcome(Trial("task", 1, "A", 1), "pass", True, True))
            record = json.loads(path.read_text())
            record["outcome"] = "timeout"
            path.write_text(json.dumps(record) + "\n")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                chain.read_verified()

    def test_record_append_rolls_back_a_partial_write(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "records.jsonl"
            chain = RecordChain(path, "bundle")
            first = Trial("task", 1, "A", 1)
            second = Trial("task", 1, "B", 2)
            chain.append(TrialOutcome(first, "pass", True, True))
            original_write = os.write
            calls = 0

            def partial_then_fail(descriptor: int, data: object) -> int:
                nonlocal calls
                calls += 1
                if calls == 1:
                    return original_write(descriptor, bytes(data)[:7])
                raise OSError("simulated write failure")

            with patch("harness.records.os.write", side_effect=partial_then_fail):
                with self.assertRaisesRegex(OSError, "simulated write failure"):
                    chain.append(TrialOutcome(second, "pass", True, True))
            self.assertEqual([record["trial_sha256"] for record in chain.read_verified()], [first.sha256])

    def test_final_seal_rejects_a_truncated_chain(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            study = bundle()
            path = Path(temporary) / "records.jsonl"
            chain = RecordChain(path, study.sha256)
            for trial in study.schedule:
                chain.append(TrialOutcome(trial, "pass", True, True))
            admissions = AdmissionLog(Path(temporary) / "admission.jsonl", study.sha256)
            gate = ScheduledAdmission(study.schedule, admissions)
            for trial in study.schedule:
                gate.record(AdmissionAttempt(trial, True, 1))
            chain.finalize(study.schedule, admissions)
            path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
            with self.assertRaisesRegex(ValueError, "scheduled-record mismatch"):
                chain.verify_finalized(study.schedule, admissions)

    def test_final_seal_rejects_outcomes_not_matching_admitted_order(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            study = bundle()
            outcomes = RecordChain(Path(temporary) / "outcomes.jsonl", study.sha256)
            for trial in reversed(study.schedule):
                outcomes.append(TrialOutcome(trial, "pass", True, True))
            admissions = AdmissionLog(Path(temporary) / "admissions.jsonl", study.sha256)
            for trial in study.schedule:
                admissions.append(AdmissionAttempt(trial, True, 1))
            with self.assertRaisesRegex(ValueError, "ordered one-to-one"):
                outcomes.finalize(study.schedule, admissions)

    def test_admission_log_retries_same_episode_before_admission(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            trial = Trial("task", 1, "A", 1)
            log = AdmissionLog(Path(temporary) / "admission.jsonl", "bundle")
            later = Trial("task", 1, "B", 2)
            gate = ScheduledAdmission((trial, later), log)
            self.assertFalse(gate.record(AdmissionAttempt(trial, False, 1, "production busy")))
            with self.assertRaisesRegex(ValueError, "current scheduled"):
                gate.record(AdmissionAttempt(later, True, 1))
            self.assertTrue(gate.record(AdmissionAttempt(trial, True, 2)))
            with self.assertRaisesRegex(ValueError, "cannot retry"):
                log.append(AdmissionAttempt(trial, True, 3))

    def test_admission_gate_recovers_after_restart_and_seals_with_outcomes(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            study = bundle()
            admissions = AdmissionLog(Path(temporary) / "admission.jsonl", study.sha256)
            first, *remaining = study.schedule
            ScheduledAdmission(study.schedule, admissions).record(AdmissionAttempt(first, True, 1))
            recovered = ScheduledAdmission(study.schedule, admissions)
            self.assertEqual(recovered.current, remaining[0])
            for trial in remaining:
                recovered.record(AdmissionAttempt(trial, True, 1))
            outcomes = RecordChain(Path(temporary) / "outcomes.jsonl", study.sha256)
            for trial in study.schedule:
                outcomes.append(TrialOutcome(trial, "pass", True, True))
            outcomes.finalize(study.schedule, admissions)
            outcomes.verify_finalized(study.schedule, admissions)

    def test_accounting_uses_canonical_trial_identity_not_display_id(self):
        from tempfile import TemporaryDirectory

        first = Trial("a", 1, "B:s1:r1:C", 1)
        second = Trial("a:r1:B:s1", 1, "C", 1)
        self.assertEqual(first.id, second.id)
        self.assertNotEqual(first.sha256, second.sha256)
        with TemporaryDirectory() as temporary:
            chain = RecordChain(Path(temporary) / "records.jsonl", "bundle")
            chain.append(TrialOutcome(first, "pass", True, True))
            with self.assertRaisesRegex(ValueError, "scheduled-record mismatch"):
                chain.assert_schedule_accounted_for((second,))

    def test_outcome_reasons_are_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown outcome"):
            TrialOutcome(Trial("task", 1, "A", 1), "invented_reason", True, False).validate()

    def test_chain_rejects_a_post_request_error_as_infrastructure_invalid(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            chain = RecordChain(Path(temporary) / "records.jsonl", "bundle")
            with self.assertRaisesRegex(ValueError, "post-request"):
                chain.append(TrialOutcome(Trial("task", 1, "A", 1), "infrastructure_invalid", True, False))
