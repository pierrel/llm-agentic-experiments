# Current Assist pilot v3 amendment

The v2 worker import succeeded, but the descriptor, result, and request-marker
arguments were still relative paths. The admission wrapper changes cwd, so v2
failed before the marker and issued no model request. Pilot v3 resolves every
cross-wrapper path to an absolute path. All behavioral settings and the oracle
remain unchanged.
