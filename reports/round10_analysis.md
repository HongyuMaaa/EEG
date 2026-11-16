# Round 10: limited calibration (Chapter 1, direction 1)

**Data:** results in `76e86a74`.

**Setup:**
- Within subject, the 168 leave-one-session-out folds, with the test and validation sessions
  unchanged.
- Only n of the 4 own training sessions are used (`aved.data.limit_train_sessions`: nested and
  balanced). n = 4 is the existing full-data condition.
- 3 seeds, all 12 runs complete (168/168 folds each).
- Subject-level paired statistics, n = 28 subjects; 95% bootstrap CIs; Wilcoxon tests.

**Figure:** `docs/thesis/figures/ch1_calibration.png`.

## 1. Single-trial accuracy (%)

| Own training sessions | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| EEGNet | 69.41 | 72.65 | 74.02 | 74.48 |
| EEGNet + pretraining | 71.54 | 73.27 | 74.33 | 74.77 |
| RED | 71.56 | 73.78 | 74.85 | 75.30 |
| **RED + pretraining** | **72.53** | **74.14** | **75.12** | **75.49** |

## 2. Gains (pp)

Each cell: mean gain [95% CI], subjects improved.

| Comparison | 1 session | 2 sessions | 3 sessions | 4 sessions |
|---|---|---|---|---|
| RED − EEGNet | **+2.14** [1.87, 2.43], 28/28 | +1.13 [0.90, 1.39], 28/28 | +0.84 [0.66, 1.03], 27/28 | +0.81 [0.67, 0.95], 26/28 |
| Pretraining − EEGNet | **+2.13** [1.63, 2.70], 28/28 | +0.62 [0.35, 0.93], 23/28 | +0.31 [0.10, 0.53], 18/28 | +0.29 [0.13, 0.44], 18/28 |
| RED + pretraining − EEGNet + pretraining | +0.99 [0.76, 1.21], 25/28 | +0.87 [0.63, 1.10], 26/28 | +0.79 [0.61, 1.00], 26/28 | +0.72 [0.55, 0.90], 26/28 |
| RED + pretraining − RED | +0.97 [0.64, 1.38], 26/28 | +0.36 [0.19, 0.53], 22/28 | +0.27 [0.14, 0.39], 23/28 | +0.20 [0.09, 0.30], 20/28 |
| **RED + pretraining − EEGNet** | **+3.12** [2.70, 3.60], **28/28** | **+1.49** [1.28, 1.71], **28/28** | **+1.11** [0.93, 1.29], **28/28** | **+1.01** [0.86, 1.16], **28/28** |

**Significance:** all p ≤ 0.008.

**Per seed** (gain of RED + pretraining over EEGNet, pp):

| Own training sessions | Seed 0 | Seed 1 | Seed 2 |
|---|---|---|---|
| 1 | +2.85 | +3.36 | +3.14 |
| 2 | +1.45 | +1.44 | +1.58 |
| 3 | +1.10 | +1.11 | +1.11 |
| 4 | +0.96 | +1.00 | +1.07 |

## 3. Character level (32 classes, 6 repetitions)

| Own training sessions | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| EEGNet | 47.6% | 57.2% | 62.1% | 62.7% |
| RED + pretraining | **56.3%** | **61.3%** | 64.2% | 65.2% |
| Δ | **+8.8 pp** (p = 4 × 10⁻⁶) | +4.1 pp (p = 7 × 10⁻⁶) | +2.1 pp | +2.6 pp |
| Peak ITR, EEGNet | 14.7 bits/min | 19.0 bits/min | | 22.5 bits/min |
| Peak ITR, RED + pretraining | **19.0 bits/min** | **22.2 bits/min** | | 24.3 bits/min |

With 1 session, RED + pretraining gains +5.2 to +8.8 pp character accuracy at every repetition count.

## 4. Findings

1. **Both components gain most when calibration data are scarce.**

   | Component | Gain at 1 session | Gain at 4 sessions |
   |---|---|---|
   | RED | +2.14 pp | +0.81 pp (2.6×) |
   | Pretraining | +2.13 pp | +0.29 pp (7×) |

   This matches the headroom analysis: what remains to be gained shrinks with data, and both act like
   additional data.

2. **RED's contribution is the most robust.** On top of pretraining it gives +0.7 to +1.0 pp at every
   data level, with 25–26/28 subjects improved. Pretraining's contribution vanishes quickly
   (+0.3 pp from 3 sessions on).

3. **The combination improves every subject at every data level** (28/28 four times). At 1 session
   it is super-additive in absolute terms but sub-additive relative to the sum of the parts
   (+3.12 vs +4.27 pp): the two sources partly overlap when own data are very few.

4. **Calibration time saved.** Taken directly from the table, without extrapolation:

   | RED + pretraining with | Accuracy | Compared with EEGNet with | Accuracy |
   |---|---|---|---|
   | 2 sessions | 74.14% | 3 sessions | 74.02% |
   | 3 sessions | 75.12% | 4 sessions | 74.48% |

   - RED + pretraining with n sessions matches or beats EEGNet with n + 1 sessions.
   - At 2 sessions this saves 1 of 3 sessions, i.e. at least a third of the calibration.
   - With a fit of EEGNet's own curve (acc = 76.85 − 7.44 · n^(−0.85)), 1 session of RED +
     pretraining corresponds to 1.9 EEGNet sessions and 2 sessions to 3.3. Equivalents above 4
     sessions are extrapolations and are not reported.

5. **Weak subjects gain most at 1 session.** The combined gain correlates with the baseline accuracy
   at ρ = −0.70 (p = 3 × 10⁻⁵).

6. **Fine-tuning stops earlier with less data.** Median best epoch from pretraining vs from scratch:

   | Own training sessions | Fine-tuned | From scratch |
   |---|---|---|
   | 1 | 73 | 135 |
   | 2 | 101 | 161 |

   The initialisation is kept unchanged in only 3 of 504 one-session folds.

## 5. Consequences for Chapter 1

- **The headline result is now a calibration result.**
  - With 1 calibration session: +3.1 pp single-trial (28/28) and +8.8 pp character accuracy; peak
    ITR rises from 14.7 to 19.0 bits/min (+29%).
  - At every amount of data, RED + pretraining reaches the accuracy EEGNet needs one more session
    for.
- **RED is the component that matters at every data level;** pretraining is a short-calibration
  aid.
- **Suggested chapter structure:**
  1. Transfer routes: the negative results.
  2. RED and its mechanism.
  3. Complementarity with cross-subject pretraining.
  4. Limited calibration: the main practical result, Figure `ch1_calibration`.
  5. Character level.
