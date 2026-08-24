# Reconcile independent outcomes after checked async evidence

## Hypothesis

A general asynchronous-work checkpoint that asks an agent to reconcile the
independent outcomes of the current turn *after it has checked returned
evidence* will improve mixed-turn completion more reliably than asking it to
create a temporary todo list before or while the work is pending.

## Proposed intervention

Keep durable-memory guidance unchanged. Compare it to a concise, general
async-lifecycle instruction: after obtaining a checked result from tool or
subagent work, identify every independently valuable outcome from the original
turn, complete any remaining deterministic or durable action supported by that
result, then reply. It must not prescribe a tool, skill, file path, or fixture.

## Predicted observable outcome

On fresh ordinary-web mixed-outcome rows, the treatment increases full-row
completion and post-result durable capture without lowering grounding lifecycle
or factual-answer honesty. It may do so without using `write_todos`; todo use is
not the desired mechanism.

## Boundary and counterexample

Do not add a checkpoint when the turn has only one outcome, when evidence is
not yet available, or when a remaining action needs user confirmation. The
instruction should not encourage polling, premature memory writes, or claims
that unsupported work has completed.

## Origin

The sealed v3 todo-rider development screen was interrupted after 16 episodes,
but the preserved completed evidence was unfavorable: the rider used todos in
only 1/3 C1 profile-leading rows and 0/5 completed C1 rows elsewhere, while
C1 did not improve durable capture. A workshop C1 trace also performed private
state work before checking its context result. This is a new hypothesis, not a
causal conclusion from the incomplete screen.
