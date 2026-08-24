# Trace a small current-Assist edit cohort before tuning

## Evidence

This proposal is grounded only in `results/current-assist-baseline-v7/`, one
sealed real episode that exhausted its recursion limit after a provider request.

## Proposed work

Register a small cohort of fresh isolated edit episodes and capture complete
tool-event paths. Determine whether recursion-limit exhaustion is caused by the
cap itself or a repeated tool path.

## Product action

Do not change Assist prompts, middleware, or default limits from this n=1
result. Any product change requires a separately reviewed decision.
