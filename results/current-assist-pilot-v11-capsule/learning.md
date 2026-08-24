# Execution finding: malformed traces cannot strand the current baseline

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

The admitted current Assist model completed the one scheduled episode. It read
`/budget-note.txt`, used `edit_file(file_path)`, and produced the exact
required final content. The successful outcome's model-request claim is backed
by the sealed pre-invoke marker; a deterministic companion test proves that a
malformed trace instead finalizes as a marker-backed provider error.

## Limits

This is one smoke-test episode, not a behavioral effect estimate. It does not
establish reliability, transfer to other tests/models/harnesses/reasoning
settings, or a product change. The raw trace remains untracked locally under
`results/raw/`; its SHA-256 is retained in `run.json`.

## Handoffs

This is baseline evidence for later comparisons, not a blog seed or a proposed
Assist change.
