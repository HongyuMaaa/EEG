# Paired comparison — protocol `pooled`, reference `eegnet`

| method | subjects | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|
| dcpm | 28 | 63.21 ± 6.76 | -3.70 | 7/28 | 0.0020 |  |  |
| dcpm_plain | 28 | 63.15 ± 6.69 | -3.76 | 8/28 | 0.0015 |  |  |
| eegnet | 28 | 66.91 ± 8.82 | +0.00 | 0/28 | nan |  |  |
| kd_naive | 28 | 66.66 ± 9.17 | -0.24 | 10/28 | 0.2145 | 66.1 / 75.6 / 80.0 |  |
| red | 28 | 66.87 ± 8.53 | -0.04 | 13/28 | 0.7823 | 66.1 / 75.6 / 80.0 | -0.001 / 0.013 |
| red_n2n | 28 | 67.09 ± 8.61 | +0.18 | 18/28 | 0.1790 | 66.1 / 75.6 / 80.0 | 0.011 / 0.017 |
