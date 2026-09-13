"""No-model integrity contracts for the exact V8-r3 reproduction."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from harness.bundle import StudyBundle, canonical_json, digest
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v8 import runner as parent_runner
from studies.reach_for_instructions_confirmation_v8_reproduction import analysis, runner
from studies.reach_for_instructions_confirmation_v8_reproduction.integrity import (
    events_match_admissions,
    verify_event_interval,
)


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "results" / "reach-for-instructions-confirmation-v8-qwen38-current-r3"
TEST_REGISTRATION = {
    "commit": "1" * 40,
    "tag_object": "2" * 40,
    "tree": "3" * 40,
}


def _identity(manifest: dict[str, object]) -> bytes:
    runtime = manifest["runtime"]
    parent = manifest["parent"]
    publication = manifest["registration"]
    assert isinstance(runtime, dict) and isinstance(parent, dict) and isinstance(publication, dict)
    expected = runtime["expected_attestation"]
    assert isinstance(expected, dict)
    value = {
        "assist": {
            "commit": runtime["assist_commit"], "status": "", "tree": runtime["assist_tree"],
        },
        "deployment_environment": expected["deployment_environment"],
        "environment": {
            key: expected[key] for key in ("distributions", "environment", "modules", "python")
        },
        "process_scope": expected["process_scope"],
        "execution": {
            "commit": parent["commit"], "status": "", "tree": parent["tree"],
        },
        "manifest_sha256": digest(manifest),
        "publication": {
            "manifest_sha256": digest(manifest),
            "publication_branch": publication["publication_branch"],
            "publication_remote": publication["publication_remote"],
            "registration": TEST_REGISTRATION,
        },
        "registered_model": runtime["model"],
        "registration": TEST_REGISTRATION,
        "server": expected["server"] | {"pid": 123, "start_ticks": "456"},
        "shared_gate": expected["shared_gate"],
    }
    return canonical_json(value) + b"\n"


def _reproduction_fixture(parent: Path, manifest: dict[str, object]) -> Path:
    execution = manifest["execution"]
    assert isinstance(execution, dict)
    capsule = parent / Path(str(execution["capsule_relative"])).name
    shutil.copytree(HISTORICAL, capsule)
    attestations = capsule / "runtime-attestations"
    attestations.mkdir()
    identity = _identity(manifest)
    thread_id = str(execution["coordination_thread_id"])
    admissions = [json.loads(line) for line in (capsule / "admissions.jsonl").read_text().splitlines()]
    outcomes = [json.loads(line) for line in (capsule / "outcomes.jsonl").read_text().splitlines()]
    all_events = []
    for index in range(3):
        started = f"2026-09-12T00:{index * 16:02d}:00+00:00"
        finished = f"2026-09-12T00:{index * 16 + 1:02d}:00+00:00"
        next_batch_not_before = 1789172160.0 + index * 960 if index < 2 else None
        events = []
        for admission in admissions[index * 24:(index + 1) * 24]:
            self_events = [
                {"at": started, "event": "resource_started", "resource": "llm", "thread": thread_id},
                {"at": started, "event": "resource_finished", "exit_code": 0, "resource": "llm", "thread": thread_id},
            ]
            events.extend(self_events)
        all_events.extend(events)
        interval = {
            "admissions_after": (index + 1) * 24,
            "admissions_before": index * 24,
            "batch_cooldown_mtime_ns": (
                int((next_batch_not_before - 900) * 1_000_000_000)
                if next_batch_not_before is not None else None
            ),
            "events": events,
            "finished_at": finished,
            "next_batch_not_before_unix": next_batch_not_before,
            "next_denial_not_before_unix": None,
            "outcomes_after": (index + 1) * 24,
            "outcomes_before": index * 24,
            "started_at": started,
        }
        (attestations / f"{index:03d}-identity-before.json").write_bytes(identity)
        (attestations / f"{index:03d}-identity-after.json").write_bytes(identity)
        (attestations / f"{index:03d}-events.json").write_bytes(canonical_json(interval) + b"\n")
    provenance = {
        "attestation_files": {
            path.name: runner._sha256(path) for path in sorted(attestations.iterdir())
        },
        "capsule_run_sha256": runner._sha256(capsule / "run.json"),
        "coordination_thread_id": thread_id,
        "execution_witness": {
            "admission_count": len(admissions),
            "admissions_file_sha256": runner._sha256(capsule / "admissions.jsonl"),
            "event_count": len(all_events),
            "events_sha256": digest(all_events),
            "outcome_count": len(outcomes),
            "outcomes_file_sha256": runner._sha256(capsule / "outcomes.jsonl"),
        },
        "manifest_sha256": digest(manifest),
        "registration": TEST_REGISTRATION,
        "schema": "reach-v8-exact-reproduction-provenance-v1",
    }
    (capsule / "reproduction-provenance.json").write_bytes(
        canonical_json(provenance | {"record_sha256": digest(provenance)}) + b"\n"
    )
    return capsule


def _seal_capsule(capsule: Path, manifest: dict[str, object]) -> None:
    sealed_files = {
        path.relative_to(capsule).as_posix(): runner._sha256(path)
        for path in sorted(capsule.rglob("*"))
        if path.is_file()
        and path.name not in {"learning.md", "assist-roadmap-proposal.md"}
    }
    seal = {
        "schema": "reach-v8-exact-reproduction-seal-v1",
        "manifest_sha256": digest(manifest),
        "sealed_files": sealed_files,
    }
    (capsule / "reproduction-seal.json").write_bytes(
        canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n"
    )


class ReachForInstructionsConfirmationV8ReproductionTest(unittest.TestCase):
    def test_manifest_pins_the_exact_authoritative_parent(self) -> None:
        manifest = runner._load_manifest(ROOT)
        parent = manifest["parent"]
        bundle = StudyBundle.read_verified(ROOT / parent["bundle_path"])
        historical = StudyBundle.read_verified(HISTORICAL / "bundle.json")

        self.assertEqual(parent["tag"], "reach-for-instructions-confirmation-v8-qwen38-current-r3")
        self.assertEqual(parent["commit"], "3ac6975e46f6c217feb8237ca15e4c65eea3065d")
        self.assertEqual(bundle.payload(), historical.payload())
        self.assertEqual(bundle.sha256, parent["bundle_sha256"])
        self.assertEqual(len(bundle.schedule), 72)

    def test_locked_analysis_keeps_runs_and_all_six_cells_separate(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            reproduction = _reproduction_fixture(Path(temporary), manifest)
            output = Path(temporary) / "analysis.json"
            analysis.analyze(manifest, reproduction, HISTORICAL, output, TEST_REGISTRATION)
            report = json.loads(output.read_text())

        self.assertEqual(set(report), {"analysis", "bundle_sha256", "historical", "reproduction"})
        for run in (report["historical"], report["reproduction"]):
            self.assertEqual(len(run["cells"]), 6)
            self.assertTrue(all(cell["denominator"] == 12 for cell in run["cells"].values()))
            self.assertTrue(all(sum(cell["reason_codes"].values()) == 12 for cell in run["cells"].values()))
            self.assertTrue(all(
                sum(position.values()) == 6
                for cell in run["cells"].values()
                for position in cell["position_outcomes"].values()
            ))
        self.assertEqual(report["historical"], report["reproduction"])

    def test_historical_capsule_cannot_substitute_for_reproduction(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "cannot substitute"):
                analysis.analyze(
                    manifest, HISTORICAL, HISTORICAL, Path(temporary) / "analysis.json",
                    TEST_REGISTRATION,
                )

            copied = Path(temporary) / manifest["execution"]["capsule_id"]
            shutil.copytree(HISTORICAL, copied)
            with self.assertRaisesRegex(ValueError, "provenance"):
                analysis.analyze(
                    manifest, copied, HISTORICAL, Path(temporary) / "copied-analysis.json",
                    TEST_REGISTRATION,
                )

    def test_reproduction_identity_cannot_be_an_opaque_fabrication(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = _reproduction_fixture(Path(temporary), manifest)
            attestations = capsule / "runtime-attestations"
            for path in attestations.glob("*-identity-*.json"):
                path.write_bytes(b'{"identity":"fabricated"}\n')
            provenance_path = capsule / "reproduction-provenance.json"
            provenance = json.loads(provenance_path.read_text())
            provenance.pop("record_sha256")
            provenance["attestation_files"] = {
                path.name: runner._sha256(path) for path in sorted(attestations.iterdir())
            }
            provenance_path.write_bytes(
                canonical_json(provenance | {"record_sha256": digest(provenance)}) + b"\n"
            )
            with self.assertRaisesRegex(ValueError, "identity attestation"):
                analysis.analyze(
                    manifest,
                    capsule,
                    HISTORICAL,
                    Path(temporary) / "analysis.json",
                    TEST_REGISTRATION,
                )

    def test_locked_analysis_rejects_changed_historical_metadata(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            reproduction = _reproduction_fixture(Path(temporary), manifest)
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            metadata = capsule / "trial-metadata.json"
            metadata.write_bytes(metadata.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "trial metadata"):
                analysis.analyze(
                    manifest, reproduction, capsule, Path(temporary) / "analysis.json",
                    TEST_REGISTRATION,
                )

    def test_locked_analysis_rejects_undeclared_response_surface_changes(self) -> None:
        manifest = runner._load_manifest(ROOT)

        def prompt(bundle: dict[str, object]) -> None:
            registration = bundle["registration"]
            assert isinstance(registration, dict)
            requests = registration["provider_request_sha256"]
            assert isinstance(requests, dict)
            first = next(iter(requests))
            requests[first] = "0" * 64

        def schema(bundle: dict[str, object]) -> None:
            schemas = bundle["tool_schemas"]
            assert isinstance(schemas, dict)
            schemas["load_skill"] = {"name": "different"}

        def fixture(bundle: dict[str, object]) -> None:
            fixtures = bundle["fixtures"]
            assert isinstance(fixtures, dict)
            fixtures["C-low"] = "0" * 64

        def decoding(bundle: dict[str, object]) -> None:
            settings = bundle["settings"]
            model = bundle["model"]
            assert isinstance(settings, dict) and isinstance(model, dict)
            model_settings = settings["model"]
            assert isinstance(model_settings, dict)
            model_settings["temperature"] = 0.2
            model["configuration_sha256"] = digest(model_settings)

        def schedule(bundle: dict[str, object]) -> None:
            trials = bundle["schedule"]
            assert isinstance(trials, list)
            del trials[-2:]

        for name, mutate in {
            "prompt": prompt,
            "schema": schema,
            "fixture": fixture,
            "decoding": decoding,
            "omitted-scheduled-pair": schedule,
        }.items():
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                reproduction = _reproduction_fixture(Path(temporary), manifest)
                capsule = Path(temporary) / "capsule"
                shutil.copytree(HISTORICAL, capsule)
                bundle_path = capsule / "bundle.json"
                stored = json.loads(bundle_path.read_text())
                mutate(stored["bundle"])
                stored["sha256"] = digest(stored["bundle"])
                bundle_path.write_bytes(canonical_json(stored) + b"\n")
                with self.assertRaises(ValueError):
                    analysis.analyze(
                        manifest, reproduction, capsule, Path(temporary) / "analysis.json",
                        TEST_REGISTRATION,
                    )

    def test_locked_analysis_rejects_an_altered_result_record(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            reproduction = _reproduction_fixture(Path(temporary), manifest)
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            outcomes = capsule / "outcomes.jsonl"
            records = outcomes.read_text().splitlines()
            first = json.loads(records[0])
            first["outcome"] = "pass" if first["outcome"] != "pass" else "artifact_failure"
            records[0] = canonical_json(first).decode()
            outcomes.write_text("\n".join(records) + "\n")
            with self.assertRaises(ValueError):
                analysis.analyze(
                    manifest, reproduction, capsule, Path(temporary) / "analysis.json",
                    TEST_REGISTRATION,
                )

    def test_progress_guard_rejects_an_omitted_scheduled_outcome(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            shutil.copy2(HISTORICAL / "admissions.jsonl", output / "admissions.jsonl")
            records = (HISTORICAL / "outcomes.jsonl").read_text().splitlines()
            (output / "outcomes.jsonl").write_text("\n".join(records[:-1]) + "\n")
            with self.assertRaisesRegex(ValueError, "progress differs"):
                runner._verified_progress(output, bundle)

    def test_progress_guard_rejects_a_rechained_invalid_outcome(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            shutil.copy2(HISTORICAL / "admissions.jsonl", output / "admissions.jsonl")
            records = [
                json.loads(line)
                for line in (HISTORICAL / "outcomes.jsonl").read_text().splitlines()
            ]
            previous = bundle.sha256
            encoded = []
            for index, record in enumerate(records):
                record.pop("record_sha256")
                record["previous_sha256"] = previous
                if index == 0:
                    record["outcome"] = "invented"
                previous = digest(record)
                encoded.append(canonical_json(record | {"record_sha256": previous}))
            (output / "outcomes.jsonl").write_bytes(b"\n".join(encoded) + b"\n")
            with self.assertRaisesRegex(ValueError, "outcome record"):
                runner._verified_progress(output, bundle)

    def test_opaque_condition_labels_never_reach_model_prompts(self) -> None:
        bundle = StudyBundle.read_verified(ROOT / runner._load_manifest(ROOT)["parent"]["bundle_path"])
        with parent_runner._configured():
            task = core._root_task(ROOT)
            for trial in bundle.schedule:
                descriptor = core._descriptor(bundle, trial, task)
                self.assertNotIn("G01", descriptor["system_prompt"])
                self.assertNotIn("G02", descriptor["system_prompt"])
                self.assertNotIn("G01", descriptor["user_prompt"])
                self.assertNotIn("G02", descriptor["user_prompt"])

    def test_admission_events_must_match_each_shared_resource_transaction(self) -> None:
        thread = "thread-1"
        admitted = [{"admitted": True}, {"admitted": True}]
        events = [
            {"thread": thread, "resource": "llm", "event": "resource_started"},
            {"thread": thread, "resource": "llm", "event": "resource_finished", "exit_code": 0},
            {"thread": thread, "resource": "llm", "event": "resource_started"},
            {"thread": thread, "resource": "llm", "event": "resource_finished", "exit_code": 1},
        ]
        self.assertTrue(events_match_admissions(
            new_admissions=admitted, new_outcomes=[{"outcome": "pass"}, {"outcome": "provider_error"}],
            new_events=events, thread_id=thread
        ))
        self.assertFalse(events_match_admissions(
            new_admissions=admitted, new_outcomes=[{"outcome": "pass"}, {"outcome": "provider_error"}],
            new_events=events[:-1], thread_id=thread
        ))
        self.assertTrue(events_match_admissions(
            new_admissions=[{"admitted": True}], new_outcomes=[{"outcome": "timeout"}],
            new_events=events[:1], thread_id=thread
        ))

    def test_only_exact_corroborated_production_denial_can_retry(self) -> None:
        thread = "thread-1"
        detail = (
            "agentic: production is busy (processing=1); not starting llm work. "
            "Run `tools/agentic production status --attempt N`, set its next-probe timer, "
            "and continue other work."
        )
        admission = {"admitted": False, "detail": detail}
        event = {"thread": thread, "resource": "llm", "event": "production_admission_denied"}
        self.assertTrue(runner._true_denial(
            new_admissions=[admission], new_events=[event], thread_id=thread
        ))
        self.assertTrue(events_match_admissions(
            new_admissions=[admission], new_outcomes=[], new_events=[event], thread_id=thread
        ))
        self.assertFalse(runner._true_denial(
            new_admissions=[admission],
            new_events=[event, {"thread": thread, "resource": "llm", "event": "resource_started"}],
            thread_id=thread,
        ))
        completed = [
            {"thread": thread, "resource": "llm", "event": "resource_started"},
            {"thread": thread, "resource": "llm", "event": "resource_finished", "exit_code": 0},
        ]
        self.assertTrue(runner._true_denial(
            new_admissions=[{"admitted": True}, admission],
            new_events=completed + [event],
            thread_id=thread,
        ))
        self.assertTrue(events_match_admissions(
            new_admissions=[{"admitted": True}, admission],
            new_outcomes=[{"outcome": "pass"}],
            new_events=completed + [event],
            thread_id=thread,
        ))
        self.assertFalse(runner._true_denial(
            new_admissions=[admission | {"detail": "worker failed"}],
            new_events=[event],
            thread_id=thread,
        ))

    def test_attestation_inventory_is_complete_and_invariant(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = _reproduction_fixture(Path(temporary), manifest)
            root = capsule / "runtime-attestations"
            paths, intervals = runner.verify_attestation_inventory(
                root, manifest=manifest, registration=TEST_REGISTRATION
            )
            self.assertEqual((len(paths), len(intervals)), (9, 3))
            (root / "001-identity-after.json").write_bytes(b'{"identity":2}\n')
            with self.assertRaisesRegex(ValueError, "identity differs"):
                runner.verify_attestation_inventory(
                    root, manifest=manifest, registration=TEST_REGISTRATION
                )

    def test_wrong_coordinator_identity_rejects_before_any_subprocess(self) -> None:
        output = Path("/tmp") / runner.STUDY
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "wrong-thread"}), patch(
            "studies.reach_for_instructions_confirmation_v8_reproduction.runner.subprocess.run"
        ) as execute:
            with self.assertRaisesRegex(ValueError, "thread identity"):
                runner.run_batch(
                    ROOT, output, Path("/unused-attestations"),
                    execution_root=Path("/unused-experiment"),
                    assist_source=Path("/unused-assist"),
                    assist_python=Path("/unused-python"),
                    workspace_root=Path("/unused-workspace"),
                    model_path=Path("/unused-model"),
                    server_pid=1,
                    llama_source=Path("/unused-llama"),
                    events=Path("/unused-events"),
                )
        execute.assert_not_called()

    def test_wrapper_lock_rejects_a_concurrent_invocation(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / runner.STUDY
            with runner._wrapper_lock(output):
                with self.assertRaisesRegex(ValueError, "invocation is active"):
                    with runner._wrapper_lock(output):
                        self.fail("concurrent wrapper lock unexpectedly succeeded")

    def test_prepare_failure_never_publishes_the_canonical_runtime(self) -> None:
        with TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            runtime = workspace / runner.RUNTIME_RELATIVE
            gate = workspace / "tools" / "agentic"
            gate.parent.mkdir()
            gate.write_text("gate")
            deploy_environment = workspace / "assist" / ".deploy.env"
            deploy_environment.parent.mkdir()
            deploy_environment.write_text("ASSIST_MODEL_URL=http://127.0.0.1:8000/v1\n")
            deploy_environment.chmod(0o600)
            manifest = {
                "runtime": {
                    "expected_attestation": {
                        "deployment_environment": {
                            "sha256": runner._sha256(deploy_environment)
                        },
                        "shared_gate": {"sha256": runner._sha256(gate)},
                    }
                }
            }
            with patch.object(
                runner, "_canonical_workspace_root", return_value=workspace
            ), patch.object(runner, "_load_manifest", return_value=manifest), patch.object(
                runner, "_verify_publication", return_value={}
            ), patch.object(
                runner.subprocess, "run", side_effect=OSError("clone failed")
            ):
                with self.assertRaisesRegex(OSError, "clone failed"):
                    runner.prepare_runtime(ROOT, Path("/unused-assist"), runtime)
            self.assertFalse(runtime.exists())
            self.assertEqual(
                list(runtime.parent.glob(f".{runner.STUDY}.preparing-*")), []
            )

    def test_scoped_child_interruption_kills_the_complete_systemd_scope(self) -> None:
        process = Mock()
        process.communicate.side_effect = [KeyboardInterrupt(), ("", "")]
        process.returncode = -9
        cleanup_state: list[str] = []

        @contextmanager
        def defer_signals():
            cleanup_state.append("entered")
            try:
                yield
            finally:
                cleanup_state.append("exited")

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / runner.STUDY
            output.mkdir(mode=0o700)
            with patch.object(
                runner.subprocess, "Popen", return_value=process
            ) as launch, patch.object(
                runner, "_bind_scope", return_value=Path(temporary) / "scope"
            ), patch.object(runner, "_release_scope"), patch.object(
                runner, "_kill_scope"
            ) as terminate, patch.object(
                runner, "_defer_termination_signals", side_effect=defer_signals
            ):
                with self.assertRaises(KeyboardInterrupt):
                    runner._run_scoped(
                        ["/unused-parent"],
                        cwd=Path(temporary),
                        env={},
                        output=output,
                        stage="archive worker",
                    )
            self.assertTrue((output / runner.INVALID).exists())
            self.assertTrue(launch.call_args.kwargs["start_new_session"])
            self.assertEqual(cleanup_state, ["entered", "exited"])
            terminate.assert_called_once()
            self.assertIs(terminate.call_args.args[0], process)
            self.assertEqual(terminate.call_args.args[1], Path(temporary) / "scope")

    def test_bound_scope_cleanup_rejects_a_missing_atomic_kill_control(self) -> None:
        process = Mock()
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "kill control is unavailable"):
                runner._kill_scope(process, Path(temporary) / "missing-scope")
        process.communicate.assert_not_called()

    def test_scope_binding_failure_kills_the_still_gated_launcher(self) -> None:
        process = Mock()
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / runner.STUDY
            output.mkdir(mode=0o700)
            with patch.object(
                runner.subprocess, "Popen", return_value=process
            ), patch.object(
                runner, "_bind_scope", side_effect=RuntimeError("scope absent")
            ), patch.object(runner, "_kill_unbound_scope") as terminate:
                with self.assertRaisesRegex(ValueError, "could not be launched"):
                    runner._run_scoped(
                        ["/unused-parent"],
                        cwd=Path(temporary),
                        env={},
                        output=output,
                        stage="parent runner",
                    )
            self.assertTrue((output / runner.INVALID).exists())
            terminate.assert_called_once()
            self.assertIs(terminate.call_args.args[0], process)

    def test_scope_bootstrap_never_releases_payload_on_pipe_eof(self) -> None:
        with TemporaryDirectory() as temporary:
            marker = Path(temporary) / "payload-ran"
            result = subprocess.run(
                [
                    "/bin/sh", "-c", runner._SCOPE_BOOTSTRAP, "sh", "1", "0",
                    "/usr/bin/touch", str(marker),
                ],
                input="",
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 125)
            marker_fields = result.stdout.split()
            self.assertEqual(marker_fields[0], "R")
            self.assertTrue(marker_fields[1].isdigit())
            self.assertFalse(marker.exists())

    def test_execution_environment_cannot_redirect_the_shared_gate(self) -> None:
        with patch.dict(
            os.environ,
            {"AGENTIC_ROOT": "/tmp/other", "PATH": "/tmp/other"},
        ), patch.object(
            runner, "_production_threads_directory", return_value=Path("/production")
        ):
            environment = runner._execution_environment(
                workspace_root=Path("/workspace"),
                execution_root=Path("/execution"),
                assist_source=Path("/assist"),
                production_threads_path_sha256="0" * 64,
            )
        self.assertEqual(environment["AGENTIC_ROOT"], "/workspace")
        self.assertEqual(environment["AGENTIC_PRODUCTION_THREADS_DIR"], "/production")
        self.assertEqual(environment["PATH"], "/usr/bin:/bin")
        self.assertEqual(environment["CODEX_THREAD_ID"], runner.COORDINATION_THREAD_ID)

    def test_production_status_directory_is_hash_pinned_from_systemd(self) -> None:
        with TemporaryDirectory() as temporary:
            threads = Path(temporary)
            expected = runner.hashlib.sha256(str(threads).encode()).hexdigest()
            service = subprocess.CompletedProcess(
                [], 0, stdout=f"OTHER=value ASSIST_THREADS_DIR={threads}\n", stderr=""
            )
            with patch.object(runner.subprocess, "run", return_value=service):
                self.assertEqual(runner._production_threads_directory(expected), threads)
            with patch.object(runner.subprocess, "run", return_value=service):
                with self.assertRaisesRegex(ValueError, "differs from registration"):
                    runner._production_threads_directory("0" * 64)

    def test_every_fixed_runtime_path_component_rejects_symlinks(self) -> None:
        with TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            runtime = workspace / runner.RUNTIME_RELATIVE
            runtime.mkdir(parents=True)
            alternate = workspace / "alternate"
            alternate.mkdir()
            (runtime / "experiment").symlink_to(alternate, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked path component"):
                runner._verify_runtime_paths(
                    workspace_root=workspace,
                    execution_root=runtime / "experiment",
                    assist_source=runtime / "assist",
                    output=runtime / "raw" / runner.STUDY,
                    attestations=runtime / "attestations",
                )

    def test_worker_workspace_is_exact_and_descriptor_bound(self) -> None:
        with TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            experiment = runtime / "experiment"
            experiment.mkdir()
            workspace = runtime / "worker-workspace"
            gate = workspace / "tools" / "agentic"
            deploy_environment = workspace / "assist" / ".deploy.env"
            gate.parent.mkdir(parents=True, mode=0o700)
            deploy_environment.parent.mkdir(mode=0o700)
            gate.write_text("gate")
            gate.chmod(0o500)
            deploy_environment.write_text("environment")
            deploy_environment.chmod(0o400)
            gate.parent.chmod(0o500)
            deploy_environment.parent.chmod(0o500)
            workspace.chmod(0o500)
            manifest = {
                "runtime": {
                    "expected_attestation": {
                        "deployment_environment": {
                            "sha256": runner._sha256(deploy_environment)
                        },
                        "shared_gate": {"sha256": runner._sha256(gate)},
                    }
                }
            }
            verified = runner._verify_worker_workspace(experiment, manifest)
            with runner._bound_worker_workspace(verified, manifest) as reference:
                self.assertEqual((reference / "tools" / "agentic").read_text(), "gate")
                resolved_by_child = subprocess.run(
                    [
                        "/bin/sh", "-c", 'exec /usr/bin/test -r "$1/tools/agentic"',
                        "sh", str(reference),
                    ],
                    check=False,
                )
                self.assertEqual(resolved_by_child.returncode, 0)
            deploy_environment.chmod(0o600)
            deploy_environment.write_text("changed")
            deploy_environment.chmod(0o400)
            with self.assertRaisesRegex(ValueError, "differs from registration"):
                runner._verify_worker_workspace(experiment, manifest)
            workspace.chmod(0o700)
            gate.parent.chmod(0o700)
            deploy_environment.parent.chmod(0o700)

    def test_worker_workspace_rejects_a_symlinked_gate_ancestor(self) -> None:
        with TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            experiment = runtime / "experiment"
            experiment.mkdir()
            workspace = runtime / "worker-workspace"
            alternate = runtime / "alternate"
            alternate.mkdir()
            (workspace / "assist").mkdir(parents=True)
            (workspace / "tools").symlink_to(alternate, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked path component"):
                runner._verify_worker_workspace(experiment, {"runtime": {}})

    def test_archive_rejects_a_symlinked_raw_cohort(self) -> None:
        with TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            runtime = workspace / runner.RUNTIME_RELATIVE
            output = runtime / "raw" / runner.STUDY
            output.parent.mkdir(parents=True)
            target = runtime / "alternate"
            target.mkdir(mode=0o700)
            output.symlink_to(target, target_is_directory=True)
            capsule = runtime / "capsule" / runner.STUDY
            with patch.dict(
                os.environ, {"CODEX_THREAD_ID": runner.COORDINATION_THREAD_ID}
            ), patch.object(
                runner, "_canonical_workspace_root", return_value=workspace
            ):
                with self.assertRaisesRegex(ValueError, "symlinked path component"):
                    runner.archive_and_analyze(
                        ROOT,
                        output,
                        capsule,
                        capsule / "reproduction-analysis.json",
                        runtime / "attestations",
                        execution_root=runtime / "experiment",
                        assist_source=runtime / "assist",
                        assist_python=Path("/unused-python"),
                        workspace_root=workspace,
                    )

    def test_secondary_metadata_is_recomputed_from_sealed_traces(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        trial = bundle.schedule[0]
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            traces = output / "traces"
            traces.mkdir()
            (traces / f"{trial.sha256}.json").write_bytes(canonical_json({
                "trial_sha256": trial.sha256,
                "result": {
                    "first_prompt_tokens": 123,
                    "skill_loaded_before_first_read": True,
                },
            }) + b"\n")
            one_trial_bundle = SimpleNamespace(schedule=(trial,))
            metadata = json.loads(runner._trial_metadata_from_traces(
                output,
                one_trial_bundle,
                [{"trial_sha256": trial.sha256, "outcome": "pass", "detail": "ok"}],
            ))
        self.assertEqual(metadata[0]["first_prompt_tokens"], 123)
        self.assertTrue(metadata[0]["skill_loaded_before_first_read"])
        self.assertEqual(metadata[0]["outcome"], "pass")

    def test_canonical_workspace_is_derived_and_cannot_be_substituted(self) -> None:
        workspace = runner._canonical_workspace_root(ROOT)
        self.assertEqual(workspace, ROOT.parents[2])
        with patch.dict(
            os.environ, {"CODEX_THREAD_ID": runner.COORDINATION_THREAD_ID}
        ), patch.object(
            runner, "_canonical_workspace_root", return_value=workspace
        ), patch.object(runner.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "canonical shared workspace"):
                runner.run_batch(
                    ROOT, Path("/tmp") / runner.STUDY, Path("/unused-attestations"),
                    execution_root=Path("/unused-experiment"),
                    assist_source=Path("/unused-assist"),
                    assist_python=Path("/unused-python"),
                    workspace_root=Path("/copied-workspace"),
                    model_path=Path("/unused-model"),
                    server_pid=1,
                    llama_source=Path("/unused-llama"),
                    events=Path("/copied-workspace/.coordination/events.jsonl"),
                )
            with self.assertRaisesRegex(ValueError, "raw output differs"):
                runtime = workspace / runner.RUNTIME_RELATIVE
                runner.run_batch(
                    ROOT,
                    workspace / ".coordination/other/raw" / runner.STUDY,
                    runtime / "attestations",
                    execution_root=runtime / "experiment",
                    assist_source=runtime / "assist",
                    assist_python=Path("/unused-python"),
                    workspace_root=workspace,
                    model_path=Path("/unused-model"),
                    server_pid=1,
                    llama_source=Path("/unused-llama"),
                    events=workspace / ".coordination/events.jsonl",
                )
            with self.assertRaisesRegex(ValueError, "runtime root differs"):
                runner.prepare_runtime(ROOT, Path("/unused-assist"), workspace / "other")
            alternate_capsule = workspace / "other" / runner.STUDY
            with self.assertRaisesRegex(ValueError, "capsule differs"):
                runner.archive_and_analyze(
                    ROOT,
                    runtime / "raw" / runner.STUDY,
                    alternate_capsule,
                    alternate_capsule / "reproduction-analysis.json",
                    runtime / "attestations",
                    execution_root=runtime / "experiment",
                    assist_source=runtime / "assist",
                    assist_python=Path("/unused-python"),
                    workspace_root=workspace,
                )
        execute.assert_not_called()

    def test_event_slice_rejects_a_rewritten_prefix(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            appended = b'{"event":"new"}\n'
            events.write_bytes(prefix + appended)
            descriptor = os.open(events, os.O_RDONLY)
            try:
                self.assertEqual(
                    runner._read_appended_events(descriptor, prefix), [{"event": "new"}]
                )
                events.write_bytes(b'{"event":"bad"}\n' + appended)
                with self.assertRaisesRegex(ValueError, "non-append-only"):
                    runner._read_appended_events(descriptor, prefix)
            finally:
                os.close(descriptor)

    def test_event_slice_ignores_a_replacement_path(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            events.write_bytes(prefix + b'{"event":"real"}\n')
            descriptor = os.open(events, os.O_RDONLY)
            try:
                replacement = events.with_suffix(".replacement")
                replacement.write_bytes(prefix + b'{"event":"fabricated"}\n')
                replacement.replace(events)
                self.assertEqual(
                    runner._read_appended_events(descriptor, prefix), [{"event": "real"}]
                )
            finally:
                os.close(descriptor)

    def test_event_slice_rejects_a_bare_carriage_return_separator(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            events.write_bytes(
                prefix + b'{"event":"started"}\r{"event":"finished"}\n'
            )
            descriptor = os.open(events, os.O_RDONLY)
            try:
                with self.assertRaisesRegex(ValueError, "malformed"):
                    runner._read_appended_events(descriptor, prefix)
            finally:
                os.close(descriptor)

    def test_termination_signals_become_cleanup_bearing_interruptions(self) -> None:
        with self.assertRaises(KeyboardInterrupt):
            with runner._termination_interrupts():
                os.kill(os.getpid(), signal.SIGTERM)

    def test_event_interval_requires_ordered_events_within_parent_run(self) -> None:
        record = {
            "admissions_after": 0,
            "admissions_before": 0,
            "batch_cooldown_mtime_ns": None,
            "started_at": "2026-09-12T00:00:00.900000+00:00",
            "finished_at": "2026-09-12T00:00:02.100000+00:00",
            "events": [
                {"at": "2026-09-12T00:00:00+00:00"},
                {"at": "2026-09-12T00:00:02+00:00"},
            ],
            "next_batch_not_before_unix": None,
            "next_denial_not_before_unix": None,
            "outcomes_after": 0,
            "outcomes_before": 0,
        }
        self.assertEqual(verify_event_interval(record), record["events"])
        with self.assertRaisesRegex(ValueError, "outside"):
            verify_event_interval(record | {
                "events": [{"at": "2026-09-12T00:00:03+00:00"}]
            })
        with self.assertRaisesRegex(ValueError, "outside"):
            verify_event_interval(record | {"events": list(reversed(record["events"]))})

    def test_batch_cooldown_requires_an_integer_outcome_count(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "batch-cooldown.json"
            for value in (24.0, True, -1):
                with self.subTest(value=value):
                    path.write_bytes(canonical_json({
                        "completed_outcomes": value,
                        "not_before_unix": 1000.0,
                    }) + b"\n")
                    with self.assertRaisesRegex(ValueError, "malformed"):
                        runner._read_batch_cooldown(path)

    def test_batch_pause_is_anchored_to_its_cooldown_file_timestamp(self) -> None:
        thread = "thread-1"
        recorded = 1789171260.0
        interval = {
            "admissions_after": 24,
            "admissions_before": 0,
            "batch_cooldown_mtime_ns": int(recorded * 1_000_000_000),
            "events": [
                event
                for _ in range(24)
                for event in (
                    {"at": "2026-09-12T00:00:00+00:00", "event": "resource_started", "resource": "llm", "thread": thread},
                    {"at": "2026-09-12T00:00:00+00:00", "event": "resource_finished", "exit_code": 0, "resource": "llm", "thread": thread},
                )
            ],
            "finished_at": "2026-09-12T00:01:00+00:00",
            "next_batch_not_before_unix": recorded + 900,
            "next_denial_not_before_unix": None,
            "outcomes_after": 24,
            "outcomes_before": 0,
            "started_at": "2026-09-12T00:00:00+00:00",
        }
        admissions = [{"admitted": True} for _ in range(24)]
        outcomes = [{"outcome": "pass"} for _ in range(24)]
        runner.verify_execution_intervals(
            [interval], admissions=admissions, outcomes=outcomes,
            thread_id=thread, schedule_size=72,
        )
        with self.assertRaisesRegex(ValueError, "registered 900 seconds"):
            runner.verify_execution_intervals(
                [interval | {"next_batch_not_before_unix": recorded + 890}],
                admissions=admissions,
                outcomes=outcomes,
                thread_id=thread,
                schedule_size=72,
            )

    def test_denial_retry_cadence_is_enforced_and_attested(self) -> None:
        admission = {"admitted": False, "trial_sha256": "trial-1"}
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            cooldown = {
                "admission_count": 1,
                "not_before_unix": 700.0,
                "trial_sha256": "trial-1",
            }
            (output / "denial-cooldown.json").write_bytes(canonical_json(cooldown) + b"\n")
            self.assertEqual(runner._denial_retry_not_before(output, [admission]), 700.0)
        thread = "thread-1"
        intervals = [
            {
                "admissions_after": 1,
                "admissions_before": 0,
                "batch_cooldown_mtime_ns": None,
                "events": [{
                    "at": "2026-09-12T00:00:00+00:00",
                    "event": "production_admission_denied",
                    "resource": "llm",
                    "thread": thread,
                }],
                "finished_at": "2026-09-12T00:00:00+00:00",
                "next_batch_not_before_unix": None,
                "next_denial_not_before_unix": 1789171800.0,
                "outcomes_after": 0,
                "outcomes_before": 0,
                "started_at": "2026-09-12T00:00:00+00:00",
            },
            {
                "admissions_after": 2,
                "admissions_before": 1,
                "batch_cooldown_mtime_ns": None,
                "events": [
                    {"at": "2026-09-12T00:10:00+00:00", "event": "resource_started", "resource": "llm", "thread": thread},
                    {"at": "2026-09-12T00:10:00+00:00", "event": "resource_finished", "exit_code": 0, "resource": "llm", "thread": thread},
                ],
                "finished_at": "2026-09-12T00:10:00+00:00",
                "next_batch_not_before_unix": None,
                "next_denial_not_before_unix": None,
                "outcomes_after": 1,
                "outcomes_before": 0,
                "started_at": "2026-09-12T00:10:00+00:00",
            },
        ]
        runner.verify_execution_intervals(
            intervals,
            admissions=[admission, {"admitted": True}],
            outcomes=[{"outcome": "pass"}],
            thread_id=thread,
            schedule_size=1,
        )
        intervals[1]["started_at"] = "2026-09-12T00:09:59+00:00"
        with self.assertRaisesRegex(ValueError, "cadence"):
            runner.verify_execution_intervals(
                intervals,
                admissions=[admission, {"admitted": True}],
                outcomes=[{"outcome": "pass"}],
                thread_id=thread,
                schedule_size=1,
            )

    def test_process_rate_uses_only_observed_secondary_measurements(self) -> None:
        manifest = runner._load_manifest(ROOT)
        bundle, _, _, metadata = analysis._verify_capsule(
            HISTORICAL, bundle_sha256=manifest["parent"]["bundle_sha256"]
        )
        changed = [dict(item) for item in metadata]
        cell_key = f'{changed[0]["trial"]["task"]}:{changed[0]["trial"]["condition"]}'
        was_loaded = changed[0]["skill_loaded_before_first_read"] is True
        changed[0]["skill_loaded_before_first_read"] = None
        changed[0]["outcome"] = "timeout"
        cell = analysis._cell_summary(bundle, changed)["cells"][cell_key]
        self.assertEqual(set(cell["reason_codes"]), analysis.OUTCOME_KINDS)
        self.assertEqual(sum(cell["reason_codes"].values()), 12)
        self.assertEqual(cell["request_fidelity_observed"], 11)
        self.assertEqual(cell["request_fidelity_unobserved"], 1)
        self.assertEqual(cell["skill_loaded_observed"], 11)
        self.assertEqual(cell["skill_loaded_missing"], 1)
        self.assertEqual(
            cell["skill_loaded_rate"],
            (cell["skill_loaded_before_first_read"] / 11),
        )
        self.assertEqual(
            cell["skill_loaded_before_first_read"],
            sum(
                item["skill_loaded_before_first_read"] is True
                for item in metadata
                if item["trial"]["task"] == changed[0]["trial"]["task"]
                and item["trial"]["condition"] == changed[0]["trial"]["condition"]
            ) - int(was_loaded),
        )

    def test_capsule_rejects_boolean_or_negative_token_counts(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            for value in (True, -1):
                with self.subTest(value=value):
                    capsule = Path(temporary) / str(value)
                    shutil.copytree(HISTORICAL, capsule)
                    metadata_path = capsule / "trial-metadata.json"
                    metadata = json.loads(metadata_path.read_text())
                    metadata[0]["first_prompt_tokens"] = value
                    metadata_path.write_bytes(canonical_json(metadata) + b"\n")
                    run_path = capsule / "run.json"
                    run = json.loads(run_path.read_text())
                    run.pop("record_sha256")
                    run["trial_metadata_sha256"] = runner._sha256(metadata_path)
                    run_path.write_bytes(
                        canonical_json(run | {"record_sha256": digest(run)}) + b"\n"
                    )
                    with self.assertRaisesRegex(ValueError, "token count"):
                        analysis._verify_capsule(
                            capsule,
                            bundle_sha256=manifest["parent"]["bundle_sha256"],
                        )

    def test_execution_exceptions_quarantine_before_resume(self) -> None:
        thread = runner.COORDINATION_THREAD_ID
        manifest = {
            "execution": {"coordination_thread_id": thread, "output_id": runner.STUDY},
            "parent": {"bundle_path": "bundle.json"},
            "runtime": {
                "expected_attestation": {
                    "distributions": {},
                    "environment": {},
                    "modules": {},
                    "production_threads_path_sha256": "0" * 64,
                    "python": {},
                }
            },
        }
        bundle = SimpleNamespace(schedule=(SimpleNamespace(sha256="trial-1"),))
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            workspace = parent / "workspace"
            runtime = workspace / runner.RUNTIME_RELATIVE
            events = workspace / ".coordination" / "events.jsonl"
            events.parent.mkdir(parents=True)
            events.write_bytes(b"")
            (runtime / "raw").mkdir(parents=True)
            output = runtime / "raw" / runner.STUDY
            attestations = runtime / "attestations"
            common = {
                "execution_root": runtime / "experiment",
                "assist_source": runtime / "assist",
                "assist_python": parent / "python",
                "workspace_root": workspace,
                "model_path": parent / "model",
                "server_pid": 1,
                "llama_source": parent / "llama",
                "events": events,
            }
            with patch.dict(
                os.environ, {"CODEX_THREAD_ID": thread}
            ), patch.object(
                runner, "_load_manifest", return_value=manifest
            ), patch.object(
                runner.StudyBundle, "read_verified", return_value=bundle
            ), patch.object(
                runner, "_canonical_workspace_root", return_value=workspace
            ), patch.object(
                runner, "_verify_local_registration", return_value=TEST_REGISTRATION
            ), patch.object(
                runner, "_production_threads_directory", return_value=workspace / "production"
            ), patch.object(
                runner, "_verify_worker_workspace", return_value=runtime / "worker-workspace"
            ), patch.object(
                runner,
                "_bound_invocation_paths",
                return_value=nullcontext({
                    "assist": runtime / "assist",
                    "execution": runtime / "experiment",
                    "python": parent / "python",
                    "worker": workspace,
                }),
            ), patch.object(
                runner,
                "_environment_identity",
                return_value={
                    "distributions": {}, "environment": {}, "modules": {}, "python": {}
                },
            ), patch.object(runner, "_verified_progress", return_value=([], [])):
                with self.subTest(stage="registered-input-drift"), patch.object(
                    runner, "_load_manifest", side_effect=ValueError("changed registration")
                ):
                    with self.assertRaisesRegex(ValueError, "registered reproduction inputs drifted"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                with self.subTest(stage="registration-drift"), patch.object(
                    runner, "_verify_local_registration", side_effect=ValueError("moved tag")
                ):
                    with self.assertRaisesRegex(ValueError, "registered reproduction inputs drifted"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                with self.subTest(stage="pre-attestation"), patch.object(
                    runner, "attest", side_effect=RuntimeError("attestation failed")
                ):
                    with self.assertRaisesRegex(ValueError, "pre-invocation"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                if attestations.exists():
                    shutil.rmtree(attestations)
                with self.subTest(stage="parent-launch"), patch.object(
                    runner, "attest", return_value=b'{}\n'
                ), patch.object(runner.subprocess, "Popen", side_effect=OSError("cannot exec")):
                    with self.assertRaisesRegex(ValueError, "could not be launched"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                shutil.rmtree(attestations)
                interrupted = Mock()
                interrupted.communicate.side_effect = [KeyboardInterrupt(), ("", "")]
                interrupted.returncode = -9
                with self.subTest(stage="parent-interrupt"), patch.object(
                    runner, "attest", return_value=b'{}\n'
                ), patch.object(
                    runner.subprocess, "Popen", return_value=interrupted
                ), patch.object(
                    runner, "_bind_scope", return_value=workspace / "scope"
                ), patch.object(runner, "_release_scope"), patch.object(runner, "_kill_scope"):
                    with self.assertRaises(KeyboardInterrupt):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                shutil.rmtree(attestations)
                with self.subTest(stage="malformed-progress"), patch.object(
                    runner, "_verified_progress", side_effect=AttributeError("not an object")
                ):
                    with self.assertRaisesRegex(ValueError, "persisted reproduction progress"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                if attestations.exists():
                    shutil.rmtree(attestations)
                with self.subTest(stage="post-attestation"), patch.object(
                    runner, "attest", side_effect=[b'{}\n', RuntimeError("changed")]
                ), patch.object(
                    runner, "_run_scoped",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ):
                    with self.assertRaisesRegex(RuntimeError, "changed"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                shutil.rmtree(attestations)
                def terminate_after_parent(*_args, **_kwargs):
                    os.kill(os.getpid(), signal.SIGTERM)
                    self.fail("SIGTERM did not interrupt the wrapper")

                attestations_after_parent = iter((b'{}\n', terminate_after_parent))

                def attest_after_parent(*args, **kwargs):
                    result = next(attestations_after_parent)
                    return result(*args, **kwargs) if callable(result) else result

                with self.subTest(stage="wrapper-interrupt"), patch.object(
                    runner, "attest", side_effect=attest_after_parent
                ), patch.object(
                    runner, "_run_scoped",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

    def test_request_fidelity_failure_is_never_a_scored_resume(self) -> None:
        self.assertTrue(runner._fidelity_error([
            {"outcome": "provider_error", "detail": "provider request differs from sealed request"}
        ]))
        self.assertFalse(runner._fidelity_error([
            {"outcome": "provider_error", "detail": "provider was temporarily unavailable"}
        ]))

    def test_archive_failures_and_interruptions_quarantine_the_raw_cohort(self) -> None:
        thread = runner.COORDINATION_THREAD_ID
        manifest = {
            "execution": {
                "analysis_file": "reproduction-analysis.json",
                "capsule_id": runner.STUDY,
                "coordination_thread_id": thread,
                "output_id": runner.STUDY,
            }
        }
        cases = (
            ("registered-input", ValueError("changed registration")),
            ("archive", ValueError("bad attestation")),
            ("archive", KeyboardInterrupt()),
        )
        for stage, error in cases:
            load_effect = (
                {"side_effect": error}
                if stage == "registered-input"
                else {"return_value": manifest}
            )
            archive_effect = {} if stage == "registered-input" else {"side_effect": error}
            with self.subTest(
                stage=stage, error=type(error).__name__
            ), TemporaryDirectory() as temporary:
                parent = Path(temporary)
                workspace = parent / "workspace"
                runtime = workspace / runner.RUNTIME_RELATIVE
                output = runtime / "raw" / runner.STUDY
                output.mkdir(mode=0o700, parents=True)
                capsule = runtime / "capsule" / runner.STUDY
                analysis_output = capsule / "reproduction-analysis.json"
                with patch.dict(
                    os.environ, {"CODEX_THREAD_ID": thread}
                ), patch.object(
                    runner,
                    "_load_manifest",
                    **load_effect,
                ), patch.object(
                    runner, "_canonical_workspace_root", return_value=workspace
                ), patch.object(
                    runner, "_verify_local_registration", return_value=TEST_REGISTRATION
                ), patch.object(
                    runner, "_termination_interrupts"
                ) as termination_guard, patch.object(
                    runner,
                    "_archive_and_analyze_locked",
                    **archive_effect,
                ):
                    def archive() -> None:
                        runner.archive_and_analyze(
                            ROOT,
                            output,
                            capsule,
                            analysis_output,
                            runtime / "attestations",
                            execution_root=runtime / "experiment",
                            assist_source=runtime / "assist",
                            assist_python=parent / "python",
                            workspace_root=workspace,
                        )

                    if isinstance(error, Exception):
                        with self.assertRaisesRegex(ValueError, "reproduction quarantined"):
                            archive()
                    else:
                        with self.assertRaises(KeyboardInterrupt):
                            archive()
                termination_guard.assert_called_once_with()
                self.assertTrue((output / runner.INVALID).exists())

    def test_archive_retry_accepts_an_existing_valid_seal(self) -> None:
        manifest = runner._load_manifest(ROOT)
        thread = manifest["execution"]["coordination_thread_id"]
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            workspace = parent / "workspace"
            runtime = workspace / runner.RUNTIME_RELATIVE
            output = runtime / "raw" / runner.STUDY
            output.parent.mkdir(parents=True)
            output.mkdir(mode=0o700)
            capsule = _reproduction_fixture(runtime / "capsule", manifest)
            analysis_output = capsule / "reproduction-analysis.json"
            analysis.analyze(
                manifest, capsule, HISTORICAL, analysis_output, TEST_REGISTRATION
            )
            _seal_capsule(capsule, manifest)
            with patch.dict(
                os.environ, {"CODEX_THREAD_ID": thread}
            ), patch.object(
                runner, "_load_manifest", return_value=manifest
            ), patch.object(
                runner, "_canonical_workspace_root", return_value=workspace
            ), patch.object(
                runner, "_verify_local_registration", return_value=TEST_REGISTRATION
            ), patch.object(runner, "_archive_and_analyze_locked") as archive:
                runner.archive_and_analyze(
                    ROOT,
                    output,
                    capsule,
                    analysis_output,
                    runtime / "attestations",
                    execution_root=runtime / "experiment",
                    assist_source=runtime / "assist",
                    assist_python=parent / "python",
                    workspace_root=workspace,
                )
            archive.assert_not_called()
            self.assertFalse((output / runner.INVALID).exists())

    def test_archive_retry_rejects_an_arbitrary_self_sealed_analysis(self) -> None:
        manifest = runner._load_manifest(ROOT)
        thread = manifest["execution"]["coordination_thread_id"]
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            workspace = parent / "workspace"
            runtime = workspace / runner.RUNTIME_RELATIVE
            output = runtime / "raw" / runner.STUDY
            output.mkdir(mode=0o700, parents=True)
            capsule = runtime / "capsule" / runner.STUDY
            capsule.mkdir(parents=True)
            analysis_output = capsule / "reproduction-analysis.json"
            analysis_output.write_text("{}\n")
            _seal_capsule(capsule, manifest)
            with patch.dict(
                os.environ, {"CODEX_THREAD_ID": thread}
            ), patch.object(
                runner, "_load_manifest", return_value=manifest
            ), patch.object(
                runner, "_canonical_workspace_root", return_value=workspace
            ), patch.object(
                runner, "_verify_local_registration", return_value=TEST_REGISTRATION
            ):
                with self.assertRaisesRegex(ValueError, "reproduction quarantined"):
                    runner.archive_and_analyze(
                        ROOT,
                        output,
                        capsule,
                        analysis_output,
                        runtime / "attestations",
                        execution_root=runtime / "experiment",
                        assist_source=runtime / "assist",
                        assist_python=parent / "python",
                        workspace_root=workspace,
                    )
            self.assertTrue((output / runner.INVALID).exists())

    def test_final_reproduction_seal_rejects_changed_evidence(self) -> None:
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary)
            evidence = capsule / "evidence.json"
            evidence.write_text("{}\n")
            (capsule / "learning.md").write_text("interpretation is intentionally outside the data seal\n")
            manifest = {"study_id": runner.STUDY}
            seal = {
                "schema": "reach-v8-exact-reproduction-seal-v1",
                "manifest_sha256": digest(manifest),
                "sealed_files": {"evidence.json": runner._sha256(evidence)},
            }
            (capsule / "reproduction-seal.json").write_bytes(
                canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n"
            )
            runner.verify_reproduction_seal(capsule, manifest)
            evidence.write_text("{\"changed\":true}\n")
            with self.assertRaisesRegex(ValueError, "sealed files differ"):
                runner.verify_reproduction_seal(capsule, manifest)


if __name__ == "__main__":
    unittest.main()
