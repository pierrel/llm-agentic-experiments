"""No-model contracts for V8's compact approval-status calibration."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from harness.bundle import StudyBundle, digest
from studies import equipment_return_oracle_calibration_v8 as calibration
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v8 import runner


ROOT = Path(__file__).resolve().parents[1]


def _copy_seal_inputs(root: Path) -> None:
    shutil.copytree(ROOT / "harness", root / "harness")
    shutil.copytree(ROOT / "studies", root / "studies")
    shutil.copytree(ROOT / "fixtures", root / "fixtures")
    experiments = root / "experiments"
    experiments.mkdir()
    for study in (runner.STUDY, calibration.STUDY):
        shutil.copytree(ROOT / "experiments" / study, experiments / study)


class ReachForInstructionsConfirmationV8Test(unittest.TestCase):
    def test_oracle_accepts_compact_status_without_supervisor_and_rejects_boundaries(self) -> None:
        calibration.verify(ROOT)
        corpus = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        self.assertTrue(calibration.handoff_is_grounded(task, corpus["accepted"][1]["handoff"]))
        for case in corpus["rejected"]:
            self.assertFalse(calibration.handoff_is_grounded(task, case["handoff"]))

    def test_fixture_grounded_handoff_passes_primary_score(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        handoff = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())["accepted"][1]["handoff"]
        calls = [{"tool_calls": [{"name": "glob", "args": {}}]}]
        calls.extend({"tool_calls": [{"name": "read_file", "args": {"file_path": path}}]} for path in task["oracle"]["required_reads"])
        calls.append({"tool_calls": [{"name": "write_file", "args": {"file_path": "outgoing/handoff.json"}}]})
        score = runner._score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(handoff)}, "messages": calls})
        self.assertTrue(score.passed)

    def test_any_write_before_all_reads_fails(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        handoff = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())["accepted"][0]["handoff"]
        messages = [
            {"tool_calls": [{"name": "glob", "args": {}}]},
            {"tool_calls": [{"name": "write_file", "args": {"file_path": "notes.txt"}}]},
            *({"tool_calls": [{"name": "read_file", "args": {"file_path": path}}]} for path in task["oracle"]["required_reads"]),
            {"tool_calls": [{"name": "write_file", "args": {"file_path": "outgoing/handoff.json"}}]},
        ]
        score = runner._score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(handoff)}, "messages": messages})
        self.assertFalse(score.passed)

    def test_schedule_uses_v8_seed_and_worker_command_is_v8(self) -> None:
        inherited = core._schedule()
        with runner._configured():
            self.assertEqual(core._schedule(), runner._schedule())
            self.assertNotEqual(core._schedule(), inherited)
            command = core._worker_command(Path("descriptor"), Path("result"), Path("marker"), Path("root"), Path("workspace"), Path("assist"), Path("python"))
        self.assertIn("studies.reach_for_instructions_confirmation_v8.runner", command)

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
            self.assertEqual(descriptor["fixture"]["task_id"], "equipment-return-handoff-v8")
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
        self.assertEqual(accepted.sha256, sealed.sha256)
        self.assertEqual(stored.sha256, sealed.sha256)


if __name__ == "__main__":
    unittest.main()
