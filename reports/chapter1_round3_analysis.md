# Chapter 1 (RED) — round 3: where averaging matters

**Data:** results committed up to `c4a9696`. Subject-level paired statistics (n = 28), seeds 0–2
averaged per subject.

**Open item:** `red_autoenc_self` seed 2 has 129/168 folds. Seeds 0 and 1 are complete and give
the same picture (per-seed Δ vs EEGNet: −1.09 / −0.75 / −0.62 pp).

## 1. Results

| Comparison | Δ (pp) | 95% CI | Subjects improved | p |
|---|---|---|---|---|
| `red` − EEGNet | +0.75 | [0.59, 0.92] | 27/28 | 4 × 10⁻⁶ |
| `red_selfteacher` − EEGNet | +0.81 | [0.67, 0.95] | 26/28 | 5 × 10⁻⁶ |
| `red` − `red_selfteacher` | −0.06 | [−0.16, 0.04] | 12/28 | 0.26 |
| `red_autoenc_self` − EEGNet | **−0.87** | [−1.13, −0.64] | 1/28 | 5 × 10⁻⁸ |
| `red_selfteacher` − `red_autoenc_self` | **+1.69** | [1.39, 2.01] | **28/28** | 7 × 10⁻⁹ |

Per-seed gains over EEGNet:

| Method | Seed 0 | Seed 1 | Seed 2 |
|---|---|---|---|
| `red_selfteacher` | +0.77 | +0.80 | +0.88 |
| `red_autoenc_self` | −1.09 | −0.75 | −0.62 |

**Training curves** (seed 0, mean over folds):

| Variant | Reconstruction loss, epochs 1 → 50 | Validation accuracy at epoch 150 |
|---|---|---|
| Averaged target | 1.01 → 0.71 | 76.5% |
| Autoencoder target | 3.63 → 0.79 | 73.4% |

With the autoencoder target, the decoder learns to reproduce the input, *noise included*.

## 2. What averaging contributes — and what it does not

**The teacher does not need averaged data.** A critic trained on single trials is as good as one
trained on averages (−0.06 pp, n.s.).

**The reconstruction target does need averaged data.** Replacing the leave-one-out average of
the trial's repetitions by the trial itself turns +0.81 pp into −0.87 pp. This is a 1.69 pp
swing, with every one of the 28 subjects affected in the same direction.

**The Noise2Noise argument predicts this:**

| Target | Noise relative to the input | Optimal reconstruction | Effect on the encoder |
|---|---|---|---|
| Average of the *other* repetitions | Independent | E[ERP \| x] (denoising) | Pushed towards ERP-preserving, noise-suppressing spatial filters |
| The trial itself | Identical | Identity | Must retain the noise, which harms single-trial classification |

**The critic is still required.** Reconstruction of averaged targets alone does nothing
(`red_n2n` +0.03 pp, round 1). Only when a frozen classifier judges the reconstruction does the
denoising become class-relevant: n2n alone +0.03, critic alone +0.29, both +0.75 pp.

### Combined picture (rounds 1–3)

| Use of averaged trials | Effect |
|---|---|
| As training samples (`eegnet_avgaug`) | −0.28 pp |
| As teacher inputs (`kd_naive`) | +0.00 pp |
| As a reconstruction target without critic (`red_n2n`) | +0.03 pp |
| As a reconstruction target **with** a frozen critic (`red`, `red_selfteacher`) | **+0.75 / +0.81 pp** |
| Same objective with a self-target, i.e. no averaging (`red_autoenc_self`) | −0.87 pp |

## 3. Implication for the chapter

The chapter keeps its theme — averaged trials improve single-trial decoding — with a precise and
defensible mechanism:

> Repetition averages are useful **not as a teacher** but as **independent-noise
> reconstruction targets**: they turn reconstruction into denoising (Noise2Noise). A frozen
> critic then makes this denoising discriminative.

**Contributions:**
1. A controlled demonstration that averaged-trial knowledge does not transfer through
   distillation, augmentation or imitation.
2. The Noise2Noise reconstruction-critic objective: +0.75–0.81 pp, 26–27/28 subjects,
   3 seeds, zero inference cost.
3. The mechanism analysis: target noise independence is necessary (+1.69 pp vs a self-target);
   the critic is necessary; the critic's training data is irrelevant.

**Simplification:** the teacher can be trained on single trials (`red_selfteacher`). The
averaged-input teacher can be presented as an equivalent variant.

## 4. Remaining runs (≈ 6 GPU-hours, in parallel)

1. **Finish `red_autoenc_self` seed 2** (39 folds; resumes automatically).
2. **Loss-scale control `red_autoenc_self@ln0.3`**, seeds 0–2. The self-target's
   reconstruction loss starts 3.6× higher, so this run lowers its weight to 0.3 to rule out
   that the harm is a loss-scale artefact. (For the averaged target, λ_n2n ∈ {0.3, 1, 3} made
   no difference: round-2 sweep.)

After that, Chapter 1's experiments are complete: next come the figures, the write-up, and an
update of the midterm slides with these measured numbers.
