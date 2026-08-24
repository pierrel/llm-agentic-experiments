# Ground local facts before generic capability routing

## Hypothesis

When a user asks about a fact in their own notes, plans, or records, a grounding
skill description that explicitly includes user-owned appointments, bills,
projects, and tasks will be selected before a generic date or scheduling
capability. This should let the agent obtain the local evidence and then use a
later capability only when the checked evidence still requires it.

## Intervention and observable outcome

Compare the current grounding description with a version that names the
user-owned-record shape without naming an eval fixture or a competing tool. On
fresh, hermetic, mixed turns, measure first skill load, checked context-task
lifecycle, sourced answer, private later commitment, and truthful final reply.

## Boundary

The intervention must not route a self-contained calendar calculation or an
actual request to create/change a recurring schedule through grounding. It is a
routing hypothesis, not a claim that all date language needs local context or
that a durable commitment can be represented by a schedule.

## Origin

Pierre asked to preserve the failed durable-promise exploration and run a new
grounding-versus-capability study after its best commitment treatment improved
simple rows but failed when date, event, and schedule language competed for
first routing.
