# Chapter 1 — results of the pilots for directions 1 and 2

**Data:** results committed in `622d7b6`.

## Direction 2 — latency-aligned repetition targets: no effect (closed)

| Method (3 seeds) | Accuracy | Δ vs EEGNet | Subjects improved |
|---|---|---|---|
| `red_selfteacher` | 75.30% | +0.81 pp | 26/28 |
| `red_aligned` | 75.25% | +0.77 pp | 27/28 |

Aligning the repetitions before averaging does not improve the target. This is consistent with
the diagnostic (`reports/pilot_alignment.md`): most of the alignment gain is noise fitting.
Direction 2 is not pursued further.

## Direction 1 — label-free adaptation to a new subject: large gain from balanced group pseudo-labels

**Protocol:**
- Leave-one-subject-out, seed 0.
- Adaptation on the target's sessions 1–3 **without labels**; test on sessions 4–6.
- Fixed a-priori budget: 10 epochs, learning rate 5 × 10⁻⁴, quantile 0.3.

| Method | Accuracy (%) | Δ vs AdaBN (pp) | Improved | p | \|P(pred=1) − 0.5\| |
|---|---|---|---|---|---|
| source (no adaptation) | 61.30 | +0.08 | | | 0.025 |
| AdaBN | 61.21 | — | | | 0.026 |
| Tent | 60.97 | −0.25 | 12/28 | 0.16 | 0.061 |
| `n2n` (label-free reconstruction) | 61.37 | +0.15 | 11/28 | 0.25 | 0.063 |
| `gpl` (group pseudo-labels, confidence threshold) | 60.46 | −0.75 | 8/28 | 0.11 | **0.329** (collapsed in 18/28 subjects) |
| **`gpl_bal`** (balanced group pseudo-labels) | **66.92** | **+5.71** | **22/28** | < 10⁻⁴ | 0.015 |
| oracle (true labels, upper reference) | 71.10 | +9.89 | 28/28 | | 0.015 |

**Observations:**
- **`gpl_bal` recovers 58% of the supervised-oracle gain without any target labels.**
- **Large, heterogeneous gains:**
  - near the oracle for Sub02 (61.9 → 86.3%), Sub15 (62.1 → 83.3%) and Sub18 (61.9 → 89.1%), whose
    source models fail although these subjects are easy within-subject;
  - small losses for 6 subjects (mean −1.2 pp; worst Sub21 −4.1 pp).
- **The gain does not depend on the source accuracy** (Spearman r = 0.06).
- **Threshold-based pseudo-labelling collapses** onto one class in most subjects. Ranking within
  each session, which uses the paradigm's class balance, is what makes self-training work. It only
  assumes that at least 30% of the codes in a session belong to each class.
- **Label-free reconstruction does not adapt the model** (+0.15 pp, n.s.).

**Why this fits Chapter 1.** The pseudo-label of a code bit comes from the **mean prediction
over its repetitions**. Averaging, which could not be distilled into single-trial models, works
at the *label* level when adapting to a new subject.

## Controls before claiming the contribution (run `adapt_pilot_v2`, 3 seeds)

| Control | Question |
|---|---|
| `balance` | Is the gain just a re-centred decision threshold? (AdaBN + bias shift so predictions are 50/50) |
| `gpl_bal_single` | How much does repetition averaging contribute? (same balanced self-training, ranked on single-trial predictions) |
| Seeds 0–2 | Stability of the gains |

Smoke test on one subject (2-epoch source, not representative):

| Method | Δ |
|---|---|
| `balance` | +0.2 pp |
| `gpl_bal_single` | +18.4 pp |
| `gpl_bal` | +25.2 pp |

## Controls and seeds (results `d7f5853`, `results/adapt_pilot_v2/`, seeds 0–2 averaged per subject)

| Comparison | Δ (pp) | 95% CI | Subjects improved | p |
|---|---|---|---|---|
| `gpl_bal` − AdaBN | **+5.24** | [2.93, 8.01] | 21/28 | 7 × 10⁻⁵ |
| `balance` − AdaBN | +0.06 | [−0.03, 0.15] | 18/28 | 0.12 |
| `gpl_bal_single` − AdaBN | −1.31 | [−3.38, 1.19] | 7/28 | 0.009 |
| **`gpl_bal` − `gpl_bal_single`** | **+6.55** | [4.72, 8.56] | **27/28** | 3 × 10⁻⁷ |
| oracle − AdaBN | +10.22 | [7.45, 13.31] | 28/28 | 8 × 10⁻⁹ |

**Per-seed gain of `gpl_bal` over AdaBN:** +5.73 / +4.27 / +5.73 pp. `gpl_bal` recovers **51%**
of the supervised-oracle gain without labels; the single-trial version recovers −13%.

**Conclusions:**
1. **The gain is not a threshold artefact.** Re-centring the decision threshold with the same
   balance prior gives +0.06 pp.
2. **Repetition averaging is what makes self-training work.** The same balanced self-training on
   single-trial predictions *hurts* (−1.3 pp). Ranking on the mean prediction over a code bit's
   repetitions turns it into +5.2 pp: +6.6 pp from averaging, 27/28 subjects.
3. **Stable across seeds.**
4. **Risk:** 7 subjects lose slightly on average (−0.4 to −1.3 pp), and Sub21 loses 4.3 pp
   (source near chance, 48.6%).

## Status of Chapter 1

| Contribution | Setting | Result |
|---|---|---|
| RED: averaged repetitions as Noise2Noise targets + frozen critic | within-subject | +0.81 pp (26/28), mechanism controlled |
| **Repetition-averaged balanced pseudo-labelling** | label-free adaptation to a new subject | **+5.2 pp (21/28), 51% of the supervised gain** |
| Negative results: distillation / augmentation / imitation from averages; aligned targets; reliability weighting | | documented |

**Unifying message:** averaging cannot be distilled into a single-trial model, but it can be
exploited (i) as independent-noise reconstruction targets during training and (ii) as
label-level evidence for adapting to new subjects without labels.

**Open points:**
- **A safety mechanism for near-chance subjects.** For example, skip or limit adaptation when
  the group predictions of the adaptation data are weakly separated (a label-free statistic).
- **Iterative / curriculum quantiles.** Grow the labelled fraction from 30% towards 50% over
  epochs.
- **Combine with a RED-trained source model.**
- **Cross-session adaptation within subject.**
- **Boundary with Chapter 2.** Chapter 2 targets cross-subject accuracy with a
  physiology-informed MoE. Group pseudo-labelling is a test-time procedure that can be applied
  on top of it, so it should be presented as complementary rather than competing.
