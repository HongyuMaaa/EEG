# Thesis plan: critical evaluation, scope and work packages for Chapters 1 and 2

**Status:** after the Chapter 1 experiments (rounds 1–3, pilots of directions 1 and 2).
**Evidence:** `reports/chapter1_round{1,2,3}_analysis.md`, `reports/chapter1_pilots_directions.md`,
`reports/pilot_reliability.md`, `reports/pilot_alignment.md`.

---

## 1. Critical evaluation of where the work stands

### 1.1 What is solid

| Finding | Strength of evidence |
|---|---|
| RED (averaged repetitions as Noise2Noise targets + frozen critic) improves single-trial accuracy within subject | +0.81 pp, 26/28 subjects, 3 seeds, p < 10⁻⁵ |
| Mechanism: the targets must be repetition averages; the critic's training data is irrelevant | +0.76 pp over the self-target at matched weights (27/28); single-trial vs averaged critic −0.06 pp n.s. |
| Averaged-trial information does not transfer through distillation, augmentation or imitation | `kd_naive` +0.00, `eegnet_avgaug` −0.28, `red_n2n` +0.03 pp |
| Repetition-averaged balanced pseudo-labels adapt a cross-subject model without labels | +5.24 pp over AdaBN (21/28, 3 seeds), 51% of the supervised gain; +6.55 pp over the single-trial version (27/28) |
| Single-trial gains compound at the character level | RED vs EEGNet +1.7–2.3 pp character accuracy at 2–6 repetitions (22/28) |

### 1.2 Weaknesses that must be addressed

1. **The Chapter 1 framing no longer matches the evidence.** The brief asked for knowledge
   distillation from an averaged-input teacher. The data show the averaged teacher is
   unnecessary. The chapter must be re-framed around *learning from repetition structure*,
   with distillation as one (negative) route.
2. **Chapter 1's single-trial gain is small** (+0.8 pp). It is statistically robust, but on its
   own it is thin for a chapter. It needs a practical angle where regularisation matters more
   (less calibration data) and the character-level evaluation.
3. **Scope overlap.** The strongest new result (label-free adaptation, +5.2 pp) is a
   *cross-subject* result, i.e. Chapter 2's problem. Left in Chapter 1, it blurs the
   boundary.
4. **Chapter 2 does not exist yet.** It is the largest remaining risk: mixture-of-experts
   models often fail to beat a single network on small EEG datasets, and nothing is
   implemented.
5. **Baseline credibility.**
   - Our DCPM (72.6% within-subject) uses our preprocessing; the original paper reports 76.3%
     code accuracy (12 subjects).
   - A faithful "DCPM with the paper's settings" baseline (2–70 Hz, no re-referencing,
     0.05–0.45 s window) is needed, otherwise reviewers may attribute EEGNet's lead to
     handicapped preprocessing.
   - For cross-subject work, **Euclidean Alignment (EA)** is the standard simple baseline and
     is currently missing.
6. **Novelty claims need a literature check.**
   - Noise2Noise-style EEG denoising, auxiliary reconstruction, frozen-critic distillation and
     pseudo-label test-time adaptation all exist individually.
   - The novelty lies in (a) using the BCI's *stimulus repetition structure* to obtain
     independent-noise targets and label-sharing groups, and (b) the controlled mechanism
     analysis.
   - This must be verified against recent ERP/BCI literature before writing.

---

## 2. Scope and boundaries

**One unifying idea across the thesis:** *the aVEP paradigm repeats every code bit several
times. This repetition structure, together with the paradigm's physiology (hemispheric
lateralisation, latency), can supervise and adapt decoders without extra labels.*

| | Chapter 1 | Chapter 2 |
|---|---|---|
| Problem | Single-trial accuracy **within a subject**, given that subject's labelled calibration data | Accuracy on a **new subject**, with no labelled data from that subject |
| Data available at training | Labelled calibration sessions of the same subject | Labelled data of other subjects; at most *unlabelled* data of the new subject |
| Evaluation | Leave-one-session-out within subject (+ pooled as a secondary check) | Leave-one-subject-out: zero-shot, and with unlabelled adaptation |
| Prior exploited | Repetition structure as **training-time privileged information** | Physiology (lateralisation, latency) for **architecture**; repetition structure for **test-time adaptation** |
| Method family | Training objective (EEGNet unchanged at inference) | Architecture (MoE) + label-free adaptation procedure |
| Excludes | New-subject transfer; any test-time adaptation | Within-subject training objectives (RED) |

