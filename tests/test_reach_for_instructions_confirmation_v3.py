"""No-model contracts for the fresh Qwen3.8 confirmation."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from harness.bundle import digest
from studies.reach_for_instructions_confirmation_v3 import runner


ROOT = Path(__file__).resolve().parents[1]


class ReachForInstructionsConfirmationV3Test(unittest.TestCase):
    def test_fresh_schedule_is_complete_and_distinct_from_v2(self) -> None:
        schedule = runner._schedule()
        self.assertEqual(len(schedule), 72)
        self.assertEqual(schedule, runner._schedule())
        self.assertNotEqual(
            [trial.sha256 for trial in schedule],
            [trial.sha256 for trial in runner.base._schedule()],
        )

    def test_calibration_gate_is_the_v3_preflight(self) -> None:
        runner.preflight(ROOT)
        value = runner.oracle_preflight(ROOT)
        self.assertEqual(set(value), {"accepted", "rejected"})
        self.assertEqual(len(value["accepted"]), 6)

    def test_worker_runs_the_v3_module(self) -> None:
        command = runner._worker_command(
            ROOT, Path("/workspace"), Path("/assist"), Path("/python"),
            Path("descriptor.json"), Path("result.json"), Path("marker"),
        )
        self.assertIn("studies.reach_for_instructions_confirmation_v3.runner", command)
        self.assertNotIn("studies.reach_for_instructions_confirmation_v2.runner", command)
        with runner._configured():
            self.assertIs(runner.base.run_worker, runner.run_worker)

    def test_seal_records_qwen38_and_binds_the_gate(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("studies", "fixtures", "experiments"):
                shutil.copytree(ROOT / directory, root / directory)
            path = root / "experiments" / runner.STUDY / "rendered-request-digests.json"
            path.write_text(json.dumps({trial.sha256: "a" * 64 for trial in runner._schedule()}))
            bundle = runner.seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            self.assertEqual(bundle.model["id"], runner.MODEL_ID)
            self.assertEqual(bundle.settings["model"]["weights_sha256"], runner.WEIGHTS_SHA256)
            self.assertEqual(bundle.model["configuration_sha256"], digest(bundle.settings["model"]))
            self.assertEqual(bundle.registration["oracle_preflight_sha256"], digest(runner.oracle_preflight(root)))

    def test_cli_seal_uses_the_v3_wrapper(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("studies", "fixtures", "experiments"):
                shutil.copytree(ROOT / directory, root / directory)
            path = root / "experiments" / runner.STUDY / "rendered-request-digests.json"
            path.write_text(json.dumps({trial.sha256: "a" * 64 for trial in runner._schedule()}))
            with patch.object(sys, "argv", ["runner", "seal", "--root", str(root), "--source-commit", "a" * 40, "--assist-revision", "b" * 40]):
                runner.main()
            bundle = runner.StudyBundle.read_verified(root / "experiments" / runner.STUDY / "bundle.json")
            self.assertEqual(bundle.model["id"], runner.MODEL_ID)


if __name__ == "__main__":
    unittest.main()
