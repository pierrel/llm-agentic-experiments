"""No-model contracts for V7's held-out oracle correction."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from harness.bundle import StudyBundle, digest
from studies import equipment_return_oracle_calibration_v7 as calibration
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v7 import runner


ROOT = Path(__file__).resolve().parents[1]


def _copy_seal_inputs(root: Path) -> None:
    shutil.copytree(ROOT / "harness", root / "harness")
    shutil.copytree(ROOT / "studies", root / "studies")
    shutil.copytree(ROOT / "fixtures", root / "fixtures")
    experiments = root / "experiments"
    experiments.mkdir()
    for study in (runner.STUDY, calibration.STUDY):
        shutil.copytree(ROOT / "experiments" / study, experiments / study)


class ReachForInstructionsConfirmationV7Test(unittest.TestCase):
    def test_oracle_accepts_the_compact_observed_form_only_with_approval(self) -> None:
        calibration.verify(ROOT)
        corpus = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        self.assertTrue(calibration.handoff_is_grounded(task, corpus["accepted"][1]["handoff"]))
        self.assertFalse(calibration.handoff_is_grounded(task, corpus["rejected"][0]["handoff"]))
        self.assertFalse(calibration.handoff_is_grounded(task, corpus["rejected"][1]["handoff"]))
        self.assertFalse(calibration.handoff_is_grounded(task, corpus["rejected"][3]["handoff"]))

    def test_fixture_grounded_handoff_passes_primary_score(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        handoff = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())["accepted"][1]["handoff"]
        calls = [{"tool_calls": [{"name": "glob", "args": {}}]}]
        calls.extend({"tool_calls": [{"name": "read_file", "args": {"file_path": path}}]} for path in task["oracle"]["required_reads"])
        calls.append({"tool_calls": [{"name": "write_file", "args": {"file_path": "outgoing/handoff.json"}}]})
        score = runner._score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(handoff)}, "messages": calls})
        self.assertTrue(score.passed)

    def test_output_write_before_all_reads_fails_even_if_a_later_write_occurs(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        handoff = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())["accepted"][0]["handoff"]
        messages = [
            {"tool_calls": [{"name": "glob", "args": {}}]},
            {"tool_calls": [{"name": "write_file", "args": {"file_path": "outgoing/handoff.json"}}]},
            *({"tool_calls": [{"name": "read_file", "args": {"file_path": path}}]} for path in task["oracle"]["required_reads"]),
            {"tool_calls": [{"name": "write_file", "args": {"file_path": "notes.txt"}}]},
        ]
        score = runner._score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(handoff)}, "messages": messages})
        self.assertFalse(score.passed)

    def test_process_metric_remains_independent_of_artifact_success(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        score = runner._score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": "{}"}, "messages": [{"tool_calls": [{"name": "load_skill", "args": {"name": runner.base.SKILL_NAME}}]}]})
        self.assertFalse(score.passed)
        self.assertTrue(score.skill_loaded_before_first_read)

    def test_current_profile_records_reasoning_and_omitted_output_limit(self) -> None:
        model = runner._settings("a" * 40, "b" * 40)["model"]
        self.assertEqual(model["model_id"], runner.MODEL_ID)
        self.assertEqual(model["reasoning"], {"enabled": True})
        self.assertIsNone(model["max_tokens"])

    def test_seal_binds_fresh_fixture_calibration_and_tag(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _copy_seal_inputs(root)
            with runner._configured():
                schedule = core._schedule()
            (root / "experiments" / runner.STUDY / "rendered-request-digests.json").write_text(json.dumps({trial.sha256: "a" * 64 for trial in schedule}))
            sealed = runner.seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            task = json.loads((root / "fixtures" / runner.FIXTURE).read_text())
            with runner._configured():
                descriptor = core._descriptor(sealed, sealed.schedule[0], task)
            self.assertEqual(sealed.fixtures, {context: digest(task) for context in core.CONTEXT_LINES})
            self.assertEqual(descriptor["fixture"]["task_id"], "equipment-return-handoff-v7")
            self.assertEqual(descriptor["max_tokens"], None)
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
        self.assertEqual(sealed.registration["primary_outcome"], "structured equipment-return handoff plus ordered workspace procedure")
        self.assertEqual(accepted.sha256, sealed.sha256)
        self.assertEqual(stored.sha256, sealed.sha256)


if __name__ == "__main__":
    unittest.main()
