"""No-model integrity contracts for the exact V8-r3 reproduction."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from harness.bundle import StudyBundle, canonical_json, digest
from studies.reach_for_instructions_confirmation_v2 import runner as core
from studies.reach_for_instructions_confirmation_v8 import runner as parent_runner
from studies.reach_for_instructions_confirmation_v8_reproduction import analysis, runner


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "results" / "reach-for-instructions-confirmation-v8-qwen38-current-r3"


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
            output = Path(temporary) / "analysis.json"
            analysis.analyze(manifest, HISTORICAL, HISTORICAL, output)
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

    def test_locked_analysis_rejects_changed_historical_metadata(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            metadata = capsule / "trial-metadata.json"
            metadata.write_bytes(metadata.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "trial metadata"):
                analysis.analyze(manifest, HISTORICAL, capsule, Path(temporary) / "analysis.json")

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
                capsule = Path(temporary) / "capsule"
                shutil.copytree(HISTORICAL, capsule)
                bundle_path = capsule / "bundle.json"
                stored = json.loads(bundle_path.read_text())
                mutate(stored["bundle"])
                stored["sha256"] = digest(stored["bundle"])
                bundle_path.write_bytes(canonical_json(stored) + b"\n")
                with self.assertRaises(ValueError):
                    analysis.analyze(manifest, HISTORICAL, capsule, Path(temporary) / "analysis.json")

    def test_locked_analysis_rejects_an_altered_result_record(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            outcomes = capsule / "outcomes.jsonl"
            records = outcomes.read_text().splitlines()
            first = json.loads(records[0])
            first["outcome"] = "pass" if first["outcome"] != "pass" else "artifact_failure"
            records[0] = canonical_json(first).decode()
            outcomes.write_text("\n".join(records) + "\n")
            with self.assertRaises(ValueError):
                analysis.analyze(manifest, HISTORICAL, capsule, Path(temporary) / "analysis.json")

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
            for index in range(2):
                (root / f"{index:03d}-identity-before.json").write_bytes(identity)
                (root / f"{index:03d}-identity-after.json").write_bytes(identity)
                (root / f"{index:03d}-events.json").write_text("[]\n")
            self.assertEqual(len(runner._verified_attestation_files(root)), 6)
            (root / "001-identity-after.json").write_bytes(b'{"identity":2}\n')
            with self.assertRaisesRegex(ValueError, "identity differs"):
                runner._verified_attestation_files(root)

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
