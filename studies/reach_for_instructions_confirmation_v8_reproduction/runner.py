"""Run an exact V8-r3 reproduction behind additional administrative integrity checks."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import math
import os
from pathlib import Path
import pwd
import re
import select
import shutil
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PYTHON = Path("/usr/bin/python3.14")
_CLEAN_ENTRYPOINT = "REACH_REPRODUCTION_CLEAN_ENTRYPOINT"


def _clean_entrypoint_environment() -> dict[str, str]:
    """Return the complete environment for the fixed wrapper interpreter."""
    return {
        "CODEX_THREAD_ID": os.environ.get("CODEX_THREAD_ID", ""),
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(SOURCE_ROOT),
        "PYTHONSAFEPATH": "1",
        _CLEAN_ENTRYPOINT: "1",
    }


def _verify_system_python_ownership() -> None:
    """Require the fixed interpreter to remain a root-owned system executable."""
    try:
        metadata = SYSTEM_PYTHON.stat()
    except OSError as error:
        raise ValueError("fixed reproduction interpreter is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise ValueError("fixed reproduction interpreter ownership differs")


def _ensure_clean_entrypoint() -> None:
    """Re-exec the CLI before importing any experiment or dependency module."""
    try:
        _verify_system_python_ownership()
    except ValueError as error:
        raise SystemExit(str(error)) from error
    environment = _clean_entrypoint_environment()
    if os.environ.get(_CLEAN_ENTRYPOINT) == "1":
        try:
            executable = Path(sys.executable).resolve(strict=True)
        except OSError as error:
            raise SystemExit("fixed reproduction interpreter is unavailable") from error
        if (
            executable != SYSTEM_PYTHON
            or not sys.flags.no_site
            or dict(os.environ) != environment
        ):
            raise SystemExit("reproduction entrypoint environment differs")
        return
    os.execve(
        str(SYSTEM_PYTHON),
        [str(SYSTEM_PYTHON), "-S", str(Path(__file__).resolve()), *sys.argv[1:]],
        environment,
    )
    raise SystemExit("fixed reproduction re-exec unexpectedly returned")


if __name__ == "__main__":
    _ensure_clean_entrypoint()


from harness.bundle import StudyBundle, atomic_write, canonical_json, digest
from harness.records import AdmissionLog, RecordChain
from studies.reach_for_instructions_confirmation_v8_reproduction import analysis
from studies.reach_for_instructions_confirmation_v8_reproduction.integrity import (
    BATCH_EPISODES,
    DENIAL,
    DENIAL_RETRY_SECONDS,
    strict_json_lines,
    strict_json_loads,
    verify_attestation_inventory,
    verify_execution_intervals,
    verify_records,
)


STUDY = "reach-for-instructions-confirmation-v8-qwen38-current-r3-reproduction-r3"
MANIFEST = Path("experiments") / STUDY / "manifest.json"
INVALID = "REPRODUCTION_INVALID.json"
REGISTRATION_TAG = f"{STUDY}"
PUBLICATION_BRANCH = "reach-experiment-reproduction-v3"
PUBLICATION_REMOTE = "https://github.com/pierrel/llm-agentic-experiments.git"
COORDINATION_THREAD_ID = "01a04877-df08-7401-aeb5-91fdee52c9b0"
RUNTIME_RELATIVE = Path(".coordination") / STUDY
RUNTIME_ROOT_DISTRIBUTIONS = ("deepagents", "langchain-openai")
HASH_CHUNK_BYTES = 1024 * 1024
EVENT_READ_BYTES = 64 * 1024
EVENT_RECORD_BYTES = 1024 * 1024
EVENT_SLICE_BYTES = 16 * 1024 * 1024
EVENT_SLICE_RECORDS = 16 * 1024
MAX_ATTESTED_EVENTS = 2 * BATCH_EPISODES
MODEL_LISTENER = "0100007F:1F40"
GIT_BINARY = "/usr/bin/git"
CANONICAL_GIT_COMMON_SHA256 = "4ec5804c9e8fe8ab2ce302ffcee710702e46712c98b1852ddffaaf4a2f87a352"
CANONICAL_WORKSPACE_SHA256 = "20019c25d374d76060ac0b3b62eb95e4a0703fc69135092b70f444c7cc18f3d1"
BATCH_SCOPE_TIMEOUT_SECONDS = 18_000
ARCHIVE_SCOPE_TIMEOUT_SECONDS = 900
INTEGRITY_COMMAND_TIMEOUT_SECONDS = 900
SYSTEM_COMMAND_TIMEOUT_SECONDS = 10
COMMAND_REAP_TIMEOUT_SECONDS = 10
ASSIST_SITE_PACKAGES_RELATIVE = Path(
    "deploy/assist/code/.venv/lib/python3.14/site-packages"
)
CANONICAL_ASSIST_SITE_PACKAGES_SHA256 = (
    "be8f93081203b389ed84a4213f6e98f019638c1c9cd275e6be6fd7384571c4d0"
)
CANONICAL_PYTHON_PATH_SHA256 = (
    "c03c93ec8cafc307d5de617b0988d1c401bf0aae3f19e8b03174a9bc0f3cb5d7"
)
PYTHON_LAUNCHER = b'''#!/bin/sh
test -n "${REACH_REPRODUCTION_SITE_PACKAGES-}" || exit 126
case ":${PYTHONPATH-}:" in
  *":${REACH_REPRODUCTION_SITE_PACKAGES}:"*) ;;
  *) PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${REACH_REPRODUCTION_SITE_PACKAGES}" ;;
esac
export PYTHONPATH
exec /usr/bin/python3.14 -S "$@"
'''
PYTHON_LAUNCHER_SHA256 = (
    "6404791c0db83b83b9b054ff5c8f4e663b6c0c024d1919a1ed4bc82a64014284"
)
REQUIRED_REVIEW_MODELS = {
    "harness-integrity": "gpt-5.6-terra",
    "minimum-adequate-setup": "gpt-5.6-terra",
    "scientific-validity": "gpt-5.6-terra",
    "statistical-validity": "gpt-5.6-terra",
    "design-final": "gpt-5.6-sol",
}
SAFE_GIT_ENVIRONMENT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_COUNT": "3",
    "GIT_CONFIG_KEY_0": "core.fsmonitor",
    "GIT_CONFIG_VALUE_0": "false",
    "GIT_CONFIG_KEY_1": "core.untrackedCache",
    "GIT_CONFIG_VALUE_1": "false",
    "GIT_CONFIG_KEY_2": "core.hooksPath",
    "GIT_CONFIG_VALUE_2": "/dev/null",
}

# systemd-run contracts each $$ pair before the shell expands the remainder to its PID.
_SCOPE_BOOTSTRAP = (
    'ready="$1"; release="$2"; shift 2; printf "R %s\\n" "$$$$" >&"$ready"; '
    'IFS= read -r token <&"$release" && [ "$token" = R ] || exit 125; '
    'exec "$@"'
)


def _sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(HASH_CHUNK_BYTES):
            value.update(chunk)
    return value.hexdigest()


def _verify_no_symlink_components(label: str, path: Path, base: Path) -> None:
    """Reject symlinks in every lexical path component below a trusted base."""
    base_path = Path(os.path.abspath(base))
    candidate_path = Path(os.path.abspath(path))
    try:
        relative = candidate_path.relative_to(base_path)
    except ValueError as error:
        raise ValueError(f"{label} escapes its trusted base") from error
    candidate = base_path
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            raise ValueError(f"{label} contains a symlinked path component")


def _git_environment() -> dict[str, str]:
    """Return a fixed Git environment without caller-controlled loader or config state."""
    env = {
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
    }
    env.update(SAFE_GIT_ENVIRONMENT)
    return env


def _system_environment() -> dict[str, str]:
    """Return the minimal environment required by local systemd metadata commands."""
    uid = os.getuid()
    return {
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{uid}/bus",
        "HOME": pwd.getpwuid(uid).pw_dir,
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "XDG_RUNTIME_DIR": f"/run/user/{uid}",
    }


def _run_integrity_command(
    command: tuple[str, ...] | list[str], *, cwd: Path | None = None,
    env: dict[str, str] | None = None, text: bool = False, check: bool = False,
    timeout_seconds: int = INTEGRITY_COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[Any]:
    """Run a preparatory command with a hard deadline for its whole process group."""
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        text=text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except BaseException as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=COMMAND_REAP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as reap_error:
            raise RuntimeError("integrity command process group could not be reaped") from reap_error
        if isinstance(error, subprocess.TimeoutExpired):
            raise ValueError("integrity command exceeded its fixed deadline") from error
        raise
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if check and result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode, command, output=stdout, stderr=stderr
        )
    return result


def _command(*arguments: str, cwd: Path | None = None) -> str:
    command = (
        (GIT_BINARY, *arguments[1:])
        if Path(arguments[0]).name == "git"
        else arguments
    )
    result = _run_integrity_command(
        command,
        cwd=cwd,
        env=_git_environment() if command[0] == GIT_BINARY else None,
        text=True,
    )
    if result.returncode:
        raise ValueError(f"command failed: {Path(arguments[0]).name}")
    return result.stdout.strip()


def _load_manifest(root: Path) -> dict[str, Any]:
    path = root / MANIFEST
    try:
        stored = strict_json_loads(path.read_bytes())
    except (OSError, ValueError) as error:
        raise ValueError("reproduction manifest is missing or malformed") from error
    if not isinstance(stored, dict) or set(stored) != {"manifest", "sha256"}:
        raise ValueError("reproduction manifest shape is invalid")
    manifest = stored["manifest"]
    if not isinstance(manifest, dict) or stored["sha256"] != digest(manifest):
        raise ValueError("reproduction manifest digest mismatch")
    if manifest.get("study_id") != STUDY:
        raise ValueError("reproduction manifest study identity mismatch")
    if manifest.get("execution") != {
        "analysis_file": "reproduction-analysis.json",
        "attestations_relative": "attestations",
        "capsule_id": STUDY,
        "capsule_relative": f"capsule/{STUDY}",
        "coordination_thread_id": COORDINATION_THREAD_ID,
        "execution_relative": "experiment",
        "output_id": STUDY,
        "output_relative": f"raw/{STUDY}",
        "runtime_relative": RUNTIME_RELATIVE.as_posix(),
        "assist_relative": "assist",
        "worker_workspace_relative": "worker-workspace",
    }:
        raise ValueError("reproduction manifest execution identity mismatch")
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
    if root != SOURCE_ROOT:
        raise ValueError("root is not this registered reproduction checkout")
    common = Path(
        _command("git", "rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root)
    ).resolve()
    git_directory = next((path for path in (common, *common.parents) if path.name == ".git"), None)
    if git_directory is None:
        raise ValueError("registration checkout is not attached to the shared workspace")
    workspace = (
        git_directory.parent if common != git_directory else git_directory.parent.parent
    ).resolve()
    if (
        hashlib.sha256(str(common).encode()).hexdigest() != CANONICAL_GIT_COMMON_SHA256
        or hashlib.sha256(str(workspace).encode()).hexdigest()
        != CANONICAL_WORKSPACE_SHA256
    ):
        raise ValueError("registered shared workspace identity differs")
    gate = workspace / "tools" / "agentic"
    _verify_no_symlink_components("canonical shared LLM gate", gate, workspace)
    if not gate.is_file() or gate.is_symlink():
        raise ValueError("canonical shared LLM gate is unavailable")
    deploy_environment = workspace / "assist" / ".deploy.env"
    _verify_no_symlink_components(
        "worker deployment environment", deploy_environment, workspace
    )
    return workspace


def _verify_review_approval(approval: Any, *, commit: str, tree: str) -> None:
    """Require the tag-bound independent review approvals for this exact candidate."""
    try:
        reviews = approval.get("reviews") if isinstance(approval, dict) else None
        valid_shape = (
            isinstance(approval, dict)
            and set(approval) == {
                "candidate_commit", "candidate_tree", "coordination_thread_id", "reviews",
                "schema", "terra_approvals_sha256",
            }
            and approval["schema"] == "reach-v8-r3-reproduction-review-approval-v2"
            and approval["candidate_commit"] == commit
            and approval["candidate_tree"] == tree
            and approval["coordination_thread_id"] == COORDINATION_THREAD_ID
            and isinstance(reviews, dict)
            and set(reviews) == set(REQUIRED_REVIEW_MODELS)
        )
    except (KeyError, TypeError):
        valid_shape = False
    if not valid_shape:
        raise ValueError("registration tag does not bind the required review approvals")
    assert isinstance(reviews, dict)
    for lens, model in REQUIRED_REVIEW_MODELS.items():
        review = reviews[lens]
        result = review.get("result") if isinstance(review, dict) else None
        lines = result.splitlines() if isinstance(result, str) else []
        required_fields = {
            "CANDIDATE_COMMIT=": f"CANDIDATE_COMMIT={commit}",
            "CANDIDATE_TREE=": f"CANDIDATE_TREE={tree}",
            "COORDINATION_THREAD_ID=": (
                f"COORDINATION_THREAD_ID={COORDINATION_THREAD_ID}"
            ),
            "REVIEW_LENS=": f"REVIEW_LENS={lens}",
            "REVIEW_MODEL=": f"REVIEW_MODEL={model}",
            "DISPOSITION=": "DISPOSITION=accepted",
        }
        exact_identity = all(
            [line for line in lines if line.startswith(prefix)] == [expected]
            for prefix, expected in required_fields.items()
        )
        summaries = [
            line.removeprefix("REVIEW_SUMMARY=")
            for line in lines if line.startswith("REVIEW_SUMMARY=")
        ]
        if (
            not isinstance(review, dict)
            or set(review) != {"disposition", "model", "result", "result_sha256"}
            or review["disposition"] != "accepted"
            or review["model"] != model
            or not isinstance(result, str)
            or not 1 <= len(result.encode()) <= 65_536
            or not result.endswith("ACCEPTED")
            or result.splitlines()[-1:] != ["ACCEPTED"]
            or not exact_identity
            or len(summaries) != 1
            or len(summaries[0].strip()) < 20
            or not isinstance(review["result_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", review["result_sha256"]) is None
            or hashlib.sha256(result.encode()).hexdigest()
            != review["result_sha256"]
        ):
            raise ValueError("registration tag review approval differs")
    terra_reviews = {
        lens: reviews[lens] for lens in REQUIRED_REVIEW_MODELS
        if lens != "design-final"
    }
    terra_digest = digest(terra_reviews)
    if (
        approval["terra_approvals_sha256"] != terra_digest
        or [
            line for line in reviews["design-final"]["result"].splitlines()
            if line.startswith("TERRA_APPROVALS_SHA256=")
        ] != [f"TERRA_APPROVALS_SHA256={terra_digest}"]
    ):
        raise ValueError("registration tag Sol approval is not Terra-dependent")


def _decode_tag_approval(tag_record: bytes) -> Any:
    """Decode exactly one canonical JSON tag message and its Git newline."""
    try:
        approval_bytes = tag_record.split(b"\n\n", 1)[1]
        approval = strict_json_loads(approval_bytes)
    except (IndexError, ValueError) as error:
        raise ValueError("registration tag review approval is malformed") from error
    if approval_bytes != canonical_json(approval) + b"\n":
        raise ValueError("registration tag review approval is not canonical")
    return approval


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
    tag_record = _run_integrity_command(
        [GIT_BINARY, "cat-file", "tag", tag], cwd=root, env=_git_environment()
    )
    if tag_record.returncode:
        raise ValueError("registration tag review approval is unavailable")
    approval = _decode_tag_approval(tag_record.stdout)
    _verify_review_approval(approval, commit=commit, tree=tree)
    current = _git_identity(root)
    if current != {"commit": commit, "tree": tree, "status": ""}:
        raise ValueError("reproduction checkout is not the clean registered commit")
    tagged_manifest = _run_integrity_command(
        [GIT_BINARY, "show", f"{commit}:{MANIFEST.as_posix()}"], cwd=root,
        env=_git_environment(),
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
        f"refs/tags/{tag}^{{}}", cwd=Path("/"),
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
        stored = strict_json_loads(path.read_bytes())
    except (OSError, ValueError) as error:
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


def _verify_fixed_path(
    label: str, actual: Path, registered: Path, workspace_root: Path
) -> None:
    """Require one exact lexical path with no symlink below the workspace root."""
    workspace = Path(os.path.abspath(workspace_root))
    actual_path = Path(os.path.abspath(actual))
    registered_path = Path(os.path.abspath(registered))
    if actual_path != registered_path:
        raise ValueError(f"{label} differs from the fixed reproduction path")
    _verify_no_symlink_components(label, registered_path, workspace)


def _python_environment_identity(assist_python: Path) -> dict[str, str]:
    """Bind execution to one system interpreter and one explicit dependency tree."""
    _verify_system_python_ownership()
    try:
        executable = assist_python.resolve(strict=True)
    except OSError as error:
        raise ValueError("Assist interpreter is unavailable") from error
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    site_packages = home / ASSIST_SITE_PACKAGES_RELATIVE
    if (
        hashlib.sha256(str(executable).encode()).hexdigest()
        != CANONICAL_PYTHON_PATH_SHA256
        or hashlib.sha256(str(site_packages).encode()).hexdigest()
        != CANONICAL_ASSIST_SITE_PACKAGES_SHA256
    ):
        raise ValueError("Assist interpreter environment path differs from registration")
    _verify_no_symlink_components("Assist dependency tree", site_packages, home)
    if not site_packages.is_dir() or site_packages.is_symlink():
        raise ValueError("Assist dependency tree is unavailable")
    return {
        "executable_path_sha256": CANONICAL_PYTHON_PATH_SHA256,
        "site_packages_path_sha256": CANONICAL_ASSIST_SITE_PACKAGES_SHA256,
        "site_packages_relative": "lib/python3.14/site-packages",
        "startup_mode": "fixed-system-interpreter-minus-S-with-explicit-pythonpath",
        "launcher_sha256": PYTHON_LAUNCHER_SHA256,
    }


def _prepare_runtime(root: Path, assist_repository: Path, runtime_root: Path) -> None:
    """Atomically publish private clean detached clones without fetching."""
    workspace_root = _canonical_workspace_root(root)
    expected_root = workspace_root / RUNTIME_RELATIVE
    _verify_fixed_path("runtime root", runtime_root, expected_root, workspace_root)
    manifest = _load_manifest(root)
    proof = _verify_publication(root, manifest)
    runtime_root.parent.mkdir(parents=True, exist_ok=True)
    with _wrapper_lock(runtime_root):
        if runtime_root.exists() or runtime_root.is_symlink():
            raise ValueError("runtime root must not already exist")
        staging = Path(tempfile.mkdtemp(prefix=f".{STUDY}.preparing-", dir=runtime_root.parent))
        staging.chmod(0o700)
        try:
            (staging / "raw").mkdir(mode=0o700)
            atomic_write(
                staging / "publication.json",
                canonical_json({"proof": proof, "sha256": digest(proof)}) + b"\n",
            )
            experiment = staging / "experiment"
            assist = staging / "assist"
            worker_workspace = staging / "worker-workspace"
            worker_tools = worker_workspace / "tools"
            worker_assist = worker_workspace / "assist"
            worker_python = worker_workspace / "python"
            worker_tools.mkdir(parents=True, mode=0o700)
            worker_assist.mkdir(mode=0o700)
            gate_source = workspace_root / "tools" / "agentic"
            deploy_source = workspace_root / "assist" / ".deploy.env"
            if (
                not deploy_source.is_file()
                or deploy_source.is_symlink()
                or stat.S_IMODE(deploy_source.stat().st_mode) != 0o600
                or _sha256(deploy_source)
                != manifest["runtime"]["expected_attestation"]["deployment_environment"]["sha256"]
            ):
                raise ValueError("worker deployment environment must be a real mode-0600 file")
            shutil.copyfile(gate_source, worker_tools / "agentic")
            shutil.copyfile(deploy_source, worker_assist / ".deploy.env")
            atomic_write(worker_python, PYTHON_LAUNCHER)
            (worker_tools / "agentic").chmod(0o500)
            (worker_assist / ".deploy.env").chmod(0o400)
            worker_python.chmod(0o500)
            worker_tools.chmod(0o500)
            worker_assist.chmod(0o500)
            worker_workspace.chmod(0o500)
            expected_gate = manifest["runtime"]["expected_attestation"]["shared_gate"]
            if _sha256(worker_tools / "agentic") != expected_gate["sha256"]:
                raise ValueError("prepared shared LLM gate differs from registration")
            _run_integrity_command(
                [GIT_BINARY, "clone", "--quiet", "--shared", "--no-checkout", str(root), str(experiment)],
                check=True, env=_git_environment(), timeout_seconds=INTEGRITY_COMMAND_TIMEOUT_SECONDS,
            )
            _run_integrity_command(
                [GIT_BINARY, "-C", str(experiment), "checkout", "--quiet", "--detach", manifest["parent"]["commit"]],
                check=True, env=_git_environment(), timeout_seconds=INTEGRITY_COMMAND_TIMEOUT_SECONDS,
            )
            _run_integrity_command(
                [GIT_BINARY, "clone", "--quiet", "--shared", "--no-checkout", str(assist_repository), str(assist)],
                check=True, env=_git_environment(), timeout_seconds=INTEGRITY_COMMAND_TIMEOUT_SECONDS,
            )
            _run_integrity_command(
                [GIT_BINARY, "-C", str(assist), "checkout", "--quiet", "--detach", manifest["runtime"]["assist_commit"]],
                check=True, env=_git_environment(), timeout_seconds=INTEGRITY_COMMAND_TIMEOUT_SECONDS,
            )
            _verify_execution(experiment, manifest)
            if _git_identity(assist) != {
                "commit": manifest["runtime"]["assist_commit"],
                "tree": manifest["runtime"]["assist_tree"],
                "status": "",
            }:
                raise ValueError("prepared Assist checkout differs from registration")
            _verify_worker_workspace(experiment, manifest)
            staging.replace(runtime_root)
        finally:
            if staging.exists():
                for directory in (
                    staging / "worker-workspace" / "tools",
                    staging / "worker-workspace" / "assist",
                    staging / "worker-workspace",
                ):
                    if directory.is_dir() and not directory.is_symlink():
                        directory.chmod(0o700)
                shutil.rmtree(staging)


def prepare_runtime(root: Path, assist_repository: Path, runtime_root: Path) -> None:
    """Prepare the fixed runtime with termination cleanup active from entry."""
    with _termination_interrupts():
        if os.environ.get("CODEX_THREAD_ID") != COORDINATION_THREAD_ID:
            raise ValueError("prepare coordinator identity differs from registration")
        _prepare_runtime(root, assist_repository, runtime_root)


_ENVIRONMENT_SHELL = (
    'set -a; . "$1"; '
    'test "${GIT_CONFIG_GLOBAL-}" = /dev/null '
    '&& test "${GIT_CONFIG_NOSYSTEM-}" = 1 '
    '&& test "${GIT_TERMINAL_PROMPT-}" = 0 '
    '&& test "${GIT_CONFIG_COUNT-}" = 3 '
    '&& test "${GIT_CONFIG_KEY_0-}" = core.fsmonitor '
    '&& test "${GIT_CONFIG_VALUE_0-}" = false '
    '&& test "${GIT_CONFIG_KEY_1-}" = core.untrackedCache '
    '&& test "${GIT_CONFIG_VALUE_1-}" = false '
    '&& test "${GIT_CONFIG_KEY_2-}" = core.hooksPath '
    '&& test "${GIT_CONFIG_VALUE_2-}" = /dev/null || exit 126; '
    'PYTHONPATH="$2"; '
    'GIT_CONFIG_GLOBAL=/dev/null; GIT_CONFIG_NOSYSTEM=1; '
    'GIT_TERMINAL_PROMPT=0; GIT_CONFIG_COUNT=3; '
    'GIT_CONFIG_KEY_0=core.fsmonitor; GIT_CONFIG_VALUE_0=false; '
    'GIT_CONFIG_KEY_1=core.untrackedCache; GIT_CONFIG_VALUE_1=false; '
    'GIT_CONFIG_KEY_2=core.hooksPath; GIT_CONFIG_VALUE_2=/dev/null; '
    'unset LD_AUDIT LD_PRELOAD PYTHONHOME PYTHONINSPECT PYTHONSTARTUP; '
    'export PYTHONPATH GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM '
    'GIT_TERMINAL_PROMPT GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 '
    'GIT_CONFIG_VALUE_0 GIT_CONFIG_KEY_1 GIT_CONFIG_VALUE_1 '
    'GIT_CONFIG_KEY_2 GIT_CONFIG_VALUE_2; shift 2; exec "$@"'
)


_ENVIRONMENT_SCRIPT = r'''
import base64, csv, hashlib, importlib, importlib.metadata, json, os, pathlib, sys
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
roots = __RUNTIME_ROOT_DISTRIBUTIONS__
def file_sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            value.update(chunk)
    return value
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
            actual_digest = file_sha256(path).digest()
            if encoded:
                algorithm, value = encoded.split("=", 1)
                actual = base64.urlsafe_b64encode(actual_digest).rstrip(b"=").decode()
                if algorithm != "sha256" or actual != value:
                    raise RuntimeError(f"installed file differs from RECORD: {name}:{relative}")
            verified.append((relative, actual_digest.hex()))
    distributions[name] = {
        "version": dist.version,
        "record_sha256": file_sha256(record_path).hexdigest(),
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
    modules[name] = {"path": str(path), "sha256": file_sha256(path).hexdigest()}
python = pathlib.Path(sys.executable).resolve()
print(json.dumps({
    "distributions": {
        "closure_sha256": hashlib.sha256(distribution_identity).hexdigest(),
        "packages": sorted(distributions),
        "roots": list(roots),
    },
    "environment": {
        "agentic_root": os.environ.get("AGENTIC_ROOT"),
        "agentic_production_threads_dir": os.environ.get("AGENTIC_PRODUCTION_THREADS_DIR"),
        "assist_model_url": os.environ.get("ASSIST_MODEL_URL"),
        "dbus_session_bus_address": os.environ.get("DBUS_SESSION_BUS_ADDRESS"),
        "git_config_count": os.environ.get("GIT_CONFIG_COUNT"),
        "git_config_global": os.environ.get("GIT_CONFIG_GLOBAL"),
        "git_config_key_0": os.environ.get("GIT_CONFIG_KEY_0"),
        "git_config_key_1": os.environ.get("GIT_CONFIG_KEY_1"),
        "git_config_key_2": os.environ.get("GIT_CONFIG_KEY_2"),
        "git_config_nosystem": os.environ.get("GIT_CONFIG_NOSYSTEM"),
        "git_config_value_0": os.environ.get("GIT_CONFIG_VALUE_0"),
        "git_config_value_1": os.environ.get("GIT_CONFIG_VALUE_1"),
        "git_config_value_2": os.environ.get("GIT_CONFIG_VALUE_2"),
        "git_terminal_prompt": os.environ.get("GIT_TERMINAL_PROMPT"),
        "path": os.environ.get("PATH"),
        "python_no_user_site": os.environ.get("PYTHONNOUSERSITE"),
        "python_path": os.environ.get("PYTHONPATH"),
        "python_safe_path": os.environ.get("PYTHONSAFEPATH"),
        "reach_reproduction_site_packages": os.environ.get("REACH_REPRODUCTION_SITE_PACKAGES"),
        "xdg_runtime_dir": os.environ.get("XDG_RUNTIME_DIR"),
    },
    "modules": modules,
    "python": {"version": sys.version, "sha256": file_sha256(python).hexdigest()},
}, sort_keys=True, separators=(",", ":")))
'''.replace("__RUNTIME_ROOT_DISTRIBUTIONS__", repr(RUNTIME_ROOT_DISTRIBUTIONS))


def _environment_identity(
    *, assist_python: Path, workspace_root: Path, execution_root: Path,
    assist_source: Path, production_threads_path_sha256: str,
    worker_workspace: Path | None = None, site_packages: Path | None = None,
    launcher: bool = False,
) -> dict[str, Any]:
    python_environment = _python_environment_identity(
        SYSTEM_PYTHON if launcher else assist_python
    )
    site_packages = site_packages or (
        Path(pwd.getpwuid(os.getuid()).pw_dir) / ASSIST_SITE_PACKAGES_RELATIVE
    )
    env = _execution_environment(
        workspace_root=workspace_root,
        execution_root=execution_root,
        assist_source=assist_source,
        site_packages=site_packages,
        production_threads_path_sha256=production_threads_path_sha256,
    )
    worker_workspace = worker_workspace or execution_root.parent / "worker-workspace"
    deploy_environment = worker_workspace / "assist" / ".deploy.env"
    if (
        deploy_environment.is_symlink() or not deploy_environment.is_file()
        or stat.S_IMODE(deploy_environment.stat().st_mode) != 0o400
    ):
        raise ValueError("worker deployment snapshot must be a real mode-0400 file")
    source_path = f"{execution_root}:{assist_source}:{site_packages}"
    python_command = (
        [str(assist_python), "-c", _ENVIRONMENT_SCRIPT]
        if launcher
        else [str(assist_python.resolve(strict=True)), "-S", "-c", _ENVIRONMENT_SCRIPT]
    )
    result = _run_integrity_command(
        [
            "sh", "-c",
            _ENVIRONMENT_SHELL,
            "sh", str(deploy_environment), source_path,
            *python_command,
        ], cwd=workspace_root,
        env=env, text=True,
        timeout_seconds=INTEGRITY_COMMAND_TIMEOUT_SECONDS,
    )
    if result.returncode:
        raise ValueError("worker environment attestation failed")
    value = strict_json_loads(result.stdout)
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
        "agentic_root": str(workspace_root),
        "agentic_production_threads_dir": env["AGENTIC_PRODUCTION_THREADS_DIR"],
        "assist_model_url": "http://127.0.0.1:8000/v1",
        "dbus_session_bus_address": f"unix:path=/run/user/{os.getuid()}/bus",
        "git_config_count": "3",
        "git_config_global": "/dev/null",
        "git_config_key_0": "core.fsmonitor",
        "git_config_key_1": "core.untrackedCache",
        "git_config_key_2": "core.hooksPath",
        "git_config_nosystem": "1",
        "git_config_value_0": "false",
        "git_config_value_1": "false",
        "git_config_value_2": "/dev/null",
        "git_terminal_prompt": "0",
        "path": "/usr/bin:/bin",
        "python_no_user_site": "1",
        "python_path": source_path,
        "python_safe_path": "1",
        "reach_reproduction_site_packages": str(site_packages),
        "xdg_runtime_dir": f"/run/user/{os.getuid()}",
    }:
        raise ValueError("worker environment differs from the exact runtime profile")
    value["environment"]["agentic_root"] = "canonical-workspace"
    value["environment"]["agentic_production_threads_dir"] = "registered-systemd-directory"
    value["environment"]["dbus_session_bus_address"] = "user-runtime-bus"
    value["environment"]["path"] = ["/usr/bin", "/bin"]
    value["environment"]["python_path"] = [
        "exact-parent-checkout", "exact-assist-checkout", "exact-dependency-tree"
    ]
    value["environment"]["reach_reproduction_site_packages"] = "exact-dependency-tree"
    value["environment"]["xdg_runtime_dir"] = "user-runtime"
    value["python_environment"] = python_environment
    return value


def _execution_environment(
    *, workspace_root: Path, execution_root: Path, assist_source: Path,
    site_packages: Path,
    production_threads_path_sha256: str
) -> dict[str, str]:
    """Build the fixed minimal environment used by parent-runner subprocesses."""
    production_threads = _production_threads_directory(production_threads_path_sha256)
    env = {
        "AGENTIC_ROOT": str(workspace_root),
        "AGENTIC_PRODUCTION_THREADS_DIR": str(production_threads),
        "CODEX_THREAD_ID": COORDINATION_THREAD_ID,
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{os.getuid()}/bus",
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
        "LANG": "C.UTF-8",
        "NO_PROXY": "127.0.0.1,localhost",
        "PATH": "/usr/bin:/bin",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": f"{execution_root}:{assist_source}:{site_packages}",
        "PYTHONSAFEPATH": "1",
        "REACH_REPRODUCTION_SITE_PACKAGES": str(site_packages),
        "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
        "no_proxy": "127.0.0.1,localhost",
    }
    env.update(SAFE_GIT_ENVIRONMENT)
    return env


def _production_threads_directory(expected_sha256: str) -> Path:
    """Resolve the hash-pinned production-status root from the Assist service."""
    result = _run_integrity_command(
        ["/usr/bin/systemctl", "show", "assist-web", "-p", "Environment", "--value"],
        env=_system_environment(),
        text=True,
        timeout_seconds=SYSTEM_COMMAND_TIMEOUT_SECONDS,
    )
    if result.returncode:
        raise ValueError("production status directory is unavailable")
    try:
        values = [
            setting.partition("=")[2]
            for setting in shlex.split(result.stdout)
            if setting.partition("=")[:2] == ("ASSIST_THREADS_DIR", "=")
        ]
    except ValueError as error:
        raise ValueError("production status directory is malformed") from error
    if len(values) != 1:
        raise ValueError("production status directory is not uniquely configured")
    path = Path(values[0])
    if (
        not path.is_absolute()
        or path.is_symlink()
        or not path.is_dir()
        or path.resolve() != path
        or hashlib.sha256(str(path).encode()).hexdigest() != expected_sha256
    ):
        raise ValueError("production status directory differs from registration")
    return path


def _verify_server_listener(proc: Path) -> None:
    """Require the attested process to own the fixed IPv4 listening socket."""
    try:
        process_namespace = proc / "ns" / "net"
        wrapper_namespace = Path("/proc/self/ns/net")
        if not process_namespace.samefile(wrapper_namespace):
            raise ValueError("llama server network namespace differs from the worker")
        with (proc / "net" / "tcp").open() as source:
            listeners = {
                fields[9]
                for line in source
                if len(fields := line.split()) >= 10
                and fields[1] == MODEL_LISTENER
                and fields[3] == "0A"
            }
        if len(listeners) != 1:
            raise ValueError("model endpoint is not uniquely listening")
        target = f"socket:[{listeners.pop()}]"
        owns_listener = False
        for descriptor in (proc / "fd").iterdir():
            try:
                if os.readlink(descriptor) == target:
                    owns_listener = True
                    break
            except FileNotFoundError:
                continue
        if not process_namespace.samefile(wrapper_namespace):
            raise ValueError("llama server network namespace changed during attestation")
    except OSError as error:
        raise ValueError("model endpoint ownership is unavailable") from error
    if not owns_listener:
        raise ValueError("attested server does not own the model endpoint")


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
        if value == "--model" and index + 1 < len(argv):
            argument = Path(argv[index + 1])
            model_arguments.append(argument)
            normalized.extend((value, argument.name))
            index += 2
        else:
            normalized.append(value)
            index += 1
    if len(model_arguments) != 1:
        raise ValueError("llama server must have exactly one model argument")
    try:
        if not model_arguments[0].samefile(model_path):
            raise ValueError("attested model is not the model loaded by the server")
    except OSError as error:
        raise ValueError("llama server model identity is unavailable") from error
    _verify_server_listener(proc)
    try:
        if (proc / "stat").read_text().split()[21] != start_ticks:
            raise ValueError("llama server process changed during attestation")
    except (OSError, IndexError) as error:
        raise ValueError("llama server process identity is unavailable") from error
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
    expected = manifest["runtime"]["expected_attestation"]
    worker_workspace = _verify_worker_workspace(execution_root, manifest)
    value = {
        "manifest_sha256": digest(manifest),
        "publication": publication,
        "registration": registration,
        "execution": execution,
        "assist": assist_identity,
        "deployment_environment": {
            "sha256": _sha256(worker_workspace / "assist" / ".deploy.env")
        },
        "environment": _environment_identity(
            assist_python=assist_python,
            workspace_root=workspace_root,
            execution_root=execution_root,
            assist_source=assist_source,
            production_threads_path_sha256=expected["production_threads_path_sha256"],
        ),
        "process_scope": _scope_capability() | {
            "systemctl_sha256": _sha256(Path("/usr/bin/systemctl")),
            "systemd_run_sha256": _sha256(Path("/usr/bin/systemd-run")),
        },
        "shared_gate": {"sha256": _sha256(worker_workspace / "tools" / "agentic")},
        "server": _server_identity(server_pid, model_path, llama_source),
        "registered_model": manifest["runtime"]["model"],
    }
    server_expected = expected["server"]
    server = value["server"]
    for key in ("argv", "binary_sha256", "model"):
        if server[key] != server_expected[key]:
            raise ValueError(f"server identity differs from registration: {key}")
    if server["source"] != server_expected["source"]:
        raise ValueError("llama.cpp source differs from registration")
    environment = value["environment"]
    for key in ("distributions", "environment", "modules", "python", "python_environment"):
        if environment[key] != expected[key]:
            raise ValueError(f"worker {key} differs from registration")
    if value["shared_gate"] != expected["shared_gate"]:
        raise ValueError("shared LLM admission gate differs from registration")
    if value["deployment_environment"] != expected["deployment_environment"]:
        raise ValueError("worker deployment environment differs from registration")
    if value["process_scope"] != expected["process_scope"]:
        raise ValueError("scoped process tools differ from registration")
    return canonical_json(value) + b"\n"


def _quarantine(output: Path, reason: str) -> None:
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError("unsafe reproduction output cannot be quarantined")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(output.stat().st_mode) != 0o700:
        raise ValueError("reproduction output must have mode 0700")
    atomic_write(output / INVALID, canonical_json({"reason": reason, "resume": False}) + b"\n")


def _is_quarantined(output: Path) -> bool:
    """Treat any real or dangling quarantine marker as permanently invalid."""
    marker = output / INVALID
    return marker.is_symlink() or marker.exists()


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
    _preflight_live_json(output)
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


def _preflight_live_json(output: Path) -> None:
    """Reject ambiguous active evidence before invoking a permissive parent reader."""
    json_paths = [
        output / name
        for name in (
            "bundle.json", "admissions.jsonl.seal", "outcomes.jsonl.seal",
            "report.json", "trial-metadata.json",
        )
    ]
    traces = output / "traces"
    if traces.is_symlink():
        raise ValueError("live trace path must be a real directory")
    if traces.exists():
        if not traces.is_dir():
            raise ValueError("live trace path must be a real directory")
        json_paths.extend(sorted(traces.glob("*.json")))
    try:
        for path in json_paths:
            if path.is_symlink():
                raise ValueError("live JSON evidence must be a real file")
            if path.exists():
                if not path.is_file():
                    raise ValueError("live JSON evidence must be a real file")
                strict_json_loads(path.read_bytes())
        for name in ("admissions.jsonl", "outcomes.jsonl"):
            path = output / name
            if path.is_symlink():
                raise ValueError("live JSONL evidence must be a real file")
            if path.exists():
                if not path.is_file():
                    raise ValueError("live JSONL evidence must be a real file")
                strict_json_lines(path.read_bytes())
    except (OSError, ValueError) as error:
        raise ValueError("live reproduction JSON evidence is malformed or ambiguous") from error


def _read_denial_cooldown(
    output: Path, admissions: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Return the cooldown bound to the latest persisted denial, if any."""
    path = output / "denial-cooldown.json"
    denial_counts = [
        index for index, admission in enumerate(admissions, start=1)
        if admission.get("admitted") is False
    ]
    if path.is_symlink():
        raise ValueError("production-denial cooldown must be a real file")
    if not path.exists():
        if denial_counts:
            raise ValueError("production-denial cooldown is missing")
        return None
    try:
        record = strict_json_loads(path.read_bytes())
    except (OSError, ValueError) as error:
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
    if not denial_counts or record["admission_count"] != denial_counts[-1]:
        raise ValueError("production-denial cooldown differs from latest denial")
    denial = admissions[denial_counts[-1] - 1]
    if denial.get("trial_sha256") != record["trial_sha256"]:
        raise ValueError("production-denial cooldown differs from admissions")
    return record


