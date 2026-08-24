# Current Assist baseline v3 amendment

V2 was denied before a model request because the shared LLM resource was busy.
The append-only admission record is retained. Local review then found that a
later admitted retry would have reused attempt number one. V3 fixes that
bookkeeping and passes the already-sealed generic reasoning setting explicitly
to Assist's model selector.

No scientific input changed: the fixture, prompt, model selection, Deep
Agents/ReAct-style harness, settings values, oracle, and one-episode schedule
are identical to v2. The three design reviews were rechecked and remain valid.
