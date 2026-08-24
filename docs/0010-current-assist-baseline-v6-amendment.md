# Current Assist baseline v6 amendment

V5 reached its admitted worker but did not make a model request: the deployment
venv's editable Assist package could not locate the current Assist templates.
The sealed v5 outcome records that infrastructure failure. V6 adds the current
Assist source revision to the harness identity and runs the worker with that
source tree on `PYTHONPATH`, so `assist.agent.create_agent` uses the exact
current templates and middleware it claims to baseline.

The fixture, prompt, model selector, reasoning value, primary oracle, and
one-episode schedule are unchanged. This is a source-identity correction, not
an experimental treatment.
