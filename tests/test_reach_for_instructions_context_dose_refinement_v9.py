"""No-model contracts for the V8 high-context dose refinement."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from harness.bundle import StudyBundle, digest
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_context_dose_refinement_v9 import runner


ROOT = Path(__file__).resolve().parents[1]


def _copy_seal_inputs(root: Path) -> None:
    for name in ("harness", "studies", "fixtures", "experiments"):
        shutil.copytree(ROOT / name, root / name)


class ReachForInstructionsContextDoseRefinementV9Test(unittest.TestCase):
    def test_schedule_is_fresh_paired_and_confined_to_the_high_context_grid(self) -> None:
        schedule = runner._schedule()
        self.assertEqual(len(schedule), 96)
        self.assertEqual({trial.task for trial in schedule}, set(runner.CONTEXT_LINES))
        self.assertEqual({trial.condition for trial in schedule}, {"G01", "G02"})
        self.assertEqual({task: sum(trial.task == task for trial in schedule) for task in runner.CONTEXT_LINES}, {task: 24 for task in runner.CONTEXT_LINES})
        with runner._configured():
            self.assertEqual(core.CONTEXT_LINES, runner.CONTEXT_LINES)
            command = core._worker_command(Path("root"), Path("workspace"), Path("assist"), Path("python"), Path("descriptor"), Path("result"), Path("marker"))
        self.assertIn("studies.reach_for_instructions_context_dose_refinement_v9.runner", command)

    def test_v8_fixture_and_oracle_remain_the_only_task_measurement_inputs(self) -> None:
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        self.assertEqual(task["task_id"], "equipment-return-handoff-v8")
        self.assertEqual(runner.CONTEXT_LINES, {"C-1800": 1800, "C-2700": 2700, "C-3600": 3600, "C-4500": 4500})

    def test_seal_binds_the_v9_grid_registration_and_immutable_tag(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _copy_seal_inputs(root)
            schedule = runner._schedule()
            digest_path = root / "experiments" / runner.STUDY / core.RENDERED_REQUEST_DIGESTS
            digest_path.write_text(json.dumps({trial.sha256: "a" * 64 for trial in schedule}))
            sealed = runner.seal(root, source_commit="a" * 40, assist_revision="b" * 40)
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
                accepted, task, _ = core._definition(root)
            stored = StudyBundle.read_verified(root / "experiments" / runner.STUDY / "bundle.json")
        self.assertEqual(len(sealed.schedule), 96)
        self.assertEqual(sealed.fixtures, {context: digest(task) for context in runner.CONTEXT_LINES})
        self.assertEqual(sealed.registration["randomization_seed"], runner.RANDOMIZATION_SEED)
        self.assertEqual(accepted.sha256, sealed.sha256)
        self.assertEqual(stored.sha256, sealed.sha256)


if __name__ == "__main__":
    unittest.main()
