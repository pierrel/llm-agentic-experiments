# Development learning: exact phrase oracles can manufacture a context signal

## Evidence

- Sealed run: `run.json`
- Result summary: `report.json`
- Full settings and schedule: `bundle.json`
- Raw-trace hashes: `run.json`; local raw traces follow the stated retention policy.

## Observation

V3 passed at 31,324 and 106,924 realized first-request tokens. The 6,124-token
episode was scored as a failure only because it said “duplicate image” rather
than the oracle's exact “duplicate receipt image,” while preserving the source
fact, portal-upload cause, and unresolved retention decision.

Together with V2, whose medium and high handoffs missed a different exact
phrase while stating the same retained-image fact, this shows that this
string-matching oracle can manufacture apparent dose effects. The three
development versions provide no reliable evidence that this model's procedure
following degraded as context grew on the tested handoff tasks.

## Limits

One episode per condition cannot estimate a behavior rate or threshold. The
results do not establish context robustness, do not transfer to another task,
model, reasoning setting, or harness, and cannot rule out a real effect hidden
by task or stochastic variation.

## Handoffs

The durable learning is experimental: before using a procedural handoff as a
context-length detector, independently develop and seal an oracle with
predeclared acceptable evidence forms or a separately calibrated semantic
extractor. A private blog seed records this result-series learning; the Assist
proposal remains deliberately no-action.
