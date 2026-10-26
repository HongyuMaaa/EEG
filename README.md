# Decoding miniature asymmetric VEPs

Master's thesis code: EEGNet-based methods for the binary left→right vs right→left
decoding of miniature lateral visual evoked potentials (Xu et al., IEEE TBME 2018).

| Path | Content |
|---|---|
| `Data/` | Raw dataset (28 subjects × 6 sessions) |
| `docs/algorithm_design.md` | Proposed methods: Chapter 1 (RED distillation), Chapter 2 (LR-MoE) |
| `docs/preprocessing.md` | Preprocessing pipeline: every parameter and its rationale |
| `configs/preprocess.yaml` | Preprocessing parameters |
| `aved/` | Python package (event parsing, preprocessing) |
| `scripts/` | `preprocess.py`, `verify_preprocessing.py` |
| `reports/` | Verification report and trial counts |

```bash
pip install -r requirements.txt
python scripts/preprocess.py
python scripts/verify_preprocessing.py
```
