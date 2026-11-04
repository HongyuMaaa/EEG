# RAPL — label-free adaptation to a new subject (seed 2, 28 subjects)

Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. `rapl` = candidate selected on the fold's validation subjects; `rapl_safe` = rapl or AdaBN by a label-free rule fitted on the other subjects.

| method | accuracy (%) | Δ vs AdaBN (pp) | improved | worse | Wilcoxon p | Δ vs oracle gap recovered |
|---|---|---|---|---|---|---|
| source | 61.15 | +0.16 | 19 | 9 | 0.186 | 0.02 |
| adabn | 60.99 | +0.00 | 0 | 0 | nan | 0.00 |
| balance | 61.04 | +0.04 | 13 | 11 | 0.338 | 0.00 |
| gpl_bal_single | 59.80 | -1.19 | 7 | 21 | 0.0146 | -0.11 |
| q30 | 66.79 | +5.80 | 22 | 6 | 0.000244 | 0.56 |
| q20 | 65.56 | +4.57 | 21 | 6 | 0.0014 | 0.44 |
| q40 | 67.19 | +6.20 | 23 | 5 | 0.000274 | 0.60 |
| sched | 67.07 | +6.07 | 24 | 4 | 9.32e-05 | 0.58 |
| q30_e20 | 67.49 | +6.50 | 21 | 7 | 0.000716 | 0.63 |
| rapl | 67.23 | +6.24 | 23 | 5 | 0.000194 | 0.60 |
| rapl_safe | 66.77 | +5.77 | 21 | 5 | 0.0011 | 0.56 |
| oracle | 71.39 | +10.39 | 28 | 0 | 7.45e-09 | 1.00 |

Nested selection picked: {'q40': 13, 'q30_e20': 10, 'sched': 5}

Label-free diagnostics vs RAPL gain (Spearman):

- sep_src: r = 0.10, p = 0.597
- sep_post: r = 0.62, p = 0.000438
- pl_stability: r = -0.46, p = 0.0139
- flip_rate: r = 0.75, p = 5.14e-06

Safety rule: adaptation skipped for 2 subject(s): Sub20 (sep_src < 0.050), Sub24 (sep_post < 0.148)
