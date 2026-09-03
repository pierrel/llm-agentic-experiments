"""Condition-blind calibration gate for the Cedar Loop handoff oracle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


STUDY = "access-transition-oracle-calibration-v1"
FIXTURE = "reach-for-instructions-access-transition-handoff-v2.json"


def _contains(value: object, *terms: str) -> bool:
    return isinstance(value, str) and all(term in value.lower() for term in terms)


def _status_is_grounded(value: object) -> bool:
    """Accept only fixture-grounded forms of an approved, incomplete removal."""
    if not isinstance(value, str):
        return False
    status = " ".join(value.lower().replace("_", " ").split())
    if "approved" not in status or "not approved" in status:
        return False
    if any(term in status for term in ("complet", "not required", "not only")):
        return False
    if "pending revocation" in status:
        return True
    if "no revocation has been recorded" in status:
        return True
    revoked = re.search(r"\brevoked\b", status)
    negated_revocation = re.search(r"\b(?:not|never)(?:\s+\w+){0,2}\s+revoked\b", status)
    if revoked and not negated_revocation:
        return False
    incomplete = re.search(r"\bnot(?:\s+\w+){0,2}\s+(?:execut\w*|revok\w*)\b", status)
    return bool(
        incomplete
        and ("remov" in status or "revo" in status)
    )


def _owner_is_grounded(value: object, expected: str) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    expected = expected.lower()
    return normalized in {expected, f"{expected} (security)", f"{expected} (security owner)"}


def _action_is_grounded(value: object) -> bool:
    if not _contains(value, "confirm", "badge", "b-77", "revok", "ced-118"):
        return False
    text = value.lower()
    if any(term in text for term in ("not", "never", "nothing", "without")):
        return False
    return text.find("confirm") < text.find("revok")


def _uncertainty_is_grounded(value: object) -> bool:
    if not _contains(value, "asset", "cl-04", "cl-04a"):
        return False
    text = value.lower()
    if any(term in text for term in ("definitely", "no uncertainty", "not unresolved", "not uncertain", "not established", "attached")):
        return False
    return any(term in text for term in ("unresolved", "uncertain", "not establish"))


def handoff_is_grounded(task: dict[str, Any], handoff: object) -> bool:
    """Score the complete semantic boundary shared by the future runtime oracle."""
    required = {"case_id", "access_status", "next_owner", "next_action"}
    if not isinstance(handoff, dict) or not required.issubset(handoff):
        return False
    expected = task["oracle"]["expected"]
    account_values = [handoff[key] for key in ("account_id", "verified_account_id") if key in handoff]
    uncertainty = handoff.get("uncertainty", handoff.get("remaining_uncertainty"))
    action = handoff.get("next_action")
    return all((
        handoff.get("case_id") == expected["case_id"],
        bool(account_values) and all(isinstance(value, str) for value in account_values) and set(account_values) == {expected["account_id"]},
        _status_is_grounded(handoff.get("access_status")),
        _owner_is_grounded(handoff.get("next_owner"), expected["next_owner"]),
        _action_is_grounded(action),
        _uncertainty_is_grounded(uncertainty),
    ))


def verify(root: Path) -> None:
    """Fail closed unless every declared calibration case has its declared label."""
    root = root.resolve()
    task = json.loads((root / "fixtures" / FIXTURE).read_text())
    corpus = json.loads((root / "experiments" / STUDY / "corpus.json").read_text())
    if not isinstance(corpus, dict) or set(corpus) != {"accepted", "rejected"}:
        raise ValueError("oracle calibration corpus shape is invalid")
    names: set[str] = set()
    for label, expected in (("accepted", True), ("rejected", False)):
        cases = corpus[label]
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"oracle calibration {label} cases are missing")
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"name", "handoff"} or not isinstance(case["name"], str) or case["name"] in names:
                raise ValueError("oracle calibration case shape is invalid")
            names.add(case["name"])
            if handoff_is_grounded(task, case["handoff"]) != expected:
                raise ValueError(f"oracle calibration mismatch: {label}:{case['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    verify(args.root)


if __name__ == "__main__":
    main()
