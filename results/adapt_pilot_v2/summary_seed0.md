# Direction 1 pilot: label-free adaptation to a new subject (seed 0)

Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. Subjects: 28. Adaptation budget: {'epochs': 10, 'lr': 0.0005, 'batch_size': 64, 'lambda_n2n': 1.0, 'gpl_threshold': 0.6, 'gpl_bal_quantile': 0.3}.

| method | accuracy (%) | Δ vs source (pp) | Δ vs adabn (pp) | improved vs adabn | Wilcoxon p vs adabn | mean |P(pred=1) - 0.5| |
|---|---|---|---|---|---|---|
| source | 61.30 | +0.00 | +0.09 | 14/28 | nan | 0.025 |
| adabn | 61.21 | -0.09 | +0.00 | 0/28 | nan | 0.026 |
| tent | 60.96 | -0.34 | -0.25 | 12/28 | 0.1563 | 0.061 |
| n2n | 61.36 | +0.05 | +0.14 | 11/28 | 0.1709 | 0.063 |
| gpl | 60.45 | -0.85 | -0.77 | 8/28 | 0.1042 | 0.329 |
| gpl_bal | 66.94 | +5.64 | +5.73 | 22/28 | 0.0001 | 0.015 |
| n2n_gpl | 60.48 | -0.82 | -0.73 | 8/28 | 0.1042 | 0.329 |
| balance | 61.30 | -0.01 | +0.08 | 15/28 | 0.0833 | 0.019 |
| gpl_bal_single | 59.49 | -1.81 | -1.72 | 7/28 | 0.0061 | 0.016 |
| oracle | 71.11 | +9.81 | +9.90 | 28/28 | 0.0000 | 0.015 |
