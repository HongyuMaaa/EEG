# Decoding miniature asymmetric VEPs

Master's thesis code: EEGNet-based methods for the binary left→right vs right→left
decoding of miniature lateral visual evoked potentials (Xu et al., IEEE TBME 2018).

| Path | Content |
|---|---|
| `Data/` | Raw dataset (28 subjects × 6 sessions) |
| `docs/algorithm_design.md` | Proposed methods: Chapter 1 (RED distillation), Chapter 2 (LR-MoE) |
| `docs/preprocessing.md` | Preprocessing pipeline: every parameter and its rationale |
| `docs/baselines.md` | EEGNet and DCPM baselines, evaluation protocols |
| `docs/chapter1_red.md` | Chapter 1 implementation (RED): components, losses, ablation variants |
| `docs/running_experiments.md` | **How to run the experiments on a local GPU and commit the results** |
| `configs/` | Preprocessing, EEGNet and DCPM parameters |
| `aved/` | Python package: event parsing, preprocessing, data splits, models, training |
| `scripts/` | `preprocess.py`, `verify_preprocessing.py`, `run_baseline.py`, `run_all_baselines.py`, `summarize_results.py`, `compare_methods.py` |
| `tests/` | Leakage and model tests (`python -m pytest -q tests`) |
| `reports/` | Preprocessing verification report and trial counts |
| `results/` | Experiment results (committed after each run) |

```bash
pip install -r requirements.txt     # plus PyTorch, see docs/running_experiments.md
python scripts/preprocess.py
python scripts/run_all_baselines.py --device cuda
```
