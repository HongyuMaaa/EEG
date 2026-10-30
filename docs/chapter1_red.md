# Chapter 1 implementation: Recoverable-ERP Distillation (RED)

Design rationale: `docs/algorithm_design.md`.
Code: `aved/models/red.py`, `aved/train_red.py`.
Configuration: `configs/red.yaml`.
Runner: `scripts/run_baseline.py --method <variant>`.

## 1. Premise check: averaging helps, but the gain does not transfer naively

Measured with shrinkage LDA on 8 subjects × 2 leave-one-session-out folds. Averages were taken
over repetitions of the same code bit (same label and neighbouring context):

| Train on | Test on | Accuracy |
|---|---|---|
| Single trials | Single trials | 72.0 % |
| Single trials | 2-trial averages | 76.7 % |
| Single trials | 3-trial averages | 79.7 % |
| Single trials | 6-trial averages | 86.6 % |
| 3-trial averages | 3-trial averages | 78.6 % |
| 3-trial averages | **single trials** | **69.0 %** |

- Averaging raises separability considerably.
- A model fitted on averages is *worse* on single trials than one fitted on single trials.
  Information visible in averages does not transfer automatically, which is the challenge RED
  addresses.

## 2. Averaging groups

A group is the set of repetitions of one code bit: same subject, session, character and bit
position.

- **Size:** up to 6 trials; 953 of 960 groups per subject are complete, the rest lost
  artifact-flagged trials.
- **Same label and same context:** every member has the same label *and* the same neighbouring
  codes. The overlapping responses from adjacent trials are therefore part of the group's
  expected signal, not noise.
- **No leakage:** groups never cross sessions, so averages are always built inside one data
  split (training, validation or test).

## 3. Components

### Teacher

- An EEGNet with the same architecture as the baseline.
- **Training data:** each epoch, for every training group, 6 random subsets are drawn with
  k ∈ {2, 3, 6} trials each (capped at the group size), and averaged.
- **Early stopping:** on validation-session 3-trial averages.
- **Sharing:** trained once per fold, then cached and shared by all variants:
  `checkpoints/teacher/<protocol>/seed<k>/<config hash>/`.
- **Reported:** test accuracy on single trials, 3-trial averages and 6-trial averages
  (`teacher_test_acc_avg1/3/6`).

### Student

- The baseline EEGNet, plus a training-only **linear ERP decoder** reading EEGNet's block-1
  output (16 virtual sources × 14 time steps):
  - a shared temporal up-sampling (14 → 58);
  - a learned forward model (16 sources → 21 channels).
- The decoder is linear, so the reconstruction must be expressible in the student's own spatial
  filters.
- **At inference only the EEGNet is used.** Parameter count and speed are identical to the
  baseline.

### Losses (switched per variant)

| Term | Definition |
|---|---|
| `ce` | Cross-entropy on the single-trial label (always on) |
| `n2n` | MSE(recon(x), a) + β · MSE(P recon(x), P a). *a* = leave-one-out average of x's group: never contains x, so its noise is independent of x and the minimiser is E[ERP \| x]. P = left-minus-right differences of the 9 mirror pairs (lateralized signal). λ = 1, β = 1. |
| `critic` | CE(T(recon(x)), y) + τ² KL(T(recon(x)) ‖ S(x)). The frozen teacher *T* judges the student's own reconstruction; its verdict on that reachable signal is distilled into the classifier *S*. λ = 0.5, τ = 2. |
| `kd_naive` | τ² KL(T(a) ‖ S(x)): classic distillation from the teacher's view of the average. λ = 1. |

### Variants (method names)

| Method | ce | n2n | critic | kd_naive | n2n target | Question answered |
|---|---|---|---|---|---|---|
| `eegnet` | ✓ | | | | | Baseline |
| `kd_naive` | ✓ | | | ✓ | | Does naive distillation from averages help? (expected: no) |
| `red_n2n` | ✓ | ✓ | | | group LOO average | Effect of recoverable-ERP reconstruction alone |
| `red_critic` | ✓ | | ✓ | | | Effect of the critic alone |
| **`red`** | ✓ | ✓ | ✓ | | group LOO average | **Full method** |
| `red_classmean` | ✓ | ✓ | ✓ | | subject class mean | Does matching the overlap context matter? |
| `red_selfteacher` | ✓ | ✓ | ✓ | | group LOO average | **Control:** teacher trained on *single trials* (k = 1). Is averaging knowledge the cause of the gain? |
| `red_randteacher` | ✓ | ✓ | ✓ | | group LOO average | **Control:** randomly initialised frozen teacher. What does an arbitrary fixed head contribute? |
| `eegnet_avgaug` | ✓ | | | | | **Baseline:** EEGNet on single trials plus random k-trial averages (k ∈ {2, 3, 6}), about 50/50, cross-entropy only |
| `red_autoenc_self` | ✓ | ✓ | ✓ | | the input trial itself | **Control (round 3):** single-trial teacher *and* autoencoder target. No averaging anywhere. Does averaging matter at all? |

### Diagnostics saved per fold

- `teacher_test_acc_avg1/3/6`: teacher accuracy on single trials and on test-session averages.
- `recon_r2_test`, `recon_r2_lateral_test`: R² of single-trial reconstructions against the
  leave-one-out average of the test trial's group, on all channels and on the lateralized
  differences. This measures how much of the averaged ERP one trial can recover. It is the
  quantity behind the Chapter 1 argument, and should rise with `n2n`.

## 4. Protocols

- **Primary:** `within` (leave-one-session-out, 168 folds).
- **Secondary:** `pooled` (one model on all subjects, 6 folds).
- Groups, teacher averages and targets always come from the training sessions only.
  Validation and early stopping use single trials, except for the teacher.

## 5. Round 2: controls and hyperparameter selection

Motivation and round-1 results: `reports/chapter1_round1_analysis.md`.

### Configuration overrides

Any configuration value can be changed per run without editing `configs/red.yaml`:

```bash
python scripts/run_baseline.py --method red --protocol within --tag lc1 --set loss.lambda_critic=1
```

- Results go to `results/red@lc1/`. The overrides are stored in `run_info.json`.
- Unknown keys are rejected, so a typo cannot silently run the default configuration.
- The teacher cache key covers the model, training and teacher settings. Runs that change only
  loss weights therefore reuse the same fold teachers.

### Sweeps and selection rule

`scripts/run_sweep.py` runs every combination of a grid on a fold subset: within protocol, all
28 subjects, test sessions 1 and 4, so validation sessions 2 and 5 (56 folds).

`scripts/select_config.py` ranks configurations by **mean validation accuracy**. Test accuracy
is displayed but never used for selection. Ties go to the configuration that changes fewer
settings from `configs/red.yaml` (the conservative choice), then to name order.

| Sweep | Grid | Starts from |
|---|---|---|
| `weights` | λ_critic ∈ {0.5, 1, 2} × λ_n2n ∈ {0.3, 1, 3} | Defaults |
| `tau` | τ ∈ {1, 2, 4} | Winner of `weights` (`--base-from weights`) |
| `teacher` | teacher k ∈ {{2, 3, 6}, {1, …, 6}} × β_lateral ∈ {1, 5} | Winner of `tau` |

The selected configuration is then run on all 168 folds with 3 seeds:
`--set-from-sweep teacher --tag tuned`.

### Leakage control

Validation sessions 2 and 5 were used for selection, and they are test sessions of other folds.
The final comparison is therefore reported twice:

- on all folds;
- on the clean folds whose test session never served for selection:
  `compare_methods.py --exclude-sessions 2 5` (112 folds).
