# Paired comparison — protocol `within`, reference `eegnet`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| eegnet | 3 | 28 | 168 | 74.48 ± 8.52 | +0.00 | 0/28 | nan |  |  |
| red_selfteacher | 3 | 28 | 168 | 75.30 ± 8.44 | +0.81 | 26/28 | 0.0000 | 74.3 / 83.3 / 87.9 | 0.019 / 0.047 |
| red_aligned | 3 | 28 | 168 | 75.25 ± 8.48 | +0.77 | 27/28 | 0.0000 | 74.3 / 83.3 / 87.9 | 0.017 / 0.044 |
