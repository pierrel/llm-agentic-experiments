# Current Assist baseline v4 amendment

V3 was not admitted for model execution. Local harness review found that it
recorded only a declared tool contract. V4 snapshots the actual Deep Agents
filesystem-tool schemas, rendered system-plus-user messages, fixture digest,
runtime model identity, and sealed settings before `invoke`; it rejects a
fixture or required-tool mismatch before a request is made.

The prompt, fixture, model selection, Deep Agents/ReAct-style architecture,
settings values, oracle, and one-episode schedule are unchanged. The original
three design reviews were rechecked and remain valid.
