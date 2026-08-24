# Durable-promise orchestration v3: interrupted development screen

## Status

This is an incomplete and invalidated development screen, not evidence for a
release decision. It preserves the first 16 valid episodes of the sealed v3
schedule and the exact administrative interruption that prevented episodes 17
and 18 from starting. No historical record has been removed or rewritten.

The raw, private evidence remains at
`results/raw/durable-orchestration-v3.6Y7Xcj` on the lab host. Its public
integrity anchors are:

| Item | SHA-256 |
| --- | --- |
| Sealed bundle | `f492db209c78490314a5d1b41250ce506a3fb43de00318d5fccf85c328260c8f` |
| Admission chain after 16 episodes | `81cfb108aa8341a7994123c6d8001f22aff7fa57d93452db9419f079003203c9` |
| Outcome chain after 16 episodes | `8accd09fa671e00e63d972a13c9259a25a0163df2a1645534f0a9a21e0ca2058` |

## Question and treatments

The screen tested whether this general prompt rider, on top of the confirmed
durable-memory C1 guidance, improved completion of a mixed ordinary-web turn:

> When one user turn has multiple independently valuable outcomes and you start
> tool, skill, or asynchronous work on one, use a short todo list with one
> outcome per item if that work could cause another to be missed. Mark each item
> complete only when the outcome is actually done, then reconcile the list before
> replying. The todo list tracks this turn; it does not replace any user-requested
> file, schedule, or durable thread-memory record.

`C0` used the same Assist revision, fresh thread, sandbox, local fixture,
model, decoding, async context route, durable-memory guidance, and ordinary
framework todo prompt without that rider. `C1` added only the rider through the
opt-in prompt middleware. One experimental unit was one fresh web-main thread.

Each natural row asked for a grounded current answer plus a future conditional
action. A full pass required correct grounding lifecycle, factual answer and
honesty, post-result durable private-memory capture of the condition/action,
and no unsupported completion claim. Todo use and reconciliation were
secondary manipulation checks; todos could not substitute for durable memory.

## Completed results

Each cell is passes out of three completed repetitions. The workshop row has
only two repetitions per condition because the interruption occurred before its
third block.

| Row | C0 full | C1 full | C0 durable memory | C1 durable memory | C0 todo used | C1 todo used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Profile-leading check-in | 2/3 | 1/3 | 2/3 | 1/3 | 1/3 | 1/3 |
| Profile-trailing check-in | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| Workshop measurements | 2/2 | 0/2 | 2/2 | 1/2 | 0/2 | 0/2 |

Grounding routing and factual answer/honesty were 3/3 for both conditions on
both profile rows. On workshop they were 2/2 for C0 and 1/2 for C1. The C1
rider therefore did not reliably activate its intended checklist mechanism,
did not improve durable capture, and was behind concurrent C0 in every
completed row with nonzero C0 success. This is directional development evidence
only, but it plainly does not support shipping the todo rider.

## Why the screen stopped

The coordinator itself correctly places each model-capable worker under the
shared LLM admission wrapper. An outer wrapper was also applied to the
coordinator command. That nested claim prevented the worker launch before any
provider request, but the coordinator had already written a `launch-intent`
marker. Its v3 recovery branch conservatively mistook any marker for a possible
started worker. Reusing v3 would have produced an infrastructure terminal
outcome for a trial that never reached the model.

The amendment at
`experiments/durable-promise-orchestration-v3/amendments/2026-08-24-pre-admission-interruption.md`
records the event. The runner now distinguishes `launch-intent` from
`model-invoke-started`; its regression test proves a pre-admission marker can
retry while a provider-boundary marker still never replays. That corrected
closure requires a fresh registered study and schedule.

## Decision

Reject the todo-rider candidate. Keep the exact C1 durable-memory guidance as
the current candidate baseline. The next candidate should address the observed
asynchronous boundary directly, rather than merely asking for a todo list:
after checked asynchronous evidence returns, reconcile all independently
valuable outcomes before replying, and persist any durable outcome from that
evidence. That is a hypothesis for a new study, not a conclusion from this
incomplete screen.
