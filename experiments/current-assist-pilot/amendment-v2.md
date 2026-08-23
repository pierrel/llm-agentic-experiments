# Current Assist pilot v2 amendment

The sealed v1 run retained in `results/current-assist-pilot-v1-failure/` was
admitted but failed before importing its worker because the command supplied a
relative `PYTHONPATH`. It produced no model response or tool call.

Pilot v2 changes only execution accounting:

- pass the experiment root as an absolute `PYTHONPATH` value;
- write a local marker immediately before `agent.invoke`;
- record a nonzero worker exit as a model request only when that marker exists.

The fixture, model, reasoning setting, harness profile, condition, primary
artifact oracle, and one-episode pilot status are unchanged. This is a new
study version, not a rewrite of the executed v1 bundle.
