"""No-model contracts for the retrieved-versus-handed guidance development runner."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import stat
from tempfile import TemporaryDirectory
import unittest

from studies.reach_for_instructions.runner import (
    CONDITION_DELIVERY,
    CONDITIONS,
    CONTEXT_LINES,
    _capture_provider_requests,
    _filler,
    _descriptor,
    _provider_request,
    _fixture_path,
    _output_lock,
    _root_task,
    _schedule,
    _score,
    _system_prompt,
    _verify_provider_request,
    _worker_command,
    seal,
)
from harness.bundle import digest


ROOT = Path(__file__).resolve().parents[1]


class ReachForInstructionsTest(unittest.TestCase):
    def test_only_the_handed_prompt_contains_the_procedure(self) -> None:
        self.assertIn("first inventory", _system_prompt("handed", 0))
        self.assertNotIn("first inventory", _system_prompt("reached", 0))
        self.assertIn("reconcile-reimbursement", _system_prompt("handed", 0))
        self.assertIn("reconcile-reimbursement", _system_prompt("reached", 0))

    def test_filler_is_deterministic_and_has_no_task_identifier(self) -> None:
        self.assertEqual(_filler(3), _filler(3))
        self.assertNotIn("Northbridge", _filler(3))
        self.assertNotIn("load_skill", _filler(3))

    def test_oracle_accepts_structured_fact_forms_and_requires_ordered_reads(self) -> None:
        task = _root_task(ROOT)
        handoff = {
            "case_id": "NB-4817",
            "amount_cents": "$214.60",
            "receipt_id": "RX-19",
            "payment_status": "No payment has been issued.",
            "next_owner": "Imani",
            "next_action": "Select the retained receipt image, then approve or return the case.",
            "uncertainty": "The receipt image to retain remains to be selected.",
        }
        messages = [{"tool_calls": [{"name": "list_files", "arguments": {}}]}]
        messages.append({"tool_calls": [{"name": "load_skill", "arguments": {"name": "reconcile-reimbursement"}}]})
        messages.extend({"tool_calls": [{"name": "read_file", "arguments": {"file_path": path}}]} for path in task["oracle"]["required_reads"])
        messages.append({"tool_calls": [{"name": "write_file", "arguments": {"file_path": "outgoing/handoff.json"}}], "usage_metadata": {"input_tokens": 1234}})
        score = _score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(handoff)}, "messages": messages})
        self.assertTrue(score.passed)
        self.assertTrue(score.skill_loaded_before_first_read)
        self.assertEqual(score.first_input_tokens, 1234)
        aliases = {key: value for key, value in handoff.items() if key not in {"amount_cents", "uncertainty"}} | {
            "verified_amount_cents": handoff["amount_cents"],
            "remaining_uncertainty": handoff["uncertainty"],
            "payment_status": "not_issued",
        }
        self.assertTrue(_score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(aliases)}, "messages": messages}).passed)
        early = messages[2:3] + messages[:2] + messages[3:]
        self.assertFalse(_score(task, {"files": task["initial_files"] | {"outgoing/handoff.json": json.dumps(handoff)}, "messages": early}).passed)

    def test_seal_binds_the_full_response_surface(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("studies", "fixtures", "experiments"):
                shutil.copytree(ROOT / directory, root / directory)
            bundle = seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            self.assertEqual(len(bundle.schedule), len(CONTEXT_LINES) * len(CONDITIONS) * 3)
            self.assertEqual({trial.task for trial in bundle.schedule}, set(CONTEXT_LINES))
            self.assertEqual({trial.condition for trial in bundle.schedule}, set(CONDITION_DELIVERY))

    def test_schedule_is_deterministic_and_interleaves_context_blocks(self) -> None:
        schedule = _schedule()
        self.assertEqual(schedule, _schedule())
        self.assertNotEqual([trial.task for trial in schedule[:2]], [trial.task for trial in schedule[2:4]])

    def test_fixture_path_rejects_escape(self) -> None:
        root = Path("/tmp/reach-for-instructions")
        self.assertEqual(_fixture_path(root, "records/a.md"), root / "records/a.md")
        with self.assertRaises(ValueError):
            _fixture_path(root, "../escape")
        with self.assertRaises(ValueError):
            _fixture_path(root, "/etc/passwd")

    def test_new_raw_output_is_private_and_existing_public_output_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-output"
            with _output_lock(output):
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
            public = Path(temporary) / "public-output"
            public.mkdir(mode=0o755)
            public.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "private"):
                with _output_lock(public):
                    pass

    def test_worker_artifacts_are_absolute_across_admission_working_directories(self) -> None:
        command = _worker_command(
            ROOT, Path("/workspace"), Path("/assist"), Path("/python"),
            Path("relative/descriptor.json"), Path("relative/result.json"), Path("relative/marker"),
        )
        for flag in ("--descriptor", "--result", "--request-started"):
            self.assertTrue(Path(command[command.index(flag) + 1]).is_absolute())

    def test_provider_request_contract_rejects_missing_or_drifted_evidence(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("studies", "fixtures", "experiments"):
                shutil.copytree(ROOT / directory, root / directory)
            task = _root_task(root)
            bundle = seal(root, source_commit="a" * 40, assist_revision="b" * 40)
            descriptor = _descriptor(bundle, bundle.schedule[0], task)
            request = {
                "messages": [{"type": "system", "content": descriptor["system_prompt"]}, {"type": "human", "content": descriptor["user_prompt"]}],
                "invocation_params": {"model": "sealed-model", "temperature": 0.1, "max_tokens": 1200, "tools": [{"type": "function", "function": {"name": "load_skill", "parameters": {"type": "object"}}}]},
            }
            descriptor = descriptor | {"provider_request_sha256": digest(request)}
            valid = {
                "provider_requests": [request],
                "expected_provider_request": request,
                "provider_request_error": None,
                "fixture_sha256": descriptor["fixture_sha256"],
            }
            self.assertIsNone(_verify_provider_request(descriptor, valid))
            self.assertEqual(_verify_provider_request(descriptor, valid | {"provider_requests": []}), "provider request capture is missing")
            self.assertIn("differs", _verify_provider_request(descriptor, valid | {"provider_requests": [request | {"messages": []}]}))
            altered = request | {"invocation_params": request["invocation_params"] | {"temperature": 0.2}}
            self.assertIn("sealed digest", _verify_provider_request(descriptor, valid | {"provider_requests": [altered], "expected_provider_request": altered}))
            self.assertIn("fixture", _verify_provider_request(descriptor, valid | {"fixture_sha256": "wrong"}))

    def test_provider_request_serializes_model_messages(self) -> None:
        class Message:
            def __init__(self, role: str, content: str) -> None:
                self.role, self.content = role, content

            def model_dump(self, **_: object) -> dict[str, str]:
                return {"type": self.role, "content": self.content}

        class Model:
            def _get_invocation_params(self, **kwargs: object) -> dict[str, object]:
                return kwargs

        request = _provider_request(Model(), [Message("system", "S"), Message("human", "U")], None, {"tools": []})
        self.assertEqual(request["messages"], [{"type": "system", "content": "S"}, {"type": "human", "content": "U"}])
        self.assertEqual(request["invocation_params"], {"stop": None, "tools": []})
        with self.assertRaisesRegex(ValueError, "messages"):
            _provider_request(Model(), "not-a-list", None, {})

    def test_provider_boundary_capture_records_and_restores_the_model(self) -> None:
        class Message:
            def model_dump(self, **_: object) -> dict[str, str]:
                return {"type": "human", "content": "U"}

        class Model:
            def _get_invocation_params(self, **kwargs: object) -> dict[str, object]:
                return kwargs

            def _generate(self, messages: list[Message], **_: object) -> str:
                return "provider response"

        with TemporaryDirectory() as temporary:
            marker = Path(temporary) / "request-started"
            model, messages = Model(), [Message()]
            expected = _provider_request(model, messages, None, {})
            with _capture_provider_requests(model, marker, expected) as capture:
                self.assertEqual(model._generate(messages), "provider response")
            self.assertEqual(capture.requests, [expected])
            self.assertIsNone(capture.error)
            self.assertTrue(marker.exists())
            self.assertEqual(model._generate(messages), "provider response")


if __name__ == "__main__":
    unittest.main()
