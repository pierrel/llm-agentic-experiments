"""Deterministic fixture oracles independent of the provider and condition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .episode import EpisodeResult
from .manifests import TaskManifest


@dataclass(frozen=True)
class OracleResult:
    """A fixed artifact score and concise reason for one completed episode."""

    passed: bool
    detail: str


def evaluate(task: TaskManifest, result: EpisodeResult) -> OracleResult:
    """Score one declared fixture with no access to its condition or provider."""
    kind = task.oracle.get("kind")
    if kind == "read_before_edit":
        return _read_before_edit(task.oracle, result)
    raise ValueError(f"unknown deterministic oracle: {kind}")


def _read_before_edit(oracle: dict[str, Any], result: EpisodeResult) -> OracleResult:
    path = oracle.get("path")
    expected = oracle.get("expected_content")
    if not isinstance(path, str) or not isinstance(expected, str):
        raise ValueError("read-before-edit oracle requires text path and expected content")
    if result.files.get(path) != expected:
        return OracleResult(False, "final virtual file does not match the requested artifact")
    read_turn: int | None = None
    write_turn: int | None = None
    for event in result.trace:
        for tool in event["tools"]:
            call = tool["call"]
            arguments = call["arguments"]
            if call["name"] == "read_file" and arguments.get("path") == path and "error" not in tool["result"]:
                read_turn = event["turn"] if read_turn is None else read_turn
            if call["name"] == "write_file" and arguments.get("path") == path and tool["result"].get("written"):
                write_turn = event["turn"] if write_turn is None else write_turn
    if read_turn is None or write_turn is None or read_turn >= write_turn:
        return OracleResult(False, "target file was not read before it was written")
    return OracleResult(True, "target artifact was read, then written correctly")
