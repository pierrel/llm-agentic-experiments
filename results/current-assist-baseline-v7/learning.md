# Current Assist loop-budget baseline

## Evidence

- Sealed settings, fixture, model, architecture, and schedule: `bundle.json`,
  verified with source commit `a86178599a2d2ac2da76c24a645dcfa2ed47acbc`
  because this recorded run predates the current shared bundle schema. The
  original registration sealed the tag name, not this resolved commit ID.
- Admitted one-episode record and outcome seal: `admissions.jsonl[.seal]` and
  `outcomes.jsonl[.seal]`.
- Aggregate summary and raw-evidence hashes: `report.json` and
  `raw-evidence.json`. `run.json` retains the standard empty raw-trace map:
  this pilot captured pre-provider input, not a trace body.
- Human-readable result: `reports/current-assist-baseline-v7.md`.

## Observation

The isolated current-Assist Deep Agents episode captured one pre-provider
request but hit its sealed recursion limit of 12 before returning the requested
edit.

## Limits and counterexample

This is one historical-pilot failure, not a comparison or a reliability
estimate. Its minimum-adequate-setup review was post-run. It does not show
whether a different loop limit, model, reasoning setting, prompt, or
architecture would succeed.

## Handoffs

The experiment seed is `seeds/2026-08-24-current-assist-loop-budget-baseline.md`.
The private blog seed is
`larochelle.io/seeds/2026-08-24-a-loop-budget-is-a-condition.org`.
The proposed Assist investigation is `assist-roadmap-proposal.md`; neither
handoff authorizes a product change.