**Decision on the adaptation result:** repetition-averaged pseudo-labelling (RAPL, the `gpl_bal`
method) moves to **Chapter 2**, as its test-time adaptation component. It answers Chapter 2's
question, and its fallback clause ("a small amount of target data may be used") permits
unlabelled target data. Chapter 1 cites it only as a forward reference.

---

## 3. Chapter 1 — Learning single-trial aVEP decoders from repetition structure

### Research questions

- **RQ1.1** Can information that only becomes visible through multi-trial averaging be
  transferred to a single-trial decoder, and through which route?
- **RQ1.2** Which components are necessary, and why? (mechanism)
- **RQ1.3** When does it matter in practice: limited calibration data, character-level
  decoding?

### Contributions

| | Contribution | Status |
|---|---|---|
| C1.1 | A controlled study of transfer routes for averaged-trial information. Distillation, augmentation and imitation fail; this supports the "non-recoverable information" argument. | **done** |
| C1.2 | **RED**: repetition-average Noise2Noise targets + frozen critic. Zero inference cost; +0.81 pp single-trial, +1.7–2.3 pp character-level. | done (character-level analysis to formalise) |
| C1.3 | Mechanism: target noise independence necessary, critic necessary, critic data irrelevant, loss-weight insensitivity | **done** |
| C1.4 | **Calibration efficiency**: RED's gain as a function of the amount of calibration data (1–4 training sessions). A regulariser is expected to help most when data are scarce, which is the practically relevant regime for BCI calibration. | **to do** |
| C1.5 | Character-level evaluation: accuracy and information-transfer rate (ITR) vs number of repetitions | partly done |

### Remaining work packages

| WP | Content | Effort |
|---|---|---|
| 1-A | Faithful DCPM baseline with the paper's preprocessing (separate preprocessing config, `dcpm` + `dcpm_plain`) | 0.5 day code, CPU minutes |
| 1-B | Calibration-efficiency study: EEGNet, DCPM, RED with 1, 2, 3, 4 training sessions (fixed validation and test sessions), 3 seeds | 1 day code; ~1 GPU-day |
| 1-C | Character-level accuracy and ITR vs repetitions for all methods (needs calibrated DCPM scores) | 1 day, CPU |
| 1-D | Optional strengthening pilot: reconstruct only the hemispheric-difference subspace (where the class information lives). The only untested idea likely to raise RED's gain. | 0.5 day code; ~5 GPU-h |
| 1-E | Figures: main comparison, ablation ladder, per-subject gains, mechanism panel, calibration curve, character accuracy / ITR | 2 days |

**Sufficiency:** C1.1–C1.3 already constitute a complete, well-controlled study. C1.4 and C1.5
give the practical relevance the small single-trial effect lacks. That is enough for a master's
chapter, provided the framing is honest (repetition structure, not "distillation works").

---

## 4. Chapter 2 — Cross-subject decoding: physiology-informed experts and repetition-guided adaptation

### Research questions

- **RQ2.1** Does a mixture-of-experts architecture whose experts and router encode aVEP physiology
  generalise better to unseen subjects than EEGNet (zero-shot)?
- **RQ2.2** Can a new subject be adapted to **without labels** using the repetition structure,
  and when is that safe?
- **RQ2.3** Do the two combine (adapting the routing / experts with repetition pseudo-labels)?

### Contributions

