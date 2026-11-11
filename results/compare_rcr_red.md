# Paired comparison — protocol `loso`, reference `rcr_full`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| rcr_full | 3 | 28 | 84 | 62.78 ± 6.90 | +0.00 | 0/28 | nan |  |  |
| rcr_red_full | 3 | 28 | 84 | 62.92 ± 7.18 | +0.14 | 15/28 | 0.4791 |  |  |
| rcr_uniform | 3 | 28 | 84 | 62.72 ± 7.20 | -0.06 | 12/28 | 0.7793 |  |  |
| rcr_red_uniform | 3 | 28 | 84 | 62.66 ± 7.13 | -0.11 | 15/28 | 0.8489 |  |  |
| rcr_top1 | 3 | 28 | 84 | 64.73 ± 7.71 | +1.95 | 22/28 | 0.0004 |  |  |
| rcr_red_top1 | 3 | 28 | 84 | 64.64 ± 7.48 | +1.86 | 21/28 | 0.0002 |  |  |
| rcr_top3 | 3 | 28 | 84 | 64.70 ± 7.81 | +1.92 | 24/28 | 0.0000 |  |  |
| rcr_red_top3 | 3 | 28 | 84 | 64.67 ± 7.54 | +1.89 | 22/28 | 0.0001 |  |  |
| rcr_soft | 3 | 28 | 84 | 64.69 ± 8.12 | +1.92 | 23/28 | 0.0000 |  |  |
| rcr_red_soft | 3 | 28 | 84 | 64.39 ± 7.83 | +1.62 | 22/28 | 0.0002 |  |  |
| rcr_oracle | 3 | 28 | 84 | 65.78 ± 7.25 | +3.00 | 28/28 | 0.0000 |  |  |
| rcr_red_oracle | 3 | 28 | 84 | 65.70 ± 7.02 | +2.92 | 26/28 | 0.0000 |  |  |
| rcr_full_rapl | 3 | 28 | 84 | 68.74 ± 9.87 | +5.96 | 23/28 | 0.0001 |  |  |
| rcr_red_full_rapl | 3 | 28 | 84 | 69.42 ± 9.90 | +6.65 | 25/28 | 0.0000 |  |  |
| rcr_top1_rapl | 3 | 28 | 84 | 69.40 ± 9.69 | +6.62 | 24/28 | 0.0000 |  |  |
| rcr_red_top1_rapl | 3 | 28 | 84 | 69.72 ± 9.85 | +6.94 | 24/28 | 0.0000 |  |  |
| rcr_top3_rapl | 3 | 28 | 84 | 69.81 ± 9.97 | +7.03 | 25/28 | 0.0000 |  |  |
| rcr_red_top3_rapl | 3 | 28 | 84 | 70.09 ± 9.70 | +7.31 | 26/28 | 0.0000 |  |  |
