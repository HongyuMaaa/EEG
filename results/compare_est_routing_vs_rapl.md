# Paired comparison — protocol `loso`, reference `est_full_rapl`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| est_full | 3 | 28 | 84 | 62.63 ± 7.27 | -5.20 | 2/28 | 0.0000 |  |  |
| est_full_rapl | 3 | 28 | 84 | 67.83 ± 9.67 | +0.00 | 0/28 | nan |  |  |
| est_knn | 3 | 28 | 84 | 62.48 ± 7.58 | -5.34 | 4/28 | 0.0000 |  |  |
| est_knn_rapl | 3 | 28 | 84 | 65.95 ± 9.46 | -1.88 | 7/28 | 0.0564 |  |  |
| est_oracle_knn | 3 | 28 | 84 | 62.42 ± 6.92 | -5.40 | 4/28 | 0.0000 |  |  |
| est_rand_knn | 3 | 28 | 84 | 60.40 ± 6.58 | -7.43 | 2/28 | 0.0000 |  |  |
