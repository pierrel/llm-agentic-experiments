"""Run an exact V8-r3 reproduction behind additional administrative integrity checks."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import time
from typing import Any

from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from harness.records import AdmissionLog, RecordChain
from studies.reach_for_instructions_confirmation_v8_reproduction import analysis
from studies.reach_for_instructions_confirmation_v8_reproduction.integrity import (
    BATCH_EPISODES,
    DENIAL,
    DENIAL_RETRY_SECONDS,
    events_match_admissions as _events_match_admissions,
    verify_attestation_inventory,
    verify_execution_intervals,
    verify_event_interval as _verify_event_interval,
    verify_records,
)


STUDY = "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r1"
MANIFEST = Path("experiments") / STUDY / "manifest.json"
INVALID = "REPRODUCTION_INVALID.json"
REGISTRATION_TAG = f"{STUDY}"
PUBLICATION_BRANCH = "reach-experiment-reproduction-v2"
PUBLICATION_REMOTE = "https://github.com/pierrel/llm-agentic-experiments.git"
RUNTIME_ROOT_DISTRIBUTIONS = ("deepagents", "langchain-openai")


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


def _canonical_workspace_root(root: Path) -> Path:
    """Locate the one shared workspace from this registered worktree's Git metadata."""
    common = Path(
        _command("git", "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root)
    ).resolve()
    git_directory = next((path for path in (common, *common.parents) if path.name == ".git"), None)
    if git_directory is None:
        raise ValueError("registration checkout is not attached to the shared workspace")
    workspace = git_directory.parent if common != git_directory else git_directory.parent.parent
    gate = workspace / "tools" / "agentic"
    if not gate.is_file() or gate.is_symlink():
        raise ValueError("canonical shared LLM gate is unavailable")
    return workspace.resolve()


def _verify_local_registration(root: Path, manifest: dict[str, Any]) -> dict[str, str]:
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
    return {"commit": commit, "tree": tree, "tag_object": tag_object}


def _verify_publication(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Prove the registered commit and annotated tag were published once."""
    identity = _verify_local_registration(root, manifest)
    registration = manifest["registration"]
    remote = registration["publication_remote"]
    branch = registration["publication_branch"]
    tag = registration["tag"]
    published = _command(
        "git", "ls-remote", remote, f"refs/heads/{branch}", f"refs/tags/{tag}",
        f"refs/tags/{tag}^{{}}", cwd=root,
    ).splitlines()
    refs = {line.split("\t", 1)[1]: line.split("\t", 1)[0] for line in published if "\t" in line}
    if refs.get(f"refs/heads/{branch}") != identity["commit"]:
        raise ValueError("registered commit is not published at the declared branch")
    if (
        refs.get(f"refs/tags/{tag}") != identity["tag_object"]
        or refs.get(f"refs/tags/{tag}^{{}}") != identity["commit"]
    ):
        raise ValueError("published annotated registration tag differs")
    return {
        "manifest_sha256": digest(manifest),
        "publication_branch": branch,
        "publication_remote": remote,
        "registration": identity,
    }


def _read_publication_proof(path: Path, manifest: dict[str, Any], identity: dict[str, str]) -> dict[str, Any]:
    try:
        stored = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("initial publication proof is missing or malformed") from error
    if not isinstance(stored, dict) or set(stored) != {"proof", "sha256"}:
        raise ValueError("initial publication proof shape is invalid")
    proof = stored["proof"]
    if not isinstance(proof, dict) or stored["sha256"] != digest(proof):
        raise ValueError("initial publication proof digest mismatch")
    if proof != {
        "manifest_sha256": digest(manifest),
        "publication_branch": PUBLICATION_BRANCH,
        "publication_remote": PUBLICATION_REMOTE,
        "registration": identity,
    }:
        raise ValueError("initial publication proof differs from registration")
    return proof


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
    proof = _verify_publication(root, manifest)
    runtime_root.mkdir(mode=0o700, parents=True)
    atomic_write(runtime_root / "publication.json", canonical_json({"proof": proof, "sha256": digest(proof)}) + b"\n")
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
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
roots = __RUNTIME_ROOT_DISTRIBUTIONS__
distributions = {}
pending = list(roots)
while pending:
    name = canonicalize_name(pending.pop())
    if name in distributions:
        continue
    dist = importlib.metadata.distribution(name)
    actual_name = canonicalize_name(dist.metadata["Name"])
    if actual_name != name:
        raise RuntimeError(f"distribution identity mismatch for {name}")
    record = next((path for path in dist.files or () if str(path).endswith(".dist-info/RECORD")), None)
    if record is None:
        raise RuntimeError(f"missing RECORD for {name}")
    record_path = pathlib.Path(dist.locate_file(record))
    verified = []
    with record_path.open(newline="") as source:
        for relative, encoded, _size in csv.reader(source):
            path = pathlib.Path(dist.locate_file(relative))
            actual_digest = hashlib.sha256(path.read_bytes()).digest()
            if encoded:
                algorithm, value = encoded.split("=", 1)
                actual = base64.urlsafe_b64encode(actual_digest).rstrip(b"=").decode()
                if algorithm != "sha256" or actual != value:
                    raise RuntimeError(f"installed file differs from RECORD: {name}:{relative}")
            verified.append((relative, actual_digest.hex()))
    distributions[name] = {
        "version": dist.version,
        "record_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
        "verified_files_sha256": hashlib.sha256(json.dumps(sorted(verified), separators=(",", ":")).encode()).hexdigest(),
    }
    for raw in dist.requires or ():
        requirement = Requirement(raw)
        if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
            pending.append(requirement.name)
distribution_identity = json.dumps(distributions, sort_keys=True, separators=(",", ":")).encode()
modules = {}
for name in ("studies.reach_for_instructions_confirmation_v8.runner", "harness.bundle", "assist", "assist.model_manager"):
    module = importlib.import_module(name)
    path = pathlib.Path(module.__file__).resolve()
    modules[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
python = pathlib.Path(sys.executable).resolve()
print(json.dumps({
    "distributions": {
        "closure_sha256": hashlib.sha256(distribution_identity).hexdigest(),
        "packages": sorted(distributions),
        "roots": list(roots),
    },
    "environment": {
        "assist_model_url": os.environ.get("ASSIST_MODEL_URL"),
        "python_no_user_site": os.environ.get("PYTHONNOUSERSITE"),
        "python_path": os.environ.get("PYTHONPATH"),
        "python_safe_path": os.environ.get("PYTHONSAFEPATH"),
    },
    "modules": modules,
    "python": {"version": sys.version, "sha256": hashlib.sha256(python.read_bytes()).hexdigest()},
}, sort_keys=True, separators=(",", ":")))
'''.replace("__RUNTIME_ROOT_DISTRIBUTIONS__", repr(RUNTIME_ROOT_DISTRIBUTIONS))


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
    executable = proc / "exe"
    argv_executable = Path(argv[0])
    try:
        resolved_executable = executable.resolve(strict=True)
        if argv_executable.is_absolute() and not argv_executable.samefile(executable):
            raise ValueError("llama server argv does not identify the running executable")
    except OSError as error:
        raise ValueError("llama server executable identity is unavailable") from error
    if argv_executable.name != resolved_executable.name:
        raise ValueError("llama server argv basename differs from its executable")
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
        "binary_sha256": _sha256(executable),
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
    registration = _verify_local_registration(root, manifest)
    publication = _read_publication_proof(execution_root.parent / "publication.json", manifest, registration)
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
        "publication": publication,
        "registration": registration,
        "execution": execution,
        "assist": assist_identity,
        "environment": _environment_identity(
            assist_python=assist_python,
            workspace_root=workspace_root,
            execution_root=execution_root,
            assist_source=assist_source,
        ),
        "shared_gate": {"sha256": _sha256(workspace_root / "tools" / "agentic")},
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
    if value["shared_gate"] != expected["shared_gate"]:
        raise ValueError("shared LLM admission gate differs from registration")
    return canonical_json(value) + b"\n"


def _quarantine(output: Path, reason: str) -> None:
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError("unsafe reproduction output cannot be quarantined")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(output.stat().st_mode) != 0o700:
        raise ValueError("reproduction output must have mode 0700")
    atomic_write(output / INVALID, canonical_json({"reason": reason, "resume": False}) + b"\n")


@contextmanager
def _wrapper_lock(output: Path):
    """Serialize the full administrative wrapper without deadlocking its child."""
    parent = output.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("reproduction output parent must be a real directory")
    lock = parent / f".{output.name}.reproduction.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        mode = stat.S_IMODE(metadata.st_mode)
        if not stat.S_ISREG(metadata.st_mode) or mode != 0o600:
            raise ValueError("reproduction wrapper lock must be a mode-0600 file")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("another reproduction wrapper invocation is active") from error
        yield
    finally:
        os.close(descriptor)


def _verified_progress(
    output: Path, bundle: StudyBundle
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verify that persisted admissions and outcomes retain one schedule prefix."""
    admissions = AdmissionLog(output / "admissions.jsonl", bundle.sha256)
    outcomes = RecordChain(output / "outcomes.jsonl", bundle.sha256).read_verified()
    admission_records = admissions.read_verified()
    verify_records(bundle.schedule, admission_records, outcomes)
    index = admissions.progress_index(bundle.schedule)
    admitted = [record["trial_sha256"] for record in admission_records if record["admitted"]]
    completed = [record["trial_sha256"] for record in outcomes]
    if index != len(outcomes) or admitted != completed or len(outcomes) > len(bundle.schedule):
        raise ValueError("persisted reproduction progress differs from the schedule")
    return admission_records, outcomes


def _denial_retry_not_before(
    output: Path, admissions: list[dict[str, Any]]
) -> float | int | None:
    """Validate and return the latest still-applicable denial boundary."""
    path = output / "denial-cooldown.json"
    if not path.exists():
        if admissions and admissions[-1].get("admitted") is False:
            raise ValueError("production-denial cooldown is missing")
        return None
    try:
        record = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("production-denial cooldown is malformed") from error
    if (
        not isinstance(record, dict)
        or set(record) != {"admission_count", "not_before_unix", "trial_sha256"}
        or not isinstance(record["admission_count"], int)
        or isinstance(record["admission_count"], bool)
        or not isinstance(record["not_before_unix"], (int, float))
        or isinstance(record["not_before_unix"], bool)
        or not math.isfinite(record["not_before_unix"])
        or not isinstance(record["trial_sha256"], str)
        or not 1 <= record["admission_count"] <= len(admissions)
    ):
        raise ValueError("production-denial cooldown is malformed")
    denial = admissions[record["admission_count"] - 1]
    if denial.get("admitted") is not False or denial.get("trial_sha256") != record["trial_sha256"]:
        raise ValueError("production-denial cooldown differs from admissions")
    if record["admission_count"] == len(admissions):
        return record["not_before_unix"]
    return None


def verify_reproduction_seal(capsule: Path, manifest: dict[str, Any]) -> None:
    """Verify the final immutable reproduction evidence inventory."""
    if capsule.is_symlink() or not capsule.is_dir():
        raise ValueError("reproduction capsule must be a real directory")
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


def _prepare_attestation_directory(
    attestations: Path,
    *,
    manifest: dict[str, Any],
    registration: dict[str, str],
) -> list[dict[str, Any]]:
    if attestations.is_symlink() or (attestations.exists() and not attestations.is_dir()):
        raise ValueError("runtime attestations must be a real directory")
    attestations.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(attestations.stat().st_mode) != 0o700:
        raise ValueError("runtime attestations must have mode 0700")
    if any(attestations.iterdir()):
        _, intervals = verify_attestation_inventory(
            attestations, manifest=manifest, registration=registration
        )
        return intervals
    return []


def _read_appended_events(events: Path, prefix: bytes) -> list[dict[str, Any]]:
    """Read only complete event records appended to an unchanged exact prefix."""
    complete = events.read_bytes()
    if complete[:len(prefix)] != prefix:
        raise ValueError("coordination event log changed non-append-only")
    appended = complete[len(prefix):]
    if appended and not appended.endswith(b"\n"):
        raise ValueError("coordination event slice has an unterminated record")
    try:
        records = [json.loads(line) for line in appended.splitlines()]
    except json.JSONDecodeError as error:
        raise ValueError("coordination event slice is malformed") from error
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("coordination event slice is malformed")
    return records


def _time_bound() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_parent(
    command: list[str], *, cwd: Path, env: dict[str, str], output: Path
) -> subprocess.CompletedProcess[str]:
    """Run the exact parent and quarantine even when the wrapper is interrupted."""
    try:
        return subprocess.run(
            command, cwd=cwd, env=env, text=True, capture_output=True
        )
    except BaseException as error:
        _quarantine(output, "parent runner could not be launched or was interrupted")
        if not isinstance(error, Exception):
            raise
        raise ValueError("parent runner could not be launched") from error


def _read_batch_cooldown(path: Path) -> dict[str, int | float]:
    """Read the exact inherited batch-cooldown record shape."""
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("sealed batch cooldown is missing or malformed") from error
    if (
        not isinstance(value, dict)
        or set(value) != {"completed_outcomes", "not_before_unix"}
        or not isinstance(value["completed_outcomes"], int)
        or isinstance(value["completed_outcomes"], bool)
        or value["completed_outcomes"] < 0
        or not isinstance(value["not_before_unix"], (int, float))
        or isinstance(value["not_before_unix"], bool)
        or not math.isfinite(value["not_before_unix"])
    ):
        raise ValueError("sealed batch cooldown is missing or malformed")
    return value


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


def _verify_run_scope(
    root: Path, output: Path, workspace_root: Path, events: Path
) -> dict[str, Any]:
    """Validate all caller-selected paths before creating the wrapper lock."""
    manifest = _load_manifest(root)
    if output.name != manifest["execution"]["output_id"]:
        raise ValueError("raw output ID differs from registration")
    if os.environ.get("CODEX_THREAD_ID", "") != manifest["execution"]["coordination_thread_id"]:
        raise ValueError("execution thread identity differs from registration")
    if workspace_root.resolve() != _canonical_workspace_root(root):
        raise ValueError("worker workspace differs from the canonical shared workspace")
    if events.resolve() != (workspace_root / ".coordination" / "events.jsonl").resolve():
        raise ValueError("coordination event log path differs from the shared gate")
    return manifest


def _run_batch_locked(
    root: Path,
    output: Path,
    attestations: Path,
    *,
    manifest: dict[str, Any],
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
    thread_id = manifest["execution"]["coordination_thread_id"]
    registration = _verify_local_registration(root, manifest)
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError("reproduction output must be a real directory")
    if output.exists() and stat.S_IMODE(output.stat().st_mode) != 0o700:
        raise ValueError("reproduction output must have mode 0700")
    if (output / INVALID).exists():
        raise ValueError("reproduction output is quarantined and cannot resume")
    try:
        bundle = StudyBundle.read_verified(execution_root / manifest["parent"]["bundle_path"])
        prior_admissions, existing_outcomes = _verified_progress(output, bundle)
        denial_not_before = _denial_retry_not_before(output, prior_admissions)
    except Exception as error:
        _quarantine(output, "persisted reproduction progress is invalid")
        raise ValueError("persisted reproduction progress is invalid") from error
    remaining = len(bundle.schedule) - len(existing_outcomes)
    try:
        prior_intervals = _prepare_attestation_directory(
            attestations, manifest=manifest, registration=registration
        )
        if prior_intervals:
            verify_execution_intervals(
                prior_intervals,
                admissions=prior_admissions,
                outcomes=existing_outcomes,
                thread_id=thread_id,
                schedule_size=len(bundle.schedule),
            )
        batch_intervals = [
            interval for interval in prior_intervals
            if interval["next_batch_not_before_unix"] is not None
        ]
        attested_batch_not_before = (
            batch_intervals[-1]["next_batch_not_before_unix"] if batch_intervals else None
        )
        attested_batch_mtime_ns = (
            batch_intervals[-1]["batch_cooldown_mtime_ns"] if batch_intervals else None
        )
        attested_batch_boundary = (
            batch_intervals[-1]["outcomes_after"] if batch_intervals else 0
        )
        cooldown = output / "batch-cooldown.json"
        if not attested_batch_boundary and cooldown.exists():
            raise ValueError("sealed batch cooldown exists before a batch boundary")
        batch_file_not_before: float | int | None = None
        batch_file_mtime_ns: int | None = None
        if attested_batch_boundary:
            value = _read_batch_cooldown(cooldown)
            if (
                value["completed_outcomes"] != attested_batch_boundary
            ):
                raise ValueError("sealed batch cooldown differs from run progress")
            batch_file_not_before = value["not_before_unix"]
            batch_file_mtime_ns = cooldown.stat().st_mtime_ns
        attested_denial_not_before = (
            prior_intervals[-1]["next_denial_not_before_unix"] if prior_intervals else None
        )
        if batch_file_not_before != attested_batch_not_before:
            raise ValueError("sealed batch cooldown differs from its attestation")
        if batch_file_mtime_ns != attested_batch_mtime_ns:
            raise ValueError("sealed batch cooldown timestamp differs from its attestation")
        if denial_not_before != attested_denial_not_before:
            raise ValueError("production-denial cooldown differs from its attestation")
        now = time.time()
        if attested_denial_not_before is not None and now < attested_denial_not_before:
            return "denial-cooldown"
        if (
            prior_intervals
            and batch_intervals
            and prior_intervals[-1] is batch_intervals[-1]
            and attested_batch_not_before is not None
            and now < attested_batch_not_before
        ):
            return "cooldown"
        before = attest(
            root, execution_root=execution_root, assist_source=assist_source,
            assist_python=assist_python, workspace_root=workspace_root,
            model_path=model_path, server_pid=server_pid, llama_source=llama_source,
        )
        identity_files = sorted(attestations.glob("*-identity-*.json"))
        if any(prior.read_bytes() != before for prior in identity_files):
            raise ValueError("runtime identity differs across attestations")
        label = f"{len(list(attestations.glob('*-identity-before.json'))):03d}"
        atomic_write(attestations / f"{label}-identity-before.json", before)
    except Exception as error:
        _quarantine(output, "pre-invocation runtime attestation failed")
        raise ValueError("pre-invocation runtime attestation failed") from error
    if not events.exists() or events.is_symlink():
        _quarantine(output, "coordination event log is unavailable")
        raise ValueError("coordination event log is unavailable")
    try:
        prefix = events.read_bytes()
    except OSError as error:
        _quarantine(output, "coordination event log is unavailable")
        raise ValueError("coordination event log is unavailable") from error
    if prefix and not prefix.endswith(b"\n"):
        _quarantine(output, "coordination event log has an unterminated prefix")
        raise ValueError("coordination event log has an unterminated prefix")
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
    started_at = _time_bound()
    result = _run_parent(command, cwd=workspace_root, env=env, output=output)
    finished_at = _time_bound()
    try:
        after = attest(
            root, execution_root=execution_root, assist_source=assist_source,
            assist_python=assist_python, workspace_root=workspace_root,
            model_path=model_path, server_pid=server_pid, llama_source=llama_source,
        )
        if after != before:
            raise ValueError("runtime identity changed during the bounded invocation")
        atomic_write(attestations / f"{label}-identity-after.json", after)
    except Exception:
        _quarantine(output, "runtime identity changed during the bounded invocation")
        raise
    try:
        new_events = _read_appended_events(events, prefix)
    except (OSError, ValueError) as error:
        _quarantine(output, str(error))
        raise
    try:
        admissions, outcomes = _verified_progress(output, bundle)
    except Exception as error:
        _quarantine(output, "persisted reproduction progress became invalid")
        raise ValueError("persisted reproduction progress became invalid") from error
    new_admissions = admissions[len(prior_admissions):]
    new_outcomes = outcomes[len(existing_outcomes):]
    if result.returncode:
        _quarantine(output, "parent runner returned a nonzero status")
        raise ValueError("parent runner failed; reproduction quarantined")
    if _fidelity_error(new_outcomes):
        _quarantine(output, "provider-request fidelity failure")
        raise ValueError("provider-request fidelity failure; fresh reproduction required")
    next_batch_not_before: float | int | None = None
    batch_cooldown_mtime_ns: int | None = None
    if len(new_outcomes) == BATCH_EPISODES and len(outcomes) < len(bundle.schedule):
        batch_cooldown_path = output / "batch-cooldown.json"
        try:
            batch_cooldown = _read_batch_cooldown(batch_cooldown_path)
            batch_cooldown_mtime_ns = batch_cooldown_path.stat().st_mtime_ns
        except (OSError, ValueError) as error:
            _quarantine(output, "sealed batch cooldown is missing or malformed")
            raise ValueError("sealed batch cooldown is missing or malformed") from error
        if (
            batch_cooldown["completed_outcomes"] != len(outcomes)
        ):
            _quarantine(output, "sealed batch cooldown differs from run progress")
            raise ValueError("sealed batch cooldown differs from run progress")
        next_batch_not_before = batch_cooldown["not_before_unix"]
    denied = any(record.get("admitted") is False for record in new_admissions)
    next_denial_not_before: float | int | None = None
    if denied:
        if not _true_denial(
            new_admissions=new_admissions, new_events=new_events, thread_id=thread_id
        ):
            _quarantine(output, "ambiguous pre-request failure")
            raise ValueError("ambiguous pre-request failure; reproduction quarantined")
        next_denial_not_before = time.time() + DENIAL_RETRY_SECONDS
        denial = new_admissions[-1]
        cooldown = {
            "admission_count": len(admissions),
            "not_before_unix": next_denial_not_before,
            "trial_sha256": denial["trial_sha256"],
        }
        try:
            atomic_write(output / "denial-cooldown.json", canonical_json(cooldown) + b"\n")
        except Exception as error:
            _quarantine(output, "production-denial cooldown could not be recorded")
            raise ValueError("production-denial cooldown could not be recorded") from error
    attested_events = [
        event for event in new_events
        if event.get("thread") == thread_id and event.get("resource") == "llm"
        and event.get("event") in {"production_admission_denied", "resource_started", "resource_finished"}
    ]
    interval = {
        "admissions_after": len(admissions),
        "admissions_before": len(prior_admissions),
        "batch_cooldown_mtime_ns": batch_cooldown_mtime_ns,
        "events": attested_events,
        "finished_at": finished_at,
        "next_batch_not_before_unix": next_batch_not_before,
        "next_denial_not_before_unix": next_denial_not_before,
        "outcomes_after": len(outcomes),
        "outcomes_before": len(existing_outcomes),
        "started_at": started_at,
    }
    try:
        _verify_event_interval(interval)
        atomic_write(attestations / f"{label}-events.json", canonical_json(interval) + b"\n")
        _, complete_intervals = verify_attestation_inventory(
            attestations, manifest=manifest, registration=registration
        )
        verify_execution_intervals(
            complete_intervals,
            admissions=admissions,
            outcomes=outcomes,
            thread_id=thread_id,
            schedule_size=len(bundle.schedule),
        )
    except Exception as error:
        _quarantine(output, "runtime event attestation failed")
        raise ValueError("runtime event attestation failed") from error
    if denied:
        return "denied"
    expected = min(BATCH_EPISODES, remaining)
    if len(new_outcomes) != expected:
        _quarantine(output, "bounded invocation ended without its registered outcomes")
        raise ValueError("bounded invocation ended early; reproduction quarantined")
    return "complete" if len(outcomes) == len(bundle.schedule) else "batch-complete"


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
    """Serialize and run one inherited bounded invocation."""
    manifest = _verify_run_scope(root, output, workspace_root, events)
    with _wrapper_lock(output):
        try:
            return _run_batch_locked(
                root,
                output,
                attestations,
                manifest=manifest,
                execution_root=execution_root,
                assist_source=assist_source,
                assist_python=assist_python,
                workspace_root=workspace_root,
                model_path=model_path,
                server_pid=server_pid,
                llama_source=llama_source,
                events=events,
            )
        except BaseException as error:
            if not isinstance(error, Exception):
                _quarantine(output, "reproduction wrapper was interrupted")
            raise


def _verify_archive_runtime(
    *,
    manifest: dict[str, Any],
    registration: dict[str, str],
    execution_root: Path,
    assist_source: Path,
    assist_python: Path,
    workspace_root: Path,
) -> None:
    """Re-establish trusted code and interpreter identity before archival."""
    _read_publication_proof(
        execution_root.parent / "publication.json", manifest, registration
    )
    _verify_execution(execution_root, manifest)
    if _git_identity(assist_source) != {
        "commit": manifest["runtime"]["assist_commit"],
        "tree": manifest["runtime"]["assist_tree"],
        "status": "",
    }:
        raise ValueError("Assist archive runtime differs from registration")
    environment = _environment_identity(
        assist_python=assist_python,
        workspace_root=workspace_root,
        execution_root=execution_root,
        assist_source=assist_source,
    )
    expected = manifest["runtime"]["expected_attestation"]
    for key in ("distributions", "environment", "modules", "python"):
        if environment[key] != expected[key]:
            raise ValueError(f"archive worker {key} differs from registration")
    if _sha256(workspace_root / "tools" / "agentic") != expected["shared_gate"]["sha256"]:
        raise ValueError("shared LLM gate differs before archival")


def _archive_and_analyze_locked(
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
    """Archive the verified reproduction, then perform the locked separate analysis."""
    manifest = _load_manifest(root)
    if workspace_root.resolve() != _canonical_workspace_root(root):
        raise ValueError("archive workspace differs from the canonical shared workspace")
    registration = _verify_local_registration(root, manifest)
    _verify_archive_runtime(
        manifest=manifest,
        registration=registration,
        execution_root=execution_root,
        assist_source=assist_source,
        assist_python=assist_python,
        workspace_root=workspace_root,
    )
    if capsule.name != manifest["execution"]["capsule_id"]:
        raise ValueError("capsule ID differs from registration")
    registered_analysis = capsule / manifest["execution"]["analysis_file"]
    if analysis_output.resolve() != registered_analysis.resolve():
        raise ValueError("analysis output path differs from registration")
    if os.environ.get("CODEX_THREAD_ID") != manifest["execution"]["coordination_thread_id"]:
        raise ValueError("archive coordinator identity differs from registration")
    if (output / INVALID).exists():
        raise ValueError("a quarantined reproduction cannot be archived")
    attestation_files, intervals = verify_attestation_inventory(
        attestations, manifest=manifest, registration=registration
    )
    bundle = StudyBundle.read_verified(output / "bundle.json")
    admissions, outcomes = _verified_progress(output, bundle)
    if len(outcomes) != len(bundle.schedule):
        raise ValueError("incomplete reproduction cannot be archived")
    execution_events = verify_execution_intervals(
        intervals,
        admissions=admissions,
        outcomes=outcomes,
        thread_id=manifest["execution"]["coordination_thread_id"],
        schedule_size=len(bundle.schedule),
    )
    env = os.environ.copy()
    env.update({"PYTHONPATH": f"{execution_root}:{assist_source}", "PYTHONSAFEPATH": "1", "PYTHONNOUSERSITE": "1"})
    command = [
        str(assist_python), "-m", "studies.reach_for_instructions_confirmation_v8.runner", "archive",
        "--root", str(execution_root), "--output", str(output), "--archive", str(capsule),
    ]
    subprocess.run(command, cwd=workspace_root, env=env, check=True)
    copied_attestations = capsule / "runtime-attestations"
    copied_attestations.mkdir()
    for source in attestation_files:
        atomic_write(copied_attestations / source.name, source.read_bytes())
    witness = {
        "admission_count": len(admissions),
        "admissions_file_sha256": _sha256(capsule / "admissions.jsonl"),
        "event_count": len(execution_events),
        "events_sha256": digest(execution_events),
        "outcome_count": len(outcomes),
        "outcomes_file_sha256": _sha256(capsule / "outcomes.jsonl"),
    }
    provenance = {
        "attestation_files": {source.name: _sha256(source) for source in attestation_files},
        "capsule_run_sha256": _sha256(capsule / "run.json"),
        "coordination_thread_id": manifest["execution"]["coordination_thread_id"],
        "execution_witness": witness,
        "manifest_sha256": digest(manifest),
        "registration": registration,
        "schema": "reach-v8-exact-reproduction-provenance-v1",
    }
    atomic_write(
        capsule / "reproduction-provenance.json",
        canonical_json(provenance | {"record_sha256": digest(provenance)}) + b"\n",
    )
    historical = root / manifest["historical_comparator"]["capsule"]
    analysis.analyze(manifest, capsule, historical, analysis_output, registration)
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
    """Serialize archival and permanently quarantine integrity failures."""
    manifest = _load_manifest(root)
    if output.name != manifest["execution"]["output_id"]:
        raise ValueError("raw output ID differs from registration")
    if capsule.name != manifest["execution"]["capsule_id"]:
        raise ValueError("capsule ID differs from registration")
    if analysis_output.resolve() != (
        capsule / manifest["execution"]["analysis_file"]
    ).resolve():
        raise ValueError("analysis output path differs from registration")
    if os.environ.get("CODEX_THREAD_ID") != manifest["execution"]["coordination_thread_id"]:
        raise ValueError("archive coordinator identity differs from registration")
    if workspace_root.resolve() != _canonical_workspace_root(root):
        raise ValueError("archive workspace differs from the canonical shared workspace")
    with _wrapper_lock(output):
        if (output / INVALID).exists():
            raise ValueError("a quarantined reproduction cannot be archived")
        try:
            if capsule.exists():
                verify_reproduction_seal(capsule, manifest)
                registration = _verify_local_registration(root, manifest)
                analysis.verify_existing_analysis(
                    manifest,
                    capsule,
                    root / manifest["historical_comparator"]["capsule"],
                    analysis_output,
                    registration,
                )
                return
            _archive_and_analyze_locked(
                root,
                output,
                capsule,
                analysis_output,
                attestations,
                execution_root=execution_root,
                assist_source=assist_source,
                assist_python=assist_python,
                workspace_root=workspace_root,
            )
        except Exception as error:
            _quarantine(output, "archive or analysis integrity failed")
            raise ValueError("archive or analysis integrity failed; reproduction quarantined") from error


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
