# Current Assist loop-budget baseline

## Evidence

- Sealed settings, fixture, model, architecture, and schedule: `bundle.json`,
  verified with the immutable `current-assist-baseline-v7` tag because this
  recorded run predates the current shared bundle schema.
- Admitted one-episode record and outcome seal: `admissions.jsonl[.seal]` and
  `outcomes.jsonl[.seal]`.
- Aggregate summary and raw-evidence hashes: `report.json` and `run.json`.
- Human-readable result: `reports/current-assist-baseline-v7.md`.

## Observation

The isolated current-Assist Deep Agents episode made one provider request but
hit its sealed recursion limit of 12 before returning the requested edit.

## Limits and counterexample

This is one reason-coded failure, not a comparison or a reliability estimate.
It does not show whether a different loop limit, model, reasoning setting,
prompt, or architecture would succeed.

## Handoffs

The experiment seed is `seeds/2026-08-24-current-assist-loop-budget-baseline.md`.
The private blog seed is
`larochelle.io/seeds/2026-08-24-a-loop-budget-is-a-condition.org`.
The proposed Assist investigation is `assist-roadmap-proposal.md`; neither
handoff authorizes a product change.
