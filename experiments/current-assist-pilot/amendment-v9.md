# Current Assist pilot v9 amendment

The scripted-MVP v2 correction extends `harness/manifests.py`, which belongs to
the current pilot's sealed import closure. It does not change current-Assist
episode behavior, but the source digest must not claim an older implementation.

Pilot v9 therefore registers the same current-Assist configuration against the
new implementation digest. The fixture, model, reasoning setting, harness
profile, native edit oracle, neutral condition, one-episode schedule, and
no-replay policy are unchanged. The v11 result remains evidence for the exact
v8 implementation; v9 awaits a new execution only if that revised source
version itself needs a baseline record.
