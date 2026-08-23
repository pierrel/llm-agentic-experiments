# Current Assist pilot v4 amendment

The v3 worker reached Assist model selection but the admission wrapper did not
load the ignored local deployment environment. `select_assistant_model` thus
rejected the missing `ASSIST_MODEL_URL` before `agent.invoke`. Pilot v4 sources
the existing local `.deploy.env` inside the GPU-admitted shell without exposing
any setting value in argv. The test and all sealed behavioral settings remain
unchanged.