def _denial_retry_not_before(
    output: Path, admissions: list[dict[str, Any]]
) -> float | int | None:
    """Validate and return the latest still-applicable denial boundary."""
    record = _read_denial_cooldown(output, admissions)
    if record is None:
        return None
    if record["admission_count"] == len(admissions):
        return record["not_before_unix"]
    return None


def verify_reproduction_seal(capsule: Path, manifest: dict[str, Any]) -> None:
    """Verify the final immutable reproduction evidence inventory."""
    if capsule.is_symlink() or not capsule.is_dir():
        raise ValueError("reproduction capsule must be a real directory")
    path = capsule / "reproduction-seal.json"
    try:
        seal = strict_json_loads(path.read_bytes())
    except (OSError, ValueError) as error:
        raise ValueError("reproduction seal is missing or malformed") from error
    if (
        not isinstance(seal, dict)
        or set(seal) != {"manifest_sha256", "schema", "seal_sha256", "sealed_files"}
        or seal.get("schema") != "reach-v8-exact-reproduction-seal-v1"
    ):
        raise ValueError("reproduction seal is malformed")
    claimed = seal.pop("seal_sha256", None)
    if claimed != digest(seal) or seal.get("manifest_sha256") != digest(manifest):
        raise ValueError("reproduction seal identity differs")
    expected = seal.get("sealed_files")
    if not isinstance(expected, dict):
        raise ValueError("reproduction seal inventory is malformed")
    actual = _sealed_file_inventory(capsule)
    if any(item.is_symlink() for item in capsule.rglob("*")) or expected != actual:
        raise ValueError("reproduction sealed files differ")


