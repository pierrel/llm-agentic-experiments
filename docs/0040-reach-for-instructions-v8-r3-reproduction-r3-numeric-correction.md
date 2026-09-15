# Reach V8-r3 reproduction r3 numeric correction

## Historical supersessions

This record supersedes only the numeric-decoding conclusion in
`docs/0038-reach-for-instructions-v8-r3-reproduction-r3-review-corrections.md`
under `Corrections`. Its other corrections, the scientific design, and the
stop boundary remain unchanged.

## Correction

External review found that rejecting JSON's named `NaN` and infinity constants
did not reject a syntactically ordinary decimal exponent that Python converts
to infinity, such as `1e999`. The strict evidence decoder now rejects any
floating-point token whose decoded value is not finite. This applies to every
JSON and JSONL evidence path that uses the registered strict decoder.

This correction changes no treatment, fixture, prompt, schedule, oracle, model
profile, outcome, or analysis rule. R3 remains tag-pending with no runtime,
model admission, server change, or result.
