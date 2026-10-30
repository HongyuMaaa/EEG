# Sweep `tau` — red, protocol `within`

Folds common to all configurations: 56 (validation sessions [2, 5]). **Selection criterion: mean validation accuracy.** Test accuracy is shown for information only.

| configuration | folds | val acc (%) | test acc (%) | overrides |
|---|---|---|---|---|
| red@sw-tau-tau2 ← selected | 56 | 75.64 | 75.62 | `loss.lambda_critic=1 loss.lambda_n2n=3 loss.tau=2` |
| red@sw-tau-tau4 | 56 | 75.58 | 75.57 | `loss.lambda_critic=1 loss.lambda_n2n=3 loss.tau=4` |
| red@sw-tau-tau1 | 56 | 75.57 | 75.66 | `loss.lambda_critic=1 loss.lambda_n2n=3 loss.tau=1` |
| *reference: eegnet* | 56 | 75.00 | 75.14 | |
| *reference: red* | 56 | 75.32 | 75.60 | |
