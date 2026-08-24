# Durable-promise outcome completion v2: held-out confirmation result

Status: complete sealed confirmation. The fixed C1 memory-scope treatment
advances to an Assist regression panel.

## What was tested

V2 tested the exact prompt-only C1 pair selected by the v1 pilot against the
current C0 pair. C1 distinguishes a conditional future action in the present
conversation from a cross-thread user fact or preference. After the agent has
checked the needed evidence, it directs the agent to write one concise
condition-and-action record to `/agent/memory.md` before claiming the outcome
was saved, set, noted, or remembered. It explicitly rejects substituting
repository memory, a TODO, or a schedule unless the user asked for that
artifact.

The four entirely new natural rows were orchard volunteer, passport form, choir
rehearsal, and vet follow-up. Each combines one local fact only available after
the deterministic context result with an independent future condition-action.
Each condition received six fresh episodes per row, for 24 per condition. The
fixed schedule is fully position-balanced: each condition was first and second
three times per task. C0 and C1 shared the same ordinary web-main graph,
Assist/fixture closure, Qwen identity, endpoint, context limit, temperature,
reasoning setting, tools, network restriction, and deterministic oracle.

R requires the grounding/context lifecycle; P requires a verified post-result
private-memory write; A requires the local fact and no unsupported completion
claim; F requires all three. P and F were co-primary. The pre-registered gate
required at least six more C1 successes on each, a one-sided exact paired sign
probability of at most 0.05 on each, and no meaningful R/A decline.

## Result

| Condition | Episodes | R | P | A | F |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 current prompts | 24 | 9 | 0 | 11 | 0 |
| C1 memory-scope treatment | 24 | 24 | 22 | 21 | 19 |

C1 improves P by 22/24 episodes and F by 19/24. There were no discordant
blocks favoring C0: the exact one-sided paired sign probabilities were
`2.38e-7` for P (22 C1-only versus 0 C0-only) and `1.91e-6` for F (19 versus
0). Both exceed the practical six-success threshold and the pre-registered
statistical threshold. R improves by 15 and A by 10, so all protection gates
pass overall and on every task.

Per-row C1/C0 full successes were 4/0 (choir), 5/0 (orchard), 5/0 (passport),
and 5/0 (vet). P was 6/0, 5/0, 6/0, and 5/0 respectively. These are descriptive
task-shape results, not a claim about a population of all agent requests.

## Integrity and limits

The sealed bundle is
`80e21c96340b2bebc6d8f2c4a72c996a712a473c02a948fa7823b0666badae15`.
The registration prose, resolved condition pairs, task bank, schedule, full
runner/accounting closure, Assist/EDD closure, non-secret endpoint digest,
decoding, and reasoning setting were checked before each admission. All 48
episodes admitted without denial, timeout, recovery, or missing provider-trace
evidence.

Raw traces are retained locally at `results/raw/durable-outcome-v2.9yjKSf`
(mode 0700), including rendered provider requests, schemas, tool calls/results,
workspace digests, and private-memory digests. Their retained hashes are:

- bundle: `554360bf7866913b5821257736742643472ba248466f60e1db3192b945e54957`
- admissions chain and seal: `b903498ee47c0660362f3cf3c9a2039ee302d3777bdb9f23952145ae7a8293b5`, `67c0bf5e4bd18636ca169b7a448dc6c9f000cee48b29e29a1615f53f5b99ee3b`
- outcomes chain and seal: `89ff1981093817f1da3dd064e0d00fd1ce798b45b4b1de30a20280d536e475e7`, `87544b6279744168361323346dd5d2593a11a1468171290911feaaa09b0647d3`
- aggregate report: `3a6e4935148cd0a657c66cd7185947a04ea3f94c92ac566cfee4ca21bbf223e8`

This confirms the specific mixed local-fact plus conditional-future-action
shape on this model and graph. It does not establish broad memory behavior,
scheduling behavior, or cross-thread preference behavior. Those are regression
requirements for the Assist candidate, not outcomes silently inferred here.

## Recommendation

Apply the frozen C1 text, and only that text, to Assist's repository- and
thread-memory prompt templates. Then compare the candidate with the current
baseline on the durable-promise rows, existing repository-memory preference and
thread-scope coverage, grounding lifecycle coverage, and relevant time/schedule
coverage. Ship only if it preserves those important existing behaviors while
retaining this large durability improvement.
