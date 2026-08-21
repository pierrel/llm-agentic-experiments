# Short glossary

- **Agentic**: the model may take several turns and use tools, not merely write
  one answer.
- **Condition**: one version of an otherwise identical experiment. A
  **treatment** is the intended change; a **control** is its comparison version.
- **Fixture**: the self-contained fake files, tool answers, and task data for a
  trial.
- **Oracle**: an automatic checker with a fixed pass/fail rule.
- **Trace**: a chronological log of prompts, model messages, tool calls, and
  tool results.
- **Preregister**: commit the question, procedure, scoring rule, and analysis
  plan before seeing results.
- **Progressive guidance**: a short catalog lists guidance documents, and the
  model must request one before receiving its full text.
- **System context**: instructions supplied to the model alongside or before a
  user request.
- **Operational guidance**: wording that directs an action, such as which tool
  workflow to use.
- **Locality**: whether useful wording appears close to the decision it is
  meant to influence.
- **Steerability**: how reliably guidance changes observed behavior.
- **Token matched**: conditions have roughly the same model input length so one
  is not helped merely by being longer.
- **Block**: one task and replicate scheduled under every condition, with order
  balanced to avoid giving one condition a time or queue advantage.
- **Confidence interval**: a range of effect sizes compatible with the data and
  the preregistered analysis.
- **Power**: the planned chance of detecting a practically worthwhile effect if
  it is real.
- **Multiplicity adjustment**: a safeguard against mistaking chance patterns
  for discoveries when many secondary questions are tested.
- **Blinded review**: a reviewer sees anonymous condition IDs rather than which
  prompt version produced a trace.
- **Held-out confirmation cohort**: a new untouched batch of tasks and runs
  used only after the design is frozen.
