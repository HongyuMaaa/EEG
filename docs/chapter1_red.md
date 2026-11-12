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

## 6. Round 9: cross-subject pretraining + within-subject fine-tuning (direction 4)

Motivation: `reports/chapter1_headroom_analysis.md`. Within the epoch window there is about 3.4 pp of
headroom left with 5 calibration sessions, and other subjects' data may supply part of it. At the LDA
level, a pooled covariance prior gave only +0.1 pp, but deep features may transfer where LDA
covariances do not.

**Pretraining** (`scripts/pretrain_subjects.py`):
- For each target subject s: one EEGNet trained on the other 27 subjects, with early stopping on
  the 3 subjects that follow s (as in LOSO).
- Each subject is z-scored per channel with its own statistics, matching the per-fold, per-subject
  normalisation of the within protocol.
- Settings: `training.loso`.
- Output: `checkpoints/pretrain/seed<k>/sub<XX>.pt`; zero-shot diagnostics in
  `results/pretrain/seed<k>/`.

**Fine-tuning** (`run_baseline.py --init pretrain --tag ft`):
- Same folds and same settings as the from-scratch runs (`training.within`). The only change is the
  initialisation.
- The pretrained model itself is epoch 0 of early stopping, so fine-tuning can never select a model
  that validates worse than the initialisation.
- For RED, the teacher (trained on single trials, `red_selfteacher`) and the student's EEGNet both
  start from the pretrained model; the ERP decoder starts random.
- Fold diagnostics: `init_val_acc`, `init_test_acc` (the pretrained model on the fold's validation
  and test session, before fine-tuning).

| Method | Question |
|---|---|
| `eegnet@ft` vs `eegnet` | Does cross-subject pretraining help within-subject decoding? |
| `red_selfteacher@ft` vs `eegnet@ft` | Does RED still add on top of pretraining? |
| `red_selfteacher@ft` vs `eegnet` | Total gain of the combination |

**Job queue:** `scripts/round9.ps1`, 3 seeds.
1. Phase 1: pretraining.
2. Phase 2: fine-tuning.

**Cost estimates** from the earlier runs (the earlier per-seed run times are 0.6 h LOSO, 1.4 h
EEGNet within, 11 h RED within):

| Job | Total time | 6 jobs in parallel |
|---|---|---|
| Pretraining, 3 seeds | about 2 h | |
| Fine-tuning, 3 seeds | about 40 h | about 7–8 h |

## 7. Round 10: limited calibration (direction 1)

Motivation: `reports/chapter1_headroom_analysis.md` and `reports/round9_analysis.md`.

- **Headroom grows as own data shrink.** In the LDA learning curve, going from 1 to 5 own sessions
  gains 5.1 pp, while the step from 4 to 5 adds only 0.4 pp.
- **Both components should matter more with little data:**
  - RED acts like extra calibration data;
  - pretraining supplies a prior that dominates when own data are few.

**Design:**

| Item | Choice |
|---|---|
| Folds | The 168 within-subject folds, with the test and validation sessions unchanged |
| Own training sessions | Only n = 1, 2 or 3 of the 4 (`run_baseline.py --n-train-sessions N`) |
| Session choice | `aved.data.limit_train_sessions`: cyclic order after the validation session, skipping the test session |
| 4-session condition | The existing `eegnet`, `eegnet@ft`, `red_selfteacher`, `red_selfteacher@ft` results |
| Methods | The same four, with tags `cal<N>` (from scratch) and `ft_cal<N>` (fine-tuned from the round-9 pretrained models) |

The session choice has three properties:
- it is deterministic, and identical for every method and seed;
- it is nested: the session for n = 1 is part of n = 2, which is part of n = 3;
- it is balanced: each session is the single training session in exactly one fold per subject.

**Implementation details:**
- Training settings are unchanged (`training.within`), with early stopping on the validation
  session.
- The RED teacher cache is keyed on n, so the teachers of different calibration amounts never mix.

**Questions:**
1. How does each method's accuracy scale with calibration data?
2. Does RED's gain grow as data shrink?
3. Does pretraining's gain grow as data shrink?
4. Does the combination remain additive?
5. How much calibration time does each method save? (data equivalence: the number of own sessions
   EEGNet needs to match it)

**Job queue:** `scripts/round10.ps1`. Seed-major order, so seed 0 can be analysed first. Estimated
cost:

| Scope | Job-hours | Wall time, 6 jobs in parallel |
|---|---|---|
| 3 seeds | about 110 | about 18–20 h |
| `-Seeds 0` only | | about 6–7 h |
