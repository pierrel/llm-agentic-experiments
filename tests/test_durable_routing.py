from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import subprocess
from dataclasses import replace

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

    def current_definition(self):
        """Build a test-only definition whose closure matches this checkout."""
        from harness.bundle import StudyBundle
        from durable_routing_harness.durable_coordinator import (
            DurableRoutingDefinition, durable_implementation_sha256,
        )

        bundle = StudyBundle.read_verified(
            ROOT / "experiments/durable-promise-outcome-v1/bundle.json"
        )
        conditions = json.loads(
            (ROOT / "experiments/durable-promise-outcome-v1/conditions.json").read_text()
        )
        return DurableRoutingDefinition(
            replace(
                bundle,
                registration=bundle.registration | {
                    "implementation_sha256": durable_implementation_sha256(ROOT),
                    "advance_primary_dimensions": ["persistence", "full"],
                    "sentinel_non_regression_dimensions": ["routing", "answer_and_honesty"],
                    "advance_minimum_delta": 2,
                    "paired_sign_test_max_p": 0.05,
                    "guard_maximum_decrease": 2,
                },
            ),
            read_tasks(ROOT / "experiments/durable-promise-outcome-v1/tasks.json"),
            "memory_guidance",
            {key: value["memory_guidance"] for key, value in conditions.items()},
        )

    def test_locked_confirmation_bank_has_four_distinct_tasks(self) -> None:
        self.assertEqual(set(self.tasks), {
            "library-shift", "insurance-renewal", "garden-plan", "course-partner",
        })
        self.assertEqual(len({task.user_prompt for task in self.tasks.values()}), 4)
        self.assertTrue(all(task.initial_files for task in self.tasks.values()))

    def test_registered_v2_confirmation_is_fresh_and_fully_position_balanced(self) -> None:
        from durable_routing_harness.durable_coordinator import durable_definition

        definition = durable_definition(ROOT)
        self.assertEqual(definition.bundle.study_id, "durable-promise-outcome-v2")
        self.assertEqual(set(definition.tasks), {
            "orchard-volunteer", "passport-form", "choir-rehearsal", "vet-followup",
        })
        self.assertEqual(len(definition.bundle.schedule), 48)
        for task in definition.tasks:
            positions = {"C0": [], "C1": []}
            for replicate in range(1, 7):
                block = [trial.condition for trial in definition.bundle.schedule
                         if trial.task == task and trial.replicate == replicate]
                for condition in positions:
                    positions[condition].append(block.index(condition))
            self.assertEqual(positions["C0"].count(0), 3)
            self.assertEqual(positions["C1"].count(0), 3)

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
                "condition_field": "grounding_description", "condition_value": "control description",
                "task": self.task.payload(),
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
            self.assertEqual(run.call_args.kwargs["model_settings"], {
                "model_id": "test-model", "context_limit": 1,
            })

    def test_worker_passes_a_sealed_memory_guidance_pair(self) -> None:
        from durable_routing_harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            guidance = {"repository_memory_prompt": "repo", "thread_memory_prompt": "thread"}
            descriptor.write_text(json.dumps({
                "bundle_sha256": "bundle", "trial_sha256": "trial",
                "condition_field": "memory_guidance", "condition_value": guidance,
                "task": self.task.payload(), "model_settings": {"model_id": "test-model", "context_limit": 1},
            }))
            episode_result = DurableRoutingResult("", "", (), "", (), (), "", "")
            with patch("durable_routing_harness.durable_worker._verify_model_settings"), patch(
                    "durable_routing_harness.durable_worker.run_episode", return_value=episode_result) as run:
                run_descriptor(descriptor, root / "result.json", root / "started")
            self.assertEqual(run.call_args.kwargs["memory_guidance"], guidance)

    def test_worker_rejects_a_descriptor_with_undeclared_fields(self) -> None:
        from durable_routing_harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            descriptor.write_text(json.dumps({"task": self.task.payload(), "direct_model": True}))
            with self.assertRaisesRegex(ValueError, "invalid descriptor"):
                run_descriptor(descriptor, root / "result.json", root / "started")

    def test_episode_uses_only_the_sealed_decoding_and_reasoning_options(self) -> None:
        from durable_routing_harness.durable_routing import _selection_settings

        self.assertEqual(
            _selection_settings({"decoding": {"temperature": 0.1}, "reasoning": {"enabled": False}}),
            (0.1, False),
        )
        with self.assertRaisesRegex(ValueError, "temperature"):
            _selection_settings({"decoding": {}, "reasoning": {"enabled": False}})
        with self.assertRaisesRegex(ValueError, "reasoning"):
            _selection_settings({"decoding": {"temperature": 0.1}, "reasoning": {}})

    def test_paired_sign_test_has_a_directional_exact_tail(self) -> None:
        from durable_routing_harness.durable_coordinator import _one_sided_sign_p

        self.assertEqual(_one_sided_sign_p(0, 0), 1.0)
        self.assertEqual(_one_sided_sign_p(6, 0), 1 / 64)
        self.assertEqual(_one_sided_sign_p(3, 3), 42 / 64)

    def test_worker_binds_the_nonsecret_provider_endpoint_identity(self) -> None:
        from assist.model_manager import OpenAIConfig
        from durable_routing_harness.durable_worker import _verify_model_settings

        url = "http://127.0.0.1:8000/v1"
        settings = {
            "model_id": "test-model", "context_limit": 131072,
            "provider_url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        }
        with patch("assist.model_manager.current_model_config",
                   return_value=OpenAIConfig(url, "test-model", "secret", 131072)):
            _verify_model_settings(settings)
            with self.assertRaisesRegex(ValueError, "differs"):
                _verify_model_settings(settings | {"provider_url_sha256": "0" * 64})

    def test_worker_marks_the_last_safe_pre_model_checkpoint(self) -> None:
        from durable_routing_harness.durable_worker import run_descriptor

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = root / "descriptor.json"
            started = root / "started"
            descriptor.write_text(json.dumps({
                "bundle_sha256": "bundle", "trial_sha256": "trial",
                "condition_field": "grounding_description", "condition_value": "control description",
                "task": self.task.payload(),
                "model_settings": {"model_id": "test-model", "context_limit": 1},
            }))
            with patch("durable_routing_harness.durable_worker._verify_model_settings",
                       side_effect=ValueError("sealed preflight failed")):
                with self.assertRaisesRegex(ValueError, "preflight failed"):
                    run_descriptor(descriptor, root / "result.json", started)
            self.assertEqual(json.loads(started.read_text())["state"], "task-validated")

    def test_sealed_definition_and_worker_command_require_the_gpu_admission_path(self) -> None:
        from durable_routing_harness.durable_coordinator import durable_worker_command

        definition = self.current_definition()
        self.assertEqual(definition.bundle.study_id, "durable-promise-outcome-v1")
        self.assertEqual(len(definition.bundle.schedule), 24)
        self.assertEqual(definition.condition_field, "memory_guidance")
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
            with patch("durable_routing_harness.durable_coordinator.durable_definition",
                       return_value=self.current_definition()):
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

        task = read_tasks(ROOT / "experiments/durable-promise-outcome-v1/tasks.json")["workshop-review"]
        result = DurableRoutingResult(
            initial_response="", completion_response="The workshop review is October 14.",
            calls=(
                {"name": "load_skill", "args": {"name": "grounding"}},
                {"name": "start_async_task", "context_task_id": "context-1", "args": {"description": "find shift", "subagent_type": "context-agent"}},
                {"name": "get_async_task_result", "args": {"task_id": "context-1"}},
                {"name": "write_file", "args": {"file_path": "/agent/memory.md", "content": "When proposal is mailed, remind user to send the review packet to Reina."}},
            ),
            memory="When proposal is mailed, remind user to send the review packet to Reina.",
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

            with patch("durable_routing_harness.durable_coordinator.durable_definition",
                       return_value=self.current_definition()):
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
            bundle = self.current_definition().bundle
            trial = bundle.schedule[0]
            output.mkdir(mode=0o700)
            bundle.write(output / "bundle.json")
            (output / f".{trial.sha256}.lifecycle.json").write_text(
                json.dumps({"state": "model-invoke-started", "pid": 999999})
            )
            with patch("durable_routing_harness.durable_coordinator.durable_definition",
                       return_value=self.current_definition()):
                first = run_durable_routing_once(
                    ROOT, output, workspace_root=Path("/workspace"),
                    assist_root=Path("/assist"), assist_python=Path("/venv/bin/python"), assist_env=Path("/env"),
                    command_runner=lambda _command: self.fail("interrupted trial must not be replayed"),
                )
            self.assertEqual(first.status, "recover_worker")
            with patch("durable_routing_harness.durable_coordinator.durable_definition",
                       return_value=self.current_definition()):
                second = run_durable_routing_once(
                    ROOT, output, workspace_root=Path("/workspace"),
                    assist_root=Path("/assist"), assist_python=Path("/venv/bin/python"), assist_env=Path("/env"),
                    command_runner=lambda _command: self.fail("interrupted trial must not be replayed"),
                )
            self.assertEqual(second.status, "next_trial")
            outcome = json.loads((output / "outcomes.jsonl").read_text())
            self.assertEqual(outcome["outcome"], "provider_error")
            self.assertTrue(outcome["model_request_made"])

    def test_recovery_rejects_a_result_without_a_provider_boundary(self) -> None:
        from durable_routing_harness.durable_coordinator import _record_recovered_result
        from harness.records import AdmissionLog, RecordChain

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            definition = self.current_definition()
            bundle_path = root / "bundle.json"
            definition.bundle.write(bundle_path)
            trial = definition.bundle.schedule[0]
            result_path = root / "result.json"
            result_path.write_text(json.dumps({
                "bundle_sha256": definition.bundle.sha256, "trial_sha256": trial.sha256,
                "result": DurableRoutingResult("", "", (), "", (), ({"messages": [], "kwargs": {}},)).payload(),
            }))
            started = root / "started.json"
            started.write_text(json.dumps({"state": "model-verified", "pid": os.getpid()}))
            progress = _record_recovered_result(
                bundle_path, RecordChain(root / "outcomes.jsonl", definition.bundle.sha256),
                AdmissionLog(root / "admissions.jsonl", definition.bundle.sha256), root / "traces",
                definition, trial, result_path, started,
            )
            self.assertEqual(progress.status, "next_trial")
            outcome = json.loads((root / "outcomes.jsonl").read_text())
            self.assertEqual(outcome["outcome"], "infrastructure_invalid")
            self.assertFalse(outcome["model_request_made"])

    def test_worker_identity_rejects_pid_reuse(self) -> None:
        from durable_routing_harness.durable_coordinator import _process_identity, _worker_is_running

        with TemporaryDirectory() as temporary:
            marker = Path(temporary) / "lifecycle.json"
            marker.write_text(json.dumps({
                "state": "model-invoke-started", "pid": os.getpid(),
                "process_identity": _process_identity(os.getpid()) | {"command_sha256": "wrong"},
            }))
            self.assertFalse(_worker_is_running(marker))

    def test_worker_failure_detail_keeps_the_exception_tail(self) -> None:
        from durable_routing_harness.durable_coordinator import _command_detail

        result = subprocess.CompletedProcess(["worker"], 1, "", "prefix " * 100 + "actual cause")
        self.assertIn("actual cause", _command_detail(result))

    def test_coordinator_preserves_a_virtualenv_python_symlink(self) -> None:
        from durable_routing_harness.durable_coordinator import run_durable_routing_once

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "python"
            executable.symlink_to("/usr/bin/python3")
            commands: list[list[str]] = []
            with patch("durable_routing_harness.durable_coordinator.durable_definition",
                       return_value=self.current_definition()):
                run_durable_routing_once(
                    ROOT, root / "output", workspace_root=Path("/workspace"),
                    assist_root=Path("/assist"), assist_python=executable, assist_env=Path("/env"),
                    command_runner=lambda command: (commands.append(list(command)) or subprocess.CompletedProcess(
                        command, 1, "", "production is busy")),
                )
            self.assertIn(str(executable), commands[0])
