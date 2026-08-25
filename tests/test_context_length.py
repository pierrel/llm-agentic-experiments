"""No-model contract tests for the context-length development runner."""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from harness.manifests import TaskManifest
from studies.context_length.runner import _filler, _score, main, seal


ROOT = Path(__file__).resolve().parents[1]


class ContextLengthTest(unittest.TestCase):
    def test_filler_is_deterministic_and_case_free(self) -> None:
        filler = _filler(3)
        self.assertEqual(filler, _filler(3))
        self.assertNotIn("Oakridge", filler)
        self.assertNotIn("outgoing", filler)
        self.assertNotIn("read_file", filler)

    def test_oracle_requires_ordered_reads_and_complete_handoff(self) -> None:
        task = TaskManifest.read(ROOT / "fixtures" / "context-length-case-handoff.json")
        output = "\n".join(task.oracle["required_phrases"]) + "\n"
        messages = [{"tool_calls": [{"name": "glob", "args": {}}]}]
        messages += [{"tool_calls": [{"name": "read_file", "args": {"file_path": path}}]} for path in task.oracle["required_reads"]]
        messages += [{"tool_calls": [{"name": "write_file", "args": {"file_path": task.oracle["output_path"]}}], "usage_metadata": {"input_tokens": 1234}}]
        passed, _, tokens = _score(task, {"files": task.initial_files | {task.oracle["output_path"]: output}, "messages": messages})
        self.assertTrue(passed)
        self.assertEqual(tokens, 1234)
        early = messages[:2] + messages[-1:]
        self.assertFalse(_score(task, {"files": task.initial_files | {task.oracle["output_path"]: output}, "messages": early})[0])
        late_inventory = messages[1:] + messages[:1]
        self.assertFalse(_score(task, {"files": task.initial_files | {task.oracle["output_path"]: output}, "messages": late_inventory})[0])

    def test_seal_binds_all_three_conditions(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("harness", "studies", "fixtures", "experiments"):
                shutil.copytree(ROOT / directory, root / directory)
            bundle = seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            self.assertEqual({trial.condition for trial in bundle.schedule}, {"C-low", "C-medium", "C-high"})
            self.assertEqual(bundle.registration["randomization_seed"], 20260825)
            self.assertTrue((root / "experiments" / "context-length-dev-v1" / "bundle.json").exists())

    def test_cli_default_root_is_repository_root(self) -> None:
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["runner", "seal", "--source-commit", "a" * 40, "--assist-revision", "b" * 40]), patch(
            "studies.context_length.runner.seal"
        ) as sealed:
            main()
        self.assertEqual(sealed.call_args.args[0], ROOT)


if __name__ == "__main__":
    unittest.main()
