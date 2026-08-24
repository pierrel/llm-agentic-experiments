# Synthetic MVP v2 measurement-path outcome

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

All four sealed scripted episodes passed after the implementation digest was
extended to include the package-initialization import closure. This validates
the no-model measurement path for that exact source set.

## Limits

The scripted provider cannot establish model behavior, treatment effects, or
transfer to the current Assist harness. Raw trace bodies remain untracked under
`results/raw/`; their hashes are retained in `run.json`.

## Handoffs

This is a harness-integrity result, not a blog seed or an Assist product change.
