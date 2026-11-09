# Round 7: repetition-consistency routing (RCR) over subject-bagged experts

**Data:** results in `e784e22`. Leave-one-subject-out, test on sessions 4–6, 3 seeds averaged
per subject, n = 28.

**Expert pool per target subject:** the full-data EEGNet + 8 EEGNets, each on a random 13 of the
27 source subjects.

**Router:** repetition consistency `cons` on the target's **unlabelled** sessions 1–3.

## 1. Results

| Method | Accuracy (%) | Δ vs full model (pp) | Improved | p |
|---|---|---|---|---|
| `rcr_full` (full-data model) | 62.78 | — | | |
| `rcr_random` (random expert) | 60.81 | −1.96 | 5/28 | < 10⁻⁴ |
| `rcr_uniform` (equal average of all 9 experts) | 62.72 | −0.06 | 12/28 | 0.78 |
| **`rcr_top1`** | 64.73 | **+1.95** | 22/28 | 4 × 10⁻⁴ |
| **`rcr_top3`** | 64.70 | **+1.92** | **24/28** | < 10⁻⁴ |
| `rcr_soft` | 64.69 | +1.92 | 23/28 | < 10⁻⁴ |
| `rcr_oracle` (best expert by test labels) | 65.78 | +3.00 | 28/28 | |
| `rcr_full_rapl` (full model + RAPL) | 68.74 | +5.96 | 23/28 | 1 × 10⁻⁴ |
| `rcr_top1_rapl` | 69.40 | +6.62 | 24/28 | < 10⁻⁴ |
| **`rcr_top3_rapl`** | **69.81** | **+7.03** | **25/28** | < 10⁻⁴ |

**RCR on top of RAPL:**
- `rcr_top3_rapl` − `rcr_full_rapl` = **+1.07 pp** (24/28, p = 1 × 10⁻⁴);
- `rcr_top1_rapl` − `rcr_full_rapl` = +0.66 pp (20/28, p = 0.016).

**Per seed:**

| Comparison | Seed 0 | Seed 1 | Seed 2 |
|---|---|---|---|
| `rcr_top3` − full (pp) | +1.96 | +2.77 | +1.03 |
| `rcr_top3_rapl` − `rcr_full_rapl` (pp) | +1.34 | +1.39 | +0.48 |

## 2. What the router does

- **It is selection, not ensembling.** The uniform average of the same 9 experts gives −0.06 pp;
  routing by consistency gives +1.9 pp.
- **The score tracks the experts' true accuracy.** Mean within-subject Spearman between `cons`
  and test accuracy is 0.59. The top-1 choice is the truly best of 9 experts in 48% of cases
  (median rank 2). The full-data model is chosen only 10% of the time.
- **The routing captures about two thirds of the oracle gain:** +1.92 of +3.00 pp.
- **Gains are broad:** +2.3 pp for strongly lateralising subjects, +1.6 pp for the others
  (correlation with mirror_corr r = 0.25, n.s.).
- **Risk with RAPL:** `rcr_top3_rapl` is below the plain full-data model for only 3 subjects
  (Sub14 −2.5, Sub03 −1.1, Sub05 −0.5 pp).

## 3. Chapter 2 — final contributions

| | Contribution | Evidence |
|---|---|---|
| C2.1 | **Repetition-consistency routing (RCR):** a subject-level, label-free mixture of experts whose router is driven by the paradigm's repetition structure | +1.92 pp over the full model (24/28); +1.07 pp on top of RAPL (24/28); uniform ensemble +0.0 |
| C2.2 | **RAPL:** repetition-averaged, session-balanced pseudo-labelling for label-free subject adaptation | +5.2–6.0 pp in four independent runs (rounds 3–7); controls: single-trial pseudo-labels hurt, threshold re-centring does nothing |
| C2.3 | **RCR + RAPL combined** | **62.8 → 69.8% (+7.0 pp)** without any target labels; supervised oracle ≈ 71% |
| C2.4 | **Why trial-level physiological routing fails, and what subject heterogeneity can and cannot offer** (negative / diagnostic results) | LR-MoE gates collapse (entropy 0.996); oracle phenotype routing +1.5–1.8 pp but carried by a label-dependent latency feature; label-free mirror/anti descriptors (r ≈ 0.8) do not help routing |

**Narrative:**
1. A conventional, physiology-gated MoE fails on single aVEP trials (SNR ≈ −16 dB).
2. Subjects differ in exploitable ways, but the oracle shows the useful information needs labels.
3. The paradigm's own repetition structure provides a label-free signal strong enough to choose
   experts per subject (RCR) and to adapt them (RAPL).
