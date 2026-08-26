# V6 interpretation withdrawn: provider-request fidelity was not retained

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

V6 completed 18 admitted episodes, but a post-run local review found that the
runtime callback path left every retained provider-request capture empty. The
runner also had no request-contract check before scoring. Its numerical outcomes
are preserved in this capsule but are not interpretable evidence about guidance
delivery, because the exact provider-facing prompt and tool schema were not
auditable.

## Limits

V6 cannot establish any delivery effect, context threshold, or product action.
It also cannot transfer across tasks, models, reasoning settings, or harnesses.

## Handoffs

The runner correction receives a fresh, non-result-informed V7 validation run
with the unchanged final fixture, conditions, schedule, and oracle. Do not make
an Assist change or a blog learning from V6's numerical cells.
