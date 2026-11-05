# Paired comparison — protocol `loso`, reference `eegnet`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| eegnet | 1 | 28 | 168 | 62.26 ± 7.88 | +0.00 | 0/28 | nan |  |  |
| oracle_phen_split | 3 | 28 | 168 | 62.06 ± 7.76 | -0.19 | 11/28 | 0.6136 |  |  |
| oracle_rand_split | 3 | 28 | 168 | 59.96 ± 6.46 | -2.30 | 4/28 | 0.0003 |  |  |
| oracle_wrong_split | 3 | 28 | 168 | 59.54 ± 6.44 | -2.72 | 5/28 | 0.0052 |  |  |
| oracle_phen_knn | 3 | 28 | 168 | 64.05 ± 9.27 | +1.79 | 19/28 | 0.0065 |  |  |
| oracle_rand_knn | 3 | 28 | 168 | 59.96 ± 5.96 | -2.30 | 5/28 | 0.0009 |  |  |
| oracle_phen_cond | 3 | 28 | 168 | 63.10 ± 10.04 | +0.85 | 17/28 | 0.2842 |  |  |
