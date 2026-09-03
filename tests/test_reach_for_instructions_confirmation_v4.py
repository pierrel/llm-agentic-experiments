"""No-model contracts for V4 after V3's request-fidelity correction."""

from __future__ import annotations

from pathlib import Path
import unittest

from studies.reach_for_instructions_confirmation_v4 import runner


ROOT = Path(__file__).resolve().parents[1]


class ReachForInstructionsConfirmationV4Test(unittest.TestCase):
    def test_fresh_schedule_and_worker_module_are_bound(self) -> None:
        with runner._configured():
            schedule = runner.base._schedule()
            command = runner.base._worker_command(
                ROOT, Path("/workspace"), Path("/assist"), Path("/python"),
                Path("descriptor"), Path("result"), Path("marker"),
            )
        self.assertEqual(len(schedule), 72)
        self.assertIn("studies.reach_for_instructions_confirmation_v4.runner", command)
        self.assertNotEqual(schedule, runner.base._schedule())


if __name__ == "__main__":
    unittest.main()
