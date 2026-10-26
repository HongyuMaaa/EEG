# Baselines: EEGNet and DCPM

Both baselines use the same preprocessed trials (`docs/preprocessing.md`):
21 channels × 58 samples, [0.05, 0.34) s after pair onset, 200 Hz. Labels: 0 = left→right,
1 = right→left. Artifact-flagged trials (19 of 80,640) are excluded everywhere.

## Evaluation protocols (`aved/data.py`)

Whole sessions or subjects are always held out. Trials whose epochs overlap in time, or that
belong to the same character, therefore never fall on different sides of a split.

| Protocol | Test | Validation | Training | Models |
|---|---|---|---|---|
| `within` | Subject *s*, session *k* | Same subject, session *k* mod 6 + 1 | Same subject, the other 4 sessions | 28 × 6 = 168 |
| `pooled` | Session *k* of all 28 subjects | Session *k* mod 6 + 1 of all subjects | The other 4 sessions of all subjects | 6 |
| `loso` | All sessions of subject *s* | The next 3 subjects (cyclic) | The remaining 24 subjects | 28 |

- **Validation data** are used only for model selection: EEGNet early stopping, and the
  number of DCPM components. Models are never refitted on validation data, so EEGNet and DCPM
  see identical training data.
- **Reported metric:** accuracy per subject over all its test trials, then mean ± std over
  subjects.

## EEGNet (`aved/models/eegnet.py`, `configs/eegnet.yaml`)

EEGNet-8,2 (Lawhern et al. 2018), ported from the reference Keras implementation:

| Item | Setting |
|---|---|
| Architecture | F1 = 8, D = 2, F2 = 16; pooling 4 and 8; ELU activations; BatchNorm |
| Temporal kernel | **32 samples (160 ms)** — the original's fs/2 = 100 samples would exceed the 58-sample trial |
| Separable kernel | 16 samples |
| Weight constraints | Max-norm 1.0 on the depthwise spatial filters, 0.25 on the classifier (Keras semantics) |
| Input normalisation | Per-channel z-score, with mean and std computed on the training data only and stored in the checkpoint |
| Optimiser | Adam, learning rate 10⁻³, cross-entropy loss |
| Early stopping | On validation loss; the best epoch's weights are restored |

Per-protocol settings:

| Protocol | Dropout | Batch size | Max epochs | Patience |
|---|---|---|---|---|
| `within` | 0.5 | 64 | 300 | 50 |
| `pooled` | 0.25 | 256 | 150 | 20 |
| `loso` | 0.25 | 256 | 150 | 20 |

Dropout follows the EEGNet paper: 0.5 within-subject, 0.25 cross-subject.

## DCPM (`aved/models/dcpm.py`, `configs/dcpm.yaml`)

Discriminative Canonical Pattern Matching (Xu et al. 2018, Sec. II-E):

1. **Spatial filters (DSP).** Solve S_B w = λ S_w w, where
   - S_B = (X̄₁ − X̄₂)(X̄₁ − X̄₂)ᵀ (between-class),
   - S_w = σ₁² + σ₂² (within-class scatter).

   A ridge of 10⁻⁶ × mean eigenvalue is added to S_w for numerical stability. The top *m*
   eigenvectors are kept.
2. **Similarity coefficients.** For each class template, compute five coefficients between the
   filtered template and the filtered trial:
   - Pearson correlation;
   - negative Euclidean distance;
   - first canonical correlation;
   - correlation after projection onto each of the two canonical vectors.

   The five are summed with equal weight, as in paper Eq. 11. The class with the larger sum
   wins.
3. **Number of components.** *m* ∈ {1, 2, 4, 8} is chosen per fold by validation accuracy
   (ties go to the smaller *m*).

Two variants are run:

| Method name | Templates |
|---|---|
| `dcpm` | **Paper version.** Templates conditioned on the preceding and following codes. Four binary DCPMs on the opposite context pairs '000'/'111', '001'/'110', '100'/'011', '101'/'010'; class scores summed. Context is used only for training. |
| `dcpm_plain` | One template per class (no context) |

Trials at the start or end of a character run have no preceding or following code. They are
used by `dcpm_plain` but not by the context templates.

**Difference from the paper:** the paper filtered 2–70 Hz without re-referencing before DCPM.
Here DCPM uses the shared preprocessing (1–30 Hz, common average reference), so both baselines
and the proposed methods receive identical inputs.

## Outputs

See `docs/running_experiments.md`. Each fold stores its accuracy, training metadata, per-trial
predictions and (EEGNet) training curves under `results/`. Model checkpoints are stored under
`checkpoints/` and can be reloaded with `aved.train.load_checkpoint`.
