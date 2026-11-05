# Round 5: oracle phenotype routing — the feasibility gate for Chapter 2's MoE direction

**Data:** results in `ccbaa2a`.
**Code:** `scripts/run_oracle_routing.py` (variants), `aved/phenotype.py` (descriptors).
**Protocol:** leave-one-subject-out, test on all 6 sessions; same EEGNet, settings and global
normalisation as the LOSO baseline. Variants have 3 seeds; the EEGNet baseline has seed 0 only.

## 1. Results (subject level, n = 28)

| Comparison | Δ (pp) | 95% CI | Subjects improved | p |
|---|---|---|---|---|
| **`phen_knn` (13 nearest-phenotype subjects) − `rand_knn` (13 random)** | **+4.09** | [2.35, 6.01] | 22/28 | 1 × 10⁻⁴ |
| **`phen_knn` − EEGNet (all 27 subjects)** | **+1.79** | [0.28, 3.30] | 19/28 | 0.007 |
| `phen_split` (own half) − `rand_split` | +2.10 | [0.74, 3.53] | 19/28 | 0.012 |
| `phen_split` − `wrong_split` (opposite half) | +2.53 | [−0.08, 5.27] | 21/28 | 0.014 |
| `phen_split` − EEGNet | −0.19 | [−1.74, 1.45] | 11/28 | 0.61 |
| `phen_cond` (descriptor-conditioned read-out) − EEGNet | +0.85 | [−1.29, 2.88] | 17/28 | 0.28 |
| `rand_split` − EEGNet (cost of halving the training subjects) | −2.30 | [−3.59, −1.01] | 4/28 | 3 × 10⁻⁴ |

**Gain over EEGNet by phenotype** (above / below the median mirror correlation):

| Variant | High mirror correlation | Low mirror correlation |
|---|---|---|
| `phen_knn` | +2.7 pp | +0.9 pp |
| `phen_cond` | +2.2 pp | −0.5 pp (Sub22 45.7%, Sub24 45.5%: extrapolated conditioning flips decisions) |

## 2. Conclusion — the gate passes

**Subject heterogeneity can be exploited by routing.** Training on the 13 subjects whose phenotype
is closest beats training on all 27, although it uses less than half the data. The control with
13 random subjects shows the gain comes from **phenotype matching** (+4.1 pp), not from the
amount of data (−2.3 pp).

## 3. Can the phenotype be estimated without labels?

A CPU analysis of the existing LOSO predictions:
- pseudo-labels on the target's sessions 1–3 from the LOSO EEGNet, using balanced group
  averages, are 73.9% correct on average;
- class averages are then formed from these pseudo-labels.

| Descriptor | r(estimate, truth), EEGNet pseudo-labels | r, DCPM pseudo-labels |
|---|---|---|
| mirror_corr | **0.81** | 0.72 |
| anti_ratio | **0.78** | 0.58 |
| lat_latency | −0.05 | −0.13 |

The 13 nearest neighbours chosen from the **estimated** descriptors (mirror_corr, anti_ratio, plus
lat_latency) overlap the oracle neighbours by **79%** (76% with DCPM pseudo-labels; random 48%).

**Decision taken before any accuracy result:**
- the label-free routing uses **mirror_corr and anti_ratio** only;
- lat_latency is dropped, because it cannot be estimated without labels.

## 4. Next: label-free phenotype routing (round 6, `scripts/run_est_routing.py`)

**Per target:**
1. train a full-data source model;
2. derive balanced group pseudo-labels on sessions 1–3;
3. estimate the 2 descriptors;
4. train on the 13 nearest subjects (`est_knn`);
5. optionally adapt with RAPL (`est_knn_rapl`).

**References, all on sessions 4–6 and trained in the same run:**

| Method | Role |
|---|---|
| `est_full` | full-data model |
| `est_full_rapl` | full-data model + RAPL |
| `est_oracle_knn` | true 2 descriptors |
| `est_rand_knn` | 13 random subjects |

**Claim to test:** `est_knn` > `est_full` and ≈ `est_oracle_knn`; `est_knn_rapl` > `est_full_rapl`
(physiology-informed source selection and repetition-guided adaptation are complementary).
