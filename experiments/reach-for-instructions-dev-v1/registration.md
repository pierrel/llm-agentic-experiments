# Reach-for-instructions development registration v1

## Question

For the pinned current Assist Deep Agents loop and model, does a reimbursement
handoff procedure work better when the agent retrieves it through a
shape-matched skill than when the host presents the same procedure in system
context before the first decision?

This is a whole-policy comparison. The reached condition includes the decision
to load the guide, while the handed condition receives it automatically. It is
not a claim that a tool-result message is intrinsically stronger than the same
text in a system message.

## Conditions

Both arms expose the same `load_skill(name)` tool and the same catalog entry for
`reconcile-reimbursement`. The tool returns the same procedure in either arm.
The handed arm additionally includes that procedure in system context before the
first decision. The reached arm includes only the catalog entry until the agent
calls the tool. The model, filesystem backend, tool schemas, fixture, user
request, decoding, recursion limit, and skill body are otherwise fixed.

## Development response surface

The only response-surface axis is inert system-context length. `C-low`,
`C-medium`, and `C-high` contain 0, 900, and 3600 deterministic declarative
filler lines, respectively. Actual first-request provider input tokens are
recorded rather than inferred from filler size. Context length is crossed with
guidance delivery, for six cells. Each cell has three fresh episodes, scheduled
in deterministic pseudorandom order. The current local provider offers no
sealed generation-seed control, so trial seeds are schedule identities rather
than matched sampling seeds. This is a development screen, not a
confirmation cohort and not an estimate of a general threshold.

Task complexity and catalog size are held fixed. A future version may vary one
of them only after this screen, under a new sealed registration.

## Outcomes and accounting

The primary outcome is artifact-plus-procedure success: one JSON handoff with
the declared fields and values, no source-file mutation, and a trace showing an
inventory plus every source record read before the handoff write. The secondary
process outcome records whether `reconcile-reimbursement` was loaded before the
first source-record read. The primary oracle receives no condition label and
does not require literal natural-language phrases; structured values and trace
order avoid the prior context-length study's phrase-equivalence defect.

An episode is one fresh process, conversation, fixture, and tool state. Every
admitted terminal episode is retained with a reason code. A shared-GPU denial
is recorded administratively and the same sealed trial is retried before the
schedule advances. Timeout, refusal, invalid tool call, provider error, and
loop exhaustion score primary failure.

## Interpretation rule

Report every cell's success count, process outcome, first-request token count,
and reason-coded failures. Treat an observed difference as development evidence
only. Do not claim transfer across models, reasoning settings, harnesses, task
complexities, or catalog sizes. If no detectable difference appears, this
registered version ends; any follow-up is a separately reviewed sealed variant
under the laboratory's autonomous-development process.
