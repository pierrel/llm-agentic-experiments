# Execution finding: current Deep Agents uses `edit_file` for the successful edit

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

The admitted current Assist model completed the fixture: it discovered and read
`budget-note.txt`, changed its content from `$20` to `$25` with `edit_file`,
and returned a completion. The primary artifact was correct.

The v7 oracle recorded `artifact_failure` because it recognized only a
`write_file` call after the read. This is an oracle mismatch, not a behavioral
failure. The sealed trace hash in `run.json` is the evidence source.

## Limits

One pilot episode cannot establish a general behavior, compare models or
architectures, or validate this corrected oracle. A new registration must test
the same artifact predicate while accepting the declared Deep Agents edit tool.

## Handoffs

This is a laboratory harness learning, not evidence for an Assist product
change or blog seed.
