# Reach-for-instructions confirmation V5 pre-admission runtime correction

The initial V5 bundle received no model admission. Review found that V5's
module-global wrapper configuration did not take an outer re-entrant lock,
unlike the V3 wrapper it transitively configures. Concurrent in-process tooling
could therefore interleave patch and restoration of V4 globals.

V5 now holds its own `RLock` across the complete patch, delegated configuration,
and restoration sequence. This changes no task, schedule seed, condition,
prompt, tool schema, model setting, harness setting, oracle, or analysis rule.
The bundle is re-rendered and resealed before its first admission; the initial
no-admission bundle remains in Git history and is not a result record.

The subsequent launch also stopped before admission: V5's rewritten bundle
retained its inherited registration tag, while the current sealed bundle was
stored under the immutable `-r2` tag. V5 now writes its exact immutable tag
into the registration and has a no-model regression that builds a temporary
tagged repository and passes the same definition check used before launch. The
new `-r3` tag is a provenance correction only; it does not alter the registered
scientific design.
