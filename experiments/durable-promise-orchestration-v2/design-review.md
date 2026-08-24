# Design reviews and dispositions

## Scientific integrity

Review required a new study rather than amending v1, an unambiguous current-C1
control, literal rider and injection point, fresh confirmation tasks, component
oracles, sealed requests/schemas/settings/closure, and a distinction between
administrative retries and observed behavior. All are adopted in
`registration.md`; implementation must enforce them before model use.

## Statistical rigor

Review required independent fresh-thread units, explicit per-row/per-condition
replications, seeded balanced condition order, exploratory development separate
from confirmation, component outcomes, concurrent controls, and concrete gates.
All are adopted. The final analysis program will implement the specified
row-stratified permutation test before a model run.

## Agentic harness fit

Review found the existing `durable_routing_harness` adequate because it runs the
real web-main graph, main skills, deterministic async context completion,
sandbox, private `/agent`, and provider-request capture. V2 needs only: a
sealed todo-rider condition, final todo-state capture, a narrow allowance for
`write_todos` between context dispatch and checked result, and component
scoring. It must not add a second skill or a simulator.

## Minimum adequate setup

The only production-side candidate mechanism is one prompt-appending middleware
with no tools or state. The harness extension is bounded to the evidence needed
to distinguish a checklist from durable storage. Production queue and RunService
plumbing, schedules, delegates, live network, and arbitrary async-task support
are intentionally out of scope.