def _sealed_file_inventory(capsule: Path) -> dict[str, str]:
    """Hash the files covered by the final reproduction evidence seal."""
    excluded = {"learning.md", "assist-roadmap-proposal.md", "reproduction-seal.json"}
    sealed = {}
    for path in sorted(capsule.rglob("*")):
        relative = path.relative_to(capsule).as_posix()
        if path.is_file() and not path.is_symlink() and relative not in excluded:
            sealed[relative] = _sha256(path)
    return sealed


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


def _descriptor_sha256(descriptor: int, size: int) -> str:
    """Hash an exact descriptor prefix without allocating it as one object."""
    value = hashlib.sha256()
    offset = 0
    while offset < size:
        chunk = os.pread(descriptor, min(HASH_CHUNK_BYTES, size - offset), offset)
        if not chunk:
            raise ValueError("coordination event log changed while being read")
        value.update(chunk)
        offset += len(chunk)
    return value.hexdigest()


def _read_event_descriptor(descriptor: int) -> tuple[int, str, bool]:
    """Fingerprint one stable event-log inode at its current exact length."""
    size = os.fstat(descriptor).st_size
    digest_value = _descriptor_sha256(descriptor, size)
    final = os.pread(descriptor, 1, size - 1) if size else b""
    if size and len(final) != 1:
        raise ValueError("coordination event log changed while being read")
    return size, digest_value, final == b"\n"


