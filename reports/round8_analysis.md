# Round 8: RCR with RED-trained experts — linking Chapters 1 and 2

**Data:** results in `e8f2a3c`.
**Design:**
- every expert trained with the Chapter 1 objective (`red_selfteacher`);
- each expert sees exactly the subjects of its round-7 EEGNet counterpart, so the comparison is
  paired and only the training objective differs;
- leave-one-subject-out, test on sessions 4–6, 3 seeds, n = 28.

## 1. RED experts vs EEGNet experts (paired)

| Method | RED − EEGNet (pp) | 95% CI | Subjects improved | p |
|---|---|---|---|---|
| full-data model | +0.14 | [−0.42, 0.71] | 15/28 | 0.46 |
| uniform ensemble | −0.05 | [−0.31, 0.22] | 13/28 | 0.63 |
| RCR top1 | −0.09 | [−0.52, 0.35] | 13/28 | 0.54 |
| RCR top3 | −0.03 | [−0.33, 0.28] | 11/28 | 0.69 |
| RCR soft | −0.30 | [−0.57, −0.04] | 9/28 | 0.042 |
| oracle expert | −0.08 | [−0.39, 0.20] | 15/28 | 0.99 |
| **full + RAPL** | **+0.68** | **[0.37, 1.03]** | **23/28** | **4 × 10⁻⁴** |
| top1 + RAPL | +0.32 | [−0.09, 0.74] | 18/28 | 0.18 |
| top3 + RAPL | +0.28 | [−0.01, 0.60] | 16/28 | 0.19 |

**Absolute accuracy, best pipeline:**

| Pipeline | Accuracy | vs full-data EEGNet (62.78%) |
|---|---|---|
| `rcr_red_top3_rapl` | 70.09% | +7.31 pp (26/28) |
| `rcr_top3_rapl` | 69.81% | +7.03 pp |

## 2. Interpretation

1. **RED does not make cross-subject experts more accurate by themselves** (+0.14 pp, n.s.).
   This agrees with round 1, where RED gave nothing in the pooled protocol. RED's benefit is
   within-subject.
2. **Routing works equally well on RED experts.** The router gain is +1.89 pp vs +1.92 pp, and
   the uniform ensemble again gives nothing.
3. **RED experts are more adaptable.** With RAPL, the RED-trained full model gains 0.68 pp more
   than the EEGNet full model (23/28, p = 4 × 10⁻⁴).
   - A plausible reason: RED's reconstruction of averaged repetitions shapes features in which
     repetition-group pseudo-labels are more reliable, i.e. denoised features help self-training.
4. **In the complete pipeline the advantage shrinks** to +0.28 pp (n.s.). Routing and RED's
   adaptability partly overlap, because both favour experts on which pseudo-labelling works well.

## 3. Consequence for the thesis

- **The chapters are linked experimentally, modestly.**
  - The Chapter 1 objective makes source models measurably easier to adapt without labels
    (+0.68 pp, robust).
  - The final cross-subject pipeline is equally good with either expert type (70.1% vs 69.8%).
- **Recommended presentation in Chapter 2:**
  - main pipeline: RCR + RAPL with EEGNet experts (simpler, and the gain is fully attributed);
  - the RED-expert variant as a cross-chapter analysis: "the denoising objective improves
    label-free adaptability but not zero-shot transfer".
