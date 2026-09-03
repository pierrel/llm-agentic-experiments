# Access-transition oracle calibration gate v1

This model-free gate verifies the deterministic primary-oracle grammar required
before a new retrieved-versus-handed guidance confirmation can use the Cedar
Loop handoff task.

- **Unit:** one fixed, condition-blind structured-handoff corpus record.
- **Fixture:** `fixtures/reach-for-instructions-access-transition-handoff-v2.json`.
- **Intervention:** none. The gate evaluates a proposed oracle, not an agent.
- **Primary outcome:** every accepted corpus record passes and every rejected
  record fails under the same `handoff_is_grounded` function.
- **Status grammar:** accept an approved removal or revocation that is pending,
  unexecuted, unrevoked, or explicitly unrecorded. Reject an unrelated approved
  action, a completed/not-required revocation, or a bare active status.
- **Other facts:** require the one verified account (with no conflicting alias),
  Marisol with only the source-grounded security role forms, a badge-confirm and
  revoke next action, and an asset-tag/label uncertainty.
- **Decision:** fail closed on any corpus mismatch. A pass permits a fresh
  Qwen3.8 registration only; it cannot alter V1 or V2.