| | Contribution | Status |
|---|---|---|
| C2.1 | **LR-MoE**: hemispheric decomposition (symmetric / antisymmetric streams), lateralised and symmetric experts with latency variants, a router driven by physiological descriptors, and mirror-consistency training | **to do** |
| C2.2 | **RAPL**: repetition-averaged, session-balanced pseudo-labelling for label-free subject adaptation. Already +5.24 pp over AdaBN (51% of the supervised gain), with controls showing that averaging is the active ingredient. | **pilot done** |
| C2.3 | **Safe adaptation**: a label-free criterion (e.g. separation of the group-level predictions) that predicts whether adaptation will help, to protect near-chance subjects such as Sub21 (−4.3 pp) | to do |
| C2.4 | **Integration**: RAPL on top of LR-MoE, adapting the router (subject-level expert weights) first and experts second | to do |
| C2.5 | Interpretability: do router assignments follow the measured per-subject mirror correlation and latency? | to do |

### Evidence that motivates C2.1 (already measured)

- Per-subject mirror correlation of the class-average lateralised ERPs ranges from −0.64 to
  0.75: some subjects are strongly lateralised, others not at all.
- Peak latencies range from 105 to 245 ms.
- The within-subject vs LOSO gap is 74.5% vs 62.3% (EEGNet).
- The subjects that RAPL rescues (Sub02, 15, 18: ~62% → 83–89%) are exactly those whose
  source model fails although they are easy within-subject. This is heterogeneity a
  subject-aware model should capture.

### Work packages

| WP | Content | Effort |
|---|---|---|
| 2-A | Baselines for LOSO: EEGNet (done), DCPM (done), **EA + EEGNet**, mirror-augmentation-only EEGNet | 1 day; ~2 GPU-h |
| 2-B | LR-MoE implementation + unit tests (mirror operator, equivariance constraint, router descriptors) | 3–4 days |
| 2-C | LR-MoE ablations: generic gate vs physiological router; no hemispheric decomposition; single expert family; no latency variants; each loss term; 3 seeds | ~2 GPU-days |
| 2-D | RAPL consolidation: quantile schedule (30% → 50%), number of epochs, source from RED vs EEGNet. **Selection on held-out source subjects only, never on the target.** | 1 day; ~0.5 GPU-day |
| 2-E | Safe adaptation criterion (C2.3): evaluate label-free statistics as predictors of the adaptation gain across subjects; abstain rule | 1 day, CPU |
| 2-F | Integration (C2.4) and interpretability (C2.5) | 2 days; ~1 GPU-day |
| 2-G | Figures and write-up | 3 days |

**Risk and fallback.** If LR-MoE does not beat EEGNet + EA zero-shot, Chapter 2 still carries
two contributions:
- **C2.2 + C2.3:** a validated, safe, label-free adaptation method;
- **C2.5:** the physiological heterogeneity analysis.

LR-MoE would then be reported as a well-controlled negative / neutral architectural result.
The order of WPs reflects this: 2-A and 2-D first (cheap, secure), then 2-B/2-C.

---

## 5. Why the two chapters are distinct yet coherent

- **Distinct:**
  - Chapter 1 never sees a new subject, and Chapter 2 never uses a new subject's labels.
  - Chapter 1 changes the *training objective* of a fixed architecture; Chapter 2 changes the
    *architecture* and adds a *test-time procedure*.
- **Coherent:** both exploit what is special about this paradigm — repetitions and hemispheric
  lateralisation — rather than generic deep-learning tricks.
- **Shared infrastructure:** preprocessing, protocols, baselines and statistics (subject-level
  Wilcoxon, 3 seeds, leakage-safe splits) are common to both, which keeps the comparisons
  consistent.

---

## 6. Proposed order of work

1. **Week 1:**
   - 1-A (faithful DCPM) and 2-A (EA baseline) — cheap; secures baseline credibility for both
     chapters;
   - 1-B (calibration study) launched on the GPU.
2. **Week 2:** 2-D and 2-E (RAPL consolidation and safety, on held-out source subjects);
   1-C (character-level / ITR).
3. **Weeks 3–4:** 2-B and 2-C (LR-MoE implementation and ablations).
4. **Week 5:** 2-F (integration, interpretability); 1-D only if time allows.
5. **Weeks 6–7:** figures and chapter drafts (1-E, 2-G); update the midterm slides — the
   current RED values in `presentation/` are illustrative placeholders that contradict the
   measurements.
