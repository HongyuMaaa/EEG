# Chapter 1 (RED) — round 2 analysis: controls, seeds and tuning

**Data:** results committed up to `d7d8c07`.
**Statistics:** subject level, n = 28. Paired Wilcoxon signed-rank tests; 95% bootstrap CIs.
Methods with 3 seeds are averaged per subject. Tables: `results/compare_within.md` and
`results/compare_within_clean.md` (test sessions 2 and 5 excluded, because they served as
validation sessions for tuning; conclusions are identical), plus `results/sweep_*.md`.

## 1. Results

| Comparison | Δ (pp) | 95% CI | Subjects improved | p |
|---|---|---|---|---|
| `red` − EEGNet (3 seeds each) | **+0.75** | [0.59, 0.92] | 27/28 | 4 × 10⁻⁶ |
| `red@tuned` − EEGNet (3 seeds each) | +0.79 | | 26/28 | < 10⁻⁴ |
| `red@tuned` − `red` (3 seeds each) | +0.04 | [−0.07, 0.15] | 13/28 | 0.71 |
| `red` − `red_selfteacher` (seed 0) | **−0.07** | [−0.24, 0.10] | 12/28 | 0.56 |
| `red_selfteacher` − `red_randteacher` (seed 0) | +0.41 | [0.22, 0.59] | 23/28 | 0.0009 |
| `red_randteacher` − EEGNet (seed 0) | +0.35 | [0.15, 0.55] | 22/28 | 0.004 |
| `eegnet_avgaug` − EEGNet (seed 0) | **−0.28** | [−0.48, −0.11] | 8/28 | 0.008 |

**Seed variability:**

| Quantity | Value |
|---|---|
| EEGNet mean accuracy over seeds 0 / 1 / 2 | 74.42 / 74.50 / 74.53 % |
| `red` mean accuracy over seeds 0 / 1 / 2 | 75.11 / 75.25 / 75.34 % |
| RED gain per seed | +0.69 / +0.75 / +0.82 pp |
| Within-subject seed SD | 0.37 pp |

**Tuning:**

| Sweep | Validation-accuracy span of the configurations | Selected |
|---|---|---|
| `weights` (9 configurations) | 75.14–75.64 % | λ_critic = 1, λ_n2n = 3 |
| `tau` | ±0.07 pp | τ = 2 (the default) |
| `teacher` | | k ∈ {2, 3, 6}, β = 1 (the defaults) |

The `weights` span (0.50 pp) equals the seed-to-seed spread of a single configuration on the
same 56 folds (`red`: 0.49 pp). The loss-weight landscape is flat within noise.

## 2. Conclusions

1. **RED's improvement is real and reproducible**: +0.75 pp, 27/28 subjects, stable across
   seeds. It is insensitive to the loss weights, temperature and teacher settings, so the
   defaults are kept.
2. **The improvement does not come from averaged-trial knowledge.** A teacher trained on
   single trials gives the same gain as the teacher trained on averages (Δ = −0.07 pp, CI
   [−0.24, 0.10]).
3. **What the gain needs:**
   - **a trained frozen critic:** trained-teacher variants beat the random teacher by
     +0.41 pp;
   - **the reconstruction branch:** critic alone gave +0.29 pp in round 1; with
     reconstruction, +0.75 pp.

   Even a random critic plus reconstruction helps (+0.35 pp).
4. **Using averages directly is harmful or useless:**

   | How averages are used | Effect |
   |---|---|
   | As training samples (`eegnet_avgaug`) | −0.28 pp |
   | As a distillation teacher (`kd_naive`) | +0.00 pp |
   | As a reconstruction target alone (`red_n2n`) | +0.03 pp |

   The class-separable structure that averaging reveals cannot be pushed into a single-trial
   classifier by any of these routes. This supports the challenge stated in the research
   brief: averaged discriminative information is largely not recoverable from single trials.

## 3. One open question before the narrative is fixed

The self-teacher variant still uses **averaged reconstruction targets** (leave-one-out group
averages). Whether averaging matters *anywhere* in RED is therefore still open. One more
control decides it:

| Run | Definition | If ≈ `red` | If clearly below `red` |
|---|---|---|---|
| `red_autoenc_self` | Self-trained teacher; reconstruction target = **the input trial itself** (autoencoder). No averaging anywhere. | Averaging is irrelevant; RED is a reconstruction-critic regulariser | Averages are useful as *denoising targets* but not as teachers |

Cost: about 5 GPU-hours (one 168-fold run plus its teachers).

## 4. Options for the chapter

**A. Honest reframing (recommended baseline plan).**
- **Chapter claim:** "Averaged-trial knowledge does not transfer to single-trial aVEP decoding
  by distillation, augmentation or imitation; a reconstruction-critic objective nevertheless
  improves single-trial accuracy consistently."
- **Contributions:**
  1. a systematic test of the transferability of averaging gains, which is negative and well
     controlled;
  2. the reconstruction-critic objective, a consistent +0.75 pp at zero inference cost;
  3. its mechanism analysis (critic training, reconstruction, teacher data).
- **Risk:** an effect of under 1 pp, and a novelty that rests on the analysis rather than on
  a large gain.

**B. Redesign so that averaging contributes information a single trial cannot.**
- **Idea:** the round-2 controls show that averages fail when used as *targets*. Their unique
  property is *group-level reliability*: a 6-trial average reveals whether a subject attended
  to a given character/bit. A candidate is reliability-weighted training: down-weight training
  trials whose group average the teacher cannot classify (attention lapses act like label
  noise for single trials).
- **Status:** untested; needs a cheap pilot (LDA or one EEGNet run) before any commitment.

**C. Shift Chapter 1's weight toward the pooled / cross-session setting** — **not
recommended.** There, RED and the controls gave nothing (round 1), so it offers no better
foothold.

**Recommendation:**
1. Run `red_autoenc_self` (≈ 5 h) and a quick reliability-weighting pilot (B).
2. If B shows ≥ 1 pp, develop it as the chapter's method. Otherwise write the chapter as A.
3. Either way, start Chapter 2 (LR-MoE) now. The inter-subject gap (within 74.4% vs LOSO
   62.3%) is ten times larger than anything Chapter 1 can move, so Chapter 2 is where the
   larger accuracy gains are likely.
4. Update the midterm slides: the illustrative RED numbers (+2–5 pp, N2N > critic) are
   contradicted by the measurements.
