# Running the baselines on your own machine (GPU)

This guide takes you from a fresh clone to committed results. It covers Windows and Linux;
macOS works the same as Linux, but without CUDA.

**What gets committed:** only `results/`, which is small (a few MB).

**What stays local** (git-ignored): `derivatives/` (preprocessed data, regenerated in about
1 minute), `checkpoints/` (trained models), `logs/` and `.venv/`.

---

## 1. One-time setup

### 1.1 Prerequisites

| Requirement | Notes |
|---|---|
| Git | |
| Python **3.10 or newer** | 3.11–3.13 recommended. Check with `python --version`. |
| Recent NVIDIA driver | Check that `nvidia-smi` shows the RTX 3060 |

### 1.2 Clone the repository and switch to the working branch

```bash
git clone https://github.com/HongyuMaaa/EEG.git
cd EEG
git checkout claude/elegant-babbage-ebonby
```

If you already have a clone:

```bash
git fetch origin
git checkout claude/elegant-babbage-ebonby
git pull
```

### 1.3 Create a virtual environment and install the dependencies

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Then install the dependencies (any OS):

```bash
pip install -r requirements.txt
```

### 1.4 Install PyTorch with CUDA

PyTorch is deliberately not in `requirements.txt`. On Windows, the default `pip install torch`
gives a CPU-only build. Install the CUDA build instead:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

The RTX 3060 works with any current CUDA build. If this command fails, pick the command for
your OS from https://pytorch.org/get-started/locally/ (Package: Pip, Compute Platform: CUDA).

Check that the GPU is visible:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

This must print `True` and `NVIDIA GeForce RTX 3060`.

### 1.5 Preprocess the data and run the tests

```bash
python scripts/preprocess.py          # ~1 min -> derivatives/preprocessed/
python -m pytest -q tests             # ~5 s; expect "10 passed"
```

`python scripts/verify_preprocessing.py` (about 6 minutes) is optional. It regenerates
`reports/preprocessing_verification.md`, which should be unchanged.

---

## 2. Smoke test (about 1 minute)

Run each piece once, on a few epochs, into throw-away folders:

```bash
python scripts/run_baseline.py --method eegnet --protocol within --subjects 1 --sessions 1 --max-epochs 3 --device cuda --results-dir results_smoke --checkpoint-dir checkpoints_smoke
python scripts/run_baseline.py --method eegnet --protocol loso --subjects 1 --max-epochs 1 --device cuda --results-dir results_smoke --checkpoint-dir checkpoints_smoke
python scripts/run_baseline.py --method dcpm --protocol within --subjects 1 --sessions 1 --results-dir results_smoke --checkpoint-dir checkpoints_smoke
```

- Each run should end with `test accuracy ...` and `done -> ...`.
- The first command's header must say `on cuda`.
- `results_smoke/` and `checkpoints_smoke/` are git-ignored; delete them afterwards.

---

## 3. Full runs

### 3.1 Everything in one command (recommended)

```bash
python scripts/run_all_baselines.py --device cuda
```

This runs the following in order, then writes `results/summary.md`:
1. DCPM (`dcpm`, `dcpm_plain`) on `within`, `pooled` and `loso` (CPU; minutes per protocol);
2. EEGNet on `within`, `pooled` and `loso` (GPU).

Console output is also saved to `logs/`.

**Expected durations:**

| Run | Measured on the cloud's 4-core CPU | On the RTX 3060 |
|---|---|---|
| DCPM, all protocols | ~1–15 min per protocol and variant (LOSO is the longest) | Same (CPU) |
| EEGNet `within` (168 models) | ~12 h | Not yet measured; expected several times faster |
| EEGNet `pooled` (6 models) | ~6 h | Not yet measured |
| EEGNet `loso` (28 models) | ~15–30 h | Not yet measured |

Your actual GPU timings will be recorded per fold as `train_time_s` in
`results/.../folds/*.json`.

**Additional seeds** for EEGNet, recommended once seed 0 works:

```bash
python scripts/run_all_baselines.py --device cuda --methods eegnet --seeds 1 2
```

### 3.2 Individual runs

```bash
python scripts/run_baseline.py --method eegnet --protocol within --device cuda
python scripts/run_baseline.py --method eegnet --protocol pooled --device cuda
python scripts/run_baseline.py --method eegnet --protocol loso   --device cuda
python scripts/run_baseline.py --method dcpm       --protocol within    # also: pooled, loso
python scripts/run_baseline.py --method dcpm_plain --protocol within    # also: pooled, loso
```

Useful options:

| Option | Effect |
|---|---|
| `--subjects 1 2 3` | Only these test subjects (`within`, `loso`) |
| `--sessions 1 2` | Only these test sessions (`within`, `pooled`) |
| `--seed N` | Random seed; results go to `results/<method>/<protocol>/seedN/` |
| `--overwrite` | Re-run folds that already have results |
| `--max-epochs N` | Cap the number of epochs. For testing only: it is recorded and shown in the summary |

### 3.3 Interruptions and splitting the work

- **Resuming:** every finished fold is saved immediately. If a run stops (Ctrl+C, reboot,
  crash), run the same command again: completed folds are skipped.