def _read_appended_events(
    descriptor: int, prefix: tuple[int, str, bool], thread_id: str
) -> list[dict[str, Any]]:
    """Validate an append-only event slice and retain its bounded relevant records."""
    prefix_size, prefix_sha256, _ = prefix
    complete_size = os.fstat(descriptor).st_size
    if (
        complete_size < prefix_size
        or _descriptor_sha256(descriptor, prefix_size) != prefix_sha256
    ):
        raise ValueError("coordination event log changed non-append-only")
    if complete_size - prefix_size > EVENT_SLICE_BYTES:
        raise ValueError("coordination event slice is too large")
    records: list[dict[str, Any]] = []
    buffer = b""
    offset = prefix_size
    record_count = 0
    while offset < complete_size:
        chunk = os.pread(
            descriptor, min(EVENT_READ_BYTES, complete_size - offset), offset
        )
        if not chunk:
            raise ValueError("coordination event log changed while being read")
        if b"\r" in chunk:
            raise ValueError("coordination event slice is malformed")
        offset += len(chunk)
        lines = (buffer + chunk).split(b"\n")
        buffer = lines.pop()
        for line in lines:
            record_count += 1
            if record_count > EVENT_SLICE_RECORDS:
                raise ValueError("coordination event slice has too many records")
            if len(line) > EVENT_RECORD_BYTES:
                raise ValueError("coordination event record is too large")
            try:
                record = strict_json_loads(line)
            except ValueError as error:
                raise ValueError("coordination event slice is malformed") from error
            if not isinstance(record, dict):
                raise ValueError("coordination event slice is malformed")
            if (
                record.get("thread") == thread_id
                and record.get("resource") == "llm"
                and record.get("event") in {
                    "production_admission_denied", "resource_started", "resource_finished"
                }
            ):
                records.append(record)
                if len(records) > MAX_ATTESTED_EVENTS:
                    raise ValueError(
                        "coordination event slice has too many relevant events"
                    )
        if len(buffer) > EVENT_RECORD_BYTES:
            raise ValueError("coordination event record is too large")
    if buffer:
        raise ValueError("coordination event slice has an unterminated record")
    return records


