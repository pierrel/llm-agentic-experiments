# Proposed Assist roadmap item

## Proposed outcome

Before changing Assist's default instruction-delivery policy, run one locked,
held-out confirmation that compares automatic guidance with a shape-matched
retrieved guide in the pinned Deep Agents loop at a large-context dose.

## Evidence and limits

`results/reach-for-instructions-dev-v6/` is an exploratory 18-episode
development screen. Its only promising cell was `C-high`: retrieved `G02`
passed 3/3 and handed `G01` passed 1/3 after the shared `not_issued` oracle
normalization. The remaining cells do not show a general advantage. A distinct
task and a frozen oracle are required before interpreting this as a product
direction.

The confirmation must preserve current Assist behavior outside the study: its
general system instructions, available skills, user-facing task flow, and
existing behavioral-eval coverage remain unchanged until a confirmed result
justifies a narrowly scoped design decision.

## Product action

Add a lab-to-Assist roadmap item: "Confirm the reach-for-instructions signal on
a held-out large-context operational task, with an independently frozen
artifact oracle, before changing how Assist supplies procedural guidance."
Do not implement or merge an Assist change from this file without Pierre's
explicit decision.
