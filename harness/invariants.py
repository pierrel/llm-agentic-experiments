"""Fail-closed checks for declared condition differences and reviewer packets."""

from __future__ import annotations

from typing import Any

from .bundle import canonical_json


def assert_equal_except(
    left: dict[str, Any], right: dict[str, Any], allowed_top_level: set[str]
) -> None:
    """Reject an undeclared top-level condition difference.

    A study declaration must name every rendered request, schema, fixture, or
    decoding field it is allowed to vary. This deliberately conservative starter
    check is extended with path-level allowlists only when a registered study
    needs them.
    """
    keys = set(left) | set(right)
    for key in keys - allowed_top_level:
        if key not in left or key not in right or canonical_json(left[key]) != canonical_json(right[key]):
            raise ValueError(f"undeclared condition difference: {key}")


def assert_no_condition_label(packet: str, labels: set[str]) -> None:
    """Reject treatment names from a qualitative-review packet."""
    def normalize(text: str) -> str:
        return "".join(character for character in text.casefold() if character.isalnum())

    normalized_packet = normalize(packet)
    leaked = sorted(label for label in labels if label and normalize(label) in normalized_packet)
    if leaked:
        raise ValueError(f"condition label leaked into review packet: {', '.join(leaked)}")
