"""No-model contracts for the current-profile held-out confirmation."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from harness.bundle import StudyBundle, digest
from studies import equipment_return_oracle_calibration as calibration
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v6 import runner


ROOT = Path(__file__).resolve().parents[1]


def _copy_seal_inputs(root: Path) -> None:
    shutil.copytree(ROOT / "studies", root / "studies")
    shutil.copytree(ROOT / "fixtures", root / "fixtures")
    experiments = root / "experiments"
    experiments.mkdir()
    for study in (runner.STUDY, calibration.STUDY):
        shutil.copytree(ROOT / "experiments" / study, experiments / study)


class ReachForInstructionsConfirmationV6Test(unittest.TestCase):
    def test_delivery_surfaces_are_explicitly_separate(self) -> None:
        handed = runner._system_prompt("handed", 0)
        reached = runner._system_prompt("reached", 0)
        self.assertIn("first inventory", handed)
        self.assertNotIn("first inventory", reached)
        self.assertNotIn(runner.SKILL_NAME, handed)
        self.assertIn(runner.SKILL_NAME, reached)

    def test_process_metric_survives_primary_failure(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        messages = [{"tool_calls": [{"name": "load_skill", "args": {"name": runner.SKILL_NAME}}]}]
        score = runner._score(task, {
            "files": task["initial_files"] | {"outgoing/handoff.json": "{}"},
            "messages": messages,
        })
        self.assertFalse(score.passed)
        self.assertTrue(score.skill_loaded_before_first_read)

    def test_fixture_grounded_handoff_passes_the_new_primary_score(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        handoff = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())["accepted"][0]["handoff"]
        calls = [{"tool_calls": [{"name": "glob", "args": {}}]}]
        calls.extend({"tool_calls": [{"name": "read_file", "args": {"file_path": path}}]} for path in task["oracle"]["required_reads"])
        calls.append({"tool_calls": [{"name": "write_file", "args": {"file_path": "outgoing/handoff.json"}}]})
        score = runner._score(task, {
            "files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(handoff)},
            "messages": calls,
        })
        self.assertTrue(score.passed)

    def test_current_profile_records_reasoning_and_omitted_output_limit(self) -> None:
        model = runner._settings("a" * 40, "b" * 40)["model"]
        self.assertEqual(model["model_id"], runner.MODEL_ID)
        self.assertEqual(model["reasoning"], {"enabled": True})
        self.assertIsNone(model["max_tokens"])

    def test_calibration_accepts_unresolved_attachment_and_rejects_assertion(self) -> None:
        calibration.verify(ROOT)
        corpus = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        cases = {case["name"]: case["handoff"] for label in corpus for case in corpus[label]}
        self.assertTrue(calibration.handoff_is_grounded(task, cases["observed-unresolved-attached-form"]))
        self.assertFalse(calibration.handoff_is_grounded(task, cases["unsupported-attached-assertion"]))
        self.assertFalse(calibration.handoff_is_grounded(task, cases["unsupported-completion-claim"]))

    def test_calibration_rejects_positive_completion_status(self) -> None:
        self.assertFalse(calibration._status_is_grounded("Closure is approved and complete; no receiving scan has been recorded."))
        self.assertFalse(calibration._status_is_grounded("Approved; the return was received and completion recorded."))
        self.assertTrue(calibration._status_is_grounded("Closure is approved but not complete; no receiving scan has been recorded."))
        self.assertTrue(calibration._status_is_grounded("Approved closure; the return is still pending."))
        self.assertTrue(calibration._status_is_grounded("Approved; closure is not complete and not received."))

    def test_seal_binds_fresh_schedule_and_immutable_tag(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _copy_seal_inputs(root)
            with runner._configured():
                schedule = core._schedule()
            (root / "experiments" / runner.STUDY / "rendered-request-digests.json").write_text(
                json.dumps({trial.sha256: "a" * 64 for trial in schedule})
            )
            sealed = runner.seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            task = json.loads((root / "fixtures" / runner.FIXTURE).read_text())
            with runner._configured():
                descriptor = core._descriptor(sealed, sealed.schedule[0], task)
            self.assertEqual(sealed.fixtures, {context: digest(task) for context in core.CONTEXT_LINES})
            self.assertEqual(descriptor["fixture"]["task_id"], "equipment-return-handoff")
            self.assertEqual(descriptor["max_tokens"], None)
            drifted = root / "descriptor.json"
            drifted.write_text(json.dumps(descriptor | {"user_prompt": descriptor["user_prompt"] + " Also name the guide."}))
            with self.assertRaises(ValueError):
                runner._run_worker(drifted, root / "result.json", root / "marker")
            drifted.write_text(json.dumps(descriptor | {"files": descriptor["files"] | {"records/extra.md": "Injected material."}}))
            with self.assertRaises(ValueError):
                runner._run_worker(drifted, root / "result.json", root / "marker")
            self.assertTrue(
                runner.SKILL_NAME in descriptor["system_prompt"]
                or runner.PROCEDURE in descriptor["system_prompt"]
            )
            for command in (
                ["git", "init", "--quiet", str(root)],
                ["git", "-C", str(root), "config", "user.email", "tests@example.invalid"],
                ["git", "-C", str(root), "config", "user.name", "Test"],
                ["git", "-C", str(root), "add", "."],
                ["git", "-C", str(root), "commit", "--quiet", "-m", "sealed definition"],
                ["git", "-C", str(root), "tag", runner.REGISTRATION_TAG],
            ):
                subprocess.run(command, check=True, capture_output=True)
            with runner._configured():
                accepted, _, _ = core._definition(root)
            stored = StudyBundle.read_verified(root / "experiments" / runner.STUDY / "bundle.json")
        self.assertEqual(len(sealed.schedule), 72)
        self.assertEqual(sealed.registration["randomization_seed"], runner.RANDOMIZATION_SEED)
        self.assertEqual(sealed.registration["primary_outcome"], runner.PRIMARY_OUTCOME)
        self.assertIn("equipment-return", sealed.registration["primary_outcome"])
        self.assertEqual(accepted.sha256, sealed.sha256)
        self.assertEqual(stored.sha256, sealed.sha256)


if __name__ == "__main__":
    unittest.main()
