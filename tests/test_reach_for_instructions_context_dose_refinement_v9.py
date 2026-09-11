"""No-model contracts for the V9 high-context dose refinement."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from harness.bundle import StudyBundle, digest
from studies import equipment_return_oracle_calibration_v8 as calibration
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
        with patch.object(runner, "RANDOMIZATION_SEED", runner.RANDOMIZATION_SEED + 1):
            self.assertNotEqual(schedule, runner._schedule())
        with runner._configured():
            self.assertEqual(core.CONTEXT_LINES, runner.CONTEXT_LINES)
            command = core._worker_command(Path("root"), Path("workspace"), Path("assist"), Path("python"), Path("descriptor"), Path("result"), Path("marker"))
        self.assertIn("studies.reach_for_instructions_context_dose_refinement_v9.runner", command)

    def test_v8_fixture_and_oracle_remain_the_only_task_measurement_inputs(self) -> None:
        runner.preflight(ROOT)
        corpus = json.loads((ROOT / "experiments" / calibration.STUDY / "corpus.json").read_text())
        task = json.loads((ROOT / "fixtures" / runner.FIXTURE).read_text())
        self.assertEqual(task["task_id"], "equipment-return-handoff-v8")
        self.assertTrue(calibration.handoff_is_grounded(task, corpus["accepted"][0]["handoff"]))
        self.assertFalse(calibration.handoff_is_grounded(task, corpus["rejected"][0]["handoff"]))
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
        self.assertEqual(sealed.schedule, runner._schedule())
        self.assertEqual(sealed.fixtures, {context: digest(task) for context in runner.CONTEXT_LINES})
        self.assertEqual(sealed.registration["randomization_seed"], runner.RANDOMIZATION_SEED)
        self.assertEqual(sealed.registration["max_turns"], runner.MAX_TURNS)
        self.assertEqual(sealed.registration["registration_tag"], runner.REGISTRATION_TAG)
        self.assertEqual(sealed.model["id"], "Qwen3.8-27B-UD-Q4_K_XL.gguf")
        self.assertEqual(sealed.model["revision"], "2026-09-11")
        self.assertEqual(accepted.sha256, sealed.sha256)
        self.assertEqual(stored.sha256, sealed.sha256)

    def _assert_definition_rejects(self, mutate: object, message: str) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _copy_seal_inputs(root)
            schedule = runner._schedule()
            digest_path = root / "experiments" / runner.STUDY / core.RENDERED_REQUEST_DIGESTS
            digest_path.write_text(json.dumps({trial.sha256: "a" * 64 for trial in schedule}))
            sealed = runner.seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            mutate(sealed).write(root / "experiments" / runner.STUDY / "bundle.json")
            for command in (
                ["git", "init", "--quiet", str(root)],
                ["git", "-C", str(root), "config", "user.email", "tests@example.invalid"],
                ["git", "-C", str(root), "config", "user.name", "Test"],
                ["git", "-C", str(root), "add", "."],
                ["git", "-C", str(root), "commit", "--quiet", "-m", "altered definition"],
                ["git", "-C", str(root), "tag", runner.REGISTRATION_TAG],
            ):
                subprocess.run(command, check=True, capture_output=True)
            with runner._configured(), self.assertRaisesRegex(ValueError, message):
                core._definition(root)

    def test_definition_rejects_self_consistent_schedule_seed_tag_and_model_changes(self) -> None:
        self._assert_definition_rejects(lambda bundle: replace(bundle, schedule=tuple(reversed(bundle.schedule))), "schedule does not match")
        self._assert_definition_rejects(lambda bundle: replace(bundle, registration=bundle.registration | {"randomization_seed": -1}), "seed does not match")
        self._assert_definition_rejects(lambda bundle: replace(bundle, registration=bundle.registration | {"max_turns": 1}), "max turns does not match")
        self._assert_definition_rejects(lambda bundle: replace(bundle, registration=bundle.registration | {"registration_tag": "other"}), "tag")
        self._assert_definition_rejects(lambda bundle: replace(bundle, model=bundle.model | {"id": "other"}), "model or harness settings do not match")

    def test_definition_rejects_self_consistent_fixture_architecture_and_tool_changes(self) -> None:
        self._assert_definition_rejects(lambda bundle: replace(bundle, fixtures=bundle.fixtures | {"C-1800": "0" * 64}), "fixture does not match")
        self._assert_definition_rejects(lambda bundle: replace(bundle, harness_architecture=bundle.harness_architecture | {"id": "other"}), "architecture or tool schema does not match")
        self._assert_definition_rejects(lambda bundle: replace(bundle, tool_schemas=bundle.tool_schemas | {"load_skill": {"name": "other", "arguments": {"name": "string"}}}), "architecture or tool schema does not match")


if __name__ == "__main__":
    unittest.main()
