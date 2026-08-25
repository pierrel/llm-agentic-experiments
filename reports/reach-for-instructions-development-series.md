# Reach-for-instructions development series

## Result

The final calibrated development cohort gives a narrow follow-up signal, not a
product conclusion. In the pinned current Assist Deep Agents loop, retrieved
guidance (`G02`) passed all three high-context episodes and automatically handed
guidance (`G01`) passed one of three. No comparable signal appears at the two
smaller context doses.

| First-request context | Handed `G01` | Retrieved `G02` |
| --- | ---: | ---: |
| `C-low`, about 6k tokens | 0/3 | 1/3 |
| `C-medium`, about 27k tokens | 0/3 | 0/3 |
| `C-high`, about 89k tokens | 1/3 | 3/3 |

The high-context 3/3 versus 1/3 cell is the only candidate region for a
held-out confirmation. It does not establish a general advantage, a context
threshold, or an Assist change.

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
new request and was the final allowed development variant. Its archived capsule
has 18 admissions, 18 terminal outcomes, sealed record chains, and hashes for
all retained local raw traces.

## Interpretation and next step

This work supports two durable process lessons. First, an instruction-delivery
hypothesis must be tested over a surface, not as one binary average: this task's
only promising region was the largest tested context. Second, a plausible cell
contrast is not evidence until the artifact oracle has been calibrated against
observed equivalent outputs.

The proposed next experiment is one held-out large-context task with a frozen,
independently reviewed artifact oracle and a larger predeclared sample. It should
retain the whole-policy contrast, report whether the guide was loaded before the
first source read, and make no Assist product change unless that confirmation is
positive. This development series does not test transfer across models,
reasoning settings, or harness architectures.
