# Chapter 1: why RED's gain is small, and where performance can still come from

**Pilots:**
- `reports/pilot_ch1_headroom.md` (script `scripts/pilot_ch1_headroom.py`);
- `reports/pilot_ch1_fusion.md` (script `scripts/pilot_ch1_fusion.py`).

**Setup:** shrinkage LDA, within subject, leave-one-session-out, 28 subjects.

Shrinkage LDA is a fair stand-in for EEGNet here:

| Decoder | Accuracy, same window |
|---|---|
| Shrinkage LDA | 74.2% |
| EEGNet | 74.5% |

## 1. The single-trial decoder is close to the information in one epoch

| Question | Result | Conclusion |
|---|---|---|
| Does a nonlinear deep model beat a linear one? | EEGNet 74.5% vs LDA 74.2% | The window's information is essentially linear and already extracted |
| How much do more own calibration sessions give? | 1 → 5 sessions: 69.8 / 72.6 / 73.6 / 74.4 / 74.9%; 4 → 5 sessions: +0.44 pp | Strongly diminishing returns |
| What is the accuracy with unlimited own calibration data? | Fit a − b·n^(−c): asymptote 78.2%, **+3.4 pp** above 5 sessions (per-subject median +2.7 pp) | This is all the variance reduction any regulariser can still recover for this decoder family. The extrapolation from 5 points is uncertain. |
| Do other subjects' data help as a prior? | Pooled covariance prior: +0.15 pp (n.s.) at 5 sessions, +0.12 pp (n.s.) at 2 sessions | Little transferable structure at the LDA level |
| Is there usable information outside the window? | The next epoch decodes y_t at 63.5% alone, but late fusion adds only +0.22 pp (20/28, p = 0.008). Concatenating epochs hurts (−0.4 to −1.8 pp: too many dimensions). Explaining away the neighbours' overlap: +0.0 pp, even with their true labels. | The late response is mostly redundant with the early one. Window or overlap modelling is not a lever. |

## 2. What this means for RED

**RED's gain measured against the remaining headroom.** RED's +0.81 pp is small in absolute terms,
but it is a large share of what can still be gained:

- it equals the gain from about **8.2 instead of 5 calibration sessions**, i.e. about 64% more
  labelled data (about 1,500 more labelled trials per subject) at no inference cost;
- it closes roughly **a quarter of the gap to unlimited own calibration data**.

**No idea tested within this setting yields large single-trial gains.** A better architecture,
more context from neighbouring epochs, or a cross-subject prior give ≤ 0.2 pp each. Expecting
+3–5 pp single-trial within subject with 5 calibration sessions is not realistic for any method;
the bound is about +3.4 pp, even with unlimited data.

## 3. Directions that can make Chapter 1 stronger

| | Direction | Why | Expected | Cost |
|---|---|---|---|---|
| **1** | **Limited calibration data** (RED vs EEGNet with 1, 2, 3 own training sessions) | The headroom is 5.1 pp at 1 session and 2.3 pp at 2 sessions, against 0.4 pp at 4 sessions. A regulariser that is worth +64% data should gain most where data are scarce, which is also the practically relevant regime: short calibration. | RED gain clearly above 0.8 pp at 1–2 sessions (hypothesis) | ~1 GPU-day; runner = existing `Fold` with restricted `train_sessions` |
| **2** | **Data-equivalence analysis** | Reports the effect in units a BCI reader cares about (calibration time saved). Uses the EEGNet learning curve from direction 1. | Reframing, no new method | CPU, from direction 1 |
| **3** | **Character-level emphasis** | The single-trial gain compounds over 5 bits × R repetitions: RED gives +0.9–2.3 pp character accuracy and +1.9 bits/min peak ITR. | Already measured; make it a primary metric | none |
| 4 | Cross-subject pretraining + RED fine-tuning | Deep features may transfer where LDA covariances do not; the Chapter 2 full-data models already exist | Uncertain: the LDA prior gave +0.1 pp | ~0.5 GPU-day pilot |
| ✗ | Wider or overlap-aware windows | Measured above: ≤ +0.2 pp | closed | |
| ✗ | Latency-aligned targets, reliability weighting | Measured earlier: null | closed | |
