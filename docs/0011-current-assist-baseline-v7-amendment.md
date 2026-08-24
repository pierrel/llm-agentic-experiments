# Current Assist baseline v7 amendment

V6 constructed the isolated current Assist graph but the in-memory checkpointer
rejected invocation without a `thread_id`, before a model request. V7 supplies a
fresh deterministic experiment-scoped thread identity in the invocation config.
The isolated filesystem, current Assist revision, model selection, reasoning
setting, prompt, fixture, primary oracle, and one-episode schedule are
unchanged.
