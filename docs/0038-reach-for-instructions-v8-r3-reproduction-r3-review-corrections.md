# Reach V8-r3 reproduction r3 review corrections

## Historical supersessions

This record supersedes only the completion-validation description in
`docs/0037-reach-for-instructions-v8-r3-reproduction-r3.md` under
`Administrative recovery`. The earlier design remains a historical record.

## Corrections

External review found three integrity gaps before tagging or model admission.
Both a newly completed final batch and the completed-cohort shortcut now verify
the parent's final admission and outcome seals and the exact report and trace
digests before returning `complete`. Strict evidence decoding now rejects
JSON's non-standard `NaN` and infinity constants as well as duplicate members.
Runtime-attestation intervals must contain an admission, so a zero-progress
interval cannot satisfy the event chain vacuously.

These corrections change no treatment, fixture, prompt, schedule, oracle,
model profile, outcome, or analysis. R1 remains quarantined without
interpretation, r2 remains untagged and unexecuted, and r3 remains tag-pending
with no runtime or model admission.
