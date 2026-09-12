"""No-model integrity contracts for the exact V8-r3 reproduction."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harness.bundle import StudyBundle, canonical_json, digest
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v8 import runner as parent_runner
from studies.reach_for_instructions_confirmation_v8_reproduction import analysis, runner


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "results" / "reach-for-instructions-confirmation-v8-qwen38-current-r3"


def _reproduction_fixture(parent: Path, manifest: dict[str, object]) -> Path:
    execution = manifest["execution"]
    assert isinstance(execution, dict)
    capsule = parent / str(execution["capsule_id"])
    shutil.copytree(HISTORICAL, capsule)
    attestations = capsule / "runtime-attestations"
    attestations.mkdir()
    identity = b'{"identity":"test"}\n'
    (attestations / "000-identity-before.json").write_bytes(identity)
    (attestations / "000-identity-after.json").write_bytes(identity)
    interval = {
        "events": [],
        "finished_at": "2026-09-12T00:00:00+00:00",
        "started_at": "2026-09-12T00:00:00+00:00",
    }
    (attestations / "000-events.json").write_bytes(canonical_json(interval) + b"\n")
    provenance = {
        "attestation_files": {
            path.name: runner._sha256(path) for path in sorted(attestations.iterdir())
        },
        "capsule_run_sha256": runner._sha256(capsule / "run.json"),
        "coordination_thread_id": execution["coordination_thread_id"],
        "manifest_sha256": digest(manifest),
        "schema": "reach-v8-exact-reproduction-provenance-v1",
    }
    (capsule / "reproduction-provenance.json").write_bytes(
        canonical_json(provenance | {"record_sha256": digest(provenance)}) + b"\n"
    )
    return capsule


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
            analysis.analyze(manifest, reproduction, HISTORICAL, output)
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
                    manifest, HISTORICAL, HISTORICAL, Path(temporary) / "analysis.json"
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
                analysis.analyze(manifest, reproduction, capsule, Path(temporary) / "analysis.json")

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
                    analysis.analyze(manifest, reproduction, capsule, Path(temporary) / "analysis.json")

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
                analysis.analyze(manifest, reproduction, capsule, Path(temporary) / "analysis.json")

    def test_progress_guard_rejects_an_omitted_scheduled_outcome(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            shutil.copy2(HISTORICAL / "admissions.jsonl", output / "admissions.jsonl")
            records = (HISTORICAL / "outcomes.jsonl").read_text().splitlines()
            (output / "outcomes.jsonl").write_text("\n".join(records[:-1]) + "\n")
            with self.assertRaisesRegex(ValueError, "progress differs"):
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
        self.assertTrue(runner._events_match_admissions(
            new_admissions=admitted, new_outcomes=[{"outcome": "pass"}, {"outcome": "provider_error"}],
            new_events=events, thread_id=thread
        ))
        self.assertFalse(runner._events_match_admissions(
            new_admissions=admitted, new_outcomes=[{"outcome": "pass"}, {"outcome": "provider_error"}],
            new_events=events[:-1], thread_id=thread
        ))
        self.assertTrue(runner._events_match_admissions(
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
        self.assertTrue(runner._events_match_admissions(
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
        self.assertTrue(runner._events_match_admissions(
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
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = b'{"identity":1}\n'
            interval = canonical_json({
                "events": [],
                "finished_at": "2026-09-12T00:00:00+00:00",
                "started_at": "2026-09-12T00:00:00+00:00",
            }) + b"\n"
            for index in range(2):
                (root / f"{index:03d}-identity-before.json").write_bytes(identity)
                (root / f"{index:03d}-identity-after.json").write_bytes(identity)
                (root / f"{index:03d}-events.json").write_bytes(interval)
            self.assertEqual(len(runner._verified_attestation_files(root)), 6)
            (root / "001-identity-after.json").write_bytes(b'{"identity":2}\n')
            with self.assertRaisesRegex(ValueError, "identity differs"):
                runner._verified_attestation_files(root)

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

    def test_event_slice_rejects_a_rewritten_prefix(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            appended = b'{"event":"new"}\n'
            events.write_bytes(prefix + appended)
            self.assertEqual(runner._read_appended_events(events, prefix), [{"event": "new"}])
            events.write_bytes(b'{"event":"bad"}\n' + appended)
            with self.assertRaisesRegex(ValueError, "non-append-only"):
                runner._read_appended_events(events, prefix)

    def test_event_interval_requires_ordered_events_within_parent_run(self) -> None:
        record = {
            "started_at": "2026-09-12T00:00:00+00:00",
            "finished_at": "2026-09-12T00:00:02+00:00",
            "events": [
                {"at": "2026-09-12T00:00:00+00:00"},
                {"at": "2026-09-12T00:00:02+00:00"},
            ],
        }
        self.assertEqual(runner._verify_event_interval(record), record["events"])
        with self.assertRaisesRegex(ValueError, "outside"):
            runner._verify_event_interval(record | {
                "events": [{"at": "2026-09-12T00:00:03+00:00"}]
            })
        with self.assertRaisesRegex(ValueError, "outside"):
            runner._verify_event_interval(record | {"events": list(reversed(record["events"]))})

    def test_execution_exceptions_quarantine_before_resume(self) -> None:
        thread = "thread-1"
        manifest = {
            "execution": {"coordination_thread_id": thread, "output_id": runner.STUDY},
            "parent": {"bundle_path": "bundle.json"},
        }
        bundle = SimpleNamespace(schedule=(SimpleNamespace(sha256="trial-1"),))
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            workspace = parent / "workspace"
            events = workspace / ".coordination" / "events.jsonl"
            events.parent.mkdir(parents=True)
            events.write_bytes(b"")
            output = parent / runner.STUDY
            attestations = parent / "attestations"
            common = {
                "execution_root": parent / "execution",
                "assist_source": parent / "assist",
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
            ), patch.object(runner, "_verified_progress", return_value=([], [])):
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
                ), patch.object(runner.subprocess, "run", side_effect=OSError("cannot exec")):
                    with self.assertRaisesRegex(ValueError, "could not be launched"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

                shutil.rmtree(output)
                shutil.rmtree(attestations)
                with self.subTest(stage="post-attestation"), patch.object(
                    runner, "attest", side_effect=[b'{}\n', RuntimeError("changed")]
                ), patch.object(
                    runner.subprocess, "run", return_value=SimpleNamespace(returncode=0)
                ):
                    with self.assertRaisesRegex(RuntimeError, "changed"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())

    def test_request_fidelity_failure_is_never_a_scored_resume(self) -> None:
        self.assertTrue(runner._fidelity_error([
            {"outcome": "provider_error", "detail": "provider request differs from sealed request"}
        ]))
        self.assertFalse(runner._fidelity_error([
            {"outcome": "provider_error", "detail": "provider was temporarily unavailable"}
        ]))

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
