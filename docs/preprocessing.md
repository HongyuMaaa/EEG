# EEG Preprocessing Pipeline

Reproducible preprocessing for the miniature asymmetric-VEP dataset (`Data/`).
All parameters are set in [`configs/preprocess.yaml`](../configs/preprocess.yaml).
Every run also writes them, with the derived quantities and software versions,
to `derivatives/preprocessed/params.json`.

```bash
pip install -r requirements.txt
python scripts/preprocess.py               # -> derivatives/preprocessed/SubXX.npz, trial_counts.csv, ...
python scripts/verify_preprocessing.py     # -> reports/preprocessing_verification.md
```

---

## 1. Dataset facts (verified from the files)

| Item | Value | Note |
|---|---|---|
| Subjects / files | 28 subjects × 6 sessions = 168 EDF files | |
| Channels | 21 parieto-occipital: P7 P5 P3 P1 PZ P2 P4 P6 P8 PO7 PO5 PO3 POZ PO4 PO6 PO8 CB1 O1 OZ O2 CB2 | `64-channels.loc` covers a larger montage; only these 21 are recorded |
| Sampling rate | **200 Hz** | `description.docx` says 250 Hz; the EDF headers and event timing say 200 Hz |
| Original reference | Vertex (central, top of head) | Many sessions contain large common-mode artifacts, removed by re-referencing (§3.3) |
| Event files | `session_XX_events.edf` are **plain-text tables**, not EDF: `sample_index  0  code` | Sample index refers to the 200 Hz recording |
| Character markers | A–D = **51–54**, E–H = 61–64, … | `description.docx` says 52–55; only 51 matches `Session_INFO.txt` (all 168 files) |

## 2. Trial and label definition

- **One trial = one stimulus pair.** Each code event marks the onset of one
  200 ms lateral stimulus pair, so each event is used as one trial; events
  are never merged or split.
  - The event spacing confirms this: the mode is 40 samples (200 ms), the
    minimum is 32 samples (160 ms), and there are no events ~100 ms apart.
  - Each character has 5 bits × 6 repetitions = 30 events. Stimulus-level
    events would give 60.
- **Labels:**

  | Trigger | Code | Stimulus order | Label |
  |---|---|---|---|
  | `1` | `0` | left → right | **0** |
  | `2` | `1` | right → left | **1** |

- **Session structure:** 16 target characters × 30 trials = **480 trials per
  file**, exactly balanced (240 per class). Each character's 30 trials are its
  5-bit code repeated 6 times. Every trial carries its character, repetition
  (0–5) and bit position (0–4).
- **Codebook:** fixed across all subjects and sessions; 32 distinct codes
  ('A' = 01100). The full table is in `reports/preprocessing_verification.md`.
- **Timing jitter:** the spacing between events within a code repetition
  varies from 32 to 47 samples (mode 40). Onsets are taken from the event file
  as recorded; no correction is applied.

## 3. Processing steps and parameters

Order: load (µV) → band-pass → bad-channel detection → interpolation → common
average reference → epoching → resampling → artifact flag.

### 3.1 Band-pass filter

| Parameter | Value |
|---|---|
| Pass band | **1–30 Hz** |
| Type | FIR, windowed-sinc design (`firwin`), Hamming window |
| Phase | Zero-phase (non-causal), applied forwards to the **continuous** recording before epoching (no epoch-edge artefacts) |
| Transition bands | 1.0 Hz below the high-pass edge (stop band at 0 Hz); 7.5 Hz above the low-pass edge (stop band from 37.5 Hz) |
| Filter length | 3.3 / 1.0 Hz = 3.3 s → **661 taps** at 200 Hz |
| Notch | Not needed: the data were notch-filtered at 50 Hz before release, and 50 Hz lies in the stop band |

**Rationale:**
- 1 Hz removes drift and slow components that are irrelevant within a 200 ms
  window.
- 30 Hz keeps the ERP and the ~10 Hz stimulation-locked response, and removes
  muscle activity and line noise.

### 3.2 Bad channels (per session)

- **Detection:** after band-pass filtering, compute each channel's standard
  deviation over the task interval under a common average reference (CAR)
  built from the remaining good channels. A channel is bad if its std
  > **3 × the median channel std**.
  - The worst offender is removed and the CAR recomputed, for up to 3
    iterations, so one broken channel cannot mask another.
- **Repair:** spherical-spline interpolation (MNE), using electrode positions
  from `Data/64-channels.loc`.
- **Result:** 15 of 168 sessions have one interpolated channel. Most are
  isolated cases; Sub10 OZ (sessions 3–6) and Sub08 PO5 (sessions 1–4) recur.
  The list is in `derivatives/preprocessed/bad_channels.csv`.

### 3.3 Re-referencing

- **Common average reference** over all 21 channels, after interpolation.
- Many sessions have common-mode artifacts on the vertex reference with
  standard deviations of 100–10,000 µV (e.g. all of Sub07, Sub08 sessions 1–4,
  Sub09 session 5, Sub10). CAR reduces these to the typical ~3 µV.
- The hemispheric difference signals used in Chapter 2 (left − right channel
  pairs) are unaffected by the choice of reference.

### 3.4 Epoch window

| Parameter | Value |
|---|---|
| Window | **[0.05, 0.34) s** after pair onset (start included, end excluded) = 290 ms |
| Samples | 58 per channel at 200 Hz (native samples +10 … +67) |
| Baseline correction | None: the pre-onset interval contains the previous trial's response, and the 1 Hz high-pass already removes offsets |

