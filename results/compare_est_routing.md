# Paired comparison — protocol `loso`, reference `est_full`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| est_full | 3 | 28 | 84 | 62.63 ± 7.27 | +0.00 | 0/28 | nan |  |  |
| est_full_rapl | 3 | 28 | 84 | 67.83 ± 9.67 | +5.20 | 26/28 | 0.0000 |  |  |
| est_knn | 3 | 28 | 84 | 62.48 ± 7.58 | -0.15 | 14/28 | 0.8489 |  |  |
| est_knn_rapl | 3 | 28 | 84 | 65.95 ± 9.46 | +3.32 | 21/28 | 0.0065 |  |  |
| est_oracle_knn | 3 | 28 | 84 | 62.42 ± 6.92 | -0.21 | 13/28 | 0.8489 |  |  |
| est_rand_knn | 3 | 28 | 84 | 60.40 ± 6.58 | -2.23 | 6/28 | 0.0020 |  |  |
