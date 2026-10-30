# Sweep `weights` — red, protocol `within`

Folds common to all configurations: 56 (validation sessions [2, 5]). **Selection criterion: mean validation accuracy.** Test accuracy is shown for information only.

| configuration | folds | val acc (%) | test acc (%) | overrides |
|---|---|---|---|---|
| red@sw-weights-lc1_ln3 ← selected | 56 | 75.64 | 75.65 | `loss.lambda_critic=1 loss.lambda_n2n=3` |
| red@sw-weights-lc0.5_ln3 | 56 | 75.51 | 75.77 | `loss.lambda_critic=0.5 loss.lambda_n2n=3` |
| red@sw-weights-lc2_ln0.3 | 56 | 75.41 | 75.53 | `loss.lambda_critic=2 loss.lambda_n2n=0.3` |
| red@sw-weights-lc2_ln3 | 56 | 75.40 | 75.64 | `loss.lambda_critic=2 loss.lambda_n2n=3` |
| red@sw-weights-lc2_ln1 | 56 | 75.39 | 75.78 | `loss.lambda_critic=2 loss.lambda_n2n=1` |
| red@sw-weights-lc1_ln1 | 56 | 75.33 | 75.73 | `loss.lambda_critic=1 loss.lambda_n2n=1` |
| red@sw-weights-lc1_ln0.3 | 56 | 75.33 | 75.41 | `loss.lambda_critic=1 loss.lambda_n2n=0.3` |
| red@sw-weights-lc0.5_ln1 | 56 | 75.31 | 75.60 | `loss.lambda_critic=0.5 loss.lambda_n2n=1` |
| red@sw-weights-lc0.5_ln0.3 | 56 | 75.14 | 75.44 | `loss.lambda_critic=0.5 loss.lambda_n2n=0.3` |
| *reference: eegnet* | 56 | 75.00 | 75.14 | |
| *reference: red* | 56 | 75.32 | 75.60 | |
