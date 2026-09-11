"""Condition-blind semantic oracle calibration for V8's fresh return task."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


STUDY = "equipment-return-oracle-calibration-v8"
FIXTURE = "reach-for-instructions-equipment-return-handoff-v8.json"


def _normalise(value: object) -> str:
    return " ".join(value.lower().replace("_", " ").split()) if isinstance(value, str) else ""


def _status_is_grounded(return_status: object, approval_status: object) -> bool:
    """Require conditional approval and a still-pending intake photo in either form."""
    status, approval = _normalise(return_status), _normalise(approval_status)
    completion_residue = status.replace("not completed", "").replace("not complete", "")
    if not status or "received" in status or "closed" in status or re.search(r"\bcomplet(?:e|ed)\b", completion_residue):
        return False
    approval_is_grounded = (
        "approved" in approval
        and "conditional" in approval
        and "photo" in approval
        and any(term in approval for term in ("pending", "awaiting"))
        and not any(term in approval for term in ("not approved", "not conditionally approved", "no approval", "rejected", "completed", "received", "closed", "photo was confirmed", "photo is confirmed", "photo has been confirmed", "photo confirmed", "intake photo confirmed"))
    )
    if "approved" in status:
        return "not approved" not in status and any(term in status for term in ("pending", "not complete", "no receiving scan")) and approval_is_grounded
    return status in {"not completed", "return not completed"} and approval_is_grounded


def _owner_is_grounded(value: object, expected: str) -> bool:
    owner = _normalise(value)
    return owner in {expected.lower(), f"{expected.lower()} (operations)", f"{expected.lower()} (operations owner)"}


def _action_is_grounded(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.lower()
    confirm = re.search(r"\bconfirm\b", text)
    close = re.search(r"\bclose\b", text)
    return (
        confirm is not None
        and close is not None
        and re.search(r"(?<![a-z0-9-])k-31(?![a-z0-9-])", text) is not None
        and re.search(r"(?<![a-z0-9-])eb-507(?![a-z0-9-])", text) is not None
        and "photo" in text
        and not any(term in text for term in ("not", "never", "without"))
        and confirm.start() < close.start()
    )


def _has_unsupported_label_claim(value: object) -> bool:
    """Reject a direct label relationship while allowing an unresolved alternative."""
    if not isinstance(value, str):
        return False
    clauses = re.split(r"(?:[.;]|\b(?:but|though|however)\b)", value.lower())
    pattern = re.compile(r"(?<![a-z0-9-])s-4b?(?![a-z0-9-])\s+(?:is\s+)?(?:attached|assigned|belongs)\b")
    return any(pattern.search(clause) and "s-4 or s-4b" not in clause for clause in clauses)


def _uncertainty_is_grounded(value: object) -> bool:
    if not isinstance(value, str) or not all(re.search(rf"(?<![a-z0-9-]){re.escape(label)}(?![a-z0-9-])", value.lower()) for label in ("s-4", "s-4b", "k-31")):
        return False
    text = value.lower()
    if "not unresolved" in text or _has_unsupported_label_claim(text):
        return False
    if "do not establish which" in text and "attached" in text:
        return True
    return "unresolved" in text and any(term in text for term in ("whether", "which")) and any(term in text for term in ("label", "belongs", "assigned"))


def handoff_is_grounded(task: dict[str, Any], handoff: object) -> bool:
    """Evaluate the full fresh-fixture handoff boundary without a supervisor-name rule."""
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
        not any(_has_unsupported_label_claim(value) for value in handoff.values()),
    ))


def verify(root: Path) -> None:
    """Fail closed unless every predeclared calibration label is correct."""
    root = root.resolve()
    task = json.loads((root / "fixtures" / FIXTURE).read_text())
    corpus = json.loads((root / "experiments" / STUDY / "corpus.json").read_text())
    if not isinstance(corpus, dict) or set(corpus) != {"accepted", "rejected"}:
        raise ValueError("V8 equipment-return calibration corpus shape is invalid")
    names: set[str] = set()
    for label, expected in (("accepted", True), ("rejected", False)):
        cases = corpus[label]
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"V8 equipment-return calibration {label} cases are missing")
        for case in cases:
            if not isinstance(case, dict) or set(case) != {"name", "handoff"} or not isinstance(case["name"], str) or case["name"] in names:
                raise ValueError("V8 equipment-return calibration case shape is invalid")
            names.add(case["name"])
            if handoff_is_grounded(task, case["handoff"]) != expected:
                raise ValueError(f"V8 equipment-return calibration mismatch: {label}:{case['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    verify(args.root)


if __name__ == "__main__":
    main()
