"""No-model contracts for the corrected Qwen3.8 V5 cohort."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from harness.bundle import StudyBundle
from studies.reach_for_instructions_confirmation_v5 import runner


ROOT = Path(__file__).resolve().parents[1]


class ReachForInstructionsConfirmationV5Test(unittest.TestCase):
    def test_seal_binds_the_actual_fresh_schedule_seed_and_worker(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("studies", "fixtures", "experiments"):
                shutil.copytree(ROOT / directory, root / directory)
            with runner._configured():
                schedule = runner.base.base.base._schedule()
                command = runner.base.base.base._worker_command(
                    root, Path("/workspace"), Path("/assist"), Path("/python"),
                    Path("descriptor"), Path("result"), Path("marker"),
                )
            rendered = root / "experiments" / runner.STUDY / "rendered-request-digests.json"
            rendered.write_text(json.dumps({trial.sha256: "a" * 64 for trial in schedule}))
            bundle = runner.seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            stored_seed = StudyBundle.read_verified(
                root / "experiments" / runner.STUDY / "bundle.json"
            ).registration["randomization_seed"]
        self.assertEqual(len(schedule), 72)
        self.assertEqual(bundle.registration["randomization_seed"], runner.RANDOMIZATION_SEED)
        self.assertEqual(list(bundle.schedule), list(schedule))
        self.assertIn("studies.reach_for_instructions_confirmation_v5.runner", command)
        self.assertEqual(stored_seed, runner.RANDOMIZATION_SEED)


if __name__ == "__main__":
    unittest.main()
