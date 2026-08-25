# Reach-for-instructions development series

## Status

V6's 18 outcome records are preserved but withdrawn from interpretation. A
post-run review found that the callback used by the current runtime did not
retain any provider-facing requests, and V6 did not reject a request-fidelity
mismatch before scoring. V7 repeated the unchanged final design with a sealed
post-middleware provider-request digest for every trial and an exact
model-boundary comparison on every live episode. All 18 V7 episodes met that
contract, so its result is the first interpretable development evidence.

## Setup

Each fresh episode used the current Deep Agents filesystem/tool loop with the
pinned Assist revision `45762e5831a5c656a68677cbb6f43338eb954e0c`, Deep Agents
0.6.1, and local `Qwen_Qwen3.6-27B-Q4_K_M.gguf` with reasoning disabled,
temperature 0.1, and a 1,200-token output limit. The natural user request asked
for a reimbursement handoff from local records. It did not name a skill, tool,
output path, or oracle.

Both opaque conditions had the same tools, catalog entry, synthetic files,
procedure body, decoding settings, and three inert context doses. `G01` also
received the procedure in system context before its first decision. `G02`
received only the catalog entry until it chose to call `load_skill`. Success
required exactly one grounded JSON handoff, unchanged source files, an inventory
and every source read before writing. The deterministic artifact oracle was
condition-blind.

## Development history

The first three sealed registrations were stopped before a model request because
runtime checks caught, respectively, an invalid worker environment, an unsafe
new-output-directory mode, and a relative artifact path after admission. They
remain in the registry as setup evidence, not failed model trials.

V4 completed 18 model episodes but the original literal-field oracle rejected
otherwise usable handoffs. V5 predeclared broader field aliases and exposed a
3/3 versus 0/3 high-context contrast. Trace review found that two handed
handoffs had only used the equally direct status `not_issued`, which V5 had not
accepted. V6 added that one normalization equally to both conditions before any
new request and completed its 18 episodes. Its archived capsule has 18
admissions, 18 terminal outcomes, sealed record chains, and hashes for all
retained local raw traces. The later review found that its retained request
arrays were empty, so V6 is invalid for interpretation.

V7 is a fresh validation version, not an additional result-informed treatment
change. It produced 5/9 complete artifact passes for retrieved `G02` and 2/9
for always-present `G01`. By context dose, the cells were `G01/G02`: 0 lines
`0/3` versus `1/3`; 900 lines `0/3` versus `1/3`; 3,600 lines `2/3` versus
`3/3`. The treatment loaded the skill before the first source read in 5/9
episodes. No delivery-by-context cell has more than three fresh trials.

## Interpretation and next step

The durable process lesson is stricter than the provisional result: an
instruction-delivery contrast is uninterpretable until both the artifact oracle
and the provider-facing request have been audited. The valid V7 result is
directional enough to justify one preregistered held-out task confirmation, but
not a product change. It does not establish why performance rose in the
high-context cells, a context threshold, or transfer across models, reasoning
settings, or harness architectures.
