# Study registry

This index is append-only. A new revision records a new row; it never changes
the status or contents of an executed registration.

| Study version | Status | Registration | Results | Notes |
| --- | --- | --- | --- | --- |
| Design 0001 | design only | N/A | N/A | Program design for the first two studies; no model trials have run. |
| reach-for-instructions-dev-v1 | superseded before model admission | [registration](../experiments/reach-for-instructions-dev-v1/registration.md) | N/A | Sealed bundle retained at tag `reach-for-instructions-dev-v1`; a no-model runtime probe found its worker environment wrapper would not set `PYTHONPATH`. |
| reach-for-instructions-dev-v2 | superseded before model admission | [registration](../experiments/reach-for-instructions-dev-v2/registration.md) | N/A | Sealed bundle retained at tag `reach-for-instructions-dev-v2`; its new local output directory was created with mode 0755, and the runner correctly refused it before its first worker command. |
| reach-for-instructions-dev-v3 | superseded before model admission | [registration](../experiments/reach-for-instructions-dev-v3/registration.md) | N/A | Sealed bundle retained at tag `reach-for-instructions-dev-v3`; its first worker used a relative descriptor path after shared admission changed the working directory, so no model callback marker was created. |
| reach-for-instructions-dev-v4 | development registered | [registration](../experiments/reach-for-instructions-dev-v4/registration.md) | pending | V3's corrected absolute worker-artifact paths, with unchanged question, conditions, fixture, schedule, and planned 18 episodes. |
| reach-for-instructions-dev-v4 result | reported development result | [registration](../experiments/reach-for-instructions-dev-v4/registration.md) | [capsule](../results/reach-for-instructions-dev-v4/) | 18/18 literal-schema failures; traces show fixed JSON-key names, not a delivery-mode conclusion. |
| reach-for-instructions-dev-v5 | development registered | [registration](../experiments/reach-for-instructions-dev-v5/registration.md) | pending | V4 oracle-alias calibration, with the same 18-episode response surface. |
| reach-for-instructions-dev-v5 result | reported development result | [registration](../experiments/reach-for-instructions-dev-v5/registration.md) | [capsule](../results/reach-for-instructions-dev-v5/) | High-context apparent 3/3 versus 0/3 contrast includes two handed runs rejected only for `not_issued`; V6 isolates that remaining oracle form. |
| reach-for-instructions-dev-v6 | development registered | [registration](../experiments/reach-for-instructions-dev-v6/registration.md) | pending | Final normalized-payment oracle calibration, with unchanged response surface. |
