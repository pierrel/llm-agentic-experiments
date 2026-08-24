# Durable-promise outcome completion v1: sealed pilot result

Status: complete sealed pilot. It supplies a candidate hypothesis, not release
authorization.

## Question and treatment

The study asked whether resolving an internal conflict between repository memory
and thread memory would help the agent preserve a requested conditional future
action after it checks the local evidence needed to answer the same request.

C0 used the exact current pair of Assist memory-prompt templates. C1 changed
only those two templates. In general terms, C1 says that a later
condition-and-action in the current conversation is thread state, that it must
be written concisely to `/agent/memory.md` after required evidence is checked
and before saying it was saved or remembered, and that repository memory, a
TODO, or a schedule are not substitutes unless the user requested them.

Every condition ran three fresh ordinary-web-main episodes for each of four new
natural mixed requests: `workshop-review`, `camera-return`, `reading-group`,
and `lease-keys`. The 24 fixed-order counterbalanced episodes used the same
Assist source, Qwen model, decoding, deterministic context completion, tools,
and private workspace. No tool, schema, fixture, middleware behavior, or model
setting differed between C0 and C1.

R requires grounding first, context next, and a checked local result before
dependent work. P requires the requested post-result `/agent/memory.md` write.
A requires the local fact in the response and no unsupported completion claim.
F requires all three.

## Result

| Condition | Episodes | R | P | A | F |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 current prompts | 12 | 4 | 0 | 4 | 0 |
| C1 memory-scope treatment | 12 | 9 | 9 | 12 | 9 |

C1 produced nine more verified private commitments and nine more full outcomes
than C0. It also answered every row with the checked local fact and made no
unsupported saved/remembered claim. The improvement appears on all four task
shapes: C1/C0 full successes were 3/0 for workshop review, 3/0 for camera
return, 1/0 for reading group, and 2/0 for lease keys.

The lower-conflict sentinels still expose an important boundary. C1 routing was
1/3 versus C0's 1/3 for reading group, and 2/3 versus C0's 3/3 for lease keys.
C1's persistence and answer outcomes were not lower on either sentinel, but
the lease-keys routing count is lower. This is a reason to test routing again
on unseen tasks, not to weaken the treatment toward these fixtures.

## Registered discrepancy and interpretation

The registration prose specified a P/F advancement test plus no R/A decline on
the sentinels. After 11 admissions, an audit found that the frozen coordinator
actually evaluates R/F plus no P/A decline. That discrepancy was recorded in
an append-only amendment before the remaining admissions, and the coordinator
reported its sealed rule: C1 advances to a fresh confirmation cohort.

The result is therefore strong pilot evidence for the general memory-scope
treatment, while not itself a release decision. A new, previously unseen task
bank must use the intended P/F decision rule, retain the routing and honesty
non-regression gates, and test repository-memory preference behavior before an
Assist candidate is considered.

## Evidence and history

The raw traces are retained locally at
`results/raw/durable-outcome-v1.03aRhD` with mode 0700. They contain every
rendered provider request, dynamic schema, tool call/result, workspace digest,
and private-memory digest. The sealed cohort bundle is
`8acdc8acf10638111faa3e0d3e9dd41d0c75f4fa92ad8f35e8c2e2932618ac48`.

- bundle: `29a53d5aa8ff66ee8fbf5d4bef716eb0fadf1529887aacd5a5787436d0ac1517`
- admissions chain and seal: `22c64ee66eada7e9b29ce46d886e39319c1f37fb57a7db4307b17d6fa9016167`, `af7713fa9d3c9f42e658c00a0d96e4389ccae272760ab6589d3ca11d8edd4fac`
- outcomes chain and seal: `a9aefb2e48e00b83df094620fc8a039776ed9b919e298b5436b009de18574bd8`, `f8a836f5b59d5403d2d4109142e85ee187acfad93db1a765b7fabbcb3ddf81ce`
- aggregate report: `3bd22063264eb7ca7aefe8ed92d0bf1b8bf5507a1acef5b2084a8ee4b48b765e`

Earlier durable-promise routing versions v1-v4 remain recorded as pre-provider
infrastructure failures; routing v5 is a completed, rejected grounding-skill
pilot. Neither is folded into this cohort. This result report, its frozen
registration, the amendment, and the raw sealed records preserve the complete
lineage for the next confirmation study.

## Recommendation

Keep C1 exactly fixed. First harden the confirmation harness around the review
findings, then preregister fresh tasks and a P/F primary decision rule. If C1
again improves durable commitments and full outcomes without material routing,
honesty, or repository-memory regressions, use the exact tested prompt wording
as the narrow Assist candidate and run the existing production regression panel.
