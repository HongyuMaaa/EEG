# Sweep `teacher` — red, protocol `within`

Folds common to all configurations: 56 (validation sessions [2, 5]). **Selection criterion: mean validation accuracy.** Test accuracy is shown for information only.

| configuration | folds | val acc (%) | test acc (%) | overrides |
|---|---|---|---|---|
| red@sw-teacher-k236_bl1 ← selected | 56 | 75.63 | 75.61 | `loss.lambda_critic=1 loss.lambda_n2n=3 loss.tau=2 teacher.k_set=[2, 3, 6] loss.beta_lateral=1` |
| red@sw-teacher-k123456_bl1 | 56 | 75.52 | 75.41 | `loss.lambda_critic=1 loss.lambda_n2n=3 loss.tau=2 teacher.k_set=[1, 2, 3, 4, 5, 6] loss.beta_lateral=1` |
| red@sw-teacher-k236_bl5 | 56 | 75.36 | 75.60 | `loss.lambda_critic=1 loss.lambda_n2n=3 loss.tau=2 teacher.k_set=[2, 3, 6] loss.beta_lateral=5` |
| red@sw-teacher-k123456_bl5 | 56 | 75.32 | 75.73 | `loss.lambda_critic=1 loss.lambda_n2n=3 loss.tau=2 teacher.k_set=[1, 2, 3, 4, 5, 6] loss.beta_lateral=5` |
| *reference: eegnet* | 56 | 75.00 | 75.14 | |
| *reference: red* | 56 | 75.32 | 75.60 | |
