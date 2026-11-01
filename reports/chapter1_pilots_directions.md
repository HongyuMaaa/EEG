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
