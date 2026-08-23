# Current Assist pilot v5 amendment

The v4 deployment-environment path targeted `code/.deploy.env`; the real
ignored file is the parent deployment directory's `.deploy.env`. Pilot v5
corrects that path only. No model request was made in v4.
