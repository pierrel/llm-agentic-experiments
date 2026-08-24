# V3 pre-admission interruption record

V3 is closed without completing its 18-episode development schedule. Sixteen
episodes reached the provider and have a valid append-only result chain. Before
episode 17 reached the worker or provider, an outer orchestration command also
claimed the shared LLM resource while the coordinator was designed to claim it
for its worker. The inner admission therefore did not start the worker, leaving
only the coordinator's `launch-intent` lifecycle marker.

The sealed v3 coordinator treated any existing lifecycle marker as an
interrupted worker. Continuing it would have converted a pre-provider
administrative failure into a reason-coded terminal outcome. That would not be
a model observation, so v3 is invalidated as an incomplete development screen.
The private raw directory, its bundle, admission chain, 16 outcome records,
traces, and the pre-admission marker are retained unchanged. Neither pending
episode is replayed under v3.

The replacement runner accepts a stale pre-admission marker as retryable but
continues to forbid replay after `model-invoke-started`. A fresh study version
must seal that runner closure and a new schedule before any further request.