def _time_bound() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _termination_interrupts():
    """Raise on the first terminating signal and coalesce repeats through cleanup."""
    numbers = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    originals = {number: signal.getsignal(number) for number in numbers}
    interrupted = False

    def interrupt(number: int, _frame: Any) -> None:
        nonlocal interrupted
        if interrupted:
            return
        interrupted = True
        raise KeyboardInterrupt(f"wrapper received signal {number}")

    try:
        for number in originals:
            signal.signal(number, interrupt)
        yield
    finally:
        for number, handler in originals.items():
            signal.signal(number, handler)


@contextmanager
def _defer_termination_signals():
    """Defer terminating signals until cleanup and quarantine are durable."""
    numbers = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, numbers)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def _scope_cgroup(unit: str) -> Path:
    uid = os.getuid()
    return Path(
        f"/sys/fs/cgroup/user.slice/user-{uid}.slice/"
        f"user@{uid}.service/app.slice/{unit}.scope"
    )


def _bind_scope(unit: str, ready: int) -> Path:
    """Observe the gated payload inside its exact live transient cgroup."""
    deadline = time.monotonic() + 10
    message = b""
    while b"\n" not in message and len(message) <= 64:
        remaining = max(0, deadline - time.monotonic())
        readable, _, _ = select.select([ready], [], [], remaining)
        if not readable:
            raise RuntimeError("scoped process did not become ready")
        chunk = os.read(ready, 65 - len(message))
        if not chunk:
            raise RuntimeError("scoped process readiness pipe closed")
        message += chunk
    fields = message.rstrip(b"\n").split()
    if len(fields) != 2 or fields[0] != b"R" or not fields[1].isdigit():
        raise RuntimeError("scoped process readiness is malformed")
    bootstrap_pid = fields[1].decode()
    scope = _scope_cgroup(unit)
    control = scope / "cgroup.kill"
    members = scope / "cgroup.procs"
    _verify_no_symlink_components("scoped process", members, Path("/"))
    _verify_no_symlink_components(
        "scoped process kill control", control, Path("/")
    )
    try:
        scope_metadata = scope.lstat()
        control_metadata = control.stat()
        member_pids = members.read_text().split()
    except OSError as error:
        raise RuntimeError("scoped process could not be bound") from error
    if (
        not stat.S_ISDIR(scope_metadata.st_mode)
        or scope.is_symlink()
        or not stat.S_ISREG(control_metadata.st_mode)
        or control_metadata.st_uid != os.getuid()
        or not stat.S_IMODE(control_metadata.st_mode) & stat.S_IWUSR
        or bootstrap_pid not in member_pids
    ):
        raise RuntimeError("scoped process identity differs from registration")
    return scope


