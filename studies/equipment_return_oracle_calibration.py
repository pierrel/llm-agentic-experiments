"""Condition-blind semantic oracle calibration for the Dockside return task."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STUDY = "equipment-return-oracle-calibration-v1"
FIXTURE = "reach-for-instructions-equipment-return-handoff-v1.json"


def _contains(value: object, *terms: str) -> bool:
    return isinstance(value, str) and all(term in value.lower() for term in terms)


NEGATED_COMPLETION = (
    "not yet completed",
    "not yet complete",
    "not completed",
    "not complete",
    "never completed",
    "awaiting completion",
    "pending completion",
    "completion is pending",
    "completion pending",
    "incomplete",
)


def _status_is_grounded(value: object) -> bool:
    """Accept an approved but uncompleted return without inventing receipt."""
    if not isinstance(value, str):
        return False
    text = " ".join(value.lower().replace("_", " ").split())
    asserted = text
    for term in NEGATED_COMPLETION:
        asserted = asserted.replace(term, "")
    if "approved" not in text or any(term in asserted for term in ("complete", "completion", "received", "closed")):
        return False
    return "no receiving scan" in text or "pending" in text or "not complete" in text


def _owner_is_grounded(value: object, expected: str) -> bool:
    if not isinstance(value, str):
        return False
    owner = value.strip().lower()
    expected = expected.lower()
    return owner in {expected, f"{expected} (facilities)", f"{expected} (facilities owner)"}


def _action_is_grounded(value: object) -> bool:
    if not _contains(value, "confirm", "photo", "k-14", "close", "eq-204"):
        return False
    text = value.lower()
    return not any(term in text for term in ("not", "never", "without")) and text.find("confirm") < text.find("close")


def _uncertainty_is_grounded(value: object) -> bool:
    """Allow an unresolved attachment question, never an asserted attachment."""
    if not _contains(value, "p-19", "p-19a", "k-14"):
        return False
    text = value.lower()
    if "do not establish which" in text and "attached" in text:
        return True
    return "unresolved" in text and any(term in text for term in ("label", "belongs", "assigned"))


def handoff_is_grounded(task: dict[str, Any], handoff: object) -> bool:
    """Evaluate the complete fixture-grounded handoff boundary."""
    required = {"case_id", "return_status", "next_owner", "next_action"}
    if not isinstance(handoff, dict) or not required.issubset(handoff):
        return False
    expected = task["oracle"]["expected"]
    equipment = [handoff[key] for key in ("equipment_id", "verified_equipment_id") if key in handoff]
    uncertainty = handoff.get("uncertainty", handoff.get("remaining_uncertainty"))
    return all((
        handoff.get("case_id") == expected["case_id"],
        bool(equipment) and all(isinstance(value, str) for value in equipment) and set(equipment) == {expected["equipment_id"]},
        _status_is_grounded(handoff.get("return_status")),
        _owner_is_grounded(handoff.get("next_owner"), expected["next_owner"]),
        _action_is_grounded(handoff.get("next_action")),
        _uncertainty_is_grounded(uncertainty),
    ))


def verify(root: Path) -> None:
    """Fail closed unless every predeclared calibration label is correct."""
    root = root.resolve()
    task = json.loads((root / "fixtures" / FIXTURE).read_text())
    corpus = json.loads((root / "experiments" / STUDY / "corpus.json").read_text())
    if not isinstance(corpus, dict) or set(corpus) != {"accepted", "rejected"}:
        raise ValueError("equipment-return calibration corpus shape is invalid")
    names: set[str] = set()
    for label, expected in (("accepted", True), ("rejected", False)):
        cases = corpus[label]
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"equipment-return calibration {label} cases are missing")
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"name", "handoff"} or not isinstance(case["name"], str) or case["name"] in names:
                raise ValueError("equipment-return calibration case shape is invalid")
            names.add(case["name"])
            if handoff_is_grounded(task, case["handoff"]) != expected:
                raise ValueError(f"equipment-return calibration mismatch: {label}:{case['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    verify(args.root)


if __name__ == "__main__":
    main()
