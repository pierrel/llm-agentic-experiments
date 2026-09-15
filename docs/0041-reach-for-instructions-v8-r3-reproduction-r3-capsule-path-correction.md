# Reach V8-r3 reproduction r3 capsule-path correction

## Historical supersessions

None. This records a later adjacent capsule-path gap; the earlier r3 records
remain valid for the integrity properties they describe.

## Correction

External review found that analysis rejected a symlinked capsule root but did
not reject symlinked evidence beneath a real root. A pinned historical hash
could therefore describe bytes reached through a link outside the capsule.
Capsule verification now fails if the full tree cannot be traversed, or if any
descendant is neither a real directory nor a regular nonsymlinked file, before
reading the run record, seals, report, metadata, or evidence chains.

This correction changes no treatment, fixture, prompt, schedule, oracle, model
profile, outcome, or analysis rule. R3 remains tag-pending with no runtime,
model admission, server change, or result.
