# Current Assist baseline v7 result

## Result

The one registered current-Assist episode was admitted and made a model request.
It did not produce the requested artifact: the graph raised `GraphRecursionError`
at the sealed recursion limit of 12. The append-only outcome record therefore
records an artifact failure (`provider_error` with the exact recursion-limit
detail); it is not retried.

This is a single baseline observation, not a model, architecture, or prompt
comparison. It shows only that this exact isolated current-Assist construction,
with the sealed model selector, reasoning disabled, and 12-step cap, did not
finish this edit episode.

## Evidence

- Registration: `experiments/current-assist-baseline-v7/bundle.json`
  (`d476ebd6eec82b0c41e934ff5abc93e5cb5a3f9a4e07060956767fac06b6ad12`),
  tagged `current-assist-baseline-v7` at `a861785`.
- Harness: `assist.agent.create_agent` over Deep Agents, isolated virtual
  filesystem, Assist revision `f66d29eec07728d57f026e64df00508b262cfa7d`.
- Model settings: current Assist local selection, temperature 0.1, reasoning
  disabled, recursion limit 12.
- Admission and outcome chains, with their seals, are committed under
  `results/current-assist-baseline-v7/`.
- Raw evidence remains local under `results/raw/current-assist-baseline-v7/`.
  Its compact hash manifest is `results/current-assist-baseline-v7/raw-evidence.json`.
  The actual provider-request capture hash is
  `b0a0e3c26af4a0d338f12c20756b769db7ceb096353dda9bcfab7d042c81a4f4`.

The raw capture contains one pre-provider request with two messages and nine
tool definitions, including `read_file` and `edit_file`. No final graph trace
exists because the graph raised before returning a response; `trace_sha256` is
therefore explicitly null rather than invented.

## Initial learning

For this exact baseline, a simple isolated edit can exhaust a 12-step current
Assist graph budget before a final artifact is returned. This is evidence to
investigate loop budget and the intermediate tool path, not evidence that any
prompt, model, or Assist product behavior should be changed.

## Assist roadmap disposition

Propose one investigation: capture the full tool-event path for a small set of
fresh current-Assist edit episodes, then determine whether the cap or a
particular loop is responsible. Do not change Assist guidance or middleware on
the basis of this n=1 result.

## Review disposition

The final local review found reusable-runner hardening work that does not alter
this sealed v7 result. It is documented in
`docs/0012-current-assist-baseline-local-review.md` and deferred to a separate
registration rather than folded into this first pass.
