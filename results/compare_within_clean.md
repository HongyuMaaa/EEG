# Paired comparison — protocol `within`, reference `eegnet`

Test sessions excluded: [2, 5]. Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| eegnet | 3 | 28 | 112 | 74.57 ± 8.63 | +0.00 | 0/28 | nan |  |  |
| dcpm | 1 | 28 | 112 | 72.64 ± 9.35 | -1.93 | 1/28 | 0.0000 |  |  |
| eegnet_avgaug | 1 | 28 | 112 | 74.32 ± 8.81 | -0.24 | 8/28 | 0.0337 |  |  |
| kd_naive | 1 | 28 | 112 | 74.59 ± 8.71 | +0.02 | 15/28 | 0.6295 | 73.5 / 83.3 / 89.4 |  |
| red_n2n | 1 | 28 | 112 | 74.57 ± 8.85 | +0.00 | 16/28 | 0.7966 | 73.5 / 83.3 / 89.4 | 0.036 / 0.049 |
| red_critic | 1 | 28 | 112 | 74.91 ± 8.54 | +0.34 | 21/28 | 0.0011 | 73.5 / 83.3 / 89.4 |  |
| red_classmean | 1 | 28 | 112 | 75.18 ± 8.75 | +0.61 | 26/28 | 0.0000 | 73.5 / 83.3 / 89.4 | 0.020 / 0.039 |
| red_randteacher | 1 | 28 | 112 | 74.86 ± 8.79 | +0.29 | 19/28 | 0.0317 | 48.8 / 48.7 / 48.8 | 0.036 / 0.050 |
| red_selfteacher | 1 | 28 | 112 | 75.26 ± 8.61 | +0.69 | 25/28 | 0.0000 | 74.4 / 83.4 / 88.2 | 0.019 / 0.047 |
| red | 3 | 28 | 112 | 75.32 ± 8.54 | +0.75 | 26/28 | 0.0000 | 73.4 / 83.4 / 89.3 | 0.025 / 0.046 |
| red@tuned | 3 | 28 | 112 | 75.34 ± 8.44 | +0.77 | 26/28 | 0.0000 | 73.4 / 83.4 / 89.3 | 0.030 / 0.049 |
