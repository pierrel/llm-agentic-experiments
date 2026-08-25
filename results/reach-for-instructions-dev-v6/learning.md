# Development learning: the promising delivery difference is localized, not general

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

This final development cohort recorded 18 admitted, terminal episodes. At the
largest predeclared context dose (`C-high`, about 89k first-request tokens),
retrieved guidance (`G02`) passed 3/3 while automatically handed guidance
(`G01`) passed 1/3. At `C-medium` (about 27k tokens), neither condition passed;
at `C-low` (about 6k tokens), `G02` passed 1/3 and `G01` passed 0/3.

The V5 apparent high-context contrast was partly an oracle error: two handed
handoffs used the direct `not_issued` status that V5 did not accept. V6 accepts
that form equally in both conditions, leaving a smaller 3/3 versus 1/3
high-context contrast. The useful development learning is therefore not that
retrieval generally wins. It is that the proposed effect, if real for this
runtime, is conditional: a large-context region is the only promising region
in this screen and must be confirmed on held-out tasks before changing Assist.

## Limits

Three episodes per cell are a development screen, not a stable effect estimate.
The local provider has no sealed sampling seed, and the same reimbursement task
was used across all doses. This result cannot establish a general retrieved-
versus-handed effect, a monotonic context threshold, causation from loading
alone, or transfer to another task, model, reasoning setting, or harness
architecture. Both arms exposed the same loading tool by design; one successful
handed high-context episode also loaded the guide before its first source read.

## Handoffs

Add a private blog seed about treating instruction-delivery claims as response
surfaces and calibrating the oracle before interpreting a contrast. The proposed
Assist roadmap item is a held-out confirmation at the promising large-context
region. Neither handoff authorizes an Assist change by itself.
