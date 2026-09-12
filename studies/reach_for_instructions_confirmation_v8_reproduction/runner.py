"""Run an exact V8-r3 reproduction behind additional administrative integrity checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from typing import Any

from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from harness.records import AdmissionLog, RecordChain
from studies.reach_for_instructions_confirmation_v8_reproduction import analysis


STUDY = "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r1"
MANIFEST = Path("experiments") / STUDY / "manifest.json"
INVALID = "REPRODUCTION_INVALID.json"
REGISTRATION_TAG = f"{STUDY}"
PUBLICATION_BRANCH = "reach-experiment-reproduction-v2"
PUBLICATION_REMOTE = "https://github.com/pierrel/llm-agentic-experiments.git"
DENIAL = re.compile(
    r"^agentic: production is busy \(.+\); not starting (?:llm|real-llm) work\. "
    r"Run `tools/agentic production status --attempt N`, set its next-probe timer, "
    r"and continue other work\.$"
)
DEPENDENCIES = ("deepagents", "langchain", "langgraph")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _command(*arguments: str, cwd: Path | None = None) -> str:
    result = subprocess.run(arguments, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"command failed: {Path(arguments[0]).name}")
    return result.stdout.strip()


def _load_manifest(root: Path) -> dict[str, Any]:
    path = root / MANIFEST
    try:
        stored = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("reproduction manifest is missing or malformed") from error
    if not isinstance(stored, dict) or set(stored) != {"manifest", "sha256"}:
        raise ValueError("reproduction manifest shape is invalid")
    manifest = stored["manifest"]
    if not isinstance(manifest, dict) or stored["sha256"] != digest(manifest):
        raise ValueError("reproduction manifest digest mismatch")
    if manifest.get("study_id") != STUDY:
        raise ValueError("reproduction manifest study identity mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("reproduction manifest file inventory is missing")
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("reproduction manifest file inventory is invalid")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("reproduction manifest file path escapes its checkout")
        if _sha256(root / path) != expected:
            raise ValueError(f"reproduction input differs from manifest: {relative}")
    return manifest


def _git_identity(root: Path) -> dict[str, str]:
    return {
        "commit": _command("git", "rev-parse", "HEAD", cwd=root),
        "tree": _command("git", "rev-parse", "HEAD^{tree}", cwd=root),
        "status": _command("git", "status", "--porcelain=v1", cwd=root),
    }


def _verify_registration(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    registration = manifest["registration"]
    tag = registration["tag"]
    if registration != {
        "publication_branch": PUBLICATION_BRANCH,
        "publication_remote": PUBLICATION_REMOTE,
        "tag": REGISTRATION_TAG,
    }:
        raise ValueError("reproduction publication identity differs from the fixed protocol")
    if _command("git", "cat-file", "-t", tag, cwd=root) != "tag":
        raise ValueError("reproduction registration tag must be annotated")
    tag_object = _command("git", "rev-parse", tag, cwd=root)
    commit = _command("git", "rev-parse", f"{tag}^{{commit}}", cwd=root)
    tree = _command("git", "rev-parse", f"{tag}^{{tree}}", cwd=root)
    current = _git_identity(root)
    if current != {"commit": commit, "tree": tree, "status": ""}:
        raise ValueError("reproduction checkout is not the clean registered commit")
    tagged_manifest = subprocess.run(
        ["git", "show", f"{commit}:{MANIFEST.as_posix()}"], cwd=root, capture_output=True
    )
    if tagged_manifest.returncode or tagged_manifest.stdout != (root / MANIFEST).read_bytes():
        raise ValueError("registered commit does not retain the exact manifest")
    remote = registration["publication_remote"]
    branch = registration["publication_branch"]
    published = _command(
        "git", "ls-remote", remote, f"refs/heads/{branch}", f"refs/tags/{tag}",
        f"refs/tags/{tag}^{{}}", cwd=root,
    ).splitlines()
    refs = {line.split("\t", 1)[1]: line.split("\t", 1)[0] for line in published if "\t" in line}
    if refs.get(f"refs/heads/{branch}") != commit:
        raise ValueError("registered commit is not published at the declared branch")
    if refs.get(f"refs/tags/{tag}") != tag_object or refs.get(f"refs/tags/{tag}^{{}}") != commit:
        raise ValueError("published annotated registration tag differs")
    return {"commit": commit, "tree": tree, "tag_object": tag_object}


def _verify_execution(execution_root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    parent = manifest["parent"]
    identity = _git_identity(execution_root)
    if identity != {"commit": parent["commit"], "tree": parent["tree"], "status": ""}:
        raise ValueError("execution checkout differs from exact V8-r3 parent")
    tag = parent["tag"]
    if _command("git", "cat-file", "-t", tag, cwd=execution_root) != "commit":
        raise ValueError("parent V8-r3 tag kind differs from registration")
    if _command("git", "rev-parse", f"{tag}^{{commit}}", cwd=execution_root) != parent["commit"]:
        raise ValueError("parent V8-r3 tag resolves to another commit")
    bundle_path = execution_root / parent["bundle_path"]
    bundle = StudyBundle.read_verified(bundle_path)
    if bundle.sha256 != parent["bundle_sha256"] or _sha256(bundle_path) != parent["bundle_file_sha256"]:
        raise ValueError("parent bundle differs from registration")
    if len(bundle.schedule) != 72:
        raise ValueError("parent schedule is not the exact 72-episode cohort")
    return identity


def prepare_runtime(root: Path, assist_repository: Path, runtime_root: Path) -> None:
    """Create private clean detached clones for execution without fetching."""
    if runtime_root.exists() or runtime_root.is_symlink():
        raise ValueError("runtime root must not already exist")
    manifest = _load_manifest(root)
    _verify_registration(root, manifest)
    runtime_root.mkdir(mode=0o700, parents=True)
    experiment = runtime_root / "experiment"
    assist = runtime_root / "assist"
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(root), str(experiment)], check=True)
    subprocess.run(["git", "-C", str(experiment), "checkout", "--quiet", "--detach", manifest["parent"]["commit"]], check=True)
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(assist_repository), str(assist)], check=True)
    subprocess.run(["git", "-C", str(assist), "checkout", "--quiet", "--detach", manifest["runtime"]["assist_commit"]], check=True)
    _verify_execution(experiment, manifest)
    if _git_identity(assist) != {
        "commit": manifest["runtime"]["assist_commit"],
        "tree": manifest["runtime"]["assist_tree"],
        "status": "",
    }:
        raise ValueError("prepared Assist checkout differs from registration")


_ENVIRONMENT_SCRIPT = r'''
import base64, csv, hashlib, importlib, importlib.metadata, json, os, pathlib, sys
names = ("deepagents", "langchain", "langgraph")
distributions = {}
for name in names:
    dist = importlib.metadata.distribution(name)
    record = next((path for path in dist.files or () if str(path).endswith(".dist-info/RECORD")), None)
    if record is None:
        raise RuntimeError(f"missing RECORD for {name}")
    record_path = pathlib.Path(dist.locate_file(record))
    verified = []
    with record_path.open(newline="") as source:
        for relative, encoded, _size in csv.reader(source):
            if not encoded:
                continue
            algorithm, value = encoded.split("=", 1)
            if algorithm != "sha256":
                raise RuntimeError(f"unsupported RECORD hash for {name}")
            path = pathlib.Path(dist.locate_file(relative))
            actual = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).rstrip(b"=").decode()
            if actual != value:
                raise RuntimeError(f"installed file differs from RECORD: {name}:{relative}")
            verified.append((relative, value))
    distributions[name] = {
        "version": dist.version,
        "record_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
        "verified_files_sha256": hashlib.sha256(json.dumps(sorted(verified), separators=(",", ":")).encode()).hexdigest(),
    }
modules = {}
for name in ("studies.reach_for_instructions_confirmation_v8.runner", "harness.bundle", "assist", "assist.model_manager"):
    module = importlib.import_module(name)
    path = pathlib.Path(module.__file__).resolve()
    modules[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
python = pathlib.Path(sys.executable).resolve()
print(json.dumps({
    "distributions": distributions,
    "environment": {
        "assist_model_url": os.environ.get("ASSIST_MODEL_URL"),
        "python_no_user_site": os.environ.get("PYTHONNOUSERSITE"),
        "python_path": os.environ.get("PYTHONPATH"),
        "python_safe_path": os.environ.get("PYTHONSAFEPATH"),
    },
    "modules": modules,
    "python": {"version": sys.version, "sha256": hashlib.sha256(python.read_bytes()).hexdigest()},
}, sort_keys=True, separators=(",", ":")))
'''


def _environment_identity(
    *, assist_python: Path, workspace_root: Path, execution_root: Path, assist_source: Path
) -> dict[str, Any]:
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": f"{execution_root}:{assist_source}",
        "PYTHONSAFEPATH": "1",
        "PYTHONNOUSERSITE": "1",
    })
    deploy_environment = workspace_root / "assist" / ".deploy.env"
    if (
        deploy_environment.is_symlink() or not deploy_environment.is_file()
        or stat.S_IMODE(deploy_environment.stat().st_mode) != 0o600
    ):
        raise ValueError("worker deployment environment must be a real mode-0600 file")
    source_path = f"{execution_root}:{assist_source}"
    result = subprocess.run(
        [
            "sh", "-c",
            'set -a; . "$1"; PYTHONPATH="$2"; export PYTHONPATH; shift 2; exec "$@"',
            "sh", str(deploy_environment), source_path,
            str(assist_python), "-c", _ENVIRONMENT_SCRIPT,
        ], cwd=workspace_root,
        env=env, text=True, capture_output=True,
    )
    if result.returncode:
        raise ValueError("worker environment attestation failed")
    value = json.loads(result.stdout)
    prefixes = {
        "studies.reach_for_instructions_confirmation_v8.runner": execution_root,
        "harness.bundle": execution_root,
        "assist": assist_source,
        "assist.model_manager": assist_source,
    }
    for name, prefix in prefixes.items():
        path = Path(value["modules"][name]["path"])
        try:
            relative = path.relative_to(prefix.resolve()).as_posix()
        except ValueError as error:
            raise ValueError(f"worker import escaped its clean checkout: {name}") from error
        value["modules"][name]["path"] = relative
    if value["environment"] != {
        "assist_model_url": "http://127.0.0.1:8000/v1",
        "python_no_user_site": "1",
        "python_path": source_path,
        "python_safe_path": "1",
    }:
        raise ValueError("worker environment differs from the exact runtime profile")
    value["environment"]["python_path"] = ["exact-parent-checkout", "exact-assist-checkout"]
    return value


def _server_identity(server_pid: int, model_path: Path, llama_source: Path) -> dict[str, Any]:
    proc = Path("/proc") / str(server_pid)
    try:
        argv = [value.decode() for value in (proc / "cmdline").read_bytes().split(b"\0") if value]
        start_ticks = (proc / "stat").read_text().split()[21]
    except (OSError, UnicodeDecodeError, IndexError) as error:
        raise ValueError("llama server process identity is unavailable") from error
    if not argv:
        raise ValueError("llama server command is empty")
    try:
        if not Path(argv[0]).samefile(proc / "exe"):
            raise ValueError("llama server argv does not identify the running executable")
    except OSError as error:
        raise ValueError("llama server executable identity is unavailable") from error
    normalized = [Path(argv[0]).name]
    model_arguments: list[Path] = []
    index = 1
    while index < len(argv):
        value = argv[index]
        normalized.append(value)
        if value == "--model" and index + 1 < len(argv):
            argument = Path(argv[index + 1])
            model_arguments.append(argument)
            normalized.append(argument.name)
            index += 2
        else:
            index += 1
    if len(model_arguments) != 1:
        raise ValueError("llama server must have exactly one model argument")
    try:
        if not model_arguments[0].samefile(model_path):
            raise ValueError("attested model is not the model loaded by the server")
    except OSError as error:
        raise ValueError("llama server model identity is unavailable") from error
    return {
        "pid": server_pid,
        "start_ticks": start_ticks,
        "argv": normalized,
        "binary_sha256": _sha256(Path(argv[0])),
        "source": _git_identity(llama_source),
        "model": {
            "name": model_path.name,
            "size": model_path.stat().st_size,
            "sha256": _sha256(model_path),
        },
    }


def attest(
    root: Path,
    *,
    execution_root: Path,
    assist_source: Path,
    assist_python: Path,
    workspace_root: Path,
    model_path: Path,
    server_pid: int,
    llama_source: Path,
) -> bytes:
    """Return the invariant non-secret identity used around every batch."""
    manifest = _load_manifest(root)
    registration = _verify_registration(root, manifest)
    execution = _verify_execution(execution_root, manifest)
    assist_identity = _git_identity(assist_source)
    if assist_identity != {
        "commit": manifest["runtime"]["assist_commit"],
        "tree": manifest["runtime"]["assist_tree"],
        "status": "",
    }:
        raise ValueError("Assist runtime differs from registration")
    value = {
        "manifest_sha256": digest(manifest),
        "registration": registration,
        "execution": execution,
        "assist": assist_identity,
        "environment": _environment_identity(
            assist_python=assist_python,
            workspace_root=workspace_root,
            execution_root=execution_root,
            assist_source=assist_source,
        ),
        "server": _server_identity(server_pid, model_path, llama_source),
        "registered_model": manifest["runtime"]["model"],
    }
    expected = manifest["runtime"]["expected_attestation"]
    server_expected = expected["server"]
    server = value["server"]
    for key in ("argv", "binary_sha256", "model"):
        if server[key] != server_expected[key]:
            raise ValueError(f"server identity differs from registration: {key}")
    if server["source"] != server_expected["source"]:
        raise ValueError("llama.cpp source differs from registration")
    environment = value["environment"]
    for key in ("distributions", "environment", "modules", "python"):
        if environment[key] != expected[key]:
            raise ValueError(f"worker {key} differs from registration")
    return canonical_json(value) + b"\n"


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def _quarantine(output: Path, reason: str) -> None:
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write(output / INVALID, canonical_json({"reason": reason, "resume": False}) + b"\n")


def verify_reproduction_seal(capsule: Path, manifest: dict[str, Any]) -> None:
    """Verify the final immutable reproduction evidence inventory."""
    path = capsule / "reproduction-seal.json"
    try:
        seal = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("reproduction seal is missing or malformed") from error
    if not isinstance(seal, dict):
        raise ValueError("reproduction seal is malformed")
    claimed = seal.pop("seal_sha256", None)
    if claimed != digest(seal) or seal.get("manifest_sha256") != digest(manifest):
        raise ValueError("reproduction seal identity differs")
    expected = seal.get("sealed_files")
    if not isinstance(expected, dict):
        raise ValueError("reproduction seal inventory is malformed")
    actual = {
        item.relative_to(capsule).as_posix(): _sha256(item)
        for item in sorted(capsule.rglob("*"))
        if item.is_file() and not item.is_symlink()
        and item.name not in {"learning.md", "assist-roadmap-proposal.md", path.name}
    }
    if any(item.is_symlink() for item in capsule.rglob("*")) or expected != actual:
        raise ValueError("reproduction sealed files differ")


def _true_denial(
    *,
    new_admissions: list[dict[str, Any]],
    new_events: list[dict[str, Any]],
    thread_id: str,
) -> bool:
    denied = [record for record in new_admissions if record.get("admitted") is False]
    if len(denied) != 1 or denied[0] is not new_admissions[-1]:
        return False
    detail = denied[0].get("detail")
    if not isinstance(detail, str) or DENIAL.fullmatch(detail) is None:
        return False
    relevant = [
        event for event in new_events
        if event.get("thread") == thread_id and event.get("resource") == "llm"
        and event.get("event") in {"production_admission_denied", "resource_started", "resource_finished"}
    ]
    events = [event["event"] for event in relevant]
    return events.count("production_admission_denied") == 1 and events[-1:] == [
        "production_admission_denied"
    ]


def _events_match_admissions(
    *,
    new_admissions: list[dict[str, Any]],
    new_outcomes: list[dict[str, Any]],
    new_events: list[dict[str, Any]],
    thread_id: str,
) -> bool:
    """Require one complete shared-resource transaction per admitted episode."""
    relevant = [
        event for event in new_events
        if event.get("thread") == thread_id and event.get("resource") == "llm"
        and event.get("event") in {"production_admission_denied", "resource_started", "resource_finished"}
    ]
    terminal = iter(new_outcomes)
    position = 0
    for admission in new_admissions:
        if admission.get("admitted") is False:
            if position >= len(relevant) or relevant[position]["event"] != "production_admission_denied":
                return False
            position += 1
            continue
        if admission.get("admitted") is not True or position >= len(relevant):
            return False
        if relevant[position]["event"] != "resource_started":
            return False
        position += 1
        try:
            outcome = next(terminal)
        except StopIteration:
            return False
        if position < len(relevant) and relevant[position]["event"] == "resource_finished":
            if not isinstance(relevant[position].get("exit_code"), int):
                return False
            position += 1
        elif outcome.get("outcome") != "timeout":
            return False
    try:
        next(terminal)
    except StopIteration:
        pass
    else:
        return False
    return position == len(relevant)


def _verified_attestation_files(attestations: Path) -> list[Path]:
    """Verify the complete, immutable per-invocation attestation inventory."""
    paths = sorted(attestations.iterdir())
    if not paths:
        raise ValueError("runtime attestations are missing")
    if any(path.is_symlink() or not path.is_file() or path.suffix != ".json" for path in paths):
        raise ValueError("runtime attestation inventory contains an unexpected entry")
    names = {path.name for path in paths}
    invocations = len(paths) // 3
    expected = {
        f"{index:03d}-{suffix}.json"
        for index in range(invocations)
        for suffix in ("events", "identity-after", "identity-before")
    }
    if names != expected:
        raise ValueError("runtime attestation inventory is incomplete or unexpected")
    identity = (attestations / "000-identity-before.json").read_bytes()
    if any(
        path.read_bytes() != identity
        for path in paths
        if "-identity-" in path.name
    ):
        raise ValueError("runtime identity differs across attestations")
    for index in range(invocations):
        events = json.loads((attestations / f"{index:03d}-events.json").read_text())
        if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
            raise ValueError("runtime event attestation is malformed")
    return paths


def _prepare_attestation_directory(attestations: Path) -> None:
    if attestations.is_symlink() or (attestations.exists() and not attestations.is_dir()):
        raise ValueError("runtime attestations must be a real directory")
    attestations.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(attestations.stat().st_mode) != 0o700:
        raise ValueError("runtime attestations must have mode 0700")
    if any(attestations.iterdir()):
        _verified_attestation_files(attestations)


def _fidelity_error(records: list[dict[str, Any]]) -> bool:
    phrases = (
        "provider request capture", "provider request differs", "worker rendered provider request",
        "worker fixture identity", "malformed worker result",
    )
    return any(
        record.get("outcome") == "provider_error"
        and isinstance(record.get("detail"), str)
        and any(phrase in record["detail"] for phrase in phrases)
        for record in records
    )


def run_batch(
    root: Path,
    output: Path,
    attestations: Path,
    *,
    execution_root: Path,
    assist_source: Path,
    assist_python: Path,
    workspace_root: Path,
    model_path: Path,
    server_pid: int,
    llama_source: Path,
    events: Path,
) -> str:
    """Run one inherited bounded invocation or fail closed without reinterpretation."""
    manifest = _load_manifest(root)
    if output.name != manifest["execution"]["output_id"]:
        raise ValueError("raw output ID differs from registration")
    if (output / INVALID).exists():
        raise ValueError("reproduction output is quarantined and cannot resume")
    bundle = StudyBundle.read_verified(execution_root / manifest["parent"]["bundle_path"])
    existing_outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256).read_verified() if output.exists() else []
    remaining = len(bundle.schedule) - len(existing_outcomes)
    if remaining and len(existing_outcomes):
        cooldown = output / "batch-cooldown.json"
        if cooldown.exists():
            try:
                value = json.loads(cooldown.read_text())
            except (OSError, json.JSONDecodeError) as error:
                _quarantine(output, "sealed batch cooldown is malformed")
                raise ValueError("sealed batch cooldown is malformed") from error
            if (
                not isinstance(value, dict)
                or set(value) != {"completed_outcomes", "not_before_unix"}
                or not isinstance(value["completed_outcomes"], int)
                or not isinstance(value["not_before_unix"], (int, float))
                or value["completed_outcomes"] > len(existing_outcomes)
            ):
                _quarantine(output, "sealed batch cooldown differs from run progress")
                raise ValueError("sealed batch cooldown differs from run progress")
            if (
                value["completed_outcomes"] == len(existing_outcomes)
                and value["not_before_unix"] > time.time()
            ):
                return "cooldown"
    _prepare_attestation_directory(attestations)
    before = attest(
        root, execution_root=execution_root, assist_source=assist_source,
        assist_python=assist_python, workspace_root=workspace_root,
        model_path=model_path, server_pid=server_pid, llama_source=llama_source,
    )
    identity_files = sorted(attestations.glob("*-identity-*.json"))
    for prior in identity_files:
        if prior.read_bytes() != before:
            _quarantine(output, "runtime identity differs across attestations")
            raise ValueError("runtime identity differs across attestations")
    label = f"{len(list(attestations.glob('*-identity-before.json'))):03d}"
    atomic_write(attestations / f"{label}-identity-before.json", before)
    if not events.exists() or events.is_symlink():
        _quarantine(output, "coordination event log is unavailable")
        raise ValueError("coordination event log is unavailable")
    prefix = events.read_bytes()
    if prefix and not prefix.endswith(b"\n"):
        _quarantine(output, "coordination event log has an unterminated prefix")
        raise ValueError("coordination event log has an unterminated prefix")
    event_offset = events.stat().st_size
    prior_admissions = _read_records(output / "admissions.jsonl")
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": f"{execution_root}:{assist_source}",
        "PYTHONSAFEPATH": "1",
        "PYTHONNOUSERSITE": "1",
    })
    command = [
        str(assist_python), "-m", "studies.reach_for_instructions_confirmation_v8.runner", "run",
        "--root", str(execution_root), "--output", str(output),
        "--workspace-root", str(workspace_root), "--assist-source", str(assist_source),
        "--assist-python", str(assist_python),
    ]
    result = subprocess.run(command, cwd=workspace_root, env=env, text=True, capture_output=True)
    try:
        after = attest(
            root, execution_root=execution_root, assist_source=assist_source,
            assist_python=assist_python, workspace_root=workspace_root,
            model_path=model_path, server_pid=server_pid, llama_source=llama_source,
        )
        if after != before:
            raise ValueError("runtime identity changed during the bounded invocation")
        atomic_write(attestations / f"{label}-identity-after.json", after)
    except ValueError:
        _quarantine(output, "runtime identity changed during the bounded invocation")
        raise
    if events.stat().st_size < event_offset:
        _quarantine(output, "coordination event log changed non-append-only")
        raise ValueError("coordination event log changed non-append-only")
    complete_events = events.read_bytes()
    event_bytes = complete_events[event_offset:]
    if event_bytes and not event_bytes.endswith(b"\n"):
        _quarantine(output, "coordination event slice has an unterminated record")
        raise ValueError("coordination event slice has an unterminated record")
    try:
        new_events = [json.loads(line) for line in event_bytes.splitlines()]
    except json.JSONDecodeError as error:
        _quarantine(output, "coordination event slice is malformed")
        raise ValueError("coordination event slice is malformed") from error
    thread_id = os.environ.get("CODEX_THREAD_ID", "")
    if thread_id != manifest["execution"]["coordination_thread_id"]:
        _quarantine(output, "execution thread identity differs from registration")
        raise ValueError("execution thread identity differs from registration")
    attested_events = [
        event for event in new_events
        if event.get("thread") == thread_id and event.get("resource") == "llm"
        and event.get("event") in {"production_admission_denied", "resource_started", "resource_finished"}
    ]
    atomic_write(attestations / f"{label}-events.json", canonical_json(attested_events) + b"\n")
    admissions = _read_records(output / "admissions.jsonl")
    new_admissions = admissions[len(prior_admissions):]
    outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256).read_verified()
    new_outcomes = outcomes[len(existing_outcomes):]
    if result.returncode:
        _quarantine(output, "parent runner returned a nonzero status")
        raise ValueError("parent runner failed; reproduction quarantined")
    if _fidelity_error(new_outcomes):
        _quarantine(output, "provider-request fidelity failure")
        raise ValueError("provider-request fidelity failure; fresh reproduction required")
    if not thread_id or not _events_match_admissions(
        new_admissions=new_admissions, new_outcomes=new_outcomes,
        new_events=new_events, thread_id=thread_id
    ):
        _quarantine(output, "shared-resource events do not match admission records")
        raise ValueError("shared-resource event/admission mismatch; reproduction quarantined")
    if any(record.get("admitted") is False for record in new_admissions):
        if not _true_denial(new_admissions=new_admissions, new_events=new_events, thread_id=thread_id):
            _quarantine(output, "ambiguous pre-request failure")
            raise ValueError("ambiguous pre-request failure; reproduction quarantined")
        return "denied"
    expected = min(24, remaining)
    if len(new_outcomes) != expected:
        _quarantine(output, "bounded invocation ended without its registered outcomes")
        raise ValueError("bounded invocation ended early; reproduction quarantined")
    return "complete" if len(outcomes) == len(bundle.schedule) else "batch-complete"


def archive_and_analyze(
    root: Path,
    output: Path,
    capsule: Path,
    analysis_output: Path,
    attestations: Path,
    *,
    execution_root: Path,
    assist_source: Path,
    assist_python: Path,
    workspace_root: Path,
) -> None:
    """Archive the verified parent run, then perform the locked separate analysis."""
    manifest = _load_manifest(root)
    if capsule.name != manifest["execution"]["capsule_id"]:
        raise ValueError("capsule ID differs from registration")
    registered_analysis = capsule / manifest["execution"]["analysis_file"]
    if analysis_output.resolve() != registered_analysis.resolve():
        raise ValueError("analysis output path differs from registration")
    if (output / INVALID).exists():
        raise ValueError("a quarantined reproduction cannot be archived")
    env = os.environ.copy()
    env.update({"PYTHONPATH": f"{execution_root}:{assist_source}", "PYTHONSAFEPATH": "1", "PYTHONNOUSERSITE": "1"})
    command = [
        str(assist_python), "-m", "studies.reach_for_instructions_confirmation_v8.runner", "archive",
        "--root", str(execution_root), "--output", str(output), "--archive", str(capsule),
    ]
    subprocess.run(command, cwd=workspace_root, env=env, check=True)
    historical = root / manifest["historical_comparator"]["capsule"]
    analysis.analyze(manifest, capsule, historical, analysis_output)
    copied_attestations = capsule / "runtime-attestations"
    copied_attestations.mkdir()
    attestation_files = _verified_attestation_files(attestations)
    for source in attestation_files:
        atomic_write(copied_attestations / source.name, source.read_bytes())
    bundle = StudyBundle.read_verified(capsule / "bundle.json")
    admissions = AdmissionLog(capsule / "admissions.jsonl", bundle.sha256).read_verified()
    outcomes = RecordChain(capsule / "outcomes.jsonl", bundle.sha256).read_verified()
    execution_events = [
        event
        for path in sorted(copied_attestations.glob("*-events.json"))
        for event in json.loads(path.read_text())
    ]
    if not _events_match_admissions(
        new_admissions=admissions,
        new_outcomes=outcomes,
        new_events=execution_events,
        thread_id=manifest["execution"]["coordination_thread_id"],
    ):
        raise ValueError("archived shared-resource events do not match the complete run")
    sealed_files = {
        path.relative_to(capsule).as_posix(): _sha256(path)
        for path in sorted(capsule.rglob("*"))
        if path.is_file() and path.name not in {"learning.md", "assist-roadmap-proposal.md"}
    }
    seal = {
        "schema": "reach-v8-exact-reproduction-seal-v1",
        "manifest_sha256": digest(manifest),
        "sealed_files": sealed_files,
    }
    atomic_write(capsule / "reproduction-seal.json", canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n")
    verify_reproduction_seal(capsule, manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run-batch", "archive-analyze"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--assist-repository", type=Path)
    parser.add_argument("--execution-root", type=Path)
    parser.add_argument("--assist-source", type=Path)
    parser.add_argument("--assist-python", type=Path)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--server-pid", type=int)
    parser.add_argument("--llama-source", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--attestations", type=Path)
    parser.add_argument("--capsule", type=Path)
    parser.add_argument("--analysis-output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.runtime_root is None or args.assist_repository is None:
            raise SystemExit("prepare requires --runtime-root and --assist-repository")
        prepare_runtime(args.root, args.assist_repository, args.runtime_root)
        return
    common = (args.execution_root, args.assist_source, args.assist_python, args.workspace_root, args.output)
    if any(value is None for value in common):
        raise SystemExit("command requires execution, Assist, Python, workspace, and output paths")
    if args.command == "run-batch":
        extra = (args.attestations, args.model_path, args.server_pid, args.llama_source, args.events)
        if any(value is None for value in extra):
            raise SystemExit("run-batch requires attestation, model, server, llama, and event inputs")
        print(run_batch(
            args.root, args.output, args.attestations,
            execution_root=args.execution_root, assist_source=args.assist_source,
            assist_python=args.assist_python, workspace_root=args.workspace_root,
            model_path=args.model_path, server_pid=args.server_pid,
            llama_source=args.llama_source, events=args.events,
        ))
    else:
        if args.capsule is None or args.analysis_output is None or args.attestations is None:
            raise SystemExit("archive-analyze requires --capsule, --analysis-output, and --attestations")
        archive_and_analyze(
            args.root, args.output, args.capsule, args.analysis_output, args.attestations,
            execution_root=args.execution_root, assist_source=args.assist_source,
            assist_python=args.assist_python, workspace_root=args.workspace_root,
        )


if __name__ == "__main__":
    main()
