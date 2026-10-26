# Algorithm Design

Master's thesis: improving binary decoding of miniature asymmetric visual evoked
potentials (aVEPs) with EEGNet-based methods.

Dataset: Xu et al., "A Brain–Computer Interface Based on Miniature-Event-Related
Potentials Induced by Very Small Lateral Visual Stimuli", IEEE TBME 2018.

---

## 0. Problem definition

| Item | Definition |
|---|---|
| Task | Binary classification of one stimulus **pair** (one trial) |
| Class 0 | Code `0` = **left → right** lateral stimulus sequence (event trigger `1`) |
| Class 1 | Code `1` = **right → left** lateral stimulus sequence (event trigger `2`) |
| Data | 28 subjects × 6 sessions × 480 trials, 21 parieto-occipital channels |
| Baselines | EEGNet (unmodified), DCPM |

The two classes differ in the *temporal order* of hemispheric lateralization,
not in a static left/right location. See `docs/preprocessing.md` for the full
data and label specification.

### Empirical observations that motivate the designs

Obtained from exploratory analysis of the class-averaged ERPs (1–30 Hz):

1. **Very weak effect.** The between-class difference is about 1 µV.
2. **Time-varying lateralization.** The class difference of the hemispheric
   difference (PO7 − PO8) reverses sign between ≈100 ms (−0.9 µV) and ≈200 ms
   (+1.3 µV), matching the left/right stimulus order.
3. **Overlapping responses.** Trials are spaced 200 ms apart, so each epoch
   also contains the responses to the following 2–3 trials.
4. **Large inter-subject heterogeneity.**
   - Mirroring the montage across the midline should map class 0 onto class 1.
     Per subject, the correlation between the lateralized class-average ERPs
     under mirroring ranges from **−0.64 to 0.75** (median ≈ 0.1); only
     ≈9 of 28 subjects follow the mirror rule strongly.
   - The peak latency of the lateralization effect ranges from ≈105 to
     ≈245 ms.
   - In several subjects, the discriminative information lies mainly in the
     hemispheric *sum* rather than the *difference*.

---

## Chapter 1 — Recoverable-ERP Distillation (RED)

**Goal:** improve within-subject, single-trial accuracy using multi-trial
averages as training-only privileged information.

### Challenge

Information visible in a k-trial average may be unrecoverable from a single
trial. Forcing a single-trial student to imitate an averaged-input teacher
can therefore transfer nothing, or hurt.

### Key idea: distil the conditional expectation, not the average

Let *x* be a single trial and *a* an average of **other** trials from the
same group (same class, same character, same bit position). Because the
code is repeated six times per character, *a* contains the same
neighbouring-trial overlap as *x*. Its noise is independent of *x*, so

    argmin_f  E‖f(x) − a‖²   =   E[a | x]   =   E[ERP | x]   (Noise2Noise argument).

The student is therefore pushed towards exactly the part of the averaged ERP
that **is** recoverable from one trial. Unrecoverable components shrink
towards the class mean instead of being forced. This turns the challenge into
a property of the objective.

### Architecture

```
Teacher (training only):  EEGNet on k-trial averages, k ∈ {2, 3, 6}; frozen after training
Student:                  EEGNet encoder ─┬─> classifier            (kept at inference)
                                          └─> light ERP decoder     (training only)
```

### Training losses for the student

| Loss | Definition | Purpose |
|---|---|---|
| L_CE | Cross-entropy on the single-trial label | Standard supervision |
| L_N2N | ‖decoder(x) − a‖², with *a* a held-out same-group average (never containing *x*); errors weighted towards the hemispheric-difference signal (left − right pairs) in 80–300 ms | Learn the recoverable ERP |
| L_critic | CE(teacher(decoder(x)), y) + KL(teacher(decoder(x)) ‖ student(x)) | Teacher judges the *reconstruction* the student can actually produce, so the distillation target is always reachable |

Total loss: L = L_CE + λ₁·L_N2N + λ₂·L_critic.

### Inference

A plain single-trial EEGNet. Gains come only from training, so the comparison
with the EEGNet baseline is clean.

### Evaluation

- **Protocols:**
  - within-subject, 6-fold leave-one-session-out;
  - pooled across subjects, with the same session-wise splits.
