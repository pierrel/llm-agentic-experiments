# Example study walkthrough

This is invented data. It demonstrates the procedure; it is not evidence about
any model.

## One small agentic task

The fake workspace contains `note.txt` with “Budget: $20.” The user says,
“Change the budget to $25.” The available tools can list files, read one file,
write one file, and load a skill. In the operational-skill conditions, the
relevant skill says to read the current file before editing it; the other
conditions receive equal-length non-operational text instead.

The automatic checker passes only when the final file is exactly
`Budget: $25.\n` and
the trace shows a successful read before the write. This final file is the
observable **artifact**: a file or state change the checker can inspect.

## What conditions change

Study A has four versions. In this illustration, the system prompt and the
skill either include the same “read before editing” rule or an equal-length
non-operational sentence. Tools, user request, fake file, model settings, and
loop limit stay identical.

| Anonymous condition | System rule | Skill rule |
| --- | --- | --- |
| A | neutral | neutral |
| B | operational | neutral |
| C | neutral | operational |
| D | operational | operational |

The runner records A/B/C/D. It does not attach the human-friendly names until
every scheduled trial has been scored.

## One invented trace

1. User: “Change the budget to $25.”
2. Model calls `load_skill(edit-note)`.
3. Tool returns the fixed skill body.
4. Model calls `read_file(note.txt)` and receives “Budget: $20.”
5. Model calls `write_file(note.txt, "Budget: $25")`.
6. The checker reads the final fake workspace and scores a pass.

The trace also contains the exact request messages, tool schemas, fixture hash,
model settings, condition ID, and outcome. The fixed checker scores before any
optional human reads a redacted trace.

## How to read an invented result

Suppose the locked cohort reports D at 34/40 passes and B at 28/40. The report
would say the estimated difference is 15 percentage points and show its
confidence interval. It would then say whether that interval and the
preregistered decision rule support the stated hypothesis. It would **not** say
that repeating instructions always helps every model or every agent framework.