def _release_scope(descriptor: int) -> None:
    """Release the bound startup gate so the registered payload can exec."""
    os.write(descriptor, b"R\n")


def _scope_capability() -> dict[str, str]:
    """Verify the user slice exposes its owner-writable atomic kill control."""
    uid = os.getuid()
    control = Path(
        f"/sys/fs/cgroup/user.slice/user-{uid}.slice/"
        f"user@{uid}.service/app.slice/cgroup.kill"
    )
    try:
        metadata = control.stat()
    except OSError as error:
        raise ValueError("systemd scope kill control is unavailable") from error
    mode = stat.S_IMODE(metadata.st_mode)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != uid or not mode & stat.S_IWUSR:
        raise ValueError("systemd scope kill control is not delegated to this runtime")
    return {
        "cgroup_kill_mode": f"{mode:04o}",
        "cgroup_kill_owner": "runtime-user",
        "slice": "app.slice",
    }


def _verify_scope_empty(scope: Path) -> None:
    """Prove a previously bound cgroup is now empty or has been removed."""
    _verify_no_symlink_components("scoped process", scope, Path("/"))
    _verify_no_symlink_components(
        "scoped process membership", scope / "cgroup.procs", Path("/")
    )
    try:
        members = (scope / "cgroup.procs").read_text().strip()
    except OSError as error:
        if error.errno in {errno.ENOENT, errno.ENODEV}:
            return
        raise
    if members:
        raise RuntimeError("scoped process still contains live members")


def _kill_scope(process: subprocess.Popen[str], scope: Path) -> None:
    """Atomically kill the complete transient cgroup and prove it is empty."""
    def kill_members() -> None:
        path = scope / "cgroup.kill"
        _verify_no_symlink_components(
            "scoped process kill control", path, Path("/")
        )
        descriptor = -1
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            )
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise RuntimeError("scope kill control is not a regular cgroup file")
            os.write(descriptor, b"1")
        except OSError as error:
            try:
                (scope / "cgroup.procs").read_text()
            except OSError as membership_error:
                if membership_error.errno in {errno.ENOENT, errno.ENODEV}:
                    return
            raise RuntimeError("bound scope kill control is unavailable") from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    kill_members()
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        kill_members()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("scoped process launcher could not be reaped") from error
    _verify_scope_empty(scope)


def _kill_unbound_scope(
    process: subprocess.Popen[str], unit: str, env: dict[str, str]
) -> None:
    """Stop a startup-gated launcher before any payload command can begin."""
    try:
        _run_integrity_command(
            [
                "/usr/bin/systemctl", "--user", "kill", "--kill-whom=all",
                "--signal=SIGKILL", f"{unit}.scope",
            ],
            env=env,
            text=True,
            timeout_seconds=SYSTEM_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, ValueError, RuntimeError):
        pass
    scope = _scope_cgroup(unit)
    _verify_no_symlink_components("startup-gated process scope", scope, Path("/"))
    scope_error: Exception | None = None
    if scope.exists():
        try:
            _kill_scope(process, scope)
            return
        except Exception as error:
            scope_error = error
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("startup-gated scope launcher could not be reaped") from error
    try:
        _verify_scope_empty(scope)
    except Exception:
        if scope_error is not None:
            raise RuntimeError("startup-gated scope could not be killed") from scope_error
        raise


