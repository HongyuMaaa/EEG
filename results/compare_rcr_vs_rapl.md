# Paired comparison — protocol `loso`, reference `rcr_full_rapl`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| rcr_full | 3 | 28 | 84 | 62.78 ± 6.90 | -5.96 | 4/28 | 0.0001 |  |  |
| rcr_random | 3 | 28 | 84 | 60.81 ± 6.67 | -7.93 | 5/28 | 0.0000 |  |  |
| rcr_uniform | 3 | 28 | 84 | 62.72 ± 7.20 | -6.02 | 7/28 | 0.0002 |  |  |
| rcr_top1 | 3 | 28 | 84 | 64.73 ± 7.71 | -4.01 | 7/28 | 0.0006 |  |  |
| rcr_top3 | 3 | 28 | 84 | 64.70 ± 7.81 | -4.04 | 8/28 | 0.0016 |  |  |
| rcr_soft | 3 | 28 | 84 | 64.69 ± 8.12 | -4.05 | 8/28 | 0.0022 |  |  |
| rcr_oracle | 3 | 28 | 84 | 65.78 ± 7.25 | -2.96 | 10/28 | 0.0218 |  |  |
| rcr_full_rapl | 3 | 28 | 84 | 68.74 ± 9.87 | +0.00 | 0/28 | nan |  |  |
| rcr_top1_rapl | 3 | 28 | 84 | 69.40 ± 9.69 | +0.66 | 20/28 | 0.0163 |  |  |
| rcr_top3_rapl | 3 | 28 | 84 | 69.81 ± 9.97 | +1.07 | 24/28 | 0.0001 |  |  |
