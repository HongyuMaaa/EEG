# Paired comparison — protocol `loso`, reference `eegnet_sz`

Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.

| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p | teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |
|---|---|---|---|---|---|---|---|---|---|
| lrmoe | 1 | 28 | 168 | 61.46 ± 8.09 | +0.90 | 15/28 | 0.2359 |  |  |
| lrmoe_subjgate | 1 | 28 | 168 | 61.44 ± 8.07 | +0.88 | 17/28 | 0.2016 |  |  |
| eegnet_sz | 1 | 28 | 168 | 60.55 ± 8.02 | +0.00 | 0/28 | nan |  |  |
| eegnet_sz_subjgate | 1 | 28 | 168 | 60.55 ± 8.02 | +0.00 | 0/28 | nan |  |  |
| eegnet_mirroraug | 1 | 28 | 168 | 61.62 ± 7.92 | +1.06 | 12/28 | 0.8139 |  |  |
| eegnet_mirroraug_subjgate | 1 | 28 | 168 | 61.62 ± 7.92 | +1.06 | 12/28 | 0.8139 |  |  |
| lrmoe_generic | 1 | 28 | 168 | 62.13 ± 8.15 | +1.57 | 17/28 | 0.0477 |  |  |
| lrmoe_generic_subjgate | 1 | 28 | 168 | 61.56 ± 7.98 | +1.00 | 12/28 | 0.8665 |  |  |
| lrmoe_nodecomp | 1 | 28 | 168 | 62.18 ± 7.97 | +1.63 | 18/28 | 0.0185 |  |  |
| lrmoe_nodecomp_subjgate | 1 | 28 | 168 | 62.20 ± 8.04 | +1.64 | 20/28 | 0.0167 |  |  |
| lrmoe_nolat | 1 | 28 | 168 | 61.54 ± 7.95 | +0.99 | 15/28 | 0.0595 |  |  |
| lrmoe_nolat_subjgate | 1 | 28 | 168 | 61.57 ± 7.96 | +1.01 | 17/28 | 0.0402 |  |  |
| lrmoe_nocoh | 1 | 28 | 168 | 61.75 ± 8.17 | +1.20 | 15/28 | 0.3187 |  |  |
| lrmoe_nocoh_subjgate | 1 | 28 | 168 | 61.71 ± 8.28 | +1.16 | 14/28 | 0.4932 |  |  |
| lrmoe_anti | 1 | 28 | 168 | 62.06 ± 7.74 | +1.50 | 14/28 | 0.5806 |  |  |
| lrmoe_anti_subjgate | 1 | 28 | 168 | 62.03 ± 7.74 | +1.47 | 16/28 | 0.5979 |  |  |
