"""Tests for the standalone access-transition oracle calibration gate."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from studies.access_transition_oracle_calibration import handoff_is_grounded, verify


ROOT = Path(__file__).resolve().parents[1]


class AccessTransitionOracleCalibrationTest(unittest.TestCase):
    def test_declared_corpus_passes(self) -> None:
        verify(ROOT)

    def test_new_grounded_status_forms_pass(self) -> None:
        task = json.loads((ROOT / "fixtures" / "reach-for-instructions-access-transition-handoff-v2.json").read_text())
        handoff = {
            "case_id": "CL-2704", "account_id": "CED-118",
            "access_status": "Active: removal approved but not yet executed.",
            "next_owner": "Marisol (security)",
            "next_action": "Confirm badge B-77 handoff, then revoke access for CED-118.",
            "uncertainty": "The asset tags CL-04 and CL-04A remain unresolved.",
        }
        self.assertTrue(handoff_is_grounded(task, handoff))

    def test_adversarial_statuses_fail(self) -> None:
        task = json.loads((ROOT / "fixtures" / "reach-for-instructions-access-transition-handoff-v2.json").read_text())
        base = {
            "case_id": "CL-2704", "account_id": "CED-118", "next_owner": "Marisol",
            "next_action": "Confirm badge B-77 handoff, then revoke access for CED-118.",
            "uncertainty": "The asset tags CL-04 and CL-04A remain unresolved.",
        }
        for status in ("The approved badge handoff was not executed.", "Removal was not approved and was not executed.", "Removal approved but revocation is not required.", "Removal was approved, then revocation was completed.", "Pending revocation was completed yesterday.", "Removal approved, not only executed but revoked.", "Removal approved but not yet executed; access was revoked."):
            self.assertFalse(handoff_is_grounded(task, base | {"access_status": status}))
        self.assertFalse(handoff_is_grounded(task, base | {"next_action": "Revoke CED-119, then confirm badge B-99."}))
        self.assertFalse(handoff_is_grounded(task, base | {"next_action": "Do not confirm the badge; revoke nothing."}))
        self.assertFalse(handoff_is_grounded(task, base | {"next_action": "Never confirm badge B-77; then revoke access for CED-118."}))
        self.assertFalse(handoff_is_grounded(task, base | {"next_action": "Confirm badge B-77, then do not revoke access for CED-118."}))
        self.assertFalse(handoff_is_grounded(task, base | {"uncertainty": "The asset tag CL-04 is definitely attached."}))
        self.assertFalse(handoff_is_grounded(task, base | {"uncertainty": "The asset tags CL-04 and CL-04A are not unresolved."}))
        self.assertFalse(handoff_is_grounded(task, base | {"uncertainty": "Asset CL-04 is attached; CL-04A remains unresolved."}))
        for account in ([], {}, ["CED-118"]):
            self.assertFalse(handoff_is_grounded(task, base | {"account_id": account}))

    def test_gate_rejects_a_mislabeled_case(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in ("fixtures", "experiments/access-transition-oracle-calibration-v1"):
                source = ROOT / relative
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    import shutil
                    shutil.copytree(source, destination)
                else:
                    destination.write_bytes(source.read_bytes())
            path = root / "experiments" / "access-transition-oracle-calibration-v1" / "corpus.json"
            corpus = json.loads(path.read_text())
            corpus["accepted"][0]["handoff"]["access_status"] = "active"
            path.write_text(json.dumps(corpus))
            with self.assertRaisesRegex(ValueError, "mismatch"):
                verify(root)


if __name__ == "__main__":
    unittest.main()
