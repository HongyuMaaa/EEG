# Round 4 analysis: RAPL (C2.2–C2.3) and LR-MoE (C2.1)

**Data:** results in `94c0a9e`. Leave-one-subject-out, n = 28; paired Wilcoxon tests at subject
level. Tables: `results/rapl/summary_seed{0,1,2}.md` and `results/compare_loso_moe.md`.

## 1. RAPL — label-free adaptation (3 seeds averaged per subject)

| Comparison | Δ (pp) | Subjects improved | p |
|---|---|---|---|
| `rapl` (nested selection) − AdaBN | **+5.71** | 23/28 | 5 × 10⁻⁵ |
| `q30` (a-priori setting) − AdaBN | +5.16 | 21/28 | 6 × 10⁻⁵ |
| `rapl` − `q30` (value of nested selection) | +0.55 | 20/28 | 0.013 |
| `q30_e20` − `q30` | +0.80 | 19/28 | 0.02 |

**Per seed** (`rapl` − AdaBN):

| Seed 0 | Seed 1 | Seed 2 |
|---|---|---|
| +6.23 | +4.65 | +6.24 |

**Supervised-oracle gain recovered:** 56%.

**Nested selection.** It chooses longer adaptation or larger labelled fractions:

| Setting | Times chosen (84 fold-seeds) |
|---|---|
| `q30_e20` | 33 |
| `q40` | 33 |
| `sched` | 18 |

**Subjects that lose** (3-seed mean): Sub21 −5.4, Sub04 −1.4, Sub03 −1.1, Sub13 −1.0,
Sub14 −0.7 pp.

**Controls confirmed again (all seeds):**
- `gpl_bal_single` (no repetition averaging) is below AdaBN in every seed (−0.9 to −2.0 pp);
- threshold re-centring alone does nothing (+0.04 to +0.10 pp).

**Safety rule — not reliable:**

| Seed | `rapl_safe` − `rapl` | Subjects skipped |
|---|---|---|
| 0 | −0.13 pp | 2 |
| 1 | +0.93 pp | 4 (including Sub15, a large winner in other seeds) |
| 2 | −0.46 pp | 2 |

- The skipped subjects differ between seeds.
- The diagnostics measured *after* adaptation correlate with the gain (separation r = 0.48–0.69;
  flip rate r = 0.42–0.75), but the separation *before* adaptation does not (r ≈ 0.1).
- A threshold learned on 27 subjects does not transfer stably.
- **Conclusion:** no safe-adaptation claim. The risk is reported as a limitation, concentrated
  in near-chance subjects.

## 2. LR-MoE — physiology-informed mixture of experts (seed 0)

Reference: the original leave-one-subject-out EEGNet (global normalisation, 62.26%,
3 seeds).

| Method | Accuracy (%) | Δ vs EEGNet (pp) | Improved | p |
|---|---|---|---|---|
| `eegnet_sz` (per-subject z-score) | 60.55 | −1.70 | 13/28 | 0.14 |
| `eegnet_mirroraug` | 61.62 | −0.64 | 9/28 | 0.08 |
| **`lrmoe`** | 61.46 | −0.80 | 14/28 | 0.28 |
| `lrmoe_generic` | 62.13 | −0.13 | 15/28 | 0.96 |
| `lrmoe_nodecomp` | 62.18 | −0.07 | 18/28 | 0.75 |
| `lrmoe_anti` | 62.06 | −0.20 | 13/28 | 0.44 |

Subject-averaged routing changes nothing (±0.05 pp).

**Diagnosis — the router does not route:**

| Variant | Normalised gate entropy | Between-subject SD of mean gate |
|---|---|---|
| `lrmoe` | 0.996 | 0.012 |
| `lrmoe_nodecomp` | 0.998 | 0.010 |
| `lrmoe_generic` | 0.987 | 0.030 |
| `lrmoe_anti` | 0.999 | 0.011 |

- All variants converge to an (almost) uniform average of their experts, i.e. an ensemble.
- The antisymmetric-expert share does not follow the subjects' mirror correlation
  (Spearman r = 0.28, p = 0.15).
- The apparent gains over `eegnet_sz` (+0.9 to +1.6 pp) are ensembling, plus the fact that
  per-subject z-scoring *hurts* EEGNet in LOSO (−1.7 pp).

**Why the routing failed:**
1. **Trial-level descriptors are too noisy.** At about −16 dB single-trial SNR, a trial's
   lateralisation energy or 10 Hz amplitude says almost nothing about which *subject phenotype*
   it comes from. The router has no usable input, and cross-entropy then favours equal
   averaging.
2. **Soft gating with a balance penalty has a trivial optimum,** the uniform ensemble. Nothing
   forces specialisation.
3. **The physiological differences that matter are class-conditional.** Mirror correlation and
   lateralisation latency need the labels (left→right vs right→left) to be measured.

## 3. Consequences for Chapter 2

**RAPL is now the solid core of Chapter 2:** +5.7 pp, nested-selected, controlled, 3 seeds.

**LR-MoE as designed is a negative result.** The physiological idea can still be tested properly
with a design that addresses the three failure reasons:

> **Phenotype-routed experts with label-free phenotype estimation.**
> - Routing happens per *subject*, on subject-level, class-conditional phenotype descriptors:
>   mirror correlation, lateralisation peak latency, antisymmetric/symmetric energy ratio of
>   the class-difference ERP.
> - For training subjects the descriptors are computed with labels.
> - For a new subject they are estimated from **RAPL pseudo-labels**, using repetition-averaged
>   group predictions as labels. This links C2.1 and C2.2.

**Feasibility gate (must come first, cheap):** *oracle phenotype routing*. Cluster the training
subjects by their true phenotype descriptors and train one EEGNet per cluster (or condition one
EEGNet on the descriptor). Route each test subject with its *true* descriptor.
- If even oracle routing does not beat the single model, subject heterogeneity cannot be
  exploited by routing on this dataset, and the MoE direction is closed with a clean negative
  result.
- If it does, the label-free estimate via RAPL is the second step.
