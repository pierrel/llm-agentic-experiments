# Context-length dose-response task design

## Status

Draft task selection only. This is not a registration, does not set a token
grid or sample size, and authorizes no model request.

## Selected task: synthetic case handoff

The agent receives a fresh virtual workspace containing a small fictitious case
file: one workspace convention, three source records, and an empty outgoing
directory. The records contain a current state, verified events, one required
next action, and one unresolved discrepancy. All names, dates, and values are
synthetic.

The natural user request is:

> Please prepare the handoff for the Oakridge reimbursement case. The workspace
> has the material.

It does not name a tool, source filename, output filename, procedure, or oracle.
The workspace convention tells an agent how to recognize source material and
where a final handoff belongs; that is ordinary task context, not treatment
guidance.

## Fixed procedural instruction

Both context-length conditions receive the same system procedure:

> For a case handoff, first inventory the workspace. Read the governing
> convention and all relevant source records before writing. Reconcile only
> supported facts, label unresolved conflicts, create one final handoff with the
> current state, verified facts, next action, and uncertainties, and leave source
> records unchanged.

The instruction is general: it names no fixture path, expected tool argument,
or oracle phrase.

## Deterministic oracle

Success requires all of the following:

1. Exactly one final handoff appears in the convention-defined outgoing
   location; source records are byte-identical.
2. The handoff contains the four convention-defined sections and every required
   synthetic fact, including the unresolved discrepancy as uncertainty rather
   than an invented resolution.
3. The trace lists the workspace and reads the convention plus each source
   record before its first write.

This conjunction makes the primary outcome procedure-plus-artifact success.
The artifact-only and procedure-only components remain secondary diagnostics.

## Quantified fixed design variables

- Task complexity: four input files, seven required facts, four output sections,
  and three ordered procedure obligations.
- Task length: one natural user request and four short input records.
- Available skills: zero task skills in this first dose-response study.
- Tools: list, read, and write only.

These values are recorded for every episode and held fixed. They are not yet
axes in this study; later registrations can add complexity or skill-catalog size
only with their own powered design.

## Context-length intervention boundary

The context payload is a sealed, synthetic, declarative corpus with no
instructions, case facts, filenames, answer cues, or task-relevant entities.
It appears before the unchanged procedure block. The procedure block and user
request therefore retain their exact relative position, while total rendered
input tokens vary. The runner records actual serialized request tokens under a
pinned tokenizer. A later position experiment may vary distance from the user;
this task does not conflate that question with total context length.

## Why this is the minimum adequate task

A one-file edit would make a final artifact easy to obtain without following the
instruction, while a multi-agent workflow would introduce unnecessary routing,
skill, and scheduling variance. This task needs source inspection, factual
reconciliation, a constrained write, and honest uncertainty handling, but no
network, live Assist thread, external data, or qualitative judge.
