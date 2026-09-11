# V8 execution record: a context-dependent retrieved-guidance advantage

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

All 72 scheduled episodes completed and verify against sealed bundle
`13f853ad3c04150741c8a94a8f4dd8afb5c2eeeeb7a4666b2ead5a0d12cf5044`.
Retrieved guidance (G02) passed 30/36 while always-present guidance (G01)
passed 25/36. The difference is most pronounced at the high context dose:
G02 passed 11/12 and G01 5/12. At low context, G01 passed 12/12 and G02
10/12; at medium context, G01 passed 8/12 and G02 9/12.

For this Qwen3.8 reasoning-on Deep Agents filesystem task, the evidence is
consistent with the hypothesis only when context is already large: requiring
the agent to load a matched procedure outperformed handing it the same
procedure. It is not evidence that retrieval is uniformly better.

## Limits

This is one synthetic equipment-return task, one model revision, one reasoning
profile, one ReAct-like Deep Agents loop, and 12 episodes per cell. It does not
estimate a universal context threshold, establish causation for product Assist,
or transfer across models, harnesses, skills, or natural task families. The 17
artifact failures remain outcomes and are not retroactively changed.

## Handoffs

The next confirmation should hold this task family fixed while refining the
context grid around the observed high-dose separation, then test a fresh task
family before any Assist change. A private blog seed and the scoped Assist
roadmap proposal accompany this capsule; neither authorizes implementation.
