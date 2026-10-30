# Pilot: reliability weighting from repetition averages (shrinkage LDA, within-subject LOSO-session)

Subjects: 28; folds: 168. Mean fraction of training trials in groups with cross-fitted reliability r <= 0.5: 13.1%.

| weighting | accuracy (%) | Δ vs uniform (pp) | subjects improved | Wilcoxon p |
|---|---|---|---|---|
| uniform | 74.16 | +0.00 | 0/28 | nan |
| soft | 74.20 | +0.03 | 13/28 | 0.7163 |
| soft2 | 74.08 | -0.08 | 12/28 | 0.4278 |
| hard | 73.91 | -0.25 | 9/28 | 0.0279 |

Diagnostic: baseline single-trial test accuracy by reliability of the trial's own test group

| group reliability | trials | accuracy (%) |
|---|---|---|
| r<=0.5 | 9621 | 44.10 |
| 0.5<r<=0.9 | 15528 | 61.21 |
| r>0.9 | 55472 | 83.01 |

## Interpretation

- **Reliability varies a lot.** 13% of training trials belong to repetition groups that a
  cross-fitted LDA cannot classify even after averaging. On the test side, trials of such
  groups are classified below chance (44% vs 83% for reliable groups).
  - Caveat: a group average includes the trial itself, so part of this association is built in.
- **Weighting training trials by reliability does not help:**

  | Weighting | Δ vs uniform |
  |---|---|
  | soft | +0.03 pp (n.s.) |
  | soft² | −0.08 pp (n.s.) |
  | hard (drop unreliable groups) | −0.25 pp (p = 0.03) |

  Low-reliability trials are not label noise to discard; they still carry information that
  the classifier uses.
- **Decision:** option B (reliability-weighted distillation) is **not pursued**. The LDA
  single-trial baseline (74.2%) is close to EEGNet (74.4%), so a gain of ≥ 1 pp with EEGNet is
  implausible.
