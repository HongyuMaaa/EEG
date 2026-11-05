# Round 6: label-free phenotype routing — and what actually carries the routing gain

**Data:** results in `166fe4e`. Leave-one-subject-out, test on sessions 4–6, 3 seeds, n = 28.

## 1. Label-free phenotype routing does not help

| Method | Accuracy (%) | Δ vs `est_full` (pp) | Improved | p |
|---|---|---|---|---|
| `est_full` (all 27 subjects) | 62.63 | — | | |
| `est_knn` (13 nearest by *estimated* mirror_corr, anti_ratio) | 62.48 | −0.15 | 14/28 | 0.85 |
| `est_oracle_knn` (13 nearest by the *true* values of the same two descriptors) | 62.42 | −0.21 | 13/28 | 0.85 |
| `est_rand_knn` (13 random) | 60.40 | −2.23 | 6/28 | 0.002 |
| **`est_full_rapl`** | **67.83** | **+5.20** | **26/28** | < 10⁻⁴ |
| `est_knn_rapl` | 65.95 | +3.32 | 21/28 | 0.007 |

**Findings:**
- **The estimate is good, but selecting on these two descriptors is useless even with oracle
  values.** The estimate's neighbours overlap 85% with the oracle's; pseudo-label accuracy is
  75.3%.
- **RAPL works best from the broad source:** full + RAPL beats kNN + RAPL by 1.88 pp
  (p = 0.056).
- **RAPL replicates in a new setting:** plain EEGNet source, global normalisation, +5.2 pp,
  26/28 subjects.

## 2. Why: the round-5 routing gain is carried by the latency descriptor

| Comparison on sessions 4–6 | Δ (pp) | Improved | p |
|---|---|---|---|
| Round-5 oracle kNN (3 descriptors) − in-run full model | +1.48 | 20/28 | 0.026 |
| Round-5 oracle kNN (3 descriptors) − 2-descriptor oracle kNN | +1.68 | 19/28 | 0.036 |
| Original EEGNet baseline − in-run full model | −0.52 | 13/28 | 0.44 |

The baselines agree, and the neighbour sets of the 3- and 2-descriptor oracles overlap 83%. The
difference lies in the latency-matched part.

**But latency cannot be obtained without the target's labels:**

| Estimate | r with true latency |
|---|---|
| From pseudo-labels | −0.05 |
| Label-free proxies (peak / centroid of trial-wise or repetition-averaged antisymmetric energy) | −0.27 to −0.04 |

The true values cluster at 0.205–0.215 s; the outliers are weak lateralisers whose
class-difference peak is noisy. Latency therefore acts partly as a label-dependent reliability
marker of the test subject.

**Conclusion for phenotype routing:** inter-subject heterogeneity is real and exploitable with
labels (oracle +1.5–2 pp), but the useful part is not recoverable without them. Descriptor-based
routing is closed as a well-controlled negative result.

## 3. Pilot: subject-level routing by repetition consistency (positive)

**Idea.** Instead of predicting a subject's phenotype, judge candidate models directly on the
new subject's **unlabelled** data. A model that fits the subject should give consistent
predictions across the repetitions of each code bit.

**Criterion `cons`:** the fraction of single-trial predictions on sessions 1–3 that agree with
the balanced repetition-group pseudo-labels.

**Pilot, on models already trained without target labels:**
- pool: the full-data EEGNet + 6 random-subset models (round 5 `rand_split` / `rand_knn`, 3 seeds
  each);
- select per subject on sessions 1–3; test on 4–6.

| Selection | Accuracy (%) | vs full-data EEGNet | vs average pool model |
|---|---|---|---|
| by `cons` | **63.88** | **+1.76 pp** (14/28, p = 0.014) | +3.69 pp (p = 9 × 10⁻⁵) |
| by group separation | 63.34 | +1.23 pp (p = 0.07) | +3.15 pp (p = 1 × 10⁻⁴) |
| oracle best model (test labels) | 64.54 | | |

Within each subject, `cons` correlates with the models' true test accuracy (mean Spearman 0.52).

## 4. Proposed Chapter 2 MoE contribution (round 7)

**Repetition-consistency routing (RCR) over subject-bagged experts.**
- **Experts:** K EEGNets, each trained on a random subset of the source subjects (bagging), plus
  the full-data model.
- **Subject-level router:** label-free. For the new subject's unlabelled sessions, score each
  expert by repetition consistency; then use hard top-1, top-m averaging, or soft weights.
- **Then RAPL** on the routed model or ensemble.

**Controls:**
- uniform ensemble of all experts (is it selection or just averaging?);
- random expert;
- full-data model;
- full + RAPL (current best);
- oracle best expert.

**Why it fits the chapter.** Trial-level physiological routing fails because single trials are
too noisy (round 4). Subject-level routing succeeds when it is driven by the paradigm's
repetition structure. This is a mixture-of-experts adapted to the aVEP paradigm.