- **Splitting across terminals:** use disjoint `--subjects` or `--sessions`. Each fold writes
  its own files. For example:
  ```bash
  python scripts/run_baseline.py --method eegnet --protocol within --device cuda --subjects 1 2 3 4 5 6 7 8 9 10 11 12 13 14
  python scripts/run_baseline.py --method eegnet --protocol within --device cuda --subjects 15 16 17 18 19 20 21 22 23 24 25 26 27 28
  ```
  The GPU easily handles two or three EEGNet runs at once.
- **Long runs on Linux:** run them inside `tmux` or with `nohup ... &`. On Windows, keep the
  terminal open and disable sleep.

---

## 3b. Chapter 1 (RED) experiments

Run these after the baselines; the setup is the same. Method names and their meaning are listed in
`docs/chapter1_red.md`.

**Step 1 — re-run the EEGNet baseline with the raised epoch caps.** In the first run, all
`pooled` folds and 33 `within` folds stopped at the epoch cap. The caps are now 500
(`configs/eegnet.yaml`), so the baseline is fully converged before RED is compared against it.

```bash
git pull
python scripts/run_baseline.py --method eegnet --protocol within --device cuda --overwrite
python scripts/run_baseline.py --method eegnet --protocol pooled --device cuda --overwrite
```

**Step 2 — RED and its ablations** (`within` first, the primary protocol):

```bash
python scripts/run_all_baselines.py --device cuda --methods red red_n2n red_critic red_classmean kd_naive --protocols within
```

- The first variant also trains the fold's teacher; the other variants reuse it from
  `checkpoints/teacher/`.
- Expect roughly 2–3× the EEGNet time for `red`, less for the other variants.

**Step 3 — pooled protocol** (secondary):

```bash
python scripts/run_all_baselines.py --device cuda --methods red red_n2n kd_naive --protocols pooled
```

**Step 4 — compare, then commit as in section 4:**

```bash
python scripts/compare_methods.py --protocol within --out results/compare_within.md
python scripts/compare_methods.py --protocol pooled --out results/compare_pooled.md
```

The comparison lists, for each method:
- the paired difference to EEGNet;
- the number of subjects improved;
- the Wilcoxon p-value;
- the teacher's accuracy on single trials and averages;
- how well single trials reconstruct their group ERP (R²).

## 4. Check, commit and push the results

```bash
python scripts/summarize_results.py   # rebuilds results/summary.md, summary.csv, summary_per_subject.csv
python scripts/compare_methods.py --protocol within --out results/compare_within.md   # once RED runs exist
```

Open `results/summary.md` and check the **Run status** table:
- folds done = expected (168 / 6 / 28);
- device = `cuda` for EEGNet;
- the epochs-override column is empty.

Then commit only the results:

```bash
git status                  # should list only results/ (checkpoints/, logs/ and derivatives/ are ignored)
git add results/
git commit -m "Add baseline results: EEGNet and DCPM (seed 0)"
git pull --rebase           # in case the branch moved on in the meantime
git push origin claude/elegant-babbage-ebonby
```

It is fine to commit and push partial results (e.g. DCPM and EEGNet-within first). The summary
shows which runs are still incomplete.

---

## 5. Layout of the results

```
results/
  summary.md, summary.csv, summary_per_subject.csv
  <method>/<protocol>/seed<k>/
    run_info.json        configs, preprocessing fingerprint, git commit, device/GPU, versions
    subject_results.csv  accuracy per test subject (and test session)
    folds/<fold>.json    accuracy, per-subject accuracy, best epoch, train time, n_train/val/test, ...
    predictions/<fold>.csv  per test trial: subject, session, trial, y, pred, score
    history/<fold>.csv   EEGNet only: epoch, train_loss, val_loss, val_acc
checkpoints/<method>/<protocol>/seed<k>/<fold>.pt   (local only)
```

- `score` is P(right→left) for EEGNet, and the DCPM score difference ρ₁ − ρ₀ for DCPM.
- `trial` indexes the subject's 2,880 trials in recording order (session → character →
  repetition → bit). It links predictions back to the event metadata in `SubXX.npz`.

To reload a model:

```python
from aved.train import load_checkpoint
ckpt = load_checkpoint("checkpoints/eegnet/within/seed0/sub01_test1.pt")
model = ckpt["model"]  # EEGNet in eval mode; normalise inputs with ckpt["channel_mean"] / ckpt["channel_std"]
```

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `torch.cuda.is_available()` is False | You installed a CPU-only build. Run `pip uninstall torch`, then repeat step 1.4. Check `nvidia-smi`. |
| `preprocessed data (config ...) do not match` | The preprocessing config changed since `derivatives/` was built: re-run `python scripts/preprocess.py` |
| `.../params.json not found` | Run `python scripts/preprocess.py` first |
| CUDA out of memory | Unlikely (EEGNet needs < 1 GB). Close other GPU programs, or reduce `batch_size` in `configs/eegnet.yaml`. |
| PowerShell refuses `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once |
| Results differ slightly between GPU and CPU or between machines | Expected for EEGNet (floating-point nondeterminism). Differences should be well under 1 percentage point on average. |
