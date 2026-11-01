# Direction 1 pilot: label-free adaptation to a new subject (seed 2)

Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. Subjects: 28. Adaptation budget: {'epochs': 10, 'lr': 0.0005, 'batch_size': 64, 'lambda_n2n': 1.0, 'gpl_threshold': 0.6, 'gpl_bal_quantile': 0.3}.

| method | accuracy (%) | Δ vs source (pp) | Δ vs adabn (pp) | improved vs adabn | Wilcoxon p vs adabn | mean |P(pred=1) - 0.5| |
|---|---|---|---|---|---|---|
| source | 61.16 | +0.00 | +0.13 | 17/28 | nan | 0.023 |
| adabn | 61.03 | -0.13 | +0.00 | 0/28 | nan | 0.027 |
| tent | 60.78 | -0.37 | -0.25 | 8/28 | 0.0344 | 0.039 |
| n2n | 61.12 | -0.04 | +0.09 | 11/28 | 0.6741 | 0.062 |
| gpl | 59.54 | -1.62 | -1.49 | 7/28 | 0.0388 | 0.334 |
| gpl_bal | 66.76 | +5.60 | +5.73 | 22/28 | 0.0003 | 0.022 |
| n2n_gpl | 59.58 | -1.58 | -1.45 | 7/28 | 0.0379 | 0.334 |
| balance | 61.07 | -0.08 | +0.04 | 13/28 | 0.3601 | 0.020 |
| gpl_bal_single | 59.83 | -1.33 | -1.20 | 7/28 | 0.0136 | 0.015 |
| oracle | 71.40 | +10.24 | +10.37 | 28/28 | 0.0000 | 0.015 |
