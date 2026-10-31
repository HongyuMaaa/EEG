# Chapter 1 — pilots for directions 1 and 2

Background: `reports/chapter1_round3_analysis.md`. RED gives +0.8 pp within-subject. Repetition
averages help as independent-noise reconstruction targets.

## Direction 1 — label-free adaptation through repetition structure

**Idea.** In this paradigm, the repetition groups of a new subject's data (same session,
character position and bit position) are known from the stimulus timing alone, even when labels
are not. Two label-free training signals follow:

1. **Noise2Noise reconstruction.** Leave-one-out group averages serve as targets. This is RED's
   objective, which needs no labels.
2. **Group agreement.** All 6 repetitions share one label. A group's pseudo-label is the argmax
   of its members' **mean** prediction, so averaging helps at the label level: a 6-trial
   average is far more reliable than a single trial.

**Code:** `aved/adapt.py`, `scripts/pilot_adaptation.py`.

**Protocol:**
- Leave-one-subject-out; the source model is trained on 24 subjects and early-stopped on 3.
- Adaptation uses the target's sessions 1–3 **without labels**.
- Test uses sessions 4–6, as single trials.
- Every method gets the same fixed budget (10 epochs, learning rate 5 × 10⁻⁴), and no target
  labels are used for any choice.

**CPU pre-check** (2 hard subjects, Sub03 and Sub13, source accuracy ≈ 55%):
- no label-free method helped;
- `gpl` fell to chance (−5.2 pp), because pseudo-labels from a near-chance source are unreliable;
- this motivated `gpl_bal` and the per-method check of the predicted class balance;
- the full 28-subject run decides.

**Methods compared:**

| Method | Type |
|---|---|
| no adaptation | baseline |
| AdaBN | baseline: re-estimate BatchNorm statistics |
| Tent | baseline: entropy minimisation |
| `n2n` | proposed: Noise2Noise reconstruction |
| `gpl` | proposed: group pseudo-labels |
| `gpl_bal` | proposed: balanced group pseudo-labels — robust to a shifted decision threshold; within each session the top/bottom 30% of groups by mean prediction get labels 1/0 (each session is balanced 240/240 by design) |
| `n2n_gpl` | proposed: both |
| oracle | supervised fine-tuning with the true labels — an upper reference, not a method |

## Direction 2 — latency-aligned repetition targets

**Idea.** Align the other repetitions of a trial's group with Woody's method (±15 ms) before
averaging them into its target. A sharper target means a better denoising objective. The input
trial never enters its own target, so the Noise2Noise condition is preserved.

**Code:** `aved/alignment.py`; variant `red_aligned` (= `red_selfteacher` with aligned
targets).

**Diagnostic** (`scripts/pilot_alignment.py`, `reports/pilot_alignment.md`):
- Woody alignment raises average power by 35% on real groups.
- It does so by **41% on spatially coherent noise alone**, and by 12% on a jitter-free surrogate
  with the same shared waveform.
- So most of the alignment gain is noise fitting. Real data exceed the jitter-free null in
  28/28 subjects, so some trial-specific timing variability exists, but its size is uncertain.
- The decisive test is downstream: `red_aligned` vs `red_selfteacher` (3 seeds).
