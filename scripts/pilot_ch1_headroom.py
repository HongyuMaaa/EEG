"""Chapter 1 headroom pilot (CPU, shrinkage LDA): where can a within-subject single-trial decoder still gain?

Within subject, leave-one-session-out (train on the other 5 sessions, no validation needed for LDA), 28 subjects.
Features are downsampled x2 (100 Hz) for every variant, so all variants are comparable.

A. Window / overlap. Trials come in runs of 5 bits 200 ms apart (bit_pos 0-4; 400 ms gap between runs), so the
   response of trial t continues into epoch t+1. Neighbouring labels are uncorrelated by design (r = 0.00), so
   anything a neighbouring epoch adds about y_t is response information, not label leakage.
   Evaluation set: bit positions 1-3 (both neighbours 200 ms away); every variant is trained on the same trials.
     W0   epoch t only, 0.05-0.34 s (the thesis window)
     Wp   + previous epoch           -0.15-0.34 s
     Wn   + next epoch                0.05-0.54 s
     Wpn  + both                     -0.15-0.54 s
     Wpn_ea_oracle  Wpn after subtracting the neighbours' class responses with their TRUE labels (bound on
                    explaining away; templates fitted by least squares on the training sessions)
     Wpn_ea         same with neighbour labels estimated by a W0 LDA (cross-fitted on training data)
B. Data. W0 on all bit positions:
     lc_k   own training sessions k = 1..5 (mean of 3 random draws)  -> learning curve
     pool_a covariance = a * own (Ledoit-Wolf) + (1-a) * mean within-class covariance of the other 27 subjects

Usage: python scripts/pilot_ch1_headroom.py   -> reports/pilot_ch1_headroom.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon
from sklearn.covariance import ledoit_wolf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "derivatives/preprocessed"
SUBJECTS = range(1, 29)
OVERLAP = 18          # samples shared by consecutive epochs 200 ms apart (epoch = +10..+67, next = +50..+107)


def ds2(x):           # (..., 58) -> (..., 29)
    return 0.5 * (x[..., 0::2] + x[..., 1::2])


def load(s):
    d = np.load(DATA / f"Sub{s:02d}.npz", allow_pickle=True)
    X = d["X"].astype(np.float64)
    sd = X.std(axis=(0, 2), keepdims=True)
    return dict(X=X / sd, y=d["y"].astype(int), session=d["session"], bit=d["bit_pos"], onset=d["onset_sample"],
                artifact=d["artifact"].astype(bool))


def neighbours(d):
    n = len(d["y"])
    prev, nxt = np.full(n, -1), np.full(n, -1)
    same = (d["session"][1:] == d["session"][:-1]) & (np.diff(d["onset"]) <= 45)
    nxt[:-1][same] = np.arange(1, n)[same]
    prev[1:][same] = np.arange(n - 1)[same]
    return prev, nxt


def window_features(d, prev, nxt, idx, kind):
    X = d["X"]
    parts = []
    if "p" in kind:
        parts.append(X[prev[idx]][..., :58 - OVERLAP])         # -0.15 .. +0.05 s relative to t
    parts.append(X[idx])
    if "n" in kind:
        parts.append(X[nxt[idx]][..., OVERLAP:])               # +0.34 .. +0.54 s
    return np.concatenate(parts, axis=-1)


def flat(X):
    X = X[..., : X.shape[-1] // 2 * 2]
    return ds2(X).reshape(len(X), -1)


def fit_lda(F, y, prior_cov=None, a=1.0):
    mu0, mu1 = F[y == 0].mean(0), F[y == 1].mean(0)
    R = np.where((y == 1)[:, None], F - mu1, F - mu0)
    S, _ = ledoit_wolf(R, assume_centered=True)
    if prior_cov is not None and a < 1:
        S = a * S + (1 - a) * prior_cov
    w = np.linalg.solve(S, mu1 - mu0)
    return w, -w @ (mu0 + mu1) / 2


def acc(w, b, F, y):
    return float((((F @ w + b) > 0).astype(int) == y).mean())


def within_cov(d, idx):
    F = flat(d["X"][idx])
    y = d["y"][idx]
    R = np.where((y == 1)[:, None], F - F[y == 1].mean(0), F - F[y == 0].mean(0))
    return R.T @ R / len(R)


def main():
    subj = {s: load(s) for s in SUBJECTS}
    covs = {s: within_cov(d, ~d["artifact"]) for s, d in subj.items()}
    rng = np.random.default_rng(0)
    rows = []
    for s, d in subj.items():
        prev, nxt = neighbours(d)
        ok = ~d["artifact"]
        mid = ok & (prev >= 0) & (nxt >= 0) & (d["bit"] >= 1) & (d["bit"] <= 3)
        mid &= ok[np.maximum(prev, 0)] & ok[np.maximum(nxt, 0)]
        pool = np.mean([c for o, c in covs.items() if o != s], axis=0)
        res = {}
        for k in range(1, 7):
            te, tr = d["session"] == k, d["session"] != k
            # ---- A: windows on bit positions 1-3
            itr, ite = np.flatnonzero(tr & mid), np.flatnonzero(te & mid)
            ytr, yte = d["y"][itr], d["y"][ite]
            for kind in ("", "p", "n", "pn"):
                Ftr, Fte = (flat(window_features(d, prev, nxt, i, kind)) for i in (itr, ite))
                w, b = fit_lda(Ftr, ytr)
                res.setdefault(f"W{kind or '0'}", []).append((acc(w, b, Fte, yte), len(ite)))
            # explaining away on Wpn: X ~ c + B_cur y_t + B_prev y_{t-1} + B_next y_{t+1} (labels coded +-1)
            Ftr, Fte = (flat(window_features(d, prev, nxt, i, "pn")) for i in (itr, ite))
            pm = lambda i: 2 * d["y"][i] - 1                                     # noqa: E731
            D = np.column_stack([np.ones(len(itr)), pm(itr), pm(prev[itr]), pm(nxt[itr])])
            B = np.linalg.lstsq(D, Ftr, rcond=None)[0]

            def clean(F, yp, yn):
                return F - np.outer(yp, B[2]) - np.outer(yn, B[3])
            w, b = fit_lda(clean(Ftr, pm(prev[itr]), pm(nxt[itr])), ytr)
            res.setdefault("Wpn_ea_oracle", []).append(
                (acc(w, b, clean(Fte, pm(prev[ite]), pm(nxt[ite])), yte), len(ite)))
            # practical: neighbour labels from a W0 LDA on all positions (cross-fitted inside the training sessions)
            all_tr = np.flatnonzero(tr & ok)
            soft = np.zeros(len(d["y"]))
            F0 = flat(d["X"])
            for kk in np.unique(d["session"][all_tr]):
                inner = all_tr[d["session"][all_tr] != kk]
                w0, b0 = fit_lda(F0[inner], d["y"][inner])
                sel = np.flatnonzero(tr & (d["session"] == kk))
                soft[sel] = np.tanh((F0[sel] @ w0 + b0) / 2)                   # E[y in +-1] under the LDA
            w0, b0 = fit_lda(F0[all_tr], d["y"][all_tr])
            soft[np.flatnonzero(te)] = np.tanh((F0[te] @ w0 + b0) / 2)
            w, b = fit_lda(clean(Ftr, soft[prev[itr]], soft[nxt[itr]]), ytr)
            res.setdefault("Wpn_ea", []).append((acc(w, b, clean(Fte, soft[prev[ite]], soft[nxt[ite]]), yte),
                                                 len(ite)))
            # ---- B: data (W0, all positions)
            ite_all = np.flatnonzero(te & ok)
            Fte0, yte0 = F0[ite_all], d["y"][ite_all]
            train_sessions = [x for x in range(1, 7) if x != k]
            for n in range(1, 6):
                draws = 1 if n == 5 else 3
                a_ = []
                for _ in range(draws):
                    ss = rng.choice(train_sessions, n, replace=False)
                    i = np.flatnonzero(np.isin(d["session"], ss) & ok)
                    w, b = fit_lda(F0[i], d["y"][i])
                    a_.append(acc(w, b, Fte0, yte0))
                res.setdefault(f"lc_{n}", []).append((np.mean(a_), len(ite_all)))
            for a in (0.75, 0.5, 0.25):
                w, b = fit_lda(F0[all_tr], d["y"][all_tr], pool, a)
                res.setdefault(f"pool_{a}", []).append((acc(w, b, Fte0, yte0), len(ite_all)))
            # the same pooled prior with fewer own sessions (2), to see where the prior matters
            ss = train_sessions[:2]
            i = np.flatnonzero(np.isin(d["session"], ss) & ok)
            for a in (1.0, 0.5):
                w, b = fit_lda(F0[i], d["y"][i], pool, a)
                res.setdefault(f"lc2_pool_{a}", []).append((acc(w, b, Fte0, yte0), len(ite_all)))
        rows.append({m: 100 * sum(a * n for a, n in v) / sum(n for _, n in v) for m, v in res.items()})
        print(f"Sub{s:02d} " + " ".join(f"{m} {v:.1f}" for m, v in rows[-1].items()), flush=True)
    write_report(rows)


def write_report(rows):
    import pandas as pd
    df = pd.DataFrame(rows, index=list(SUBJECTS))
    df.to_csv(ROOT / "reports/pilot_ch1_headroom.csv", float_format="%.3f")

    def line(m, ref):
        dlt = df[m] - df[ref]
        p = wilcoxon(df[m], df[ref]).pvalue if (dlt != 0).any() else 1.0
        return f"| `{m}` | {df[m].mean():.2f} | {dlt.mean():+.2f} | {(dlt > 0).sum()}/28 | {p:.1g} |"
    out = ["# Chapter 1 headroom pilot (shrinkage LDA, within subject, leave-one-session-out)", "",
           "Generated by `scripts/pilot_ch1_headroom.py`; per-subject values in `reports/pilot_ch1_headroom.csv`.",
           "", "## A. Information outside the epoch window (bit positions 1-3)", "",
           "| Variant | Accuracy (%) | Δ vs W0 (pp) | Improved | p |", "|---|---|---|---|---|"]
    out += [line(m, "W0") for m in ("W0", "Wp", "Wn", "Wpn", "Wpn_ea", "Wpn_ea_oracle")]
    out += ["", "## B. More data: own sessions and other subjects (all bit positions, W0)", "",
            "| Variant | Accuracy (%) | Δ vs 5 own sessions (pp) | Improved | p |", "|---|---|---|---|---|"]
    out += [line(m, "lc_5") for m in ("lc_1", "lc_2", "lc_3", "lc_4", "lc_5", "pool_0.75", "pool_0.5", "pool_0.25")]
    out += ["", "| 2 own sessions | Accuracy (%) | Δ (pp) | Improved | p |", "|---|---|---|---|---|"]
    out += [line(m, "lc2_pool_1.0") for m in ("lc2_pool_1.0", "lc2_pool_0.5")]
    (ROOT / "reports/pilot_ch1_headroom.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    sys.exit(main())
