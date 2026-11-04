# RAPL — label-free adaptation to a new subject (seed 0, 28 subjects)

Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. `rapl` = candidate selected on the fold's validation subjects; `rapl_safe` = rapl or AdaBN by a label-free rule fitted on the other subjects.

| method | accuracy (%) | Δ vs AdaBN (pp) | improved | worse | Wilcoxon p | Δ vs oracle gap recovered |
|---|---|---|---|---|---|---|
| source | 61.58 | +0.10 | 14 | 13 | 0.54 | 0.01 |
| adabn | 61.48 | +0.00 | 0 | 0 | nan | 0.00 |
| balance | 61.57 | +0.10 | 16 | 9 | 0.0475 | 0.01 |
| gpl_bal_single | 59.44 | -2.04 | 7 | 21 | 0.00478 | -0.21 |
| q30 | 66.90 | +5.42 | 22 | 6 | 3.18e-05 | 0.56 |
| q20 | 65.68 | +4.20 | 20 | 8 | 0.00223 | 0.44 |
| q40 | 67.65 | +6.17 | 24 | 3 | 5.43e-05 | 0.64 |
| sched | 67.25 | +5.77 | 22 | 6 | 1.29e-05 | 0.60 |
| q30_e20 | 67.99 | +6.51 | 21 | 6 | 0.000273 | 0.68 |
| rapl | 67.71 | +6.23 | 22 | 5 | 7.37e-05 | 0.65 |
| rapl_safe | 67.58 | +6.11 | 20 | 5 | 0.000157 | 0.63 |
| oracle | 71.10 | +9.62 | 28 | 0 | 7.45e-09 | 1.00 |

Nested selection picked: {'q30_e20': 11, 'q40': 11, 'sched': 6}

Label-free diagnostics vs RAPL gain (Spearman):

- sep_src: r = 0.13, p = 0.507
- sep_post: r = 0.69, p = 4.54e-05
- pl_stability: r = -0.48, p = 0.00893
- flip_rate: r = 0.62, p = 0.00043

Safety rule: adaptation skipped for 2 subject(s): Sub01 (sep_src < 0.051), Sub05 (sep_post < 0.117)
