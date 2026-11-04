"""Subject-level aVEP phenotype descriptors (Chapter 2, oracle routing test).

Computed from a subject's labelled trials (class-average ERPs, artifact-free trials):
  mirror_corr   correlation between the left-minus-right class-1 ERP and the negated left-minus-right class-0
                ERP over the 9 mirror pairs: +1 = the subject follows the mirror rule (left->right and
                right->left are hemispheric mirror images), 0 = no lateralised class structure, < 0 = reversed
  lat_latency   time (s) of the peak |class difference| of the mean left-minus-right signal
  anti_ratio    log energy ratio of the antisymmetric vs symmetric part of the class-difference ERP
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .models.lrmoe import MIRROR_PAIRS

DESCRIPTORS = ("mirror_corr", "lat_latency", "anti_ratio")


def subject_descriptors(X: np.ndarray, y: np.ndarray, ch_names: list[str], times: np.ndarray) -> dict:
    L = [ch_names.index(a) for a, _ in MIRROR_PAIRS]
    R = [ch_names.index(b) for _, b in MIRROR_PAIRS]
    A0, A1 = X[y == 0].mean(0), X[y == 1].mean(0)
    lat0, lat1 = A0[L] - A0[R], A1[L] - A1[R]
    mirror_corr = float(np.corrcoef(lat1.ravel(), -lat0.ravel())[0, 1])
    diff = A1 - A0
    d_lat = (diff[L] - diff[R]).mean(0)
    anti = (diff[L] - diff[R]) / 2
    sym = (diff[L] + diff[R]) / 2
    return {"mirror_corr": mirror_corr, "lat_latency": float(times[np.argmax(np.abs(d_lat))]),
            "anti_ratio": float(np.log((anti ** 2).sum() / (sym ** 2).sum()))}


def descriptor_table(data_dir: str | Path, subjects=range(1, 29)) -> pd.DataFrame:
    rows = {}
    for s in subjects:
        d = np.load(Path(data_dir) / f"Sub{s:02d}.npz")
        k = ~d["artifact"]
        rows[s] = subject_descriptors(d["X"][k], d["y"][k], list(d["ch_names"]), d["times"])
    return pd.DataFrame(rows).T
