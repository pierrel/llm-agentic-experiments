# Current Assist pilot v6 amendment

The sealed v7 execution record retained in
`results/current-assist-pilot-v7-capsule/` changed the correct virtual file
after reading it, but the v7 oracle recognized only the scripted harness's
`write_file(path)` trace shape. Deep Agents used its normal
`edit_file(file_path)` tool instead, so v7 is retained as an oracle-mismatch
record rather than rewritten.

Pilot v6 recognizes both native file-edit operations and their declared path
arguments: `read_file(file_path)` followed by either `write_file(path)` or
`edit_file(file_path)`, with the final artifact still required to be exactly
the sealed expected content. The fixture, model, reasoning setting, harness
profile, neutral condition, one-episode schedule, and no-replay policy are
unchanged. This is a new registration and requires a new execution record.
