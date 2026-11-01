# Direction 1 pilot: label-free adaptation to a new subject (seed 0)

Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. Subjects: 28. Adaptation budget: {'epochs': 10, 'lr': 0.0005, 'batch_size': 64, 'lambda_n2n': 1.0, 'gpl_threshold': 0.6, 'gpl_bal_quantile': 0.3}.

| method | accuracy (%) | Δ vs source (pp) | Δ vs adabn (pp) | improved vs adabn | Wilcoxon p vs adabn | mean |P(pred=1) - 0.5| |
|---|---|---|---|---|---|---|
| source | 61.30 | +0.00 | +0.08 | 13/28 | nan | 0.025 |
| adabn | 61.21 | -0.08 | +0.00 | 0/28 | nan | 0.026 |
| tent | 60.97 | -0.33 | -0.25 | 12/28 | 0.1598 | 0.061 |
| n2n | 61.37 | +0.07 | +0.15 | 11/28 | 0.2451 | 0.063 |
| gpl | 60.46 | -0.83 | -0.75 | 8/28 | 0.1093 | 0.329 |
| gpl_bal | 66.92 | +5.63 | +5.71 | 22/28 | 0.0000 | 0.015 |
| n2n_gpl | 60.46 | -0.83 | -0.75 | 8/28 | 0.1042 | 0.329 |
| oracle | 71.10 | +9.80 | +9.89 | 28/28 | 0.0000 | 0.015 |
