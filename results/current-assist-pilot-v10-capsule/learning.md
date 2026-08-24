# Execution finding: marker-backed current Assist baseline pass

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

The first scheduled attempt was denied before a model request because production
reserved the GPU. The same sealed episode was admitted on its second attempt,
read `/budget-note.txt`, used `edit_file(file_path)`, and produced the exact
required final content. The sealed pre-invoke marker is present, so the v10
outcome's `model_request_made: true` is evidence-backed.

## Limits

This is one smoke-test episode, not a behavioral effect estimate. It does not
establish reliability, transfer to other tests/models/harnesses/reasoning
settings, or a product change. The raw trace remains untracked locally under
`results/raw/`; its SHA-256 is retained in `run.json`.

## Handoffs

This is baseline evidence for later comparisons, not a blog seed or a proposed
Assist change.
