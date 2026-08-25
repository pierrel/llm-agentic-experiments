# Development observation: V2's apparent failures are an oracle mismatch

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

The low-context episode passed. The medium and high episodes were scored as
artifact failures solely because their handoffs did not include the literal
substring “one receipt image.” Both retained the required substantive fact:
they state that Finance must choose which receipt image remains, identify the
two alternatives, and preserve the unresolved selection.

This is evidence that V2's exact-phrase oracle was too narrow for an output
that satisfies the convention's semantic requirement. It is not evidence of
context-length degradation.

## Limits

One fresh episode per condition cannot estimate behavior rates. More
importantly, an exact phrase test cannot stand in for the semantic fact here.
The raw traces support an oracle revision, not a model or Assist conclusion.

## Handoffs

V3 holds the higher-complexity fixture and context intervention fixed while
replacing this one brittle phrase check with explicit acceptable evidence forms.
That alternate oracle is a new sealed development variant, not a rewrite of V2.
