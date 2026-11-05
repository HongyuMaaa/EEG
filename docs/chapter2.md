# Chapter 2 implementation: cross-subject decoding

Scope and contributions: `docs/thesis_plan.md` §4.
All experiments are leave-one-subject-out (LOSO) and never use labels of the test subject.

## C2.1 — LR-MoE (zero-shot)

**Code:**
- model: `aved/models/lrmoe.py`;
- runner: `scripts/run_moe.py`;
- tests: `tests/test_baselines.py` (mirror operator, exact equivariance, invariant routing).

**Hemispheric decomposition.** M swaps the 9 left/right channel pairs and keeps the midline
(PZ, POZ, OZ). Mirroring turns a left→right trial into a right→left trial, i.e. it flips the
label.

| Component | Definition | Property |
|---|---|---|
| Antisymmetric stream | x_a = (x − Mx)/2 | changes sign under mirroring |
| Symmetric stream | x_s = (x + Mx)/2 | unchanged under mirroring |
| `anti` experts | (f(x_a) − f(−x_a))/2, with time shift d ∈ {−20, 0, +20} ms | **exactly mirror-equivariant** |
| `sym` experts | f(x_s), same shifts | mirror-invariant |
| `full` expert | f(x) | unconstrained |
| Physiological router | MLP on 13 mirror-invariant descriptors: x_a / x_s energy in 5 time windows, their log ratio, \|log L/R power\|, 10 Hz occipital amplitude | routing identical for x and Mx |

f is a small EEGNet.

**Losses:** cross-entropy + 0.1 · load balancing (KL of the batch-mean gate to uniform) +
0.1 · subject coherence (variance of the gates within each subject of the batch).

**Test-time routing:**
- per trial (`<method>`);
- subject-averaged (`<method>_subjgate`): the gates averaged over the test subject's trials.
  This is label-free and transductive.

**Common to all variants:**
- per-subject channel z-scoring;
- training settings of `configs/red.yaml` (loso);
- 24 training / 3 validation subjects per fold;
- test on all 6 sessions of the held-out subject.

**Variants** (reference: `eegnet_sz` = plain EEGNet under the same normalisation):

| Method | Experts | Router | Purpose |
|---|---|---|---|
| `eegnet_sz` | full | – | Baseline |
| `eegnet_mirroraug` | full | – | Mirror augmentation with label flip (cheapest use of the symmetry) |
| **`lrmoe`** | 3 anti + 3 sym + 1 full | physio | **Proposed** |
| `lrmoe_generic` | 7 full | learned EEGNet gate | Conventional MoE of the same size |
| `lrmoe_nodecomp` | 7 full (shifts) | physio | Without the hemispheric decomposition |
| `lrmoe_nolat` | anti, sym, full | physio | Without latency variants |
| `lrmoe_nocoh` | as `lrmoe` | physio | Without the subject-coherence loss |
| `lrmoe_anti` | 3 anti | physio | Equivariant experts only |

**Interpretability (C2.5).** Each fold stores the mean gate of its test subject (`mean_gate`,
`expert_kinds`). Compare it with the per-subject mirror correlation and latency.

## C2.2–C2.3 — RAPL: label-free adaptation with nested selection and a safety rule

**Code:** `aved/adapt.py`, `scripts/run_rapl.py`.

**Per target subject:**
1. **Source model** (EEGNet + decoder, cross-entropy + Noise2Noise): trained on the 24 training
   subjects, early-stopped on the 3 validation subjects.
2. **Candidates:**

   | Name | Setting |
   |---|---|
   | `q30` | balanced 30% per class, 10 epochs (a-priori setting of the pilot) |
   | `q20`, `q40` | 20% / 40% per class |
   | `sched` | 20% → 50% over the epochs |
   | `q30_e20` | 30%, 20 epochs |

3. **Nested selection (`rapl`):** each candidate is run on each validation subject (adapt on
   sessions 1–3 without labels, score on 4–6 with labels). The best mean is chosen *before* the
   target is touched.
4. **References on the target:** source, AdaBN, `balance` (threshold re-centring),
   `gpl_bal_single` (no repetition averaging), oracle (supervised).
5. **Label-free diagnostics:**

   | Diagnostic | Meaning |
   |---|---|
   | `sep_src` | group-level separation before adaptation |
   | `sep_post` | group-level separation after adaptation |
   | `pl_stability` | how stable the pseudo-labels stay across epochs |
   | `flip_rate` | fraction of predictions changed by adaptation |

