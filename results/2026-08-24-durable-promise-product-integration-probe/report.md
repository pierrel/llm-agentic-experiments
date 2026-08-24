# Durable promise product-integration probe

Status: diagnostic only, not a registered experiment or confirmation result.

## Why this exists

The held-out `durable-promise-outcome-v2` confirmation established that its
exact C1 memory-guidance treatment improved a narrow, controlled agent loop.
Before considering it as an Assist candidate, we exercised the unchanged
frozen ordinary-web integration row below. This report preserves the negative
result rather than treating the controlled confirmation as product evidence.

## Fixed candidate

Assist commit `05d0f171d090aea9b69fa158d2be0b976dd518d9` applied the exact C1
repository- and thread-memory guidance from the sealed v2 bundle. No product
mechanism changed. The accompanying prompt census was intentionally updated
and passed.

## Row and protocol

We ran the existing natural eval
`TestPromptRewriteLocalGrounding.test_preserves_a_mixed_grounded_answer_and_leading_commitment`
three times against a fresh sandbox/thread. Its user prompt is:

> When I tell you I've missed meditation for four days, please encourage me
> to start the evening check-in again. I'm choosing dinner at home tonight.
> What neighborhood am I in, and what food do I usually like?

The fixture supplies the local profile result through the normal deterministic
context-agent completion path. The frozen oracle requires grounding lifecycle,
the profile answer, and a private `/agent/memory.md` record containing the
condition, action, and key details. Each process was admitted only after
`tools/agentic production status` reported idle and was run through the shared
`resource run llm` wrapper.

## Results

| repetition | frozen full-row pass | observation |
| --- | --- | --- |
| 1 | no | Answer and grounding were correct; it wrote extracted user facts to `/agent/context/user_facts.md`, leaving `/agent/memory.md` absent. |
| 2 | no | It wrote `/agent/memory.md`, but collapsed “four days” to `4`; this is semantically close but fails the frozen lexical oracle. |
| 3 | no | Answer and grounding were correct; it did not write private thread memory. |

Strict result: **0/3**. Semantic persistence occurred in only one run and is
not adequate as a candidate result. No production conclusion follows.

## Interpretation and next step

The treatment can improve an isolated memory decision while still losing the
future outcome during the real route's skill load, asynchronous context task,
result handling, and answer synthesis. This is evidence against adding more
memory-specific prose blindly. The next registered study tests a broader
mechanism: a temporary todo checklist for several independently valuable user
outcomes when tool, subagent, or waiting work begins. A todo is explicitly not
durable storage; the treatment must still save the conditional action to thread
memory. The existing frozen mixed-outcome rows are the development panel, with
separate holdouts and general regressions specified before further model use.
