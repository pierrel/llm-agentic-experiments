from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from harness import (
    Episode,
    ProviderReply,
    RecordChain,
    ScriptedProvider,
    StudyDefinition,
    ToolCall,
    VirtualWorkspace,
    archive_scripted_run,
    evaluate,
    mvp_definition,
    mvp_implementation_sha256,
    mvp_script,
    run_scripted_study,
    script_sha256,
)
from harness.records import AdmissionAttempt, AdmissionLog, ScheduledAdmission
from harness.bundle import atomic_write


ROOT = Path(__file__).resolve().parents[1]


class MvpHarnessTest(unittest.TestCase):
    def test_mvp_digest_covers_package_initialization_imports(self):
        from tempfile import TemporaryDirectory

        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as temporary:
            copied_root = Path(temporary)
            shutil.copytree(root / "harness", copied_root / "harness")
            original = mvp_implementation_sha256(copied_root)
            (copied_root / "harness" / "current_assist.py").write_text("changed package initialization import\n")
            self.assertNotEqual(mvp_implementation_sha256(copied_root), original)

    def setUp(self) -> None:
        self.definition = mvp_definition(ROOT)

    def test_mvp_definition_is_sealed_and_initial_requests_are_identical(self) -> None:
        self.definition.validate()
        task = self.definition.tasks["read-before-edit"]
        requests = [self.definition.initial_request(task, condition) for condition in self.definition.conditions.values()]
        self.assertEqual(requests[0], requests[1])
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "provider behavior differs"):
                run_scripted_study(
                    self.definition, Path(temporary), (), lambda *_: (True, "simulated admit")
                )

    def test_manifest_digest_schema_and_decoding_contamination_fail_closed(self) -> None:
        task = self.definition.tasks["read-before-edit"]
        changed_task = replace(task, initial_files={"budget-note.txt": "Budget: $99.\n"})
        with self.assertRaisesRegex(ValueError, "fixture digest"):
            StudyDefinition(self.definition.bundle, {task.task_id: changed_task}, self.definition.conditions).validate()

        changed_schema = replace(self.definition.bundle, tool_schemas={"read_file": {"tampered": True}})
        with self.assertRaisesRegex(ValueError, "tool schemas"):
            StudyDefinition(changed_schema, self.definition.tasks, self.definition.conditions).validate()

        changed_condition = replace(self.definition.conditions["C02"], decoding_overrides={"temperature": 1})
        changed_conditions = self.definition.conditions | {"C02": changed_condition}
        changed_bundle = replace(
            self.definition.bundle,
            conditions=self.definition.bundle.conditions | {"C02": {"sha256": changed_condition.sha256}},
        )
        with self.assertRaisesRegex(ValueError, "undeclared condition difference: decoding"):
            StudyDefinition(changed_bundle, self.definition.tasks, changed_conditions).validate()
        declared_bundle = replace(
            changed_bundle,
            registration=changed_bundle.registration | {"allowed_initial_request_fields": ["decoding"]},
        )
        StudyDefinition(declared_bundle, self.definition.tasks, changed_conditions).validate()

        changed_architecture = replace(
            self.definition.bundle,
            harness_architecture=self.definition.bundle.harness_architecture | {"id": "plan-and-execute"},
        )
        self.assertNotEqual(changed_architecture.sha256, self.definition.bundle.sha256)
        with self.assertRaisesRegex(ValueError, "model identity"):
            replace(self.definition.bundle, model={"id": "other"}).assert_complete()
        with self.assertRaisesRegex(ValueError, "settings do not match"):
            replace(self.definition.bundle, settings={"model": {}, "harness_architecture": {}}).assert_complete()

    def test_oracle_rejects_write_without_prior_read(self) -> None:
        task = self.definition.tasks["read-before-edit"]
        result = Episode(
            system_prompt=task.system_prompt,
            user_prompt=task.user_prompt,
            decoding=task.decoding,
            workspace=VirtualWorkspace(task.initial_files, task.skills),
            provider=ScriptedProvider(
                (
                    ProviderReply(
                        tool_calls=(
                            ToolCall("write_file", {"path": "budget-note.txt", "content": "Budget: $25.\n"}),
                        )
                    ),
                    ProviderReply(content="Updated it.", final=True),
                )
            ),
            max_turns=3,
        ).run()
        score = evaluate(task, result)
        self.assertFalse(score.passed)
        self.assertIn("not read before", score.detail)

    def test_provider_and_tool_failures_remain_reason_coded_outcomes(self) -> None:
        task = self.definition.tasks["read-before-edit"]
        provider_error = Episode(
            system_prompt=task.system_prompt,
            user_prompt=task.user_prompt,
            decoding=task.decoding,
            workspace=VirtualWorkspace(task.initial_files, task.skills),
            provider=ScriptedProvider(()),
            max_turns=1,
        ).run()
        self.assertEqual(provider_error.provider_error, "ValueError")
        self.assertEqual(provider_error.trace[0]["provider_error"], "ValueError")

        invalid_call = Episode(
            system_prompt=task.system_prompt,
            user_prompt=task.user_prompt,
            decoding=task.decoding,
            workspace=VirtualWorkspace(task.initial_files, task.skills),
            provider=ScriptedProvider(
                (
                    ProviderReply(tool_calls=(ToolCall("read_file", {"path": "missing.txt"}),)),
                    ProviderReply(content="Done.", final=True),
                )
            ),
            max_turns=2,
        ).run()
        self.assertTrue(invalid_call.invalid_tool_call)

        malformed_call = Episode(
            system_prompt=task.system_prompt,
            user_prompt=task.user_prompt,
            decoding=task.decoding,
            workspace=VirtualWorkspace(task.initial_files, task.skills),
            provider=ScriptedProvider(
                (
                    ProviderReply(tool_calls=(ToolCall("read_file", {"path": 3}),)),
                    ProviderReply(content="Done.", final=True),
                )
            ),
            max_turns=2,
        ).run()
        self.assertTrue(malformed_call.invalid_tool_call)

    def test_virtual_workspace_rejects_host_style_paths(self) -> None:
        workspace = VirtualWorkspace({"note.txt": "one"}, {})
        with self.assertRaisesRegex(ValueError, "invalid virtual path"):
            workspace.execute(ToolCall("read_file", {"path": "../note.txt"}))
        with self.assertRaisesRegex(ValueError, "invalid virtual path"):
            workspace.execute(ToolCall("write_file", {"path": "/tmp/note", "content": "two"}))
        with self.assertRaisesRegex(ValueError, "invalid virtual path"):
            workspace.execute(ToolCall("read_file", {"path": "."}))
        with self.assertRaisesRegex(ValueError, "invalid virtual path"):
            VirtualWorkspace({"a//note.txt": "one"}, {})
        with self.assertRaisesRegex(ValueError, "typed"):
            ProviderReply(content="done", final="yes").payload()  # type: ignore[arg-type]

    def test_runner_rejects_a_nonprivate_output_directory(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            output.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "private"):
                run_scripted_study(self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit"))

    def test_scripted_schedule_is_fresh_sealed_and_fully_accounted(self) -> None:
        denied: set[str] = set()

        def admission(trial_sha256: str, _: int) -> tuple[bool, str]:
            if trial_sha256 not in denied:
                denied.add(trial_sha256)
                return False, "simulated busy"
            return True, "simulated admit"

        with TemporaryDirectory() as temporary:
            artifacts = run_scripted_study(
                self.definition, Path(temporary), mvp_script(ROOT), admission
            )
            bundle = self.definition.bundle.read_verified(artifacts.bundle)
            records = RecordChain(artifacts.outcomes, bundle.sha256)
            admissions = AdmissionLog(artifacts.admissions, bundle.sha256)
            self.assertEqual(len(admissions.read_verified()), len(bundle.schedule) * 2)
            outcomes = records.read_verified()
            self.assertEqual({record["outcome"] for record in outcomes}, {"pass"})
            self.assertTrue(all(not record["model_request_made"] for record in outcomes))
            trace_paths = sorted(artifacts.traces.glob("*.json"))
            self.assertEqual(len(trace_paths), len(bundle.schedule))
            trace = json.loads(trace_paths[0].read_text())["trace"]
            expected = self.definition.initial_request(
                self.definition.tasks["read-before-edit"], self.definition.conditions["C01"]
            )
            self.assertEqual(trace[0]["request"] | {"request_id": None}, expected | {"request_id": None})
            self.assertTrue(trace[0]["request"]["request_id"].endswith(":t1"))
            report = json.loads(artifacts.report.read_text())
            self.assertEqual(report["conditions"], {"C01": {"pass": 2}, "C02": {"pass": 2}})
            self.assertEqual(report["tests"], bundle.fixtures)
            self.assertEqual(report["model"], bundle.model)
            self.assertEqual(report["harness_architecture"], bundle.harness_architecture)
            self.assertEqual(report["settings"], bundle.settings)
            resumed = run_scripted_study(self.definition, Path(temporary), mvp_script(ROOT), admission)
            self.assertEqual(resumed, artifacts)

    def test_runner_resumes_a_denied_trial_without_changing_the_bundle(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            with self.assertRaisesRegex(RuntimeError, "never allowed"):
                run_scripted_study(
                    self.definition,
                    output,
                    mvp_script(ROOT),
                    lambda *_: (False, "simulated busy"),
                    max_admission_attempts=1,
                )
            original_bundle = (output / "bundle.json").read_bytes()
            artifacts = run_scripted_study(
                self.definition,
                output,
                mvp_script(ROOT),
                lambda *_: (True, "simulated admit"),
            )
            self.assertEqual((output / "bundle.json").read_bytes(), original_bundle)
            bundle = self.definition.bundle.read_verified(artifacts.bundle)
            records = RecordChain(artifacts.outcomes, bundle.sha256)
            self.assertEqual(len(records.read_verified()), len(bundle.schedule))

    def test_runner_recovers_an_admitted_interrupted_scripted_episode(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            bundle_path = output / "bundle.json"
            self.definition.bundle.write(bundle_path)
            bundle = self.definition.bundle.read_verified(bundle_path)
            admissions = AdmissionLog(output / "admissions.jsonl", bundle.sha256)
            gate = ScheduledAdmission(bundle.schedule, admissions)
            gate.record(AdmissionAttempt(bundle.schedule[0], True, 1, "simulated admit"))
            artifacts = run_scripted_study(
                self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit")
            )
            outcomes = RecordChain(artifacts.outcomes, bundle.sha256).read_verified()
            self.assertEqual(outcomes[0]["outcome"], "infrastructure_invalid")
            self.assertEqual(len(outcomes), len(bundle.schedule))

    def test_runner_verifies_report_and_trace_artifacts_on_resume(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            artifacts = run_scripted_study(
                self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit")
            )
            artifacts.report.write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "final seal"):
                run_scripted_study(self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit"))
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            artifacts = run_scripted_study(
                self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit")
            )
            next(artifacts.traces.glob("*.json")).unlink()
            with self.assertRaisesRegex(ValueError, "trace artifacts"):
                run_scripted_study(self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit"))

    def test_runner_discards_only_stale_atomic_trace_temps_on_resume(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            artifacts = run_scripted_study(
                self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit")
            )
            trace = next(artifacts.traces.glob("*.json"))
            stale = artifacts.traces / f".{trace.name}.123.tmp"
            stale.write_text("incomplete trace")
            self.assertEqual(
                run_scripted_study(self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit")),
                artifacts,
            )
            self.assertFalse(stale.exists())

    def test_runner_rejects_a_regular_file_at_the_trace_directory_path(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "local-run"
            output.mkdir(mode=0o700)
            self.definition.bundle.write(output / "bundle.json")
            (output / "traces").write_text("not a directory")
            with self.assertRaisesRegex(ValueError, "trace path must be a real directory"):
                run_scripted_study(
                    self.definition, output, mvp_script(ROOT), lambda *_: (True, "simulated admit")
                )

    def test_result_capsule_captures_settings_results_and_raw_trace_evidence(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = run_scripted_study(
                self.definition, root / "local-run", mvp_script(ROOT), lambda *_: (True, "simulated admit")
            )
            capsule = archive_scripted_run(artifacts, root / "results" / "mvp-scripted-v1")
            record = json.loads(capsule.record.read_text())
            self.assertEqual(record["bundle_sha256"], self.definition.bundle.sha256)
            self.assertEqual(record["settings"], self.definition.bundle.settings)
            self.assertEqual(len(record["raw_trace_sha256"]), len(self.definition.bundle.schedule))
            self.assertTrue((capsule.root / "outcomes.jsonl.seal").exists())
            self.assertIn("No interpretation recorded yet", capsule.learning.read_text())
            self.assertIn("No proposal recorded yet", capsule.assist_proposal.read_text())
            with self.assertRaisesRegex(ValueError, "new real directory"):
                archive_scripted_run(artifacts, capsule.root)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = run_scripted_study(
                self.definition, root / "local-run", mvp_script(ROOT), lambda *_: (True, "simulated admit")
            )
            next(artifacts.traces.glob("*.json")).write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "artifacts do not match"):
                archive_scripted_run(artifacts, root / "results" / "tampered")

    def test_result_capsule_rejects_a_valid_json_final_seal_with_the_wrong_shape(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = run_scripted_study(
                self.definition, root / "local-run", mvp_script(ROOT), lambda *_: (True, "simulated admit")
            )
            artifacts.outcomes.with_suffix(".jsonl.seal").write_text("[]\n")
            with self.assertRaisesRegex(ValueError, "final seal must be a JSON object"):
                archive_scripted_run(artifacts, root / "results" / "invalid-seal")

    def test_atomic_write_retries_short_writes_and_removes_failed_temp(self) -> None:
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.json"
            original_write = os.write
            writes = 0

            def short_then_complete(descriptor: int, data: bytes | memoryview) -> int:
                nonlocal writes
                writes += 1
                if writes == 1:
                    return original_write(descriptor, data[:1])
                return original_write(descriptor, data)

            with patch("harness.bundle.os.write", side_effect=short_then_complete):
                atomic_write(target, b"complete")
            self.assertEqual(target.read_bytes(), b"complete")

            with patch("harness.bundle.os.write", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    atomic_write(target.with_name("failed.json"), b"incomplete")
            self.assertFalse((target.parent / f".failed.json.{os.getpid()}.tmp").exists())

    def test_atomic_write_recovers_its_own_stale_regular_temp(self) -> None:
        with TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.json"
            stale = target.parent / f".{target.name}.{os.getpid()}.tmp"
            stale.write_bytes(b"interrupted")
            atomic_write(target, b"complete")
            self.assertEqual(target.read_bytes(), b"complete")
            self.assertFalse(stale.exists())

    def test_runner_records_provider_failures_without_dropping_episodes(self) -> None:
        sealed_empty_script = replace(
            self.definition.bundle,
            registration=self.definition.bundle.registration | {"max_turns": 1, "script_sha256": script_sha256(())},
        )
        with TemporaryDirectory() as temporary:
            artifacts = run_scripted_study(
                StudyDefinition(sealed_empty_script, self.definition.tasks, self.definition.conditions),
                Path(temporary),
                (),
                lambda *_: (True, "simulated admit"),
            )
            bundle = self.definition.bundle.read_verified(artifacts.bundle)
            outcomes = RecordChain(artifacts.outcomes, bundle.sha256).read_verified()
            self.assertEqual(len(outcomes), len(bundle.schedule))
            self.assertEqual({record["outcome"] for record in outcomes}, {"provider_error"})