- **Leakage rule:** averaging groups are built from training sessions only.
- **Ablations:**
  1. naive logit distillation from the averaged teacher (expected to fail);
  2. L_N2N only;
  3. L_critic only;
  4. k ∈ {2, 3, 6};
  5. context-matched vs **context-marginalized** targets (averaging same-class
     trials across characters, which cancels the neighbouring-trial overlap).

### Contributions

1. Distillation from trial averages formulated as conditional-expectation
   estimation, which bounds what a single trial can recover.
2. The teacher used as a critic of a recoverable reconstruction, not as a
   feature target to imitate.
3. Overlap-context-matched averaging groups exploiting the paradigm's
   repetition structure.

---

## Chapter 2 — Lateralization-Routed Mixture-of-Experts (LR-MoE)

**Goal:** improve cross-subject (leave-one-subject-out) accuracy without
target calibration.

### Key idea

Let *M* be the hemispheric mirror operator (P7↔P8, PO7↔PO8, O1↔O2, CB1↔CB2,
…). Ideally p(y=0 | Mx) = p(y=1 | x): mirroring a left→right trial produces a
right→left trial. Observation 4 shows that subjects obey this symmetry to very
different degrees and with different latencies. Experts and routing are
therefore organised along these two physiological axes:

- hemispheric symmetry;
- lateralization latency.

### Architecture

1. **Hemispheric decomposition (fixed):**
   - antisymmetric stream x_a = (x − Mx)/2: lateralized activity, invariant to
     the common reference;
   - symmetric stream x_s = (x + Mx)/2: shared response and overlap context.
2. **Shared trunk:** EEGNet temporal convolution.
3. **Experts:** each is an EEGNet depthwise-spatial block plus a
   separable-convolution block. There are three families:
   - *mirror-equivariant* experts on x_a, constrained so that
     logit(Mx) = −logit(x) (strong lateralizers);
   - *hemisphere-dominant* experts (left-weighted and right-weighted, swapped
     by *M*) for asymmetric responders;
   - *symmetric/context* experts on x_s.

   Each family has 2–3 latency variants, with temporal attention initialised
   near 100, 170 and 230 ms.
4. **Physiological router:** a small MLP over interpretable descriptors,
   producing soft top-2 weights. The descriptors are:
   - windowed lateralization index of x_a;
   - left/right hemispheric power ratio;
   - amplitude and phase of the ~10 Hz steady-state response at O1/Oz/O2;
   - antisymmetric-to-symmetric energy ratio.

### Training losses

| Loss | Purpose |
|---|---|
| Cross-entropy | Classification |
| Load balancing | Prevent expert collapse |
| Mirror consistency: route(Mx) = M(route(x)); equivariant-expert logits flip | Encode the paradigm symmetry |
| Subject-coherent routing: low within-subject routing divergence, high between-subject divergence | Experts capture *subject* variability, not trial noise |
| Mirror augmentation with label flip, applied **only** through the equivariant experts | Data augmentation without forcing symmetry on asymmetric subjects |

### Test-time settings

- **Strict LOSO** (primary): per-trial routing, no target data.
- **Fallback A:** average the router outputs over the target subject's
  *unlabelled* trials.
- **Fallback B:** fine-tune only the router on a few labelled target trials.

### Evaluation

- Leave-one-subject-out over 28 subjects; EEGNet and DCPM baselines.
- **Ablations:**
  - generic learned-gate MoE (no physiological structure);
  - no hemispheric decomposition;
  - single expert family;
  - no latency variants;
  - each auxiliary loss removed.
- **Interpretability check:** the router's expert assignments should agree
  with each subject's measured mirror correlation and peak latency.

### Contributions

1. The paradigm-specific mirror symmetry between hemispheres and class labels,
   used as a *soft*, per-subject property selected by routing.
2. Physiologically structured experts: lateralized vs symmetric streams, and
   latency variants.
3. A router driven by interpretable electrophysiological descriptors.

---

## How the two chapters relate

| | Chapter 1 (RED) | Chapter 2 (LR-MoE) |
|---|---|---|
| Problem | Single-trial SNR, within subject | Inter-subject variability |
| Prior used | Repetition structure, trial-overlap context | Hemispheric symmetry, latency |
| Evaluation | Leave-one-session-out | Leave-one-subject-out |
| Shared | EEGNet backbone, preprocessing pipeline, baselines | ← same |