6. **Safety rule (`rapl_safe`):** adapt only if a diagnostic exceeds a threshold, otherwise keep
   AdaBN. For subject s, the diagnostic and threshold are chosen on the *other 27 subjects*.

**Output:** `results/rapl/seed<k>/Sub<XX>.json`, `results/rapl/summary_seed<k>.md`.

## Chapter 1 addition — character level (C1.5)

`scripts/char_level.py` → `reports/char_level.md`: character accuracy and ITR versus the number
of repetitions, from the stored single-trial predictions.

## C2.1 feasibility gate — oracle phenotype routing (round 5)

**Motivation:** `reports/round4_analysis.md`. Trial-level routing collapsed to a uniform
ensemble.

**Question:** does routing per *subject*, with the subject's **true** phenotype, beat one
model trained on everyone? If not, the MoE direction is closed.

**Code:**
- descriptors: `aved/phenotype.py`;
- runner: `scripts/run_oracle_routing.py`;
- job queue: `scripts/round5.ps1`.

**Descriptors** (from labelled class averages): mirror correlation, lateralisation peak
latency, log ratio of antisymmetric to symmetric class-difference energy.
- Strong lateralisers (Sub02, 12, 15, 18, 21; mirror_corr 0.65–0.86) are easy within-subject
  (73–93%) but poorly served by the pooled LOSO model (49–61%).
- They are also the subjects RAPL helps most.

**Variants** (same EEGNet, settings and global normalisation as the LOSO baseline; 2 training
subjects held out for early stopping):

| Variant | Training subjects | Control for |
|---|---|---|
| `phen_split` | own half of a median split on mirror_corr | — |
| `rand_split` | random subjects, same number | less data |
| `wrong_split` | opposite phenotype half | direction of routing |
| `phen_knn` | 13 nearest subjects in descriptor space | — |
| `rand_knn` | 13 random subjects | less data |
| `phen_cond` | all 27; read-out modulated by the descriptors (W0 f + Σ d_j W_j f) | — |

**Decision rule:**
- **Routing is worth pursuing (label-free, with descriptors estimated from RAPL
  pseudo-labels)** if `phen_split` > `rand_split` and > `wrong_split`, or `phen_knn` >
  `rand_knn`, **and** a phenotype variant ≥ the full-data EEGNet baseline.
- **Otherwise** the MoE direction is closed as a documented negative result.

## Round 6 — label-free phenotype routing (+ RAPL)

The oracle gate passed (`reports/round5_analysis.md`): the 13 nearest-phenotype subjects beat both
13 random subjects and all 27 subjects.

**Label-free version:** `scripts/run_est_routing.py`, job queue `scripts/round6.ps1`.

**Per target:**
1. full-data source model;
2. balanced repetition-group pseudo-labels on sessions 1–3;
3. estimate of mirror_corr and anti_ratio;
4. EEGNet on the 13 subjects nearest to the estimate;
5. optionally RAPL on top.

**References, same run, test on sessions 4–6:** full-data model (± RAPL), oracle routing with
the same descriptors, 13 random subjects.

**Diagnostics stored per fold:** estimated vs true descriptors, neighbour overlap, and
pseudo-label accuracy. The pseudo-label accuracy is computed with labels for reporting only and
is never used.

## Round 7 — repetition-consistency routing (RCR) over subject-bagged experts

Motivation: `reports/round6_analysis.md`. Descriptor-based routing is not label-free; selecting
models by repetition consistency was a positive pilot.

**Code:** `scripts/run_rcr.py`, job queue `scripts/round7.ps1`.

**Per target:**
1. **Expert pool:** the full-data EEGNet + 8 EEGNets on random 13-subject subsets.
2. **Router score:** `cons` = agreement of an expert's single-trial predictions on the unlabelled
   sessions 1–3 with its own balanced repetition-group pseudo-labels.
3. **Routing rules,** fixed before any result:

   | Rule | Definition |
   |---|---|
   | `rcr_top1` | the expert with the highest `cons` |
   | `rcr_top3` | mean probability of the 3 highest |
   | `rcr_soft` | weights softmax(`cons` / 0.02) over all experts |

4. **RAPL (q30_e20) on top:** `rcr_full_rapl`, `rcr_top1_rapl`, `rcr_top3_rapl`.

**Controls:** `rcr_full`, `rcr_uniform` (equal average of all experts), `rcr_random`, and
`rcr_oracle` (best expert on the test sessions; reference only).

**Testing:** sessions 4–6, 3 seeds. Per-subject expert scores are stored in
`results/rcr_experts/`.