def _run_scoped(
    command: list[str], *, cwd: Path, env: dict[str, str], output: Path, stage: str,
    timeout_seconds: int = BATCH_SCOPE_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Run and reap one child tree under the caller's termination guard."""
    _scope_capability()
    unit = f"reach-v8-r3-{os.getpid()}-{time.monotonic_ns()}"
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
    scoped_command = [
        "/usr/bin/systemd-run", "--user", "--scope", "--quiet", "--collect",
        "--slice=app.slice", f"--unit={unit}", "--", "/bin/sh", "-c",
        _SCOPE_BOOTSTRAP, "sh", str(ready_write), str(release_read), *command,
    ]
    process: subprocess.Popen[str] | None = None
    scope: Path | None = None
    try:
        process = subprocess.Popen(
            scoped_command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            pass_fds=(ready_write, release_read),
        )
        os.close(ready_write)
        ready_write = -1
        os.close(release_read)
        release_read = -1
        scope = _bind_scope(unit, ready_read)
        _release_scope(release_write)
        os.close(release_write)
        release_write = -1
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        _verify_scope_empty(scope)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except BaseException as error:
        with _defer_termination_signals():
            cleanup_error: Exception | None = None
            if process is not None:
                try:
                    if scope is None:
                        _kill_unbound_scope(process, unit, env)
                    else:
                        _kill_scope(process, scope)
                except Exception as scope_error:
                    cleanup_error = scope_error
            _quarantine(output, f"{stage} could not be launched or was interrupted")
            if cleanup_error is not None:
                raise RuntimeError(
                    f"{stage} process scope could not be terminated"
                ) from cleanup_error
        if not isinstance(error, Exception):
            raise
        raise ValueError(f"{stage} could not be launched") from error
    finally:
        for descriptor in (ready_read, ready_write, release_read, release_write):
            if descriptor >= 0:
                os.close(descriptor)


def _read_batch_cooldown(path: Path) -> dict[str, int | float]:
    """Read the exact inherited batch-cooldown record shape."""
    if path.is_symlink():
        raise ValueError("sealed batch cooldown must be a real file")
    try:
        value = strict_json_loads(path.read_bytes())
    except (OSError, ValueError) as error:
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


def _verify_live_cooldowns(
    output: Path,
    admissions: list[dict[str, Any]],
    intervals: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float | int | None]:
    """Match the live cooldown files to their latest attested boundaries."""
    batch_intervals = [
        interval for interval in intervals
        if interval["next_batch_not_before_unix"] is not None
    ]
    batch_path = output / "batch-cooldown.json"
    if batch_path.is_symlink():
        raise ValueError("sealed batch cooldown must be a real file")
    if batch_intervals:
        expected_batch = batch_intervals[-1]
        batch = _read_batch_cooldown(batch_path)
        if (
            batch["completed_outcomes"] != expected_batch["outcomes_after"]
            or batch["not_before_unix"]
            != expected_batch["next_batch_not_before_unix"]
            or batch_path.stat().st_mtime_ns
            != expected_batch["batch_cooldown_mtime_ns"]
        ):
            raise ValueError("sealed batch cooldown differs from its attestation")
    elif batch_path.exists():
        raise ValueError("sealed batch cooldown exists before a batch boundary")

    denial = _read_denial_cooldown(output, admissions)
    denial_intervals = [
        interval for interval in intervals
        if interval["next_denial_not_before_unix"] is not None
    ]
    if (denial is None) != (not denial_intervals):
        raise ValueError("production-denial cooldown differs from its attestation")
    if denial is not None:
        expected_denial = denial_intervals[-1]
        if (
            denial["admission_count"] != expected_denial["admissions_after"]
            or denial["not_before_unix"]
            != expected_denial["next_denial_not_before_unix"]
        ):
            raise ValueError("production-denial cooldown differs from its attestation")
        if denial["admission_count"] == len(admissions):
            return batch_intervals, denial["not_before_unix"]
    return batch_intervals, None


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


def _verify_runtime_paths(
    *,
    workspace_root: Path,
    execution_root: Path,
    assist_source: Path,
    output: Path,
    attestations: Path,
    capsule: Path | None = None,
) -> None:
    """Bind every cohort path to the one prepared runtime root."""
    canonical_workspace = workspace_root.resolve()
    if Path(os.path.abspath(workspace_root)) != canonical_workspace:
        raise ValueError("workspace path contains a symlinked component")
    runtime_root = canonical_workspace / RUNTIME_RELATIVE
    expected = {
        "execution checkout": (execution_root, runtime_root / "experiment"),
        "Assist checkout": (assist_source, runtime_root / "assist"),
        "raw output": (output, runtime_root / "raw" / STUDY),
        "attestations": (attestations, runtime_root / "attestations"),
        "worker workspace": (
            execution_root.parent / "worker-workspace",
            runtime_root / "worker-workspace",
        ),
    }
    if capsule is not None:
        expected["capsule"] = (capsule, runtime_root / "capsule" / STUDY)
    for label, (actual, registered) in expected.items():
        _verify_fixed_path(label, actual, registered, canonical_workspace)


def _verify_worker_workspace_path(
    workspace: Path, manifest: dict[str, Any], *, bound_root: bool = False
) -> Path:
    """Verify the private gate/environment snapshot used by the exact parent."""
    gate = workspace / "tools" / "agentic"
    deploy_environment = workspace / "assist" / ".deploy.env"
    python_launcher = workspace / "python"
    _verify_no_symlink_components("prepared shared LLM gate", gate, workspace)
    _verify_no_symlink_components(
        "prepared deployment environment", deploy_environment, workspace
    )
    expected_entries = {
        workspace / "tools",
        workspace / "assist",
        gate,
        deploy_environment,
        python_launcher,
    }
    actual_entries = set(workspace.rglob("*"))
    if actual_entries != expected_entries:
        raise ValueError("prepared worker workspace contains unexpected entries")
    directories = (workspace, workspace / "tools", workspace / "assist")
    if any(
        not directory.is_dir()
        or ((directory != workspace or not bound_root) and directory.is_symlink())
        or directory.stat().st_uid != os.getuid()
        or stat.S_IMODE(directory.stat().st_mode) != 0o500
        for directory in directories
    ):
        raise ValueError("prepared worker workspace directory differs")
    if (
        not gate.is_file()
        or gate.stat().st_uid != os.getuid()
        or stat.S_IMODE(gate.stat().st_mode) != 0o500
        or _sha256(gate)
        != manifest["runtime"]["expected_attestation"]["shared_gate"]["sha256"]
        or not deploy_environment.is_file()
        or deploy_environment.stat().st_uid != os.getuid()
        or stat.S_IMODE(deploy_environment.stat().st_mode) != 0o400
        or _sha256(deploy_environment)
        != manifest["runtime"]["expected_attestation"]["deployment_environment"]["sha256"]
        or not python_launcher.is_file()
        or python_launcher.is_symlink()
        or python_launcher.stat().st_uid != os.getuid()
        or stat.S_IMODE(python_launcher.stat().st_mode) != 0o500
        or _sha256(python_launcher) != PYTHON_LAUNCHER_SHA256
    ):
        raise ValueError("prepared worker workspace differs from registration")
    return workspace


def _verify_worker_workspace(execution_root: Path, manifest: dict[str, Any]) -> Path:
    """Locate and verify the snapshot beside a prepared execution checkout."""
    return _verify_worker_workspace_path(
        execution_root.parent / "worker-workspace", manifest
    )


@contextmanager
def _bound_worker_workspace(workspace: Path, manifest: dict[str, Any]):
    """Open the worker directory first, then verify and retain that exact inode."""
    descriptor = os.open(
        workspace,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o500
        ):
            raise ValueError("prepared worker workspace descriptor differs")
        reference = Path(f"/proc/{os.getpid()}/fd/{descriptor}")
        _verify_worker_workspace_path(reference, manifest, bound_root=True)
        yield reference
    finally:
        os.close(descriptor)


@contextmanager
def _bound_invocation_paths(
    execution_root: Path,
    assist_source: Path,
    assist_python: Path,
    worker_workspace: Path,
    manifest: dict[str, Any],
):
    """Open first and verify every code/config path used by the exact parent."""
    python_environment = _python_environment_identity(assist_python)
    site_packages = (
        Path(pwd.getpwuid(os.getuid()).pw_dir) / ASSIST_SITE_PACKAGES_RELATIVE
    )
    sources = (execution_root, assist_source, site_packages)
    descriptors: list[int] = []
    try:
        for source in sources:
            descriptors.append(os.open(
                source,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
                | getattr(os, "O_NOFOLLOW", 0),
            ))
        expected_owners = (os.getuid(), os.getuid(), os.getuid())
        if any(
            not stat.S_ISDIR(os.fstat(descriptor).st_mode)
            or os.fstat(descriptor).st_uid != expected_owner
            for descriptor, expected_owner in zip(descriptors, expected_owners, strict=True)
        ):
            raise ValueError("bound invocation directory differs from registration")
        references = [Path(f"/proc/{os.getpid()}/fd/{value}") for value in descriptors]
        execution_reference, assist_reference, site_packages_reference = references
        with _bound_worker_workspace(worker_workspace, manifest) as worker_reference:
            _verify_execution(execution_reference, manifest)
            if _git_identity(assist_reference) != {
                "commit": manifest["runtime"]["assist_commit"],
                "tree": manifest["runtime"]["assist_tree"],
                "status": "",
            }:
                raise ValueError("bound Assist checkout differs from registration")
            python_reference = worker_reference / "python"
            if (
                not python_reference.is_file()
                or _sha256(python_reference) != PYTHON_LAUNCHER_SHA256
            ):
                raise ValueError("bound Assist interpreter launcher differs from registration")
            yield {
                "assist": assist_reference,
                "execution": execution_reference,
                "python": python_reference,
                "python_environment": python_environment,
                "site_packages": site_packages_reference,
                "worker": worker_reference,
            }
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _bound_execution_environment(
    bound: dict[str, Path], workspace_root: Path, manifest: dict[str, Any], label: str
) -> dict[str, str]:
    """Re-attest imports through held paths and return their execution environment."""
    expected = manifest["runtime"]["expected_attestation"]
    identity = _environment_identity(
        assist_python=bound["python"],
        workspace_root=workspace_root,
        execution_root=bound["execution"],
        assist_source=bound["assist"],
        production_threads_path_sha256=expected["production_threads_path_sha256"],
        worker_workspace=bound["worker"],
        site_packages=bound["site_packages"],
        launcher=True,
    )
    for key in ("distributions", "environment", "modules", "python", "python_environment"):
        if identity[key] != expected[key]:
            raise ValueError(f"bound {label} {key} differs from registration")
    return _execution_environment(
        workspace_root=workspace_root,
        execution_root=bound["execution"],
        assist_source=bound["assist"],
        site_packages=bound["site_packages"],
        production_threads_path_sha256=expected["production_threads_path_sha256"],
    )


def _verify_run_scope(
    root: Path,
    output: Path,
    attestations: Path,
    execution_root: Path,
    assist_source: Path,
    workspace_root: Path,
    events: Path,
) -> None:
    """Validate caller-selected paths before touching reproduction state."""
    if output.name != STUDY:
        raise ValueError("raw output ID differs from the fixed reproduction")
    if os.environ.get("CODEX_THREAD_ID", "") != COORDINATION_THREAD_ID:
        raise ValueError("execution thread identity differs from registration")
    if workspace_root.resolve() != _canonical_workspace_root(root):
        raise ValueError("worker workspace differs from the canonical shared workspace")
    _verify_runtime_paths(
        workspace_root=workspace_root,
        execution_root=execution_root,
        assist_source=assist_source,
        output=output,
        attestations=attestations,
    )
    _verify_fixed_path(
        "coordination event log",
        events,
        workspace_root / ".coordination" / "events.jsonl",
        workspace_root,
    )


def _run_batch_locked(
    root: Path,
    output: Path,
    attestations: Path,
    *,
    manifest: dict[str, Any],
    registration: dict[str, str],
    execution_root: Path,
    assist_source: Path,
    assist_python: Path,
    workspace_root: Path,
    model_path: Path,
    server_pid: int,
    llama_source: Path,
    events: Path,
) -> str:
    """Return complete for a verified cohort or run one inherited bounded invocation."""
    thread_id = manifest["execution"]["coordination_thread_id"]
    try:
        bundle = StudyBundle.read_verified(execution_root / manifest["parent"]["bundle_path"])
        prior_admissions, existing_outcomes = _verified_progress(output, bundle)
        if _fidelity_error(existing_outcomes):
            raise ValueError("persisted provider-request fidelity failure")
    except Exception as error:
        _quarantine(output, "persisted reproduction progress is invalid")
        raise ValueError("persisted reproduction progress is invalid") from error
    remaining = len(bundle.schedule) - len(existing_outcomes)
    try:
        prior_intervals = _prepare_attestation_directory(
            attestations, manifest=manifest, registration=registration
        )
        if (prior_admissions or existing_outcomes) and not prior_intervals:
            raise ValueError("persisted reproduction progress lacks runtime attestations")
        if prior_intervals:
            verify_execution_intervals(
                prior_intervals,
                admissions=prior_admissions,
                outcomes=existing_outcomes,
                thread_id=thread_id,
                schedule_size=len(bundle.schedule),
            )
        batch_intervals, denial_not_before = _verify_live_cooldowns(
            output, prior_admissions, prior_intervals
        )
        attested_batch_not_before = (
            batch_intervals[-1]["next_batch_not_before_unix"] if batch_intervals else None
        )
        attested_denial_not_before = (
            prior_intervals[-1]["next_denial_not_before_unix"] if prior_intervals else None
        )
        if denial_not_before != attested_denial_not_before:
            raise ValueError("production-denial cooldown differs from its attestation")
        if remaining == 0:
            return "complete"
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
    event_descriptor = -1
    try:
        event_descriptor = os.open(
            events,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
        event_metadata = os.fstat(event_descriptor)
        if not stat.S_ISREG(event_metadata.st_mode):
            raise ValueError("coordination event log is not a regular file")
        prefix = _read_event_descriptor(event_descriptor)
    except Exception as error:
        if event_descriptor >= 0:
            os.close(event_descriptor)
            event_descriptor = -1
        _quarantine(output, "coordination event log is unavailable")
        raise ValueError("coordination event log is unavailable") from error
    if prefix[0] and not prefix[2]:
        os.close(event_descriptor)
        event_descriptor = -1
        _quarantine(output, "coordination event log has an unterminated prefix")
        raise ValueError("coordination event log has an unterminated prefix")
    try:
        worker_workspace = execution_root.parent / "worker-workspace"
        with _bound_invocation_paths(
            execution_root, assist_source, assist_python, worker_workspace, manifest
        ) as bound:
            env = _bound_execution_environment(bound, workspace_root, manifest, "worker")
            command = [
                str(bound["python"]), "-m",
                "studies.reach_for_instructions_confirmation_v8.runner", "run",
                "--root", str(bound["execution"]), "--output", str(output),
                "--workspace-root", str(bound["worker"]),
                "--assist-source", str(bound["assist"]),
                "--assist-python", str(bound["python"]),
            ]
            started_at = _time_bound()
            result = _run_scoped(
                command,
                cwd=workspace_root,
                env=env,
                output=output,
                stage="parent runner",
                timeout_seconds=BATCH_SCOPE_TIMEOUT_SECONDS,
            )
            finished_at = _time_bound()
        new_events = _read_appended_events(event_descriptor, prefix, thread_id)
    except Exception:
        _quarantine(output, "bound runtime or event attestation failed")
        raise
    finally:
        if event_descriptor >= 0:
            os.close(event_descriptor)
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


def _run_batch(
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
    """Serialize a completed-cohort check or one inherited bounded invocation."""
    _verify_run_scope(
        root, output, attestations, execution_root, assist_source, workspace_root, events
    )
    with _wrapper_lock(output):
        with _termination_interrupts():
            try:
                if output.is_symlink() or (output.exists() and not output.is_dir()):
                    raise ValueError("reproduction output must be a real directory")
                if output.exists() and stat.S_IMODE(output.stat().st_mode) != 0o700:
                    raise ValueError("reproduction output must have mode 0700")
                if _is_quarantined(output):
                    raise ValueError("reproduction output is quarantined and cannot resume")
                try:
                    manifest = _load_manifest(root)
                    registration = _verify_local_registration(root, manifest)
                except Exception as error:
                    _quarantine(output, "registered reproduction inputs drifted")
                    raise ValueError(
                        "registered reproduction inputs drifted; fresh reproduction required"
                    ) from error
                return _run_batch_locked(
                    root,
                    output,
                    attestations,
                    manifest=manifest,
                    registration=registration,
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
                with _defer_termination_signals():
                    if not isinstance(error, Exception):
                        _quarantine(output, "reproduction wrapper was interrupted")
                raise


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
    """Check completion or run one batch with termination handling already active."""
    with _termination_interrupts():
        return _run_batch(
            root,
            output,
            attestations,
            execution_root=execution_root,
            assist_source=assist_source,
            assist_python=assist_python,
            workspace_root=workspace_root,
            model_path=model_path,
            server_pid=server_pid,
            llama_source=llama_source,
            events=events,
        )


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
        production_threads_path_sha256=manifest["runtime"]["expected_attestation"]["production_threads_path_sha256"],
    )
    expected = manifest["runtime"]["expected_attestation"]
    for key in ("distributions", "environment", "modules", "python", "python_environment"):
        if environment[key] != expected[key]:
            raise ValueError(f"archive worker {key} differs from registration")
    worker_workspace = _verify_worker_workspace(execution_root, manifest)
    if _sha256(worker_workspace / "tools" / "agentic") != expected["shared_gate"]["sha256"]:
        raise ValueError("shared LLM gate differs before archival")


def _trial_metadata_from_traces(
    output: Path, bundle: StudyBundle, outcomes: list[dict[str, Any]]
) -> bytes:
    """Recompute the parent's secondary metadata from its sealed trace bodies."""
    by_trial = {str(record["trial_sha256"]): record for record in outcomes}
    metadata = []
    for trial in bundle.schedule:
        trace_path = output / "traces" / f"{trial.sha256}.json"
        try:
            trace = strict_json_loads(trace_path.read_bytes())
        except (OSError, ValueError) as error:
            raise ValueError("sealed trial trace is missing or malformed") from error
        if not isinstance(trace, dict) or trace.get("trial_sha256") != trial.sha256:
            raise ValueError("sealed trial trace identity differs from the schedule")
        record = by_trial.get(trial.sha256)
        if record is None:
            raise ValueError("sealed outcome is missing from trial metadata")
        if "result" not in trace:
            if record["outcome"] not in {
                "timeout", "provider_error", "infrastructure_invalid",
            }:
                raise ValueError("sealed returned trace lacks secondary metadata")
            result = {}
        else:
            result = trace["result"]
            if not isinstance(result, dict) or not {
                "first_prompt_tokens", "skill_loaded_before_first_read",
            }.issubset(result):
                raise ValueError("sealed returned trace has malformed secondary metadata")
            token_count = result["first_prompt_tokens"]
            if token_count is not None and (
                not isinstance(token_count, int)
                or isinstance(token_count, bool)
                or token_count < 0
            ):
                raise ValueError("sealed returned trace has malformed secondary metadata")
            if not isinstance(result["skill_loaded_before_first_read"], bool):
                raise ValueError("sealed returned trace has malformed secondary metadata")
        metadata.append({
            "trial": trial.__dict__,
            "context_lines": analysis.CONTEXT_LINES[trial.task],
            "first_prompt_tokens": result.get("first_prompt_tokens"),
            "skill_loaded_before_first_read": result.get("skill_loaded_before_first_read"),
            "outcome": record["outcome"],
            "detail": record["detail"],
        })
    return canonical_json(metadata) + b"\n"


def _archive_and_analyze_locked(
    root: Path,
    output: Path,
    capsule: Path,
    analysis_output: Path,
    attestations: Path,
    *,
    manifest: dict[str, Any],
    registration: dict[str, str],
    execution_root: Path,
    assist_source: Path,
    assist_python: Path,
    workspace_root: Path,
) -> None:
    """Archive the verified reproduction, then perform the locked separate analysis."""
    _verify_archive_runtime(
        manifest=manifest,
        registration=registration,
        execution_root=execution_root,
        assist_source=assist_source,
        assist_python=assist_python,
        workspace_root=workspace_root,
    )
    attestation_files, intervals = verify_attestation_inventory(
        attestations, manifest=manifest, registration=registration
    )
    _preflight_live_json(output)
    bundle_path = output / "bundle.json"
    bundle = StudyBundle.read_verified(bundle_path)
    parent = manifest["parent"]
    if (
        bundle.sha256 != parent["bundle_sha256"]
        or _sha256(bundle_path) != parent["bundle_file_sha256"]
    ):
        raise ValueError("live parent bundle differs from registration")
    admissions, outcomes = _verified_progress(output, bundle)
    if _fidelity_error(outcomes):
        raise ValueError("persisted provider-request fidelity failure")
    if len(outcomes) != len(bundle.schedule):
        raise ValueError("incomplete reproduction cannot be archived")
    execution_events = verify_execution_intervals(
        intervals,
        admissions=admissions,
        outcomes=outcomes,
        thread_id=manifest["execution"]["coordination_thread_id"],
        schedule_size=len(bundle.schedule),
    )
    _verify_live_cooldowns(output, admissions, intervals)
    expected_metadata = _trial_metadata_from_traces(output, bundle, outcomes)
    worker_workspace = execution_root.parent / "worker-workspace"
    with _bound_invocation_paths(
        execution_root, assist_source, assist_python, worker_workspace, manifest
    ) as bound:
        env = _bound_execution_environment(bound, workspace_root, manifest, "archive worker")
        command = [
            str(bound["python"]), "-m",
            "studies.reach_for_instructions_confirmation_v8.runner", "archive",
            "--root", str(bound["execution"]), "--output", str(output),
            "--archive", str(capsule),
        ]
        result = _run_scoped(
            command,
            cwd=workspace_root,
            env=env,
            output=output,
            stage="archive worker",
            timeout_seconds=ARCHIVE_SCOPE_TIMEOUT_SECONDS,
        )
        if result.returncode:
            raise ValueError("parent archive returned a nonzero status")
    if (capsule / "trial-metadata.json").read_bytes() != expected_metadata:
        raise ValueError("archived trial metadata differs from sealed traces")
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
    seal = {
        "schema": "reach-v8-exact-reproduction-seal-v1",
        "manifest_sha256": digest(manifest),
        "sealed_files": _sealed_file_inventory(capsule),
    }
    atomic_write(capsule / "reproduction-seal.json", canonical_json(seal | {"seal_sha256": digest(seal)}) + b"\n")
    verify_reproduction_seal(capsule, manifest)


def _archive_and_analyze(
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
    if output.name != STUDY:
        raise ValueError("raw output ID differs from the fixed reproduction")
    if capsule.name != STUDY:
        raise ValueError("capsule ID differs from the fixed reproduction")
    if os.environ.get("CODEX_THREAD_ID") != COORDINATION_THREAD_ID:
        raise ValueError("archive coordinator identity differs from registration")
    if workspace_root.resolve() != _canonical_workspace_root(root):
        raise ValueError("archive workspace differs from the canonical shared workspace")
    _verify_runtime_paths(
        workspace_root=workspace_root,
        execution_root=execution_root,
        assist_source=assist_source,
        output=output,
        attestations=attestations,
        capsule=capsule,
    )
    _verify_fixed_path(
        "analysis output",
        analysis_output,
        capsule / "reproduction-analysis.json",
        workspace_root,
    )
    with _wrapper_lock(output):
        if output.is_symlink() or not output.is_dir():
            raise ValueError("reproduction output must be a real directory")
        if stat.S_IMODE(output.stat().st_mode) != 0o700:
            raise ValueError("reproduction output must have mode 0700")
        if _is_quarantined(output):
            raise ValueError("a quarantined reproduction cannot be archived")
        with _termination_interrupts():
            try:
                manifest = _load_manifest(root)
                registration = _verify_local_registration(root, manifest)
                if capsule.exists():
                    verify_reproduction_seal(capsule, manifest)
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
                    manifest=manifest,
                    registration=registration,
                    execution_root=execution_root,
                    assist_source=assist_source,
                    assist_python=assist_python,
                    workspace_root=workspace_root,
                )
            except BaseException as error:
                with _defer_termination_signals():
                    _quarantine(output, "archive or analysis integrity failed")
                if not isinstance(error, Exception):
                    raise
                raise ValueError(
                    "archive or analysis integrity failed; reproduction quarantined"
                ) from error


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
    """Archive with termination handling active before path or Git checks."""
    with _termination_interrupts():
        _archive_and_analyze(
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
