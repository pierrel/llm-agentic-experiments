# Reach V8-r3 reproduction r3 event correction

## Historical supersessions

None. This records a later adjacent event-reader gap;
`docs/0038-reach-for-instructions-v8-r3-reproduction-r3-review-corrections.md`
and its nonempty-interval correction remain valid.

## Correction

External review found that the event-log reader retained only the three
expected same-thread LLM event names. That allowed an unexpected event to be
discarded before the runtime-interval verifier could reject it. The reader now
retains every same-thread LLM event while continuing to ignore events for other
threads and resources. The existing interval whitelist consequently rejects an
unexpected event, or the existing relevant-event bound rejects an overfull
slice, before its invocation can become durable evidence.

This correction changes no treatment, fixture, prompt, schedule, oracle, model
profile, outcome, or analysis rule. R3 remains tag-pending with no runtime,
model admission, server change, or result.
