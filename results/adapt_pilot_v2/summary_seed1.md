# Direction 1 pilot: label-free adaptation to a new subject (seed 1)

Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. Subjects: 28. Adaptation budget: {'epochs': 10, 'lr': 0.0005, 'batch_size': 64, 'lambda_n2n': 1.0, 'gpl_threshold': 0.6, 'gpl_bal_quantile': 0.3}.

| method | accuracy (%) | Δ vs source (pp) | Δ vs adabn (pp) | improved vs adabn | Wilcoxon p vs adabn | mean |P(pred=1) - 0.5| |
|---|---|---|---|---|---|---|
| source | 60.55 | +0.00 | +0.10 | 15/28 | nan | 0.031 |
| adabn | 60.45 | -0.10 | +0.00 | 0/28 | nan | 0.025 |
| tent | 60.65 | +0.10 | +0.21 | 18/28 | 0.0986 | 0.028 |
| n2n | 60.32 | -0.23 | -0.13 | 9/28 | 0.0662 | 0.104 |
| gpl | 59.27 | -1.28 | -1.18 | 9/28 | 0.1042 | 0.340 |
| gpl_bal | 64.72 | +4.17 | +4.27 | 18/28 | 0.0056 | 0.015 |
| n2n_gpl | 59.51 | -1.04 | -0.94 | 8/28 | 0.1395 | 0.331 |
| balance | 60.51 | -0.04 | +0.06 | 13/28 | 0.4508 | 0.019 |
| gpl_bal_single | 59.44 | -1.11 | -1.01 | 8/28 | 0.0451 | 0.013 |
| oracle | 70.83 | +10.28 | +10.38 | 28/28 | 0.0000 | 0.017 |
