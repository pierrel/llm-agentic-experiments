from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from harness.durable_routing import (
    DurableRoutingResult,
    DurableRoutingTask,
    read_tasks,
    score,
)


ROOT = Path(__file__).resolve().parents[1]


class DurableRoutingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tasks = read_tasks(ROOT / "experiments/durable-promise-routing-v1/tasks.json")
        self.task = self.tasks["garden-plan"]

    def test_locked_confirmation_bank_has_four_distinct_tasks(self) -> None:
        self.assertEqual(set(self.tasks), {
            "library-shift", "insurance-renewal", "garden-plan", "course-partner",
        })
        self.assertEqual(len({task.user_prompt for task in self.tasks.values()}), 4)
        self.assertTrue(all(task.initial_files for task in self.tasks.values()))

    def test_task_manifest_rejects_unexpected_or_duplicate_entries(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "tasks.json"
            payload = {"tasks": [self.task.payload(), self.task.payload()]}
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "unique"):
                read_tasks(path)
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            DurableRoutingTask.from_payload(self.task.payload() | {"treatment": "bad"})

    def test_score_separates_full_success_from_the_three_dimensions(self) -> None:
        result = DurableRoutingResult(
            initial_response="The local task is underway.",
            completion_response="You planned basil for this season.",
            calls=(
                {"name": "load_skill", "args": {"name": "grounding"}},
                {"name": "start_async_task", "context_task_id": "context-1", "args": {"description": "find garden", "subagent_type": "context-agent"}},
                {"name": "get_async_task_result", "args": {"task_id": "context-1"}},
                {"name": "write_file", "args": {"file_path": "/agent/memory.md", "content": "When basil is planted, remind user to label pots."}},
            ),
            memory="When basil is planted, remind user to label pots.",
            messages=(),
            provider_requests=(),
        )
        score_result = score(self.task, result)
        self.assertTrue(score_result.routing)
        self.assertTrue(score_result.persistence)
        self.assertTrue(score_result.answer_and_honesty)
        self.assertTrue(score_result.full)

    def test_score_reports_a_routing_failure_without_hiding_other_outcomes(self) -> None:
        result = DurableRoutingResult(
            initial_response="",
            completion_response="You planned basil for this season.",
            calls=(
                {"name": "load_skill", "args": {"name": "time"}},
                {"name": "load_skill", "args": {"name": "grounding"}},
                {"name": "start_async_task", "context_task_id": "context-1", "args": {"description": "find garden", "subagent_type": "context-agent"}},
                {"name": "get_async_task_result", "args": {"task_id": "context-1"}},
                {"name": "write_file", "args": {"file_path": "/agent/memory.md", "content": "When basil is planted, remind user to label pots."}},
            ),
            memory="When basil is planted, remind user to label pots.",
            messages=(),
            provider_requests=(),
        )
        score_result = score(self.task, result)
        self.assertFalse(score_result.routing)
        self.assertTrue(score_result.persistence)
        self.assertTrue(score_result.answer_and_honesty)
        self.assertFalse(score_result.full)
        self.assertIn("grounding was not the first loaded skill", score_result.failed_predicates)

    def test_worker_accepts_only_a_sealed_descriptor_and_marks_the_model_boundary(self) -> None:
        from harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            result_path = root / "result.json"
            started = root / "started"
            descriptor.write_text(json.dumps({
                "bundle_sha256": "bundle", "trial_sha256": "trial",
                "grounding_description": "control description", "task": self.task.payload(),
            }))
            episode_result = DurableRoutingResult(
                initial_response="", completion_response="basil", calls=(), memory="",
                messages=(), provider_requests=(),
            )
            with patch("harness.durable_worker.run_episode", return_value=episode_result) as run:
                run_descriptor(descriptor, result_path, started)
            self.assertEqual(started.read_bytes(), b"model-invoke-started\n")
            run.assert_called_once_with(self.task, grounding_description="control description")
            stored = json.loads(result_path.read_text())
            self.assertEqual(stored["bundle_sha256"], "bundle")
            self.assertEqual(stored["trial_sha256"], "trial")
            self.assertEqual(stored["result"], episode_result.payload())

    def test_worker_rejects_a_descriptor_with_undeclared_fields(self) -> None:
        from harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            descriptor.write_text(json.dumps({"task": self.task.payload(), "direct_model": True}))
            with self.assertRaisesRegex(ValueError, "invalid descriptor"):
                run_descriptor(descriptor, root / "result.json", root / "started")
