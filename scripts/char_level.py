"""Character-level accuracy and information transfer rate (ITR) from single-trial predictions (within protocol).

A character is decoded from its 5 code bits x R repetitions (R = 1..6): per bit, the single-trial evidence of the
first R repetitions is summed, and the character whose code maximises sum_b code_b * E_b is chosen among the 32
(the paper's speller). Evidence per trial: log P(1) - log P(0) for neural models (score = P(class 1)); the DCPM
decision value rho_1 - rho_0 for DCPM (score), which the paper also sums.

ITR (paper Eq. 16): N = 32, T = R * 1.2 s (5 codes + 0.2 s pause per repetition) + 1.0 s between selections.

Usage: python scripts/char_level.py --methods eegnet red_selfteacher dcpm [--reference eegnet] [--out reports/char_level.md]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"


def load_meta(data_dir: Path) -> dict[int, pd.DataFrame]:
    meta = {}
    for s in range(1, 29):
        d = np.load(data_dir / f"Sub{s:02d}.npz")
        meta[s] = pd.DataFrame({"trial": np.arange(len(d["y"])), "session": d["session"], "char_pos": d["char_pos"],
                                "char": d["char"], "rep": d["rep"], "bit": d["bit_pos"], "y": d["y"]})
    return meta


def codebook(meta) -> np.ndarray:
    cb = {}
    for m in meta.values():
        for _, g in m[m.rep == 0].groupby(["session", "char_pos"]):
            cb[g.char.iloc[0]] = g.sort_values("bit").y.to_numpy()
    return np.array([cb[c] for c in ALPHABET])


def itr(p: float, n: int = 32, t: float = 1.0) -> float:
    """Bits per minute (Wolpaw); p = accuracy, t = seconds per selection."""
    p = min(max(p, 1e-9), 1 - 1e-9)
    bits = np.log2(n) + p * np.log2(p) + (1 - p) * np.log2((1 - p) / (n - 1)) if p > 1 / n else 0.0
    return bits * 60 / t


def char_accuracy(results: Path, method: str, meta, codes, reps: int) -> pd.Series:
    """Per-subject character accuracy, averaged over the available seeds."""
    per_seed = []
    for run in sorted((results / method / "within").glob("seed*")):
        files = sorted((run / "predictions").glob("*.csv"))
        if not files:
            continue
        pred = pd.concat([pd.read_csv(f) for f in files])
        acc = {}
        for s, ps in pred.groupby("subject"):
            m = meta[s].merge(ps[["trial", "score"]], on="trial")
            m = m[m.rep < reps]
            if method.startswith("dcpm"):
                e = m.score.to_numpy()
            else:
                q = np.clip(m.score.to_numpy(), 1e-4, 1 - 1e-4)
                e = np.log(q) - np.log(1 - q)
            m = m.assign(e=e)
            ev = m.groupby(["session", "char_pos", "bit"]).e.sum().unstack("bit").fillna(0.0)
            truth = m.groupby(["session", "char_pos"]).char.first().loc[ev.index]
            best = np.argmax(ev.to_numpy() @ codes.T, axis=1)
            acc[s] = float(np.mean([ALPHABET[b] == c for b, c in zip(best, truth)]))
        per_seed.append(pd.Series(acc))
    return pd.concat(per_seed, axis=1).mean(axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=["dcpm", "eegnet", "red", "red_selfteacher"])
    ap.add_argument("--reference", default="eegnet")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--out")
    args = ap.parse_args()
    meta = load_meta(ROOT / "derivatives/preprocessed")
    codes = codebook(meta)
    results = ROOT / args.results_dir
    lines = ["# Character-level accuracy and ITR (within-subject, leave-one-session-out)", "",
             "Evidence summed over the first R repetitions of each bit; 32-way decision; ITR with T = 1.2 R + 1 s.", "",
             "| R | method | char accuracy (%) | ITR (bits/min) | Δ vs ref (pp) | improved | Wilcoxon p |",
             "|---|---|---|---|---|---|---|"]
    for reps in range(1, 7):
        acc = {m: char_accuracy(results, m, meta, codes, reps) for m in args.methods}
        ref = acc.get(args.reference)
        for m, a in acc.items():
            t = 1.2 * reps + 1.0
            it = np.mean([itr(p, t=t) for p in a])
            if ref is not None and m != args.reference:
                d = a - ref
                p = wilcoxon(a, ref).pvalue if (d != 0).any() else float("nan")
                cmp = f"{100 * d.mean():+.2f} | {int((d > 0).sum())}/{len(d)} | {p:.3g}"
            else:
                cmp = " | | "
            lines.append(f"| {reps} | {m} | {100 * a.mean():.2f} | {it:.2f} | {cmp} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
