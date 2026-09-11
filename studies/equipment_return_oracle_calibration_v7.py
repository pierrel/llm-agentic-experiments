"""Condition-blind semantic oracle calibration for V7's held-out return task."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STUDY = "equipment-return-oracle-calibration-v7"
FIXTURE = "reach-for-instructions-equipment-return-handoff-v7.json"


def _contains(value: object, *terms: str) -> bool:
    return isinstance(value, str) and all(term in value.lower() for term in terms)


def _normalise(value: object) -> str:
    return " ".join(value.lower().replace("_", " ").split()) if isinstance(value, str) else ""


def _status_is_grounded(return_status: object, approval_status: object) -> bool:
    """Accept the documented compact status only with its separate approval fact."""
    status, approval = _normalise(return_status), _normalise(approval_status)
    if not status or "received" in status or "closed" in status or ("completed" in status and "not completed" not in status):
        return False
    if "approved" in status:
        return any(term in status for term in ("pending", "not complete", "no receiving scan"))
    return (
        status in {"not completed", "return not completed"}
        and "approved" in approval
        and "conditional" in approval
        and "photo" in approval
        and "maren" in approval
        and not any(term in approval for term in ("not approved", "not conditionally approved", "no approval", "rejected"))
        and not any(term in approval for term in ("completed", "received", "closed"))
    )


def _owner_is_grounded(value: object, expected: str) -> bool:
    owner = _normalise(value)
    return owner in {expected.lower(), f"{expected.lower()} (operations)", f"{expected.lower()} (operations owner)"}


def _action_is_grounded(value: object) -> bool:
    if not _contains(value, "confirm", "photo", "k-22", "close", "ea-311"):
        return False
    text = value.lower()
    return not any(term in text for term in ("not", "never", "without")) and text.find("confirm") < text.find("close")


def _uncertainty_is_grounded(value: object) -> bool:
    if not _contains(value, "r-7", "r-7b", "k-22"):
        return False
    text = value.lower()
    if any(claim in text for claim in ("r-7 is attached", "r-7b is attached", "r-7 attached", "r-7b attached", "r-7 is assigned", "r-7b is assigned")):
        return False
    if "do not establish which" in text and "attached" in text:
        return True
    return (
        "unresolved" in text
        and any(term in text for term in ("whether", "which"))
        and any(term in text for term in ("label", "belongs", "assigned"))
    )


def handoff_is_grounded(task: dict[str, Any], handoff: object) -> bool:
    """Evaluate the complete held-out fixture-grounded handoff boundary."""
    required = {"case_id", "return_status", "approval_status", "next_owner", "next_action"}
    if not isinstance(handoff, dict) or not required.issubset(handoff):
        return False
    expected = task["oracle"]["expected"]
    equipment = [handoff[key] for key in ("equipment_id", "verified_equipment_id") if key in handoff]
    uncertainty = handoff.get("uncertainty", handoff.get("remaining_uncertainty"))
    return all((
        handoff.get("case_id") == expected["case_id"],
        bool(equipment) and all(isinstance(value, str) for value in equipment) and set(equipment) == {expected["equipment_id"]},
        _status_is_grounded(handoff.get("return_status"), handoff.get("approval_status")),
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
        raise ValueError("V7 equipment-return calibration corpus shape is invalid")
    names: set[str] = set()
    for label, expected in (("accepted", True), ("rejected", False)):
        cases = corpus[label]
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"V7 equipment-return calibration {label} cases are missing")
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"name", "handoff"} or not isinstance(case["name"], str) or case["name"] in names:
                raise ValueError("V7 equipment-return calibration case shape is invalid")
            names.add(case["name"])
            if handoff_is_grounded(task, case["handoff"]) != expected:
                raise ValueError(f"V7 equipment-return calibration mismatch: {label}:{case['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    verify(args.root)


if __name__ == "__main__":
    main()
