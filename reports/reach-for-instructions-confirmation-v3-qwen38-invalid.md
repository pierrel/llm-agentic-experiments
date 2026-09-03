# Qwen3.8 confirmation V3: invalid before analysis

V3 admitted one Qwen3.8 episode and then stopped. Its first captured provider
request did not equal the pre-sealed rendered request, so the runner recorded a
provider error and did not advance the schedule.

The sole difference was the fixed load_skill tool description: the renderer
said “Load a listed procedural guide by exact name,” while the V3 worker said
“Load the single listed procedural guide by exact name.” Tool descriptions are
part of the provider request and therefore a real configuration change.

This is fidelity evidence, not a treatment outcome. The V3 episode is retained
in the local raw chain and is neither scored nor pooled. A fresh V4 must render
the exact worker tool schema before sealing; it receives a new bundle and full
72-episode schedule.
