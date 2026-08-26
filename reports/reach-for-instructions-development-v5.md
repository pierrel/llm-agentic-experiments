# Reach-for-instructions development v5 report

The calibrated V5 oracle produced three high-context passes in `G02` and no
passes in `G01`; every lower-context cell still failed. Trace review found that
two high-context `G01` handoffs were otherwise complete but used `not_issued`,
which V5 did not yet accept despite accepting `no_payment_issued`. The apparent
3/3 versus 0/3 high-context contrast is therefore not interpretable as a
guidance-delivery effect. V6 is the final sealed development calibration.
