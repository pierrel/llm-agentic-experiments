"""No-model integrity contracts for the exact V8-r3 reproduction."""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

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
        "python_environment": expected["python_environment"],
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
    seal = {
        "schema": "reach-v8-exact-reproduction-seal-v1",
        "manifest_sha256": digest(manifest),
        "sealed_files": runner._sealed_file_inventory(capsule),
    }
    (capsule / "reproduction-seal.json").write_bytes(
        canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n"
    )


class ReachForInstructionsConfirmationV8ReproductionTest(unittest.TestCase):
    def test_sha256_streams_files_in_bounded_chunks(self) -> None:
        payload = b"streamed model bytes"

        class Source:
            def __init__(self) -> None:
                self.offset = 0
                self.read_sizes: list[int] = []

            def __enter__(self) -> Source:
                return self

            def __exit__(self, *_: object) -> None:
                return None

            def read(self, size: int) -> bytes:
                self.read_sizes.append(size)
                chunk = payload[self.offset:self.offset + 5]
                self.offset += len(chunk)
                return chunk

        source = Source()

        class File:
            def open(self, mode: str) -> Source:
                self.mode = mode
                return source

        path = File()
        self.assertEqual(runner._sha256(path), hashlib.sha256(payload).hexdigest())
        self.assertEqual(path.mode, "rb")
        self.assertEqual(set(source.read_sizes), {runner.HASH_CHUNK_BYTES})

        analysis_source = Source()
        analysis_path = File()
        analysis_path.open = lambda mode: analysis_source
        self.assertEqual(
            analysis._sha256(analysis_path), hashlib.sha256(payload).hexdigest()
        )
        self.assertEqual(set(analysis_source.read_sizes), {analysis.HASH_CHUNK_BYTES})

    def test_environment_attestation_script_streams_every_file_hash(self) -> None:
        self.assertNotIn("read_bytes()", runner._ENVIRONMENT_SCRIPT)
        self.assertIn('source.read(1024 * 1024)', runner._ENVIRONMENT_SCRIPT)
        for key, value in runner.SAFE_GIT_ENVIRONMENT.items():
            self.assertIn(f'${{{key}-}}', runner._ENVIRONMENT_SHELL)
            self.assertIn(f"{key}={value}", runner._ENVIRONMENT_SHELL)

    def test_server_listener_must_belong_to_the_attested_process(self) -> None:
        with TemporaryDirectory() as temporary:
            proc = Path(temporary) / "proc"
            (proc / "net").mkdir(parents=True)
            (proc / "fd").mkdir()
            (proc / "ns").mkdir()
            (proc / "ns" / "net").symlink_to("/proc/self/ns/net")
            (proc / "net" / "tcp").write_text(
                "sl local_address rem_address st tx_queue tr retrnsmt uid timeout inode\n"
                "0: 0100007F:1F40 00000000:0000 0A 0 0 0 1000 0 12345\n"
            )
            descriptor = proc / "fd" / "3"
            descriptor.symlink_to("socket:[12345]")
            runner._verify_server_listener(proc)
            descriptor.unlink()
            descriptor.symlink_to("socket:[99999]")
            with self.assertRaisesRegex(ValueError, "does not own"):
                runner._verify_server_listener(proc)
            descriptor.unlink()
            descriptor.symlink_to("socket:[12345]")
            (proc / "ns" / "net").unlink()
            (proc / "ns" / "net").touch()
            with self.assertRaisesRegex(ValueError, "network namespace differs"):
                runner._verify_server_listener(proc)

    def test_server_identity_normalizes_the_model_argument_once(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "model.gguf"
            model.write_bytes(b"weights")
            executable = Path("/proc/self/exe").resolve()
            code = "import time; time.sleep(30)"
            process = subprocess.Popen([
                str(executable), "-c", code, "--model", str(model),
                "--host", "127.0.0.1",
            ])
            try:
                with patch.object(
                    runner, "_verify_server_listener"
                ), patch.object(
                    runner, "_git_identity", return_value={"commit": "1" * 40}
                ), patch.object(
                    runner, "_sha256", return_value="2" * 64
                ):
                    identity = runner._server_identity(process.pid, model, root)
            finally:
                process.terminate()
                process.wait(timeout=10)
        self.assertEqual(identity["argv"], [
            executable.name, "-c", code, "--model", model.name,
            "--host", "127.0.0.1",
        ])

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

    def test_manifest_pins_fresh_r3_administrative_identity(self) -> None:
        manifest = runner._load_manifest(ROOT)
        execution = manifest["execution"]
        publication = manifest["registration"]
        expected = manifest["runtime"]["expected_attestation"]

        self.assertEqual(
            manifest["study_id"],
            "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r3",
        )
        self.assertEqual(
            execution["coordination_thread_id"],
            "01a04877-df08-7401-aeb5-91fdee52c9b0",
        )
        self.assertEqual(
            publication,
            {
                "publication_branch": "reach-experiment-reproduction-v3",
                "publication_remote": "https://github.com/pierrel/llm-agentic-experiments.git",
                "tag": "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r3",
            },
        )
        self.assertTrue(str(execution["runtime_relative"]).endswith("reproduction-r3"))
        self.assertTrue(str(execution["output_relative"]).endswith("reproduction-r3"))
        self.assertTrue(str(execution["capsule_relative"]).endswith("reproduction-r3"))
        self.assertEqual(
            expected["shared_gate"]["sha256"],
            "64d4981b432300fa7f6d1089d72e40059aa68819bf1952f2169ab114a954b0d2",
        )
        self.assertEqual(
            expected["server"]["argv"][-5:],
            ["--reasoning", "on", "--no-reasoning-preserve", "--reasoning-effort", "low"],
        )

    def test_r3_changes_no_scientific_manifest_value_from_r2(self) -> None:
        current = runner._load_manifest(ROOT)
        predecessor_path = ROOT / (
            "experiments/"
            "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r2/"
            "manifest.json"
        )
        self.assertEqual(
            hashlib.sha256(predecessor_path.read_bytes()).hexdigest(),
            "149f639a8e20fbd6b492af8e21e8fdb496d7ff6c8d9c6b3b393f12eb8065551d",
        )
        predecessor = json.loads(predecessor_path.read_text())["manifest"]

        normalized = []
        for value in (predecessor, current):
            copy = json.loads(json.dumps(value))
            for key in ("execution", "files", "registration", "study_id"):
                copy.pop(key)
            copy["runtime"]["expected_attestation"].pop("shared_gate")
            normalized.append(copy)
        self.assertEqual(*normalized)

        source = Path(runner.__file__).read_text()
        replacements = {
            "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r3":
                "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r2",
            'PUBLICATION_BRANCH = "reach-experiment-reproduction-v3"':
                'PUBLICATION_BRANCH = "reach-experiment-reproduction-v2"',
            "01a04877-df08-7401-aeb5-91fdee52c9b0":
                "01a09689-f137-7cf1-a5c0-f32e7537fefa",
            'unit = f"reach-v8-r3-': 'unit = f"reach-v8-r2-',
            "from harness.runner import _artifact_digests\n": "",
            '        if remaining == 0:\n'
            '            _verify_completed_artifacts(output, bundle)\n'
            '            return "complete"\n': "",
            '    if len(outcomes) == len(bundle.schedule):\n'
            '        try:\n'
            '            _verify_completed_artifacts(output, bundle)\n'
            '        except Exception as error:\n'
            '            _quarantine(output, "completed reproduction artifacts are invalid")\n'
            '            raise ValueError("completed reproduction artifacts are invalid") from error\n'
            '        return "complete"\n'
            '    return "batch-complete"\n':
                '    return "complete" if len(outcomes) == len(bundle.schedule) else "batch-complete"\n',
            '\n\ndef _verify_completed_artifacts(output: Path, bundle: StudyBundle) -> None:\n'
            '    """Require the parent\'s final seals and exact artifacts for a complete cohort."""\n'
            '    admissions = AdmissionLog(output / "admissions.jsonl", bundle.sha256)\n'
            '    outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256)\n'
            '    artifacts = _artifact_digests(bundle, output / "traces", output / "report.json")\n'
            '    outcomes.verify_finalized(bundle.schedule, admissions, artifacts)\n': "",
            '    """Return complete for a verified cohort or run one inherited bounded invocation."""\n':
                '    """Run one inherited bounded invocation or fail closed without reinterpretation."""\n',
            '    """Serialize a completed-cohort check or one inherited bounded invocation."""\n':
                '    """Serialize and run one inherited bounded invocation."""\n',
            '    """Check completion or run one batch with termination handling already active."""\n':
                '    """Run one batch with termination handling active before path or Git checks."""\n',
            '                record.get("thread") == thread_id\n'
            '                and record.get("resource") == "llm"\n'
            '            ):\n':
                '                record.get("thread") == thread_id\n'
                '                and record.get("resource") == "llm"\n'
                '                and record.get("event") in {\n'
                '                    "production_admission_denied", "resource_started", "resource_finished"\n'
                '                }\n'
                '            ):\n',
            '    attested_events = new_events\n':
                '    attested_events = [\n'
                '        event for event in new_events\n'
                '        if event.get("thread") == thread_id and event.get("resource") == "llm"\n'
                '        and event.get("event") in {"production_admission_denied", "resource_started", "resource_finished"}\n'
                '    ]\n',
        }
        for new, old in replacements.items():
            self.assertEqual(source.count(new), 1)
            source = source.replace(new, old)
        self.assertEqual(
            hashlib.sha256(source.encode()).hexdigest(),
            "61fa4457d172967b22f916e1c7647470a58a811486f3357eda5b429cdaaa877f",
        )

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

    def test_capsule_requires_one_raw_trace_hash_per_scheduled_trial(self) -> None:
        manifest = runner._load_manifest(ROOT)
        for case in ("missing", "malformed", "foreign-name"):
            with self.subTest(case=case), TemporaryDirectory() as temporary:
                capsule = Path(temporary) / "capsule"
                shutil.copytree(HISTORICAL, capsule)
                run_path = capsule / "run.json"
                run = json.loads(run_path.read_text())
                run.pop("record_sha256")
                raw_hashes = run["raw_trace_sha256"]
                assert isinstance(raw_hashes, dict)
                name = next(iter(raw_hashes))
                seal_path = capsule / "outcomes.jsonl.seal"
                seal = json.loads(seal_path.read_text())
                seal.pop("seal_sha256")
                if case == "missing":
                    raw_hashes.pop(name)
                    seal["artifacts"].pop(f"traces/{name}")
                elif case == "malformed":
                    raw_hashes[name] = "g" * 64
                    seal["artifacts"][f"traces/{name}"] = "g" * 64
                else:
                    foreign = f"{'f' * 64}.json"
                    self.assertNotIn(foreign, raw_hashes)
                    raw_hashes[foreign] = raw_hashes.pop(name)
                    seal["artifacts"][f"traces/{foreign}"] = seal[
                        "artifacts"
                    ].pop(f"traces/{name}")
                seal_path.write_bytes(
                    canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n"
                )
                run["tracked_files"]["outcomes.jsonl.seal"] = runner._sha256(
                    seal_path
                )
                run_path.write_bytes(
                    canonical_json(run | {"record_sha256": digest(run)}) + b"\n"
                )
                with self.assertRaisesRegex(ValueError, "raw-trace inventory"):
                    analysis._verify_capsule(
                        capsule,
                        bundle_sha256=manifest["parent"]["bundle_sha256"],
                    )

    def test_capsule_rejects_duplicate_raw_trace_json_members(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            run_path = capsule / "run.json"
            run = json.loads(run_path.read_text())
            name, value = next(iter(run["raw_trace_sha256"].items()))
            member = canonical_json({name: value}).decode()[1:-1]
            encoded = canonical_json(run).decode()
            self.assertEqual(encoded.count(member), 1)
            run_path.write_text(encoded.replace(member, f"{member},{member}") + "\n")
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                analysis._verify_capsule(
                    capsule,
                    bundle_sha256=manifest["parent"]["bundle_sha256"],
                )

    def test_capsule_rejects_symlinked_evidence_before_reading_it(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            run_path = capsule / "run.json"
            external = Path(temporary) / "external-run.json"
            run_path.replace(external)
            run_path.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symlinked evidence"):
                analysis._verify_capsule(
                    capsule,
                    bundle_sha256=manifest["parent"]["bundle_sha256"],
                )

    def test_capsule_rejects_special_evidence_before_reading_it(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            run_path = capsule / "run.json"
            run_path.unlink()
            os.mkfifo(run_path)
            with self.assertRaisesRegex(ValueError, "only regular evidence"):
                analysis._verify_capsule(
                    capsule,
                    bundle_sha256=manifest["parent"]["bundle_sha256"],
                )

    def test_capsule_rejects_an_unreadable_descendant_tree(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            hidden = capsule / "hidden"
            hidden.mkdir()
            (hidden / "external").symlink_to(Path(temporary) / "outside")
            hidden.chmod(0)
            try:
                with self.assertRaisesRegex(ValueError, "cannot be traversed"):
                    analysis._verify_capsule(
                        capsule,
                        bundle_sha256=manifest["parent"]["bundle_sha256"],
                    )
            finally:
                hidden.chmod(0o700)

    def test_capsule_rejects_duplicate_jsonl_seal_members(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule"
            shutil.copytree(HISTORICAL, capsule)
            seal_path = capsule / "admissions.jsonl.seal"
            seal = json.loads(seal_path.read_text())
            name = "record_tip_sha256"
            member = canonical_json({name: seal[name]}).decode()[1:-1]
            encoded = canonical_json(seal).decode()
            self.assertEqual(encoded.count(member), 1)
            seal_path.write_text(encoded.replace(member, f"{member},{member}") + "\n")
            run_path = capsule / "run.json"
            run = json.loads(run_path.read_text())
            run.pop("record_sha256")
            run["tracked_files"]["admissions.jsonl.seal"] = runner._sha256(
                seal_path
            )
            run_path.write_bytes(
                canonical_json(run | {"record_sha256": digest(run)}) + b"\n"
            )
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                analysis._verify_capsule(
                    capsule,
                    bundle_sha256=manifest["parent"]["bundle_sha256"],
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

    def test_progress_guard_rejects_malformed_active_evidence_before_launch(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        for case in ("duplicate-admission", "dangling-admission", "dangling-trace"):
            with self.subTest(case=case), TemporaryDirectory() as temporary:
                output = Path(temporary)
                if case == "duplicate-admission":
                    shutil.copy2(HISTORICAL / "admissions.jsonl", output / "admissions.jsonl")
                    shutil.copy2(HISTORICAL / "outcomes.jsonl", output / "outcomes.jsonl")
                    lines = (output / "admissions.jsonl").read_text().splitlines()
                    record = json.loads(lines[0])
                    member = canonical_json({"trial_id": record["trial_id"]}).decode()[1:-1]
                    self.assertEqual(lines[0].count(member), 1)
                    lines[0] = lines[0].replace(member, f"{member},{member}")
                    (output / "admissions.jsonl").write_text("\n".join(lines) + "\n")
                elif case == "dangling-admission":
                    (output / "admissions.jsonl").symlink_to(output / "missing.jsonl")
                else:
                    traces = output / "traces"
                    traces.mkdir()
                    (traces / f"{bundle.schedule[0].sha256}.json").symlink_to(
                        output / "missing-trace.json"
                    )
                parent = Mock()
                with patch.object(
                    runner.StudyBundle, "read_verified", return_value=bundle
                ), patch.object(runner, "_run_scoped", parent):
                    with self.assertRaisesRegex(ValueError, "persisted reproduction progress"):
                        runner._run_batch_locked(
                            ROOT,
                            output,
                            output / "attestations",
                            manifest={
                                "execution": {"coordination_thread_id": "thread"},
                                "parent": {"bundle_path": "bundle.json"},
                            },
                            registration=TEST_REGISTRATION,
                            execution_root=output / "execution",
                            assist_source=output / "assist",
                            assist_python=output / "python",
                            workspace_root=output / "workspace",
                            model_path=output / "model",
                            server_pid=1,
                            llama_source=output / "llama",
                            events=output / "events.jsonl",
                        )
                parent.assert_not_called()
                self.assertTrue((output / runner.INVALID).exists())

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

    def test_complete_batch_returns_without_new_runtime_evidence(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        completed = [{} for _ in bundle.schedule]
        attest = Mock()
        parent = Mock()
        completed_artifacts = Mock()
        with TemporaryDirectory() as temporary, patch.object(
            runner.StudyBundle, "read_verified", return_value=bundle
        ), patch.object(
            runner, "_verified_progress", return_value=(completed, completed)
        ), patch.object(
            runner, "_verify_completed_artifacts", completed_artifacts
        ), patch.object(
            runner,
            "_prepare_attestation_directory",
            return_value=[{"next_denial_not_before_unix": None}],
        ), patch.object(
            runner, "verify_execution_intervals"
        ), patch.object(
            runner, "_verify_live_cooldowns", return_value=([], None)
        ), patch.object(
            runner, "attest", attest
        ), patch.object(
            runner, "_run_scoped", parent
        ):
            output = Path(temporary)
            result = runner._run_batch_locked(
                ROOT,
                output,
                output / "attestations",
                manifest={
                    "execution": {"coordination_thread_id": "thread"},
                    "parent": {"bundle_path": "bundle.json"},
                },
                registration=TEST_REGISTRATION,
                execution_root=output / "execution",
                assist_source=output / "assist",
                assist_python=output / "python",
                workspace_root=output / "workspace",
                model_path=output / "model",
                server_pid=1,
                llama_source=output / "llama",
                events=output / "events.jsonl",
            )
        self.assertEqual(result, "complete")
        completed_artifacts.assert_called_once_with(output, bundle)
        attest.assert_not_called()
        parent.assert_not_called()

    def test_complete_batch_requires_parent_final_seals_and_artifacts(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        seal = json.loads((HISTORICAL / "outcomes.jsonl.seal").read_text())
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            shutil.copytree(HISTORICAL, output)
            (output / "outcomes.jsonl.seal").unlink()
            with patch.object(
                runner, "_artifact_digests", return_value=seal["artifacts"]
            ), self.assertRaises(FileNotFoundError):
                runner._verify_completed_artifacts(output, bundle)

    def test_newly_completed_batch_requires_parent_final_seals_and_artifacts(self) -> None:
        trial = SimpleNamespace(sha256="trial-1")
        bundle = SimpleNamespace(schedule=(trial,), sha256="bundle")
        admission = {"admitted": True, "trial_sha256": trial.sha256}
        outcome = {"outcome": "pass", "trial_sha256": trial.sha256}
        events = [
            {"event": "resource_started", "resource": "llm", "thread": "thread"},
            {
                "event": "resource_finished",
                "exit_code": 0,
                "resource": "llm",
                "thread": "thread",
            },
        ]
        completed_artifacts = Mock(side_effect=FileNotFoundError("missing seal"))
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir(mode=0o700)
            attestations = root / "attestations"
            attestations.mkdir()
            event_log = root / "events.jsonl"
            event_log.write_text("\n")
            bound = {
                "assist": root / "assist",
                "execution": root / "execution",
                "python": root / "python",
                "worker": root / "worker",
            }
            with patch.object(
                runner.StudyBundle, "read_verified", return_value=bundle
            ), patch.object(
                runner, "_verified_progress",
                side_effect=[([], []), ([admission], [outcome])],
            ), patch.object(
                runner, "_prepare_attestation_directory", return_value=[]
            ), patch.object(
                runner, "_verify_live_cooldowns", return_value=([], None)
            ), patch.object(
                runner, "attest", return_value=b"{}\n"
            ), patch.object(
                runner, "_bound_invocation_paths", return_value=nullcontext(bound)
            ), patch.object(
                runner, "_bound_execution_environment", return_value={}
            ), patch.object(
                runner, "_run_scoped",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ), patch.object(
                runner, "_read_appended_events", return_value=events
            ), patch.object(
                runner, "verify_attestation_inventory", return_value=([], [{}])
            ), patch.object(
                runner, "verify_execution_intervals"
            ), patch.object(
                runner, "_verify_completed_artifacts", completed_artifacts
            ), self.assertRaisesRegex(ValueError, "completed reproduction artifacts"):
                runner._run_batch_locked(
                    ROOT,
                    output,
                    attestations,
                    manifest={
                        "execution": {"coordination_thread_id": "thread"},
                        "parent": {"bundle_path": "bundle.json"},
                    },
                    registration=TEST_REGISTRATION,
                    execution_root=root / "execution",
                    assist_source=root / "assist",
                    assist_python=root / "python",
                    workspace_root=root,
                    model_path=root / "model",
                    server_pid=1,
                    llama_source=root / "llama",
                    events=event_log,
                )
            self.assertTrue((output / runner.INVALID).exists())
        completed_artifacts.assert_called_once_with(output, bundle)

    def test_progress_guard_requires_a_request_for_every_non_infrastructure_outcome(self) -> None:
        bundle = StudyBundle.read_verified(HISTORICAL / "bundle.json")
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            shutil.copy2(HISTORICAL / "admissions.jsonl", output / "admissions.jsonl")
            records = [
                json.loads(line)
                for line in (HISTORICAL / "outcomes.jsonl").read_text().splitlines()
            ]
            changed = next(
                index for index, record in enumerate(records)
                if record["outcome"] != "infrastructure_invalid"
            )
            records[changed]["model_request_made"] = False
            previous = bundle.sha256
            encoded = []
            for record in records:
                record.pop("record_sha256")
                record["previous_sha256"] = previous
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
        self.assertFalse(events_match_admissions(
            new_admissions=[], new_outcomes=[], new_events=[], thread_id=thread
        ))

    def test_strict_json_rejects_non_finite_numeric_values(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
            with self.assertRaisesRegex(ValueError, "malformed or ambiguous"):
                runner.strict_json_loads(f'{{"value": {constant}}}')

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

    def test_attestation_inventory_rejects_duplicate_json_members(self) -> None:
        manifest = runner._load_manifest(ROOT)
        with TemporaryDirectory() as temporary:
            capsule = _reproduction_fixture(Path(temporary), manifest)
            root = capsule / "runtime-attestations"
            identity_paths = sorted(root.glob("*-identity-*.json"))
            identity = json.loads(identity_paths[0].read_text())
            name = "registered_model"
            member = canonical_json({name: identity[name]}).decode()[1:-1]
            encoded = canonical_json(identity).decode()
            self.assertEqual(encoded.count(member), 1)
            duplicated = encoded.replace(member, f"{member},{member}") + "\n"
            for path in identity_paths:
                path.write_text(duplicated)
            with self.assertRaisesRegex(ValueError, "attestation is malformed"):
                runner.verify_attestation_inventory(
                    root, manifest=manifest, registration=TEST_REGISTRATION
                )

    def test_wrong_coordinator_identity_rejects_before_any_subprocess(self) -> None:
        output = Path("/tmp") / runner.STUDY
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "wrong-thread"}), patch(
            "studies.reach_for_instructions_confirmation_v8_reproduction.runner.subprocess.Popen"
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
            with patch.dict(
                os.environ, {"CODEX_THREAD_ID": runner.COORDINATION_THREAD_ID}
            ), patch.object(
                runner, "_canonical_workspace_root", return_value=workspace
            ), patch.object(runner, "_load_manifest", return_value=manifest), patch.object(
                runner, "_verify_publication", return_value={}
            ), patch.object(
                runner, "_run_integrity_command", side_effect=OSError("clone failed")
            ):
                with self.assertRaisesRegex(OSError, "clone failed"):
                    runner.prepare_runtime(ROOT, Path("/unused-assist"), runtime)
            self.assertFalse(runtime.exists())
            self.assertEqual(
                list(runtime.parent.glob(f".{runner.STUDY}.preparing-*")), []
            )

    def test_integrity_command_deadline_kills_group_and_reaps_launcher(self) -> None:
        process = Mock()
        process.pid = 123
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(["git"], runner.INTEGRITY_COMMAND_TIMEOUT_SECONDS),
            (b"", b""),
        ]
        with patch.object(
            runner.subprocess, "Popen", return_value=process
        ) as launch, patch.object(runner.os, "killpg") as kill_group:
            with self.assertRaisesRegex(ValueError, "fixed deadline"):
                runner._run_integrity_command(["git"], check=True)
        self.assertTrue(launch.call_args.kwargs["start_new_session"])
        kill_group.assert_called_once_with(123, signal.SIGKILL)
        self.assertEqual(
            process.communicate.call_args_list,
            [
                call(timeout=runner.INTEGRITY_COMMAND_TIMEOUT_SECONDS),
                call(timeout=runner.COMMAND_REAP_TIMEOUT_SECONDS),
            ],
        )

    def test_scoped_child_interruption_kills_the_complete_systemd_scope(self) -> None:
        process = Mock()

        def interrupt_child(*_args, **_kwargs):
            os.kill(os.getpid(), signal.SIGTERM)
            self.fail("SIGTERM did not interrupt the scoped child")

        process.communicate.side_effect = interrupt_child
        process.returncode = -9
        cleanup_state: list[str] = []

        @contextmanager
        def defer_signals():
            cleanup_state.append("entered")
            os.kill(os.getpid(), signal.SIGTERM)
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
                    with runner._termination_interrupts():
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

    def test_scope_deadline_kills_and_quarantines_the_bound_cgroup(self) -> None:
        process = Mock()
        process.communicate.side_effect = subprocess.TimeoutExpired(
            ["parent"], runner.BATCH_SCOPE_TIMEOUT_SECONDS
        )
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / runner.STUDY
            output.mkdir(mode=0o700)
            scope = Path(temporary) / "scope"
            with patch.object(
                runner.subprocess, "Popen", return_value=process
            ), patch.object(
                runner, "_bind_scope", return_value=scope
            ), patch.object(runner, "_release_scope"), patch.object(
                runner, "_kill_scope"
            ) as terminate:
                with self.assertRaisesRegex(ValueError, "could not be launched"):
                    runner._run_scoped(
                        ["/unused-parent"],
                        cwd=Path(temporary),
                        env={},
                        output=output,
                        stage="parent runner",
                        timeout_seconds=runner.BATCH_SCOPE_TIMEOUT_SECONDS,
                    )
            self.assertTrue((output / runner.INVALID).exists())
            process.communicate.assert_called_once_with(
                timeout=runner.BATCH_SCOPE_TIMEOUT_SECONDS
            )
            self.assertEqual(terminate.call_args.args, (process, scope))
            self.assertEqual(terminate.call_args.args[1], Path(temporary) / "scope")

    def test_bound_scope_cleanup_accepts_a_kernel_collected_cgroup(self) -> None:
        process = Mock()
        process.pid = 123
        process.communicate.return_value = ("", "")
        with TemporaryDirectory() as temporary:
            with patch.object(runner.os, "killpg") as kill_group:
                runner._kill_scope(process, Path(temporary) / "missing-scope")
        kill_group.assert_called_once_with(123, signal.SIGKILL)
        process.communicate.assert_called_once_with(timeout=10)

    def test_bound_scope_cleanup_rejects_a_live_scope_without_atomic_kill(self) -> None:
        process = Mock()
        with TemporaryDirectory() as temporary:
            scope = Path(temporary) / "live.scope"
            scope.mkdir()
            (scope / "cgroup.procs").write_text("")
            with self.assertRaisesRegex(RuntimeError, "kill control is unavailable"):
                runner._kill_scope(process, scope)
        process.communicate.assert_not_called()

    def test_normal_scope_completion_accepts_kernel_collected_cgroup(self) -> None:
        process = Mock()
        process.communicate.return_value = ("", "")
        scope = Path("/sys/fs/cgroup/user.slice/collected.scope")
        with patch.object(
            runner, "_scope_capability"
        ), patch.object(
            runner.subprocess, "Popen", return_value=process
        ), patch.object(
            runner, "_bind_scope", return_value=scope
        ), patch.object(runner, "_release_scope"), patch.object(
            runner.Path, "read_text", side_effect=OSError(errno.ENODEV, "collected")
        ):
            result = runner._run_scoped(
                ["/unused-parent"],
                cwd=Path("/tmp"),
                env={},
                output=Path("/tmp") / runner.STUDY,
                stage="parent runner",
            )
        self.assertEqual(result.returncode, process.returncode)

    def test_scope_completion_rejects_unreadable_live_membership(self) -> None:
        with patch.object(
            runner.Path, "read_text", side_effect=OSError(errno.EIO, "failed")
        ):
            with self.assertRaises(OSError):
                runner._verify_scope_empty(Path("/sys/fs/cgroup/live.scope"))

    def test_bound_scope_cleanup_also_kills_and_reaps_the_launcher_group(self) -> None:
        process = Mock()
        process.pid = 123
        process.communicate.return_value = ("", "")
        with TemporaryDirectory() as temporary:
            scope = Path(temporary) / "scope"
            scope.mkdir()
            (scope / "cgroup.kill").write_text("")
            (scope / "cgroup.procs").write_text("")
            with patch.object(runner.os, "killpg") as kill_group:
                runner._kill_scope(process, scope)
        kill_group.assert_called_once_with(123, signal.SIGKILL)
        process.communicate.assert_called_once_with(timeout=10)

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

    def test_failed_systemd_kill_uses_the_live_unbound_scope_control(self) -> None:
        process = Mock()
        with TemporaryDirectory() as temporary:
            scope = Path(temporary) / "live.scope"
            scope.mkdir()
            with patch.object(
                runner, "_run_integrity_command", return_value=subprocess.CompletedProcess([], 1)
            ), patch.object(
                runner, "_scope_cgroup", return_value=scope
            ), patch.object(runner, "_kill_scope") as atomic_kill:
                runner._kill_unbound_scope(process, "live", {})
        atomic_kill.assert_called_once_with(process, scope)
        process.communicate.assert_not_called()

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
                site_packages=Path("/dependencies"),
                production_threads_path_sha256="0" * 64,
            )
        self.assertEqual(environment["AGENTIC_ROOT"], "/workspace")
        self.assertEqual(environment["AGENTIC_PRODUCTION_THREADS_DIR"], "/production")
        self.assertEqual(environment["PATH"], "/usr/bin:/bin")
        self.assertEqual(environment["CODEX_THREAD_ID"], runner.COORDINATION_THREAD_ID)
        self.assertEqual(environment["PYTHONPATH"], "/execution:/assist:/dependencies")
        self.assertEqual(
            environment["REACH_REPRODUCTION_SITE_PACKAGES"], "/dependencies"
        )
        self.assertEqual(
            {key: environment[key] for key in runner.SAFE_GIT_ENVIRONMENT},
            runner.SAFE_GIT_ENVIRONMENT,
        )

    def test_python_environment_ignores_caller_venv_startup_hooks(self) -> None:
        expected = runner._python_environment_identity(
            Path.home() / "deploy/assist/code/.venv/bin/python"
        )
        self.assertEqual(
            expected["startup_mode"],
            "fixed-system-interpreter-minus-S-with-explicit-pythonpath",
        )
        with TemporaryDirectory() as temporary, patch.object(
            runner, "_production_threads_directory", return_value=Path("/production")
        ):
            root = Path(temporary)
            marker = root / "pth-ran"
            custom_marker = root / "sitecustomize-ran"
            (root / "injected.pth").write_text(
                f"import pathlib; pathlib.Path({str(marker)!r}).touch()\n"
            )
            (root / "sitecustomize.py").write_text(
                f"import pathlib; pathlib.Path({str(custom_marker)!r}).touch()\n"
            )
            launcher = root / "python"
            launcher.write_bytes(runner.PYTHON_LAUNCHER)
            launcher.chmod(0o500)
            environment = runner._execution_environment(
                workspace_root=Path("/workspace"),
                execution_root=Path("/execution"),
                assist_source=Path("/assist"),
                site_packages=root,
                production_threads_path_sha256="0" * 64,
            )
            environment["PYTHONPATH"] = "/execution:/assist"
            result = runner._run_integrity_command(
                [
                    str(launcher), "-c",
                    f"import sys; assert {str(root)!r} in sys.path",
                ],
                env=environment,
            )
            self.assertEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertFalse(custom_marker.exists())

    def test_production_status_directory_is_hash_pinned_from_systemd(self) -> None:
        with TemporaryDirectory() as temporary:
            threads = Path(temporary)
            expected = runner.hashlib.sha256(str(threads).encode()).hexdigest()
            service = subprocess.CompletedProcess(
                [], 0, stdout=f"OTHER=value ASSIST_THREADS_DIR={threads}\n", stderr=""
            )
            with patch.dict(os.environ, {"LD_PRELOAD": "/attacker.so"}), patch.object(
                runner, "_run_integrity_command", return_value=service
            ) as execute:
                self.assertEqual(runner._production_threads_directory(expected), threads)
            self.assertNotIn("LD_PRELOAD", execute.call_args.kwargs["env"])
            with patch.object(runner, "_run_integrity_command", return_value=service):
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
            python_launcher = workspace / "python"
            gate.parent.mkdir(parents=True, mode=0o700)
            deploy_environment.parent.mkdir(mode=0o700)
            gate.write_text("gate")
            gate.chmod(0o500)
            deploy_environment.write_text("environment")
            deploy_environment.chmod(0o400)
            python_launcher.write_bytes(runner.PYTHON_LAUNCHER)
            python_launcher.chmod(0o500)
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
            trace_path = traces / f"{trial.sha256}.json"
            trace_path.write_bytes(canonical_json({
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

            missing = object()
            malformed_results = (
                missing,
                [],
                {"first_prompt_tokens": 123},
                {"first_prompt_tokens": True, "skill_loaded_before_first_read": False},
                {"first_prompt_tokens": -1, "skill_loaded_before_first_read": False},
                {"first_prompt_tokens": "123", "skill_loaded_before_first_read": False},
                {"first_prompt_tokens": 123, "skill_loaded_before_first_read": None},
                {"first_prompt_tokens": 123, "skill_loaded_before_first_read": "true"},
                {"first_prompt_tokens": 123, "skill_loaded_before_first_read": 1},
            )
            for result in malformed_results:
                with self.subTest(result=result):
                    trace = {"trial_sha256": trial.sha256}
                    if result is not missing:
                        trace["result"] = result
                    trace_path.write_bytes(canonical_json(trace) + b"\n")
                    with self.assertRaisesRegex(ValueError, "secondary metadata"):
                        runner._trial_metadata_from_traces(
                            output,
                            one_trial_bundle,
                            [{
                                "trial_sha256": trial.sha256,
                                "outcome": "artifact_failure",
                                "detail": "failed",
                            }],
                        )

            trace_path.write_bytes(canonical_json({
                "trial_sha256": trial.sha256,
                "result": {
                    "first_prompt_tokens": None,
                    "skill_loaded_before_first_read": False,
                },
            }) + b"\n")
            metadata = json.loads(runner._trial_metadata_from_traces(
                output,
                one_trial_bundle,
                [{
                    "trial_sha256": trial.sha256,
                    "outcome": "artifact_failure",
                    "detail": "token usage unavailable",
                }],
            ))
            self.assertIsNone(metadata[0]["first_prompt_tokens"])
            self.assertFalse(metadata[0]["skill_loaded_before_first_read"])

            trace_path.write_bytes(canonical_json({
                "trial_sha256": trial.sha256,
                "worker_error": "provider failed",
                "trace": [],
            }) + b"\n")
            metadata = json.loads(runner._trial_metadata_from_traces(
                output,
                one_trial_bundle,
                [{
                    "trial_sha256": trial.sha256,
                    "outcome": "provider_error",
                    "detail": "provider failed",
                }],
            ))
            self.assertIsNone(metadata[0]["first_prompt_tokens"])
            self.assertIsNone(metadata[0]["skill_loaded_before_first_read"])

    def test_canonical_workspace_is_derived_and_cannot_be_substituted(self) -> None:
        workspace = runner._canonical_workspace_root(ROOT)
        self.assertEqual(workspace, ROOT.parents[2])
        with patch.dict(
            os.environ, {"CODEX_THREAD_ID": runner.COORDINATION_THREAD_ID}
        ), patch.object(
            runner, "_canonical_workspace_root", return_value=workspace
        ), patch.object(runner.subprocess, "Popen") as execute:
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

    def test_source_checkout_and_git_environment_cannot_be_redirected(self) -> None:
        with TemporaryDirectory() as temporary, patch.object(
            runner, "_command"
        ) as command:
            with self.assertRaisesRegex(ValueError, "registered reproduction checkout"):
                runner._canonical_workspace_root(Path(temporary))
        command.assert_not_called()
        with patch.object(runner, "_command") as command:
            with self.assertRaisesRegex(ValueError, "registered reproduction checkout"):
                runner._canonical_workspace_root(runner.SOURCE_ROOT / "unused" / "..")
        command.assert_not_called()

        with TemporaryDirectory() as temporary:
            clone_root = Path(temporary) / "clone"
            common = clone_root / ".git"
            (clone_root.parent / "tools").mkdir()
            (clone_root.parent / "tools" / "agentic").touch()
            common.mkdir(parents=True)
            with patch.object(
                runner, "SOURCE_ROOT", clone_root
            ), patch.object(
                runner, "_command", return_value=str(common)
            ):
                with self.assertRaisesRegex(ValueError, "workspace identity differs"):
                    runner._canonical_workspace_root(clone_root)

        process = Mock()
        process.communicate.return_value = ("verified\n", "")
        process.returncode = 0
        with patch.dict(
            os.environ,
            {
                "GIT_DIR": "/redirected",
                "GIT_CONFIG_COUNT": "1",
                "LD_PRELOAD": "/attacker.so",
                "UNRELATED": "discarded",
            },
        ), patch.object(runner.subprocess, "Popen", return_value=process) as execute:
            self.assertEqual(runner._command("git", "status", cwd=ROOT), "verified")
        self.assertEqual(execute.call_args.args[0][0], runner.GIT_BINARY)
        self.assertTrue(execute.call_args.kwargs["start_new_session"])
        process.communicate.assert_called_once_with(
            timeout=runner.INTEGRITY_COMMAND_TIMEOUT_SECONDS
        )
        git_environment = execute.call_args.kwargs["env"]
        self.assertNotIn("GIT_DIR", git_environment)
        self.assertEqual(git_environment["GIT_CONFIG_COUNT"], "3")
        self.assertEqual(git_environment["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(git_environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(git_environment["GIT_CONFIG_KEY_0"], "core.fsmonitor")
        self.assertEqual(git_environment["GIT_CONFIG_KEY_2"], "core.hooksPath")
        self.assertEqual(git_environment["GIT_CONFIG_VALUE_2"], "/dev/null")
        self.assertNotIn("LD_PRELOAD", git_environment)
        self.assertNotIn("UNRELATED", git_environment)

    def test_remote_publication_check_has_no_repository_config_context(self) -> None:
        manifest = {
            "registration": {
                "publication_branch": runner.PUBLICATION_BRANCH,
                "publication_remote": runner.PUBLICATION_REMOTE,
                "tag": runner.REGISTRATION_TAG,
            }
        }
        refs = (
            f"{'1' * 40}\trefs/heads/{runner.PUBLICATION_BRANCH}\n"
            f"{'2' * 40}\trefs/tags/{runner.REGISTRATION_TAG}\n"
            f"{'1' * 40}\trefs/tags/{runner.REGISTRATION_TAG}^{{}}\n"
        )
        with patch.object(
            runner, "_verify_local_registration", return_value=TEST_REGISTRATION
        ), patch.object(runner, "_command", return_value=refs) as command:
            runner._verify_publication(ROOT, manifest)
        self.assertEqual(command.call_args.kwargs["cwd"], Path("/"))
        self.assertEqual(command.call_args.args[:3], ("git", "ls-remote", runner.PUBLICATION_REMOTE))

    def test_registration_approval_binds_every_required_review(self) -> None:
        terra_reviews = {
            lens: {
                "disposition": "accepted",
                "model": model,
                "result": (
                    f"CANDIDATE_COMMIT={'1' * 40}\n"
                    f"CANDIDATE_TREE={'2' * 40}\n"
                    f"COORDINATION_THREAD_ID={runner.COORDINATION_THREAD_ID}\n"
                    f"REVIEW_LENS={lens}\nREVIEW_MODEL={model}\n"
                    "DISPOSITION=accepted\n"
                    "REVIEW_SUMMARY=The exact protocol preserves every required invariant.\n"
                    "ACCEPTED"
                ),
            }
            for lens, model in runner.REQUIRED_REVIEW_MODELS.items()
            if lens != "design-final"
        }
        for review in terra_reviews.values():
            review["result_sha256"] = hashlib.sha256(review["result"].encode()).hexdigest()
        terra_digest = digest(terra_reviews)
        sol_result = (
            f"CANDIDATE_COMMIT={'1' * 40}\n"
            f"CANDIDATE_TREE={'2' * 40}\n"
            f"COORDINATION_THREAD_ID={runner.COORDINATION_THREAD_ID}\n"
            "REVIEW_LENS=design-final\nREVIEW_MODEL=gpt-5.6-sol\n"
            "DISPOSITION=accepted\n"
            "REVIEW_SUMMARY=The design is approved after all Terra reviews converged.\n"
            f"TERRA_APPROVALS_SHA256={terra_digest}\nACCEPTED"
        )
        approval = {
            "candidate_commit": "1" * 40,
            "candidate_tree": "2" * 40,
            "coordination_thread_id": runner.COORDINATION_THREAD_ID,
            "reviews": terra_reviews | {
                "design-final": {
                    "disposition": "accepted",
                    "model": runner.REQUIRED_REVIEW_MODELS["design-final"],
                    "result": sol_result,
                    "result_sha256": hashlib.sha256(sol_result.encode()).hexdigest(),
                }
            },
            "schema": "reach-v8-r3-reproduction-review-approval-v2",
            "terra_approvals_sha256": terra_digest,
        }
        runner._verify_review_approval(approval, commit="1" * 40, tree="2" * 40)
        harness = approval["reviews"]["harness-integrity"]
        original_result = harness["result"]
        harness["result"] += "\n"
        harness["result_sha256"] = hashlib.sha256(harness["result"].encode()).hexdigest()
        approval["terra_approvals_sha256"] = digest(terra_reviews)
        with self.assertRaisesRegex(ValueError, "review approval differs"):
            runner._verify_review_approval(approval, commit="1" * 40, tree="2" * 40)
        harness["result"] = original_result
        harness["result_sha256"] = hashlib.sha256(original_result.encode()).hexdigest()
        approval["terra_approvals_sha256"] = digest(terra_reviews)
        approval["reviews"]["scientific-validity"]["disposition"] = "revisions-required"
        with self.assertRaisesRegex(ValueError, "review approval differs"):
            runner._verify_review_approval(approval, commit="1" * 40, tree="2" * 40)

    def test_registration_approval_rejects_opaque_or_non_dependent_results(self) -> None:
        result = "Review\nACCEPTED"
        reviews = {
            lens: {
                "disposition": "accepted", "model": model, "result": result,
                "result_sha256": "3" * 64,
            }
            for lens, model in runner.REQUIRED_REVIEW_MODELS.items()
        }
        approval = {
            "candidate_commit": "1" * 40,
            "candidate_tree": "2" * 40,
            "coordination_thread_id": runner.COORDINATION_THREAD_ID,
            "reviews": reviews,
            "schema": "reach-v8-r3-reproduction-review-approval-v2",
            "terra_approvals_sha256": "4" * 64,
        }
        with self.assertRaisesRegex(ValueError, "review approval differs"):
            runner._verify_review_approval(approval, commit="1" * 40, tree="2" * 40)

    def test_registration_approval_rejects_conflicting_identity_lines(self) -> None:
        reviews = {}
        for lens, model in runner.REQUIRED_REVIEW_MODELS.items():
            result = (
                f"CANDIDATE_COMMIT={'1' * 40}\n"
                f"CANDIDATE_TREE={'2' * 40}\n"
                f"COORDINATION_THREAD_ID={runner.COORDINATION_THREAD_ID}\n"
                f"REVIEW_LENS={lens}\nREVIEW_MODEL={model}\n"
                "DISPOSITION=accepted\n"
                "REVIEW_SUMMARY=Every required identity field is unique.\n"
                "ACCEPTED"
            )
            reviews[lens] = {
                "disposition": "accepted",
                "model": model,
                "result": result,
                "result_sha256": hashlib.sha256(result.encode()).hexdigest(),
            }
        terra_reviews = {
            lens: review for lens, review in reviews.items() if lens != "design-final"
        }
        terra_digest = digest(terra_reviews)
        sol = reviews["design-final"]
        sol["result"] = sol["result"].replace(
            "\nACCEPTED", f"\nTERRA_APPROVALS_SHA256={terra_digest}\nACCEPTED"
        )
        sol["result_sha256"] = hashlib.sha256(sol["result"].encode()).hexdigest()
        approval = {
            "candidate_commit": "1" * 40,
            "candidate_tree": "2" * 40,
            "coordination_thread_id": runner.COORDINATION_THREAD_ID,
            "reviews": reviews,
            "schema": "reach-v8-r3-reproduction-review-approval-v2",
            "terra_approvals_sha256": terra_digest,
        }
        runner._verify_review_approval(approval, commit="1" * 40, tree="2" * 40)
        scientific = reviews["scientific-validity"]
        original_scientific_result = scientific["result"]
        scientific["result"] = scientific["result"].replace(
            "REVIEW_LENS=scientific-validity\n",
            "REVIEW_LENS=other\nREVIEW_LENS=scientific-validity\n",
        )
        scientific["result_sha256"] = hashlib.sha256(
            scientific["result"].encode()
        ).hexdigest()
        approval["terra_approvals_sha256"] = digest(
            {lens: review for lens, review in reviews.items() if lens != "design-final"}
        )
        with self.assertRaisesRegex(ValueError, "review approval differs"):
            runner._verify_review_approval(approval, commit="1" * 40, tree="2" * 40)
        scientific["result"] = original_scientific_result
        scientific["result_sha256"] = hashlib.sha256(
            scientific["result"].encode()
        ).hexdigest()
        terra_digest = digest(
            {lens: review for lens, review in reviews.items() if lens != "design-final"}
        )
        approval["terra_approvals_sha256"] = terra_digest
        sol["result"] = sol["result"].replace(
            f"TERRA_APPROVALS_SHA256={terra_digest}\n",
            f"TERRA_APPROVALS_SHA256={'0' * 64}\n"
            f"TERRA_APPROVALS_SHA256={terra_digest}\n",
        )
        sol["result_sha256"] = hashlib.sha256(sol["result"].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "not Terra-dependent"):
            runner._verify_review_approval(approval, commit="1" * 40, tree="2" * 40)

    def test_cli_reexecs_with_only_the_fixed_python_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "CODEX_THREAD_ID": runner.COORDINATION_THREAD_ID,
                "LD_PRELOAD": "/attacker.so",
                "PYTHONPATH": "/attacker",
            },
            clear=True,
        ), patch.object(runner.os, "execve", side_effect=RuntimeError) as execute:
            with self.assertRaises(RuntimeError):
                runner._ensure_clean_entrypoint()
        executable, arguments, environment = execute.call_args.args
        self.assertEqual(executable, "/usr/bin/python3.14")
        self.assertEqual(arguments[:2], ["/usr/bin/python3.14", "-S"])
        self.assertEqual(environment, {
            "CODEX_THREAD_ID": runner.COORDINATION_THREAD_ID,
            "HOME": str(Path.home()),
            "LANG": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(ROOT),
            "PYTHONSAFEPATH": "1",
            runner._CLEAN_ENTRYPOINT: "1",
        })
        with patch.dict(os.environ, {}, clear=True), patch.object(
            runner.os, "execve", return_value=None
        ):
            with self.assertRaisesRegex(SystemExit, "unexpectedly returned"):
                runner._ensure_clean_entrypoint()

    def test_fixed_system_python_must_be_root_owned(self) -> None:
        with TemporaryDirectory() as temporary, patch.object(
            runner, "SYSTEM_PYTHON", Path(temporary) / "python"
        ):
            runner.SYSTEM_PYTHON.write_bytes(b"python")
            runner.SYSTEM_PYTHON.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "ownership differs"):
                runner._verify_system_python_ownership()

    def test_tag_approval_rejects_surrounding_whitespace(self) -> None:
        record = b"object deadbeef\ntype commit\ntag test\n\n{}\n"
        self.assertEqual(runner._decode_tag_approval(record), {})
        for changed in (
            record.replace(b"\n\n{}", b"\n\n {}"),
            record + b"\n",
        ):
            with self.assertRaisesRegex(ValueError, "not canonical"):
                runner._decode_tag_approval(changed)

    def test_public_entrypoints_install_termination_handling_before_preflight(self) -> None:
        active: list[bool] = []

        @contextmanager
        def guard():
            active.append(True)
            try:
                yield
            finally:
                active.pop()

        def preflight(*_args, **_kwargs):
            self.assertEqual(active, [True])

        with patch.dict(
            os.environ, {"CODEX_THREAD_ID": runner.COORDINATION_THREAD_ID}
        ), patch.object(runner, "_termination_interrupts", side_effect=guard), patch.object(
            runner, "_prepare_runtime", side_effect=preflight
        ):
            runner.prepare_runtime(Path("/root"), Path("/assist"), Path("/runtime"))

        with patch.dict(os.environ, {}, clear=True), patch.object(
            runner, "_prepare_runtime"
        ) as prepare:
            with self.assertRaisesRegex(ValueError, "prepare coordinator identity"):
                runner.prepare_runtime(Path("/root"), Path("/assist"), Path("/runtime"))
        prepare.assert_not_called()

    def test_event_slice_rejects_a_rewritten_prefix(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            prefix_identity = (len(prefix), hashlib.sha256(prefix).hexdigest(), True)
            appended = (
                b'{"event":"resource_started","resource":"llm","thread":"thread"}\n'
            )
            events.write_bytes(prefix + appended)
            descriptor = os.open(events, os.O_RDONLY)
            try:
                self.assertEqual(
                    runner._read_appended_events(descriptor, prefix_identity, "thread"),
                    [{"event": "resource_started", "resource": "llm", "thread": "thread"}],
                )
                events.write_bytes(b'{"event":"bad"}\n' + appended)
                with self.assertRaisesRegex(ValueError, "non-append-only"):
                    runner._read_appended_events(descriptor, prefix_identity, "thread")
            finally:
                os.close(descriptor)

    def test_event_slice_ignores_a_replacement_path(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            prefix_identity = (len(prefix), hashlib.sha256(prefix).hexdigest(), True)
            real = b'{"event":"resource_started","resource":"llm","thread":"thread"}\n'
            events.write_bytes(prefix + real)
            descriptor = os.open(events, os.O_RDONLY)
            try:
                replacement = events.with_suffix(".replacement")
                replacement.write_bytes(prefix + b'{"event":"fabricated"}\n')
                replacement.replace(events)
                self.assertEqual(
                    runner._read_appended_events(descriptor, prefix_identity, "thread"),
                    [{"event": "resource_started", "resource": "llm", "thread": "thread"}],
                )
            finally:
                os.close(descriptor)

    def test_event_slice_retains_unexpected_same_thread_llm_events(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            relevant = {
                "event": "resource_cancelled", "resource": "llm", "thread": "thread"
            }
            events.write_bytes(
                canonical_json(relevant) + b"\n"
                + canonical_json({
                    "event": "resource_started", "resource": "other", "thread": "thread"
                }) + b"\n"
                + canonical_json({
                    "event": "resource_started", "resource": "llm", "thread": "other"
                }) + b"\n"
            )
            descriptor = os.open(events, os.O_RDONLY)
            empty = (0, hashlib.sha256(b"").hexdigest(), True)
            try:
                self.assertEqual(
                    runner._read_appended_events(descriptor, empty, "thread"),
                    [relevant],
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
            prefix_identity = (len(prefix), hashlib.sha256(prefix).hexdigest(), True)
            descriptor = os.open(events, os.O_RDONLY)
            try:
                with self.assertRaisesRegex(ValueError, "malformed"):
                    runner._read_appended_events(descriptor, prefix_identity, "thread")
            finally:
                os.close(descriptor)

    def test_event_slice_rejects_crlf_records(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            events.write_bytes(prefix + b'{"event":"new"}\r\n')
            prefix_identity = (len(prefix), hashlib.sha256(prefix).hexdigest(), True)
            descriptor = os.open(events, os.O_RDONLY)
            try:
                with self.assertRaisesRegex(ValueError, "malformed"):
                    runner._read_appended_events(descriptor, prefix_identity, "thread")
            finally:
                os.close(descriptor)

    def test_event_descriptor_hashes_with_bounded_reads(self) -> None:
        size = runner.HASH_CHUNK_BYTES * 2 + 17
        calls: list[tuple[int, int]] = []

        def pread(_descriptor: int, count: int, offset: int) -> bytes:
            calls.append((count, offset))
            return b"x" * count

        with patch.object(runner.os, "pread", side_effect=pread):
            result = runner._descriptor_sha256(7, size)
        self.assertEqual(result, hashlib.sha256(b"x" * size).hexdigest())
        self.assertEqual(
            calls,
            [
                (runner.HASH_CHUNK_BYTES, 0),
                (runner.HASH_CHUNK_BYTES, runner.HASH_CHUNK_BYTES),
                (17, runner.HASH_CHUNK_BYTES * 2),
            ],
        )

    def test_event_slice_rejects_an_oversized_record(self) -> None:
        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            prefix = b'{"event":"old"}\n'
            events.write_bytes(prefix + b"{" + b"x" * runner.EVENT_RECORD_BYTES + b"}\n")
            prefix_identity = (len(prefix), hashlib.sha256(prefix).hexdigest(), True)
            descriptor = os.open(events, os.O_RDONLY)
            try:
                with self.assertRaisesRegex(ValueError, "too large"):
                    runner._read_appended_events(descriptor, prefix_identity, "thread")
            finally:
                os.close(descriptor)

    def test_event_slice_has_total_byte_and_record_bounds(self) -> None:
        empty = (0, hashlib.sha256(b"").hexdigest(), True)
        with patch.object(
            runner.os, "fstat",
            return_value=SimpleNamespace(st_size=runner.EVENT_SLICE_BYTES + 1),
        ):
            with self.assertRaisesRegex(ValueError, "slice is too large"):
                runner._read_appended_events(7, empty, "thread")

        with TemporaryDirectory() as temporary:
            events = Path(temporary) / "events.jsonl"
            events.write_bytes(b"{}\n" * (runner.EVENT_SLICE_RECORDS + 1))
            descriptor = os.open(events, os.O_RDONLY)
            try:
                with self.assertRaisesRegex(ValueError, "too many records"):
                    runner._read_appended_events(descriptor, empty, "thread")
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
            with self.assertRaisesRegex(ValueError, "latest denial"):
                runner._denial_retry_not_before(
                    output,
                    [admission, {"admitted": False, "trial_sha256": "trial-2"}],
                )
            self.assertIsNone(runner._denial_retry_not_before(
                output,
                [admission, {"admitted": True, "trial_sha256": "trial-1"}],
            ))
            with self.assertRaisesRegex(ValueError, "latest denial"):
                runner._denial_retry_not_before(
                    output,
                    [
                        admission,
                        {"admitted": True, "trial_sha256": "trial-1"},
                        {"admitted": False, "trial_sha256": "trial-2"},
                        {"admitted": True, "trial_sha256": "trial-2"},
                    ],
                )
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
        intervals[0]["next_denial_not_before_unix"] = 1789171799.0
        with self.assertRaisesRegex(ValueError, "shorter than registered"):
            runner.verify_execution_intervals(
                intervals,
                admissions=[admission, {"admitted": True}],
                outcomes=[{"outcome": "pass"}],
                thread_id=thread,
                schedule_size=1,
            )
        intervals[0]["next_denial_not_before_unix"] = 1789171800.0
        intervals[1]["started_at"] = "2026-09-12T00:09:59+00:00"
        with self.assertRaisesRegex(ValueError, "cadence"):
            runner.verify_execution_intervals(
                intervals,
                admissions=[admission, {"admitted": True}],
                outcomes=[{"outcome": "pass"}],
                thread_id=thread,
                schedule_size=1,
            )

    def test_live_cooldowns_match_the_latest_attested_boundaries(self) -> None:
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            batch_path = output / "batch-cooldown.json"
            batch_path.write_bytes(canonical_json({
                "completed_outcomes": 24,
                "not_before_unix": 1000.0,
            }) + b"\n")
            os.utime(batch_path, ns=(900_000_000_000, 900_000_000_000))
            (output / "denial-cooldown.json").write_bytes(canonical_json({
                "admission_count": 1,
                "not_before_unix": 700.0,
                "trial_sha256": "trial-1",
            }) + b"\n")
            admissions = [
                {"admitted": False, "trial_sha256": "trial-1"},
                {"admitted": True, "trial_sha256": "trial-1"},
            ]
            denial_interval = {
                "admissions_after": 1,
                "batch_cooldown_mtime_ns": None,
                "next_batch_not_before_unix": None,
                "next_denial_not_before_unix": 700.0,
                "outcomes_after": 0,
            }
            batch_interval = {
                "admissions_after": 2,
                "batch_cooldown_mtime_ns": 900_000_000_000,
                "next_batch_not_before_unix": 1000.0,
                "next_denial_not_before_unix": None,
                "outcomes_after": 24,
            }
            self.assertEqual(
                runner._verify_live_cooldowns(
                    output, admissions, [denial_interval, batch_interval]
                ),
                ([batch_interval], None),
            )
            batch_path.write_bytes(canonical_json({
                "completed_outcomes": 23,
                "not_before_unix": 1000.0,
            }) + b"\n")
            with self.assertRaisesRegex(ValueError, "batch cooldown"):
                runner._verify_live_cooldowns(
                    output, admissions, [denial_interval, batch_interval]
                )
            batch_path.write_bytes(canonical_json({
                "completed_outcomes": 24,
                "not_before_unix": 1000.0,
            }) + b"\n")
            os.utime(batch_path, ns=(900_000_000_000, 900_000_000_000))
            (output / "denial-cooldown.json").write_bytes(canonical_json({
                "admission_count": 1,
                "not_before_unix": 701.0,
                "trial_sha256": "trial-1",
            }) + b"\n")
            with self.assertRaisesRegex(ValueError, "denial cooldown"):
                runner._verify_live_cooldowns(
                    output, admissions, [denial_interval, batch_interval]
                )

    def test_live_cooldowns_reject_symlinked_records(self) -> None:
        with TemporaryDirectory() as temporary:
            parent = Path(temporary)
            output = parent / "output"
            output.mkdir()
            external = parent / "external.json"
            external.write_bytes(canonical_json({
                "completed_outcomes": 24,
                "not_before_unix": 1000.0,
            }) + b"\n")
            (output / "batch-cooldown.json").symlink_to(external)
            with self.assertRaisesRegex(ValueError, "real file"):
                runner._verify_live_cooldowns(output, [], [])

            (output / "batch-cooldown.json").unlink()
            external.write_bytes(canonical_json({
                "admission_count": 1,
                "not_before_unix": 700.0,
                "trial_sha256": "trial-1",
            }) + b"\n")
            (output / "denial-cooldown.json").symlink_to(external)
            with self.assertRaisesRegex(ValueError, "real file"):
                runner._verify_live_cooldowns(
                    output,
                    [{"admitted": False, "trial_sha256": "trial-1"}],
                    [],
                )

    def test_archive_rechecks_live_cooldowns_before_copying(self) -> None:
        scoped = Mock()
        manifest = {
            "execution": {"coordination_thread_id": "thread"},
            "parent": {"bundle_file_sha256": "file", "bundle_sha256": "bundle"},
        }
        with patch.object(
            runner, "_verify_archive_runtime"
        ), patch.object(
            runner, "verify_attestation_inventory", return_value=([], [])
        ), patch.object(
            runner.StudyBundle, "read_verified",
            return_value=SimpleNamespace(schedule=(), sha256="bundle"),
        ), patch.object(
            runner, "_sha256", return_value="file"
        ), patch.object(
            runner, "_verified_progress", return_value=([], [])
        ), patch.object(
            runner, "verify_execution_intervals", return_value=[]
        ), patch.object(
            runner, "_verify_live_cooldowns", side_effect=ValueError("changed cooldown")
        ), patch.object(runner, "_run_scoped", scoped):
            with self.assertRaisesRegex(ValueError, "changed cooldown"):
                runner._archive_and_analyze_locked(
                    ROOT,
                    Path("output"),
                    Path("capsule"),
                    Path("analysis"),
                    Path("attestations"),
                    manifest=manifest,
                    registration=TEST_REGISTRATION,
                    execution_root=Path("execution"),
                    assist_source=Path("assist"),
                    assist_python=Path("python"),
                    workspace_root=Path("workspace"),
                )
        scoped.assert_not_called()

    def test_archive_rejects_bundle_or_fidelity_drift_before_parent_worker(self) -> None:
        scoped = Mock()
        manifest = {
            "execution": {"coordination_thread_id": "thread"},
            "parent": {"bundle_file_sha256": "file", "bundle_sha256": "bundle"},
        }
        common = {
            "manifest": manifest,
            "registration": TEST_REGISTRATION,
            "execution_root": Path("execution"),
            "assist_source": Path("assist"),
            "assist_python": Path("python"),
            "workspace_root": Path("workspace"),
        }
        with patch.object(
            runner, "_verify_archive_runtime"
        ), patch.object(
            runner, "verify_attestation_inventory", return_value=([], [])
        ), patch.object(runner, "_run_scoped", scoped):
            with self.subTest(case="bundle"), patch.object(
                runner.StudyBundle, "read_verified",
                return_value=SimpleNamespace(schedule=(), sha256="wrong"),
            ):
                with self.assertRaisesRegex(ValueError, "parent bundle"):
                    runner._archive_and_analyze_locked(
                        ROOT, Path("output"), Path("capsule"), Path("analysis"),
                        Path("attestations"), **common,
                    )

            with self.subTest(case="bundle-file"), patch.object(
                runner.StudyBundle, "read_verified",
                return_value=SimpleNamespace(schedule=(), sha256="bundle"),
            ), patch.object(runner, "_sha256", return_value="wrong"):
                with self.assertRaisesRegex(ValueError, "parent bundle"):
                    runner._archive_and_analyze_locked(
                        ROOT, Path("output"), Path("capsule"), Path("analysis"),
                        Path("attestations"), **common,
                    )

            with self.subTest(case="fidelity"), patch.object(
                runner.StudyBundle, "read_verified",
                return_value=SimpleNamespace(schedule=(), sha256="bundle"),
            ), patch.object(
                runner, "_sha256", return_value="file"
            ), patch.object(
                runner, "_verified_progress",
                return_value=([], [{
                    "detail": "provider request differs from sealed request",
                    "outcome": "provider_error",
                }]),
            ):
                with self.assertRaisesRegex(ValueError, "fidelity"):
                    runner._archive_and_analyze_locked(
                        ROOT, Path("output"), Path("capsule"), Path("analysis"),
                        Path("attestations"), **common,
                    )
        scoped.assert_not_called()

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

    def test_capsule_rejects_invalid_returned_secondary_metadata(self) -> None:
        manifest = runner._load_manifest(ROOT)
        missing = object()
        cases = (
            ("boolean-token", "first_prompt_tokens", True, "token count"),
            ("negative-token", "first_prompt_tokens", -1, "token count"),
            ("missing-token", "first_prompt_tokens", missing, "observations are missing"),
            (
                "missing-process", "skill_loaded_before_first_read", missing,
                "observations are missing",
            ),
            (
                "null-process", "skill_loaded_before_first_read", None,
                "process measure is missing",
            ),
        )
        with TemporaryDirectory() as temporary:
            for case, field, value, message in cases:
                with self.subTest(case=case):
                    capsule = Path(temporary) / case
                    shutil.copytree(HISTORICAL, capsule)
                    metadata_path = capsule / "trial-metadata.json"
                    metadata = json.loads(metadata_path.read_text())
                    if value is missing:
                        metadata[0].pop(field)
                    else:
                        metadata[0][field] = value
                    metadata_path.write_bytes(canonical_json(metadata) + b"\n")
                    run_path = capsule / "run.json"
                    run = json.loads(run_path.read_text())
                    run.pop("record_sha256")
                    run["trial_metadata_sha256"] = runner._sha256(metadata_path)
                    run_path.write_bytes(
                        canonical_json(run | {"record_sha256": digest(run)}) + b"\n"
                    )
                    with self.assertRaisesRegex(ValueError, message):
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
                    "python_environment": {},
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
                    "site_packages": parent / "site-packages",
                    "worker": workspace,
                }),
            ), patch.object(
                runner,
                "_environment_identity",
                return_value={
                    "distributions": {}, "environment": {}, "modules": {}, "python": {},
                    "python_environment": {},
                },
            ), patch.object(runner, "_verified_progress", return_value=([], [])):
                output.mkdir(mode=0o700)
                (output / runner.INVALID).symlink_to(output / "missing-invalid.json")
                with self.subTest(stage="dangling-quarantine-marker"), patch.object(
                    runner, "_run_batch_locked"
                ) as launch:
                    with self.assertRaisesRegex(ValueError, "quarantined"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    launch.assert_not_called()

                shutil.rmtree(output)
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
                resumed_bundle = SimpleNamespace(
                    schedule=(
                        SimpleNamespace(sha256="trial-1"),
                        SimpleNamespace(sha256="trial-2"),
                    )
                )
                prior_admission = {"admitted": True, "trial_sha256": "trial-1"}
                fidelity_failure = {
                    "outcome": "provider_error",
                    "detail": "provider request differs from sealed request",
                }
                scoped = Mock()
                with self.subTest(stage="persisted-fidelity-failure"), patch.object(
                    runner.StudyBundle, "read_verified", return_value=resumed_bundle
                ), patch.object(
                    runner, "_verified_progress",
                    return_value=([prior_admission], [fidelity_failure]),
                ), patch.object(runner, "_run_scoped", scoped):
                    with self.assertRaisesRegex(ValueError, "persisted reproduction progress"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())
                    scoped.assert_not_called()

                shutil.rmtree(output)
                if attestations.exists():
                    shutil.rmtree(attestations)
                completed = {"outcome": "pass", "detail": ""}
                scoped = Mock()
                with self.subTest(stage="persisted-progress-without-attestation"), patch.object(
                    runner.StudyBundle, "read_verified", return_value=resumed_bundle
                ), patch.object(
                    runner, "_verified_progress",
                    return_value=([prior_admission], [completed]),
                ), patch.object(
                    runner, "attest", return_value=b'{}\n'
                ), patch.object(runner, "_run_scoped", scoped):
                    with self.assertRaisesRegex(ValueError, "pre-invocation"):
                        runner.run_batch(ROOT, output, attestations, **common)
                    self.assertTrue((output / runner.INVALID).exists())
                    scoped.assert_not_called()

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
                self.assertEqual(termination_guard.call_count, 2)
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
            nested = capsule / "nested" / "learning.md"
            nested.parent.mkdir()
            nested.write_text("nested evidence remains sealed\n")
            manifest = {"study_id": runner.STUDY}
            seal = {
                "schema": "reach-v8-exact-reproduction-seal-v1",
                "manifest_sha256": digest(manifest),
                "sealed_files": {
                    "evidence.json": runner._sha256(evidence),
                    "nested/learning.md": runner._sha256(nested),
                },
            }
            (capsule / "reproduction-seal.json").write_bytes(
                canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n"
            )
            runner.verify_reproduction_seal(capsule, manifest)
            seal_path = capsule / "reproduction-seal.json"
            stored = json.loads(seal_path.read_text())
            name = "manifest_sha256"
            member = canonical_json({name: stored[name]}).decode()[1:-1]
            encoded = canonical_json(stored).decode()
            seal_path.write_text(encoded.replace(member, f"{member},{member}") + "\n")
            with self.assertRaisesRegex(ValueError, "seal is missing or malformed"):
                runner.verify_reproduction_seal(capsule, manifest)
            seal_path.write_bytes(
                canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n"
            )
            evidence.write_text("{\"changed\":true}\n")
            with self.assertRaisesRegex(ValueError, "sealed files differ"):
                runner.verify_reproduction_seal(capsule, manifest)
            evidence.write_text("{}\n")
            nested.write_text("changed nested evidence\n")
            with self.assertRaisesRegex(ValueError, "sealed files differ"):
                runner.verify_reproduction_seal(capsule, manifest)
            nested.write_text("nested evidence remains sealed\n")
            for change in ({"schema": "other"}, {"extra": True}):
                changed = seal | change
                (capsule / "reproduction-seal.json").write_bytes(
                    canonical_json(changed | {"seal_sha256": digest(changed)}) + b"\n"
                )
                with self.assertRaisesRegex(ValueError, "seal is malformed"):
                    runner.verify_reproduction_seal(capsule, manifest)


if __name__ == "__main__":
    unittest.main()
