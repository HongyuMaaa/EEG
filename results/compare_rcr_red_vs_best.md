# Paired comparison — protocol `loso`, reference `rcr_top3_rapl`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| rcr_full | 3 | 28 | 84 | 62.78 ± 6.90 | -7.03 | 3/28 | 0.0000 |  |  |
| rcr_red_full | 3 | 28 | 84 | 62.92 ± 7.18 | -6.89 | 7/28 | 0.0000 |  |  |
| rcr_uniform | 3 | 28 | 84 | 62.72 ± 7.20 | -7.09 | 6/28 | 0.0000 |  |  |
| rcr_red_uniform | 3 | 28 | 84 | 62.66 ± 7.13 | -7.15 | 6/28 | 0.0000 |  |  |
| rcr_top1 | 3 | 28 | 84 | 64.73 ± 7.71 | -5.08 | 6/28 | 0.0000 |  |  |
| rcr_red_top1 | 3 | 28 | 84 | 64.64 ± 7.48 | -5.17 | 5/28 | 0.0000 |  |  |
| rcr_top3 | 3 | 28 | 84 | 64.70 ± 7.81 | -5.11 | 8/28 | 0.0000 |  |  |
| rcr_red_top3 | 3 | 28 | 84 | 64.67 ± 7.54 | -5.14 | 8/28 | 0.0002 |  |  |
| rcr_soft | 3 | 28 | 84 | 64.69 ± 8.12 | -5.12 | 8/28 | 0.0000 |  |  |
| rcr_red_soft | 3 | 28 | 84 | 64.39 ± 7.83 | -5.42 | 8/28 | 0.0001 |  |  |
| rcr_oracle | 3 | 28 | 84 | 65.78 ± 7.25 | -4.03 | 9/28 | 0.0014 |  |  |
| rcr_red_oracle | 3 | 28 | 84 | 65.70 ± 7.02 | -4.11 | 8/28 | 0.0020 |  |  |
| rcr_full_rapl | 3 | 28 | 84 | 68.74 ± 9.87 | -1.07 | 3/28 | 0.0001 |  |  |
| rcr_red_full_rapl | 3 | 28 | 84 | 69.42 ± 9.90 | -0.39 | 8/28 | 0.0317 |  |  |
| rcr_top1_rapl | 3 | 28 | 84 | 69.40 ± 9.69 | -0.41 | 9/28 | 0.0628 |  |  |
| rcr_red_top1_rapl | 3 | 28 | 84 | 69.72 ± 9.85 | -0.09 | 12/28 | 0.3052 |  |  |
| rcr_top3_rapl | 3 | 28 | 84 | 69.81 ± 9.97 | +0.00 | 0/28 | nan |  |  |
| rcr_red_top3_rapl | 3 | 28 | 84 | 70.09 ± 9.70 | +0.28 | 16/28 | 0.1936 |  |  |
