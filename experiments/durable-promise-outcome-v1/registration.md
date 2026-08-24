# Durable-promise outcome completion v1

Status: registered pilot. Admissions began 2026-08-24; see the amendment below.

## Question

Can a general memory-scope and outcome-completion distinction make Assist
preserve a user-requested conditional future action in private thread state,
after it has checked any needed local evidence, while retaining repository
memory for genuine cross-thread facts and preferences?

This follows routing v5. V5 is retained as a valid study of a grounding-skill
description, but its rendered current prompt also revealed the relevant current
memory behavior: the repository-memory prompt tells the model to save
forward-looking rules to `/workspace/AGENTS.md` before work, while thread
guidance says current work belongs under `/agent`. V5 did not test a correction
to that conflict, so it cannot answer this question.

## Conditions

C0 is the exact current pair of repository-memory and thread-memory prompt
templates. C1 changes only that pair. It says that a later condition-action
within a conversation is thread state rather than a cross-thread fact or
preference; after required evidence is checked, the agent must write a concise
condition-and-action record to `/agent/memory.md` before saying it is saved,
set, noted, or remembered. It also says not to substitute repository memory, a
TODO, or a schedule unless the user explicitly requested that artifact.

The treatment is general system guidance, not a new tool, middleware behavior,
or task-specific instruction. The lab patches the two prompt strings before
agent construction. It captures the actual rendered provider requests and
schemas, so the private traces prove which prompt was used.

## Fresh pilot

Four new natural mixed requests each combine a local fact with an independent,
conditional future action: workshop review, camera return, reading group, and
lease keys. They were committed before any model request for this cohort and
share no user wording or fixtures with routing v5. Each has three fresh C0/C1
episodes for 24 total, in a sealed counterbalanced schedule.

R requires grounding first, then context next, and a checked local result before
dependent work. P requires the requested post-result `/agent/memory.md` write.
A requires the local fact in the response and no unsupported completion claim.
F requires all three. The two lower-conflict sentinels are reading group and
lease keys.

## Advance rule

This is a pilot, not a release decision. C1 advances to a fresh unseen
confirmation bank only if it has at least two more P and F successes than C0,
does not lower R or A on either lower-conflict sentinel, and does not regress a
genuine cross-thread preference check. A product candidate additionally needs
the existing repository-memory preference eval, thread-scope eval, grounding
lifecycle eval, and relevant schedule/time evals to remain non-regressed.

The sealed bundle is `bundle.json` with SHA-256
`8acdc8acf10638111faa3e0d3e9dd41d0c75f4fa92ad8f35e8c2e2932618ac48`.

## Amendment: sealed analysis discrepancy (2026-08-24)

After 11 of 24 scheduled admissions, an audit found that the committed
coordinator source sealed in `bundle.json` uses a different first advance
predicate: it requires C1 to have at least two more **R** and F successes than
C0, rather than the P and F predicate stated above. The coordinator source,
not this prose, is the executable analysis registered in the immutable bundle.

Nothing about the treatment, fixtures, schedule, provider requests, or scoring
changed. This cohort will finish and report the sealed R/F decision rule
verbatim, with P retained as a diagnostic result. It cannot by itself authorize
a product candidate or release decision. A fresh confirmation cohort, registered
before its first admission, must use the intended P/F rule and the stated
non-regression gates before any candidate is considered.
