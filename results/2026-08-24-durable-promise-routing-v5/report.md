# Durable-promise capability routing v5: pilot result

Status: complete sealed pilot. No Assist candidate advances from this result.

## Question and treatment

The registered question was whether one general sentence in grounding's skill
description improves routing when a user asks both for a fact in their records
and a future commitment that competes with date-like capabilities. C0 used the
exact current grounding description. C1 added only:

> A question about the user's own date, time, meeting, deadline, or status
> needs this skill when the answer comes from their records.

Each condition ran three fresh ordinary-web-main episodes for each of four
sealed natural rows: `library-shift`, `insurance-renewal`, `garden-plan`, and
`course-partner`. The 24 fixed-order, counterbalanced episodes used the same
current Assist source, local Qwen model, deterministic context completion, and
private workspace. C1 did not change a tool, schema, fixture, model setting,
or score.

R requires grounding first, then context next, and a checked local result before
dependent work. P requires the requested post-result `/agent/memory.md` write.
A requires the local fact in the answer and no unsupported completion claim.
F requires R, P, and A.

## Result

| Condition | Episodes | R | P | A | F |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 current description | 12 | 5 | 0 | 2 | 0 |
| C1 local-record boundary | 12 | 6 | 0 | 1 | 0 |

The preregistered advance rule required C1 to have at least two more R and F
successes, with no lower P or A count on either low-conflict sentinel. It did
not advance: R improved by one, F remained zero, P remained zero, and A fell by
one. No confirmation task bank, product regression panel, or Assist change is
justified from this treatment.

Per sealed row, C1/C0 routing was 0/0 for `library-shift`, 0/0 for
`insurance-renewal`, 3/3 for `garden-plan`, and 3/2 for `course-partner`.
Neither condition produced a full success on any row. This points to the
missing durable commitment write as the dominant unresolved behavior; the new
grounding sentence neither solved it nor established a worthwhile routing gain.

## Integrity and evidence

The raw traces are private local evidence at
`results/raw/durable-routing-v5.ggDdgY` (mode 0700), including every provider
request, dynamic schema, tool call/result, final workspace digest, and private
memory digest. The sealed cohort bundle is
`29f6f05ff6c410fa064c54fd0a356a2b5dd56298c9c7a60a456297e746ecd7a0`.
The retained artifact hashes are:

- bundle: `d9bcbc13984cd649c5d01c50e3de9072b3ee9d8af426e75a03e7aee5c2497892`
- admissions chain and seal: `2c6ed6538b464ead624c691b14d7ad85d29eb1516154d274b66e21852ba7f753`, `4327682102e5da6cbf6783a5bc42617f943b13fdd09e17768efb2852e7e1d251`
- outcomes chain and seal: `324e01447c2322cf9004d70389439548739cacc94ce5493cd0aa1b1e65b96a8a`, `bebb4559c688d720c094167647a87abc797a1ab5f6186806bdd88403fbac28d5`
- aggregate report: `2a6cbb2ee7786b6d35d5d9dd9a91c4dfa5ec47970e8c2cf486162763044a8081`

Versions v1 through v4 each failed before a provider request and are preserved
as pre-admission events. V4 identified the root cause: resolving the virtualenv
Python symlink launched system Python without `httpx`. V5 preserves the original
virtualenv executable and its 24 admissions completed normally. Those earlier
events are operational history, not behavioral observations.

## Recommendation

Keep current Assist guidance. Do not ship C1 or pursue a confirmation study.
The next useful hypothesis should target the general mechanism behind a
mixed request becoming a durable commitment after checked grounding, while
preserving honest responses and avoiding a task-specific or skill-specific
instruction. It needs a new registration and task bank; this pilot's rows are
now observed and cannot become that confirmation evidence.

## Post-result architecture finding

Subsequent prompt-trace review found that this cohort's current production-shaped
memory prompt told the model to write forward-looking rules to repository memory
before ordinary work, while its thread-memory prompt assigned current work to
`/agent`. The traces show the model following the former by writing
`/workspace/AGENTS.md` for conditional reminders. This does not invalidate the
sealed result for C1's grounding-description treatment: both conditions had the
same memory prompt. It does mean that the observed zero-persistence result is
evidence for a new memory-scope hypothesis, not evidence that a general
thread-outcome treatment cannot work. That hypothesis is registered separately
as durable-promise outcome completion v1 with fresh rows.
