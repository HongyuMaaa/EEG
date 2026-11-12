# Paired comparison — protocol `within`, reference `eegnet@ft`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| eegnet | 3 | 28 | 168 | 74.48 ± 8.52 | -0.29 | 9/28 | 0.0028 |  |  |
| eegnet@ft | 3 | 28 | 168 | 74.77 ± 8.40 | +0.00 | 0/28 | nan |  |  |
| red_selfteacher | 3 | 28 | 168 | 75.30 ± 8.44 | +0.53 | 25/28 | 0.0000 | 74.3 / 83.3 / 87.9 | 0.019 / 0.047 |
| red_selfteacher@ft | 3 | 28 | 168 | 75.49 ± 8.36 | +0.72 | 26/28 | 0.0000 | 74.7 / 83.9 / 88.8 | 0.021 / 0.047 |
