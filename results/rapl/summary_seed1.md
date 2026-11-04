# RAPL — label-free adaptation to a new subject (seed 1, 28 subjects)

Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. `rapl` = candidate selected on the fold's validation subjects; `rapl_safe` = rapl or AdaBN by a label-free rule fitted on the other subjects.

| method | accuracy (%) | Δ vs AdaBN (pp) | improved | worse | Wilcoxon p | Δ vs oracle gap recovered |
|---|---|---|---|---|---|---|
| source | 60.60 | +0.07 | 14 | 11 | 0.326 | 0.01 |
| adabn | 60.53 | +0.00 | 0 | 0 | nan | 0.00 |
| balance | 60.60 | +0.06 | 12 | 11 | 0.429 | 0.01 |
| gpl_bal_single | 59.62 | -0.92 | 9 | 19 | 0.0628 | -0.09 |
| q30 | 64.79 | +4.25 | 18 | 10 | 0.00518 | 0.41 |
| q20 | 63.77 | +3.24 | 16 | 11 | 0.0271 | 0.31 |
| q40 | 65.24 | +4.70 | 20 | 8 | 0.00223 | 0.46 |
| sched | 64.94 | +4.40 | 20 | 8 | 0.00478 | 0.43 |
| q30_e20 | 65.39 | +4.85 | 19 | 9 | 0.00518 | 0.47 |
| rapl | 65.18 | +4.65 | 21 | 7 | 0.00244 | 0.45 |
| rapl_safe | 66.12 | +5.58 | 20 | 4 | 0.000255 | 0.54 |
| oracle | 70.83 | +10.29 | 28 | 0 | 7.45e-09 | 1.00 |

Nested selection picked: {'q30_e20': 12, 'q40': 9, 'sched': 7}

Label-free diagnostics vs RAPL gain (Spearman):

- sep_src: r = 0.14, p = 0.472
- sep_post: r = 0.48, p = 0.009
- pl_stability: r = -0.37, p = 0.052
- flip_rate: r = 0.42, p = 0.0259

Safety rule: adaptation skipped for 4 subject(s): Sub01 (sep_src < 0.051), Sub03 (sep_src < 0.050), Sub15 (sep_src < 0.050), Sub21 (sep_src < 0.050)
