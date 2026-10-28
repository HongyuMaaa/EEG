# Chapter 1 (RED) — round 1 analysis and next-step strategy

**Data:** results committed in `308d49f` (seed 0, RTX 3060). Statistics are at subject level
(n = 28; each subject's accuracy pooled over its 6 test sessions). Tables:
`results/compare_within.md`, `results/compare_pooled.md`.

## 1. Results

### Within-subject (primary protocol)

| Method | Accuracy (%) | Δ vs EEGNet (pp) | 95% CI (bootstrap) | Subjects improved | Folds improved | p (Wilcoxon) | Bonferroni ×5 |
|---|---|---|---|---|---|---|---|
| DCPM | 72.57 | −1.85 | | 1/28 | | < 10⁻⁴ | |
| EEGNet | 74.42 | — | | | | | |
| kd_naive | 74.49 | +0.07 | [−0.13, 0.25] | 16/28 | 90/168 | 0.35 | 1 |
| red_n2n | 74.51 | +0.09 | [−0.11, 0.29] | 16/28 | 85/168 | 0.34 | 1 |
| red_critic | 74.77 | +0.35 | [0.19, 0.52] | 21/28 | 103/168 | 0.001 | 0.005 |
| red_classmean | 75.03 | +0.61 | [0.41, 0.81] | 25/28 | 111/168 | 4 × 10⁻⁵ | 2 × 10⁻⁴ |
| **red** | **75.11** | **+0.69** | **[0.46, 0.93]** | **25/28** | **112/168** | **3 × 10⁻⁵** | **2 × 10⁻⁴** |

- **Effect size:** Cohen's d_z = 1.10 for `red`.
- **Teacher (same for all variants):** 73.5% on single trials, 83.3% on 3-trial averages,
  89.4% on 6-trial averages.

### Pooled (secondary protocol)

| Method | Δ vs EEGNet (pp) | p |
|---|---|---|
| red | −0.04 | 0.78 |
| red_n2n | +0.18 | 0.18 |
| kd_naive | −0.24 | 0.21 |

No significant change. The pooled teacher is much weaker: 66.1% single, 80.0% on 6-trial
averages, against 89.4% within-subject.

### Training behaviour

- **Convergence:** all runs converged; ≤ 5 of 168 folds per method reached the 500-epoch cap.
- **Cost:** RED takes about 3× EEGNet's training time (80 s vs 27 s per fold, median), plus
  the shared teacher (1.3 h in total).
- **Reconstruction loss:** it plateaus by about epoch 25 (0.72 in normalised units), the noise
  floor set by the 5-trial target.
- **Critic loss:** it keeps decreasing, tracking the classification loss.

## 2. What the results establish

1. **RED improves single-trial accuracy significantly and consistently, but by a small
   amount:** +0.69 pp, 25/28 subjects. The gain survives correction for 5 comparisons. It
   recovers about 5% of the 15 pp averaging headroom (74.4% single → 89.4% teacher on 6-trial
   averages).
2. **Naive distillation from averages does nothing** (+0.07 pp, n.s.). This confirms the
   premise: averaged information does not transfer by imitating the teacher's output on the
   average.
3. **The critic is the active ingredient, and it interacts with reconstruction:**

   | Variant | Δ vs EEGNet (pp) |
   |---|---|
   | n2n alone | +0.09 (n.s.) |
   | critic alone | +0.35 |
   | both (`red`) | +0.69 |

   `red` beats `red_critic` by 0.34 pp (p = 0.002). Reconstruction matters only when the teacher
   judges it.
4. **Matching the overlap context does not matter.** The class-mean target gives +0.61 pp
   versus +0.69 pp for the group target (difference 0.08 pp, p = 0.12). The design document's
   contribution 3 ("context-matched averaging groups") is **not supported** and should be
   dropped or reframed.

## 3. Open issues

| # | Issue | Why it matters |
|---|---|---|
| I1 | **Mechanism not demonstrated.** The gain is nearly uniform across subjects. It does not correlate with baseline accuracy (r = −0.01), the teacher's averaging gain (r = 0.16) or reconstruction R² (r = −0.12). | The gain could come from a generic regularisation effect (a second, frozen classification head acting on a reconstruction) rather than from knowledge in the *averaged* teacher. Without a control, a reviewer can attribute the gain to regularisation, and the central claim would be unsupported. |
| I2 | **Effect is small** (+0.7 pp). | Statistically solid, but a thin result for a thesis chapter. Loss weights were never tuned (λ_n2n = 1, λ_critic = 0.5, τ = 2 are first guesses). |
| I3 | **Missing obvious baseline: averaging as data augmentation.** EEGNet trained on single trials *plus* random k-trial averages. | The simplest way to "use averages"; reviewers will ask. RED must beat it. |
| I4 | **Single seed.** | Seed variance is unknown. The subject-level test is strong, but the thesis needs ≥ 3 seeds for the main comparisons. |
| I5 | **No gain in the pooled protocol.** | Explained by the weak cross-subject teacher. This is a limitation of RED and points to inter-subject variability, the subject of Chapter 2. |
| I6 | **The midterm deck shows illustrative RED numbers that contradict the measurements.** It shows ≈ +2–5 pp gains and N2N contributing more than the critic; measured, N2N alone does nothing. | Must be replaced with measured values before any presentation. |

## 4. Strategy

### Phase A — controls that decide the narrative (≈ 6 GPU-hours, within protocol, seed 0)

| Run | Definition | Interpretation |
|---|---|---|
| `red_selfteacher` | RED with the teacher trained on **single trials** (k = 1) | If ≈ `red`: the gain is regularisation, not averaging knowledge (I1). If clearly below `red`: averaging knowledge is the cause. **Most important run.** |
| `red_randteacher` | RED with a randomly initialised frozen teacher | Lower bound: the effect of an arbitrary fixed head |
| `eegnet_avgaug` | EEGNet on single trials + random k-trial averages (k ∈ {2, 3, 6}), 50/50 mix | The "obvious" baseline (I3) |
| Seeds 1 and 2 of `eegnet` and `red` | | Seed variance (I4) |

### Phase B — strengthen the effect, tuned on validation data only (≈ 10–15 GPU-hours)

**Selection rule:** choose hyperparameters by mean **validation** accuracy across folds. Test
sessions are never used for selection, which keeps the test result unbiased.

1. **Loss-weight sweep:** λ_critic ∈ {0.5, 1, 2} × λ_n2n ∈ {0.3, 1, 3}, then τ ∈ {1, 2, 4} at
   the best setting.
2. **Teacher matched to what the critic sees.** The critic evaluates *reconstructions*, which
   are partially denoised. Train the teacher on averages from k = 1 to 6, so that it gives
   calibrated judgements across the whole SNR range.
3. **Critic on the hemispheric-difference reconstruction only**, if the sweep shows lateral R²
   driving the gain.

### Phase C — decision point

| If Phase A shows… | Then |
|---|---|
| `red` > `red_selfteacher` and `red` > `eegnet_avgaug` | Keep the chapter's claim ("knowledge from averaging, transferred through a reconstruction critic"). Report Phase B's best configuration over 3 seeds. |
| `red` ≈ `red_selfteacher` | Reframe the chapter as *reconstruction-critic regularisation for single-trial ERP decoding*, with averaging as one way to build the critic. Or move the averaging knowledge into the student more directly (e.g. feature-level distillation), and present the current RED as the negative/control result. |

### Then

Update the deck with the measured numbers (I6), and start Chapter 2 (LR-MoE). The pooled and
LOSO results — EEGNet 66.9% pooled and 62.3% LOSO versus 74.4% within — quantify the
inter-subject gap that Chapter 2 addresses.
