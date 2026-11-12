# Round 9: cross-subject pretraining + within-subject fine-tuning (Chapter 1, direction 4)

**Data:** results in `bb7b9ae7`.

**Setup:**
- Within subject, leave-one-session-out, 168 folds × 3 seeds (all complete).
- Subject-level paired statistics, n = 28, seeds averaged.
- 95% bootstrap CIs; Wilcoxon tests.
- `@ft`: fine-tuned from an EEGNet pretrained on the other 27 subjects. Training settings are
  otherwise identical (`docs/chapter1_red.md` §6).

## 1. Results

| Comparison | Δ (pp) | 95% CI | Subjects improved | p |
|---|---|---|---|---|
| `eegnet@ft` − `eegnet` (pretraining alone) | +0.29 | [0.13, 0.44] | 18/28 | 0.003 |
| `red_selfteacher` − `eegnet` (RED alone) | +0.81 | [0.67, 0.95] | 26/28 | 5 × 10⁻⁶ |
| `red_selfteacher@ft` − `eegnet@ft` (RED on top of pretraining) | +0.72 | [0.55, 0.90] | 26/28 | 5 × 10⁻⁶ |
| `red_selfteacher@ft` − `red_selfteacher` (pretraining on top of RED) | +0.20 | [0.09, 0.30] | 20/28 | 0.002 |
| **`red_selfteacher@ft` − `eegnet` (combined)** | **+1.01** | **[0.86, 1.16]** | **28/28** | 7 × 10⁻⁹ |

**Absolute accuracy:**

| Method | Accuracy |
|---|---|
| EEGNet | 74.48% |
| EEGNet + pretraining | 74.77% |
| RED | 75.30% |
| **RED + pretraining** | **75.49%** |

**Per seed:**

| Comparison | Seed 0 | Seed 1 | Seed 2 |
|---|---|---|---|
| Pretraining alone | +0.27 | +0.33 | +0.26 |
| RED on top of pretraining | +0.69 | +0.67 | +0.81 |
| Pretraining on top of RED | +0.20 | +0.21 | +0.18 |

**Character level** (32 classes):

| Repetitions | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| EEGNet, accuracy (%) | 31.3 | 42.0 | 50.5 | 55.6 | 59.5 | 62.7 |
| EEGNet + pretraining, accuracy (%) | 32.3 | 43.1 | 51.0 | 56.7 | 60.1 | 63.7 |
| RED, accuracy (%) | 32.2 | 44.3 | 52.2 | 57.0 | 61.4 | 64.4 |
| **RED + pretraining, accuracy (%)** | **33.2** | **44.4** | **52.3** | **58.1** | **61.7** | **65.2** |
| EEGNet, ITR (bits/min) | 21.3 | 22.5 | 22.0 | 20.3 | 18.7 | 17.3 |
| RED + pretraining, ITR (bits/min) | 23.5 | 24.3 | 23.2 | 21.7 | 19.7 | 18.3 |

RED + pretraining − EEGNet, character accuracy:

| Repetitions | Δ (pp) | p | Subjects improved |
|---|---|---|---|
| 1 | +2.0 | 8 × 10⁻⁵ | 23/28 |
| 2 | +2.4 | 4 × 10⁻⁵ | 23/28 |
| 6 | +2.6 | 5 × 10⁻⁵ | 22/28 |

## 2. Diagnostics

**The pretrained model is only a starting point.**

- Zero-shot, it reaches 60.8% on the target's test sessions, close to the LOSO baseline (62.3%).
- Fine-tuning never selects the initialisation (epoch 0 in 0 of 504 folds).
- Fine-tuning converges earlier than training from scratch:

  | Model | Median best epoch, from scratch | Median best epoch, fine-tuned |
  |---|---|---|
  | EEGNet | 168 | 136 |
  | RED | 205 | 172 |

**Who gains from pretraining is not predictable.**

| Predictor of the pretraining gain | Spearman ρ | p |
|---|---|---|
| Baseline accuracy | −0.31 | 0.11 |
| Zero-shot accuracy | +0.20 | 0.31 |

Neither is significant.

**The size matches the LDA prediction.** A pooled cross-subject prior gave +0.15 pp at the LDA level
(`reports/chapter1_headroom_analysis.md`). Deep pretraining gives +0.29 pp, so other subjects' data
are a small but real source of information for within-subject decoding.

## 3. Interpretation

**The two gains are almost additive.** RED gains +0.81 pp from scratch and +0.72 pp on top of
pretraining; pretraining gains +0.29 pp alone and +0.20 pp on top of RED. They exploit different
information:

- RED: the repetition structure of the subject's own data;
- pretraining: the other subjects.

Each therefore recovers a different part of the variance that 5 calibration sessions leave.

**The combination is the strongest Chapter 1 result.**

- +1.01 pp single-trial, with **every one of the 28 subjects improved**.
- +2.0–2.6 pp character accuracy at every number of repetitions.
- +1.9–2.2 bits/min ITR at short repetition counts.
- No inference cost: the deployed model is still a plain EEGNet.

**Data equivalent.** On the LDA learning curve of the headroom pilot, +1.0 pp at 5 sessions
corresponds to about 9 sessions of calibration data. This is a rough mapping, since the curve was
fitted for LDA.

**What the round does not change.** The single-trial ceiling estimated in the headroom analysis
(about +3.4 pp with unlimited own data) still bounds what any method can gain in this setting. The
combination now recovers about 30% of it.

## 4. Consequences for the thesis

1. **New Chapter 1 method: RED + cross-subject initialisation** (`red_selfteacher@ft`).
   - Pretraining is a standard step. Reporting it with RED pre-empts the reviewer question
     "does RED still help a pretrained model?" (yes: +0.72 pp, 26/28).
   - `eegnet@ft` becomes an additional, stronger baseline.
2. **The contribution statement becomes:** the repetition structure (RED) and cross-subject data
   (pretraining) are complementary sources for within-subject decoding.
3. **Next experiment: limited calibration (direction 1) with pretraining.** Both components should
   matter much more when own data are scarce:
   - the headroom is 5.1 pp at 1 session and 2.3 pp at 2 sessions;
   - a cross-subject prior dominates when own data are few.

   Proposed run: `eegnet`, `eegnet@ft`, `red_selfteacher`, `red_selfteacher@ft` with 1, 2 and 3
   own training sessions.