**Stimulus timing within a trial** (Xu et al. 2018, Fig. 3C): the first
lateral stimulus is shown at 0 ms and the second at 100 ms, each for 25 ms.
The paper places the aVEP P1–N1 at 81–130 ms after a stimulus and uses
0.05–0.45 s after code onset for classification.

**Why it starts at 0.05 s:** to include the response to the *first* stimulus.
The grand-average lateralization class difference, over 28 subjects, has
three phases inside the window:

| Phase | Time | Class difference | Cause |
|---|---|---|---|
| 1 | ≈90–130 ms | −0.76 µV at 110 ms (t = −6.6 at 90 ms) | First stimulus, P1–N1 |
| 2 | ≈190–210 ms | +1.01 µV at 210 ms (t = 7.3 at 190 ms) | Second stimulus, P1–N1 |
| 3 | ≈250–310 ms | −0.42 µV (t = −4.3 at 290 ms) | Later reversal |

Nothing is visible before 70 ms. An earlier version of the pipeline started
at 0.14 s and missed phase 1.

**Why it ends at 0.34 s:**
- This captures phase 3 while limiting the *next* trial's response, which
  starts 200 ms later and whose own P1–N1 begins at ≈0.28 s.
- A long window mainly adds the next trial. With [0.14, 0.64) s, the label of
  trial *t+1* was decodable from epoch *t* almost as well as trial *t*'s own
  label (mean LDA accuracy 0.712 vs 0.732; 4 subjects peaked at *t+1*).

**Comparison of windows** (leave-one-session-out shrinkage LDA, mean over 28
subjects; decoding the label of trial *t + lag* from epoch *t*):

| Window | lag −1 | lag 0 | lag +1 | Subjects peaking at lag 0 |
|---|---|---|---|---|
| **[0.05, 0.34) s (current)** | 0.618 | **0.748** | 0.587 | 28 / 28 |
| [0.14, 0.34) s | 0.551 | 0.739 | 0.594 | 28 / 28 |
| [0.14, 0.64) s | 0.545 | 0.732 | 0.712 | 24 / 28 |

**Trade-off:** starting at 0.05 s raises lag-−1 accuracy (0.551 → 0.618)
because the first 90 ms of the window overlap the end of the previous trial's
window. Consecutive epochs therefore share 18 samples. This does not leak
data under the session-wise splits used for evaluation, because neighbouring
trials always belong to the same session.

Other windows can be set via `epoch.tmin` and `epoch.tmax` for ablation; for
example the paper's [0.05, 0.45), or [0.05, 0.64) with `target_sfreq: 100`.

### 3.5 Resampling

- **Target rate: 200 Hz**, i.e. the native rate is kept (decimation factor 1).
- With a 290 ms window, 100 Hz would leave only 29 samples, too few for
  EEGNet's two pooling stages (×4, ×8).
- The 30 Hz low-pass (stop band from 37.5 Hz) already band-limits the signal,
  so `target_sfreq: 100` (exact 2× decimation of the filtered continuous
  signal) is also valid. The configuration accepts any integer divisor of
  200 Hz and rejects rates whose Nyquist frequency falls below the filter's
  stop band.

### 3.6 Artifact flag

- A trial is flagged if any channel's peak-to-peak amplitude in the window
  exceeds **100 µV**.
- Flagged trials are **kept** in the output (`artifact` field), so the
  6-repetition averaging groups of Chapter 1 stay intact. Each experiment
  decides whether to exclude them; the default is to exclude them from
  evaluation.

## 4. Output format

`derivatives/preprocessed/SubXX.npz` (not committed; regenerate with the
script):

| Key | Shape | Content |
|---|---|---|
| `X` | (2880, 21, 58) float32 | Trials, µV |
| `y` | (2880,) | 0 = left→right, 1 = right→left |
| `trigger` | (2880,) | Raw trigger (1/2) |
| `session`, `block` | (2880,) | 1–6, 1–3 |
| `char_pos`, `char` | (2880,) | Target index within the session (0–15), character |
| `rep`, `bit_pos` | (2880,) | Code repetition 0–5, bit position 0–4 |
| `onset_sample` | (2880,) | Pair onset in native samples |
| `ptp`, `artifact` | (2880,) | Max peak-to-peak (µV), flag |
| `ch_names`, `sfreq`, `times` | — | Channel order, 200.0, sample times (s) |

Trials are stored in recording order: session → character → repetition → bit.

## 5. Verification

`scripts/verify_preprocessing.py` checks the following and writes
[`reports/preprocessing_verification.md`](../reports/preprocessing_verification.md):

1. Event structure, and agreement of the markers with `Session_INFO.txt`.
2. A consistent codebook across all files.
3. Pair-level event spacing.
4. Saved labels and onsets equal a fresh parse of the event files.
5. Bit-identical reprocessing.
6. The grand-average lateralization time course.
7. **Trial–label alignment:** the label of trial *t + lag* is decoded from
   epoch *t* (leave-one-session-out shrinkage LDA, lags −1, 0, +1, plus
   permuted labels). The accuracy must peak at lag 0, at well above the
   permuted-label chance level.

Trial counts for every file are in
[`reports/trial_counts.csv`](../reports/trial_counts.csv).
