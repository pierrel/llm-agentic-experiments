from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import subprocess

from durable_routing_harness.durable_routing import (
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
            messages=({"content": self.task.context_result},),
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
            messages=({"content": self.task.context_result},),
            provider_requests=(),
        )
        score_result = score(self.task, result)
        self.assertFalse(score_result.routing)
        self.assertTrue(score_result.persistence)
        self.assertTrue(score_result.answer_and_honesty)
        self.assertFalse(score_result.full)
        self.assertIn("grounding was not the first loaded skill", score_result.failed_predicates)

    def test_score_rejects_dependent_work_and_memory_before_checked_context(self) -> None:
        result = DurableRoutingResult(
            initial_response="", completion_response="You planned basil for this season.",
            calls=(
                {"name": "load_skill", "args": {"name": "grounding"}},
                {"name": "start_async_task", "context_task_id": "context-1", "args": {"description": "find garden", "subagent_type": "context-agent"}},
                {"name": "write_file", "args": {"file_path": "/agent/memory.md", "content": "When basil is planted, remind user to label pots."}},
                {"name": "load_skill", "args": {"name": "time"}},
                {"name": "get_async_task_result", "args": {"task_id": "context-1"}},
                {"name": "write_file", "args": {"file_path": "/agent/irrelevant.md", "content": "done"}},
            ),
            memory="When basil is planted, remind user to label pots.",
            messages=({"content": self.task.context_result},), provider_requests=(),
        )
        score_result = score(self.task, result)
        self.assertFalse(score_result.routing)
        self.assertFalse(score_result.persistence)
        self.assertIn("dependent work ran before checked context result", score_result.failed_predicates)
        self.assertIn("private state was written before checked context result", score_result.failed_predicates)

    def test_score_rejects_a_saved_claim_without_this_commitment(self) -> None:
        result = DurableRoutingResult(
            initial_response="", completion_response="Saved that reminder. You planned basil.",
            calls=(
                {"name": "load_skill", "args": {"name": "grounding"}},
                {"name": "start_async_task", "context_task_id": "context-1", "args": {"description": "find garden", "subagent_type": "context-agent"}},
                {"name": "get_async_task_result", "args": {"task_id": "context-1"}},
            ),
            memory="Unrelated note from an earlier turn.",
            messages=({"content": self.task.context_result},), provider_requests=(),
        )
        score_result = score(self.task, result)
        self.assertFalse(score_result.answer_and_honesty)
        self.assertIn("final response claimed a saved commitment without durable state", score_result.failed_predicates)

    def test_worker_accepts_only_a_sealed_descriptor_and_marks_the_model_boundary(self) -> None:
        from durable_routing_harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            result_path = root / "result.json"
            started = root / "started"
            descriptor.write_text(json.dumps({
                "bundle_sha256": "bundle", "trial_sha256": "trial",
                "grounding_description": "control description", "task": self.task.payload(),
                "model_settings": {"model_id": "test-model", "context_limit": 1},
            }))
            episode_result = DurableRoutingResult(
                initial_response="", completion_response="basil", calls=(), memory="",
                messages=(), provider_requests=(),
            )
            with patch("durable_routing_harness.durable_worker._verify_model_settings"), patch(
                     "durable_routing_harness.durable_worker.run_episode",
                     side_effect=lambda *_args, **kwargs: (
                         kwargs["on_first_provider_request"](), episode_result
                     )[1],
                 ) as run:
                run_descriptor(descriptor, result_path, started)
            self.assertEqual(json.loads(started.read_text())["state"], "model-invoke-started")
            run.assert_called_once()
            stored = json.loads(result_path.read_text())
            self.assertEqual(stored["bundle_sha256"], "bundle")
            self.assertEqual(stored["trial_sha256"], "trial")
            self.assertEqual(stored["result"], episode_result.payload())

    def test_worker_rejects_a_descriptor_with_undeclared_fields(self) -> None:
        from durable_routing_harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            descriptor.write_text(json.dumps({"task": self.task.payload(), "direct_model": True}))
            with self.assertRaisesRegex(ValueError, "invalid descriptor"):
                run_descriptor(descriptor, root / "result.json", root / "started")

    def test_worker_marks_the_last_safe_pre_model_checkpoint(self) -> None:
        from durable_routing_harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            started = root / "started"
            descriptor.write_text(json.dumps({
                "bundle_sha256": "bundle", "trial_sha256": "trial",
                "grounding_description": "control description", "task": self.task.payload(),
                "model_settings": {"model_id": "test-model", "context_limit": 1},
            }))
            with patch("durable_routing_harness.durable_worker._verify_model_settings",
                       side_effect=ValueError("sealed preflight failed")):
                with self.assertRaisesRegex(ValueError, "preflight failed"):
                    run_descriptor(descriptor, root / "result.json", started)
            self.assertEqual(json.loads(started.read_text())["state"], "task-validated")

    def test_sealed_definition_and_worker_command_require_the_gpu_admission_path(self) -> None:
        from durable_routing_harness.durable_coordinator import durable_definition, durable_worker_command

        definition = durable_definition(ROOT)
        self.assertEqual(definition.bundle.study_id, "durable-promise-routing-v4")
        self.assertEqual(len(definition.bundle.schedule), 24)
        command = durable_worker_command(
            ROOT, Path("/workspace"), Path("/assist"), Path("/venv/bin/python"), Path("/env"),
            Path("/descriptor"), Path("/result"), Path("/started"),
        )
        self.assertEqual(command[:5], ["/workspace/tools/agentic", "resource", "run", "llm", "--"])
        self.assertNotIn("8000", " ".join(command))
        self.assertIn("durable_routing_harness.durable_worker", command)

    def test_coordinator_records_a_denied_admission_without_advancing_schedule(self) -> None:
        from durable_routing_harness.durable_coordinator import run_durable_routing_once

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            progress = run_durable_routing_once(
                ROOT, output, workspace_root=Path("/workspace"),
                assist_root=Path("/assist"), assist_python=Path("/venv/bin/python"), assist_env=Path("/env"),
                command_runner=lambda command: subprocess.CompletedProcess(
                    command, 1, "", "production is busy"),
            )
            self.assertEqual(progress.status, "retry_in_10_minutes")
            admission = json.loads((output / "admissions.jsonl").read_text())
            self.assertFalse(admission["admitted"])
            self.assertFalse((output / "outcomes.jsonl").exists())

    def test_coordinator_keeps_one_admitted_trial_and_its_predicates(self) -> None:
        from durable_routing_harness.durable_coordinator import run_durable_routing_once

        task = self.tasks["library-shift"]
        result = DurableRoutingResult(
            initial_response="", completion_response="Your Thursday book-drive shift starts at 5:45 PM.",
            calls=(
                {"name": "load_skill", "args": {"name": "grounding"}},
                {"name": "start_async_task", "context_task_id": "context-1", "args": {"description": "find shift", "subagent_type": "context-agent"}},
                {"name": "get_async_task_result", "args": {"task_id": "context-1"}},
                {"name": "write_file", "args": {"file_path": "/agent/memory.md", "content": "When volunteer application is submitted, remind user to bring photo ID."}},
            ),
            memory="When volunteer application is submitted, remind user to bring photo ID.",
            messages=({"content": task.context_result},), provider_requests=({"messages": [], "kwargs": {}},),
        )
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"

            def worker(command):
                Path(command[command.index("--request-started") + 1]).write_text(
                    json.dumps({"state": "model-invoke-started", "pid": os.getpid()}))
                descriptor = json.loads(Path(command[command.index("--descriptor") + 1]).read_text())
                Path(command[command.index("--result") + 1]).write_text(json.dumps({
                    "bundle_sha256": descriptor["bundle_sha256"],
                    "trial_sha256": descriptor["trial_sha256"],
                    "result": result.payload(),
                }))
                return subprocess.CompletedProcess(command, 0, "", "")

            progress = run_durable_routing_once(
                ROOT, output, workspace_root=Path("/workspace"),
                assist_root=Path("/assist"), assist_python=Path("/venv/bin/python"), assist_env=Path("/env"),
                command_runner=worker,
            )
            self.assertEqual(progress.status, "next_trial")
            outcome = json.loads((output / "outcomes.jsonl").read_text())
            self.assertEqual(outcome["outcome"], "pass")
            self.assertTrue(outcome["model_request_made"])
            trace = json.loads(next((output / "traces").glob("*.json")).read_text())
            self.assertEqual(trace["score"], {
                "routing": True, "persistence": True, "answer_and_honesty": True,
                "full": True, "failed_predicates": [],
            })

    def test_coordinator_never_replays_an_interrupted_provider_request(self) -> None:
        from durable_routing_harness.durable_coordinator import run_durable_routing_once
        from harness.bundle import StudyBundle

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            bundle = StudyBundle.read_verified(
                ROOT / "experiments/durable-promise-routing-v4/bundle.json"
            )
            trial = bundle.schedule[0]
            output.mkdir(mode=0o700)
            bundle.write(output / "bundle.json")
            (output / f".{trial.sha256}.lifecycle.json").write_text(
                json.dumps({"state": "model-invoke-started", "pid": 999999})
            )
            first = run_durable_routing_once(
                ROOT, output, workspace_root=Path("/workspace"),
                assist_root=Path("/assist"), assist_python=Path("/venv/bin/python"), assist_env=Path("/env"),
                command_runner=lambda _command: self.fail("interrupted trial must not be replayed"),
            )
            self.assertEqual(first.status, "recover_worker")
            second = run_durable_routing_once(
                ROOT, output, workspace_root=Path("/workspace"),
                assist_root=Path("/assist"), assist_python=Path("/venv/bin/python"), assist_env=Path("/env"),
                command_runner=lambda _command: self.fail("interrupted trial must not be replayed"),
            )
            self.assertEqual(second.status, "next_trial")
            outcome = json.loads((output / "outcomes.jsonl").read_text())
            self.assertEqual(outcome["outcome"], "provider_error")
            self.assertTrue(outcome["model_request_made"])

    def test_worker_failure_detail_keeps_the_exception_tail(self) -> None:
        from durable_routing_harness.durable_coordinator import _command_detail

        result = subprocess.CompletedProcess(["worker"], 1, "", "prefix " * 100 + "actual cause")
        self.assertIn("actual cause", _command_detail(result))
