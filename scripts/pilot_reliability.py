"""Pilot for Chapter 1 option B: reliability weighting of training trials from repetition averages (LDA, CPU).

Question: a 6-trial group average (same subject, session, character, bit) shows whether the subject responded
to that code; single trials of "unreliable" groups may act like label noise. Does down-weighting them help?

Per subject and leave-one-session-out fold (same splits as the main experiments; validation session unused):
  1. Cross-fitted reliability r_g for every training group: for each training session j, a shrinkage LDA trained
     on random 3-trial averages of the OTHER training sessions gives r_g = P(true class | group average of j).
  2. Train a weighted shrinkage LDA on single trials with weights w = 1 (baseline), r, r^2, or 1[r > 0.5];
     test on the single trials of the test session.
  3. Diagnostic: single-trial test accuracy of the baseline, split by the reliability of the test trial's own
     group (r from an LDA on averages of all training sessions) - do unreliable groups hold worse trials?

Usage: python scripts/pilot_reliability.py [--subjects 1 2 ...] [--out reports/pilot_reliability.md]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.covariance import ledoit_wolf_shrinkage
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aved.data import load_dataset, make_folds  # noqa: E402

SCHEMES = ("uniform", "soft", "soft2", "hard")


def group_averages(X, y, g, k, draws, rng):
    """Random k-trial averages within groups (k capped at group size)."""
    Xs, ys = [], []
    for gid in np.unique(g):
        idx = np.flatnonzero(g == gid)
        if len(idx) < 2:
            continue
        kk = min(k, len(idx))
        for _ in range(draws):
            Xs.append(X[rng.choice(idx, kk, replace=False)].mean(0))
            ys.append(y[idx[0]])
    return np.array(Xs), np.array(ys)


def full_averages(X, y, g):
    gids = np.unique(g)
    return gids, np.array([X[g == i].mean(0) for i in gids]), np.array([y[g == i][0] for i in gids])


def avg_lda(X, y, g, rng):
    Xa, ya = group_averages(X, y, g, 3, 6, rng)
    return LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit(Xa, ya)


def weighted_lda(X, y, w):
    """Two-class LDA with sample weights: weighted means and covariance, Ledoit-Wolf shrinkage
    (shrinkage intensity estimated on the unweighted centred data, identical for all weightings)."""
    mu = np.stack([np.average(X[y == c], axis=0, weights=w[y == c]) for c in (0, 1)])
    Z = X - mu[y]
    alpha = ledoit_wolf_shrinkage(Z)
    S = (Z * w[:, None]).T @ Z / w.sum()
    S = (1 - alpha) * S + alpha * np.trace(S) / S.shape[0] * np.eye(S.shape[0])
    coef = np.linalg.solve(S, mu[1] - mu[0])
    b = -coef @ (mu[0] + mu[1]) / 2 + np.log(w[y == 1].sum() / w[y == 0].sum())
    return coef, b


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", type=int, nargs="*", default=list(range(1, 29)))
    ap.add_argument("--out")
    args = ap.parse_args()
    rows, diag = [], []
    for s in args.subjects:
        ds = load_dataset(ROOT / "derivatives/preprocessed", [s])
        X = ds.X.reshape(len(ds.X), -1).astype(np.float64)
        for fold in make_folds("within", [s]):
            rng = np.random.default_rng(s * 10 + fold.test_session)
            tr, _, te = fold.masks(ds)          # validation session is not used by the pilot
            # 1. cross-fitted reliability of training groups
            r = np.full(len(ds.y), np.nan)
            for j in fold.train_sessions:
                other = tr & (ds.session != j)
                lda = avg_lda(X[other], ds.y[other], ds.group[other], rng)
                sel = tr & (ds.session == j)
                gids, A, ya = full_averages(X[sel], ds.y[sel], ds.group[sel])
                p = lda.predict_proba(A)[np.arange(len(ya)), ya]
                r[sel] = pd.Series(p, index=gids).loc[ds.group[sel]].to_numpy()
            rt = r[tr]
            # 2. weighted LDA on single trials
            weights = {"uniform": np.ones_like(rt), "soft": rt, "soft2": rt ** 2,
                       "hard": (rt > 0.5).astype(float) + 1e-6}
            rec = {"subject": s, "fold": fold.name, "frac_unreliable": float((rt <= 0.5).mean())}
            for name, w in weights.items():
                coef, b = weighted_lda(X[tr], ds.y[tr], w)
                rec[name] = float((((X[te] @ coef + b) > 0).astype(int) == ds.y[te]).mean())
            rows.append(rec)
            # 3. diagnostic on the test session
            lda_all = avg_lda(X[tr], ds.y[tr], ds.group[tr], rng)
            gids, A, ya = full_averages(X[te], ds.y[te], ds.group[te])
            rg = pd.Series(lda_all.predict_proba(A)[np.arange(len(ya)), ya], index=gids).loc[ds.group[te]].to_numpy()
            coef, b = weighted_lda(X[tr], ds.y[tr], np.ones(tr.sum()))
            correct = (((X[te] @ coef + b) > 0).astype(int) == ds.y[te])
            for lo, hi, name in ((0, 0.5, "r<=0.5"), (0.5, 0.9, "0.5<r<=0.9"), (0.9, 1.01, "r>0.9")):
                m = (rg > lo) & (rg <= hi)
                diag.append({"subject": s, "bin": name, "n": int(m.sum()), "correct": int(correct[m].sum())})
        print(f"Sub{s:02d}: " + " ".join(f"{k} {100 * np.mean([r_[k] for r_ in rows if r_['subject'] == s]):.2f}"
                                          for k in SCHEMES), flush=True)

    df = pd.DataFrame(rows)
    subj = df.groupby("subject")[list(SCHEMES) + ["frac_unreliable"]].mean()
    lines = ["# Pilot: reliability weighting from repetition averages (shrinkage LDA, within-subject LOSO-session)", "",
             f"Subjects: {len(subj)}; folds: {len(df)}. Mean fraction of training trials in groups with cross-fitted "
             f"reliability r <= 0.5: {100 * subj.frac_unreliable.mean():.1f}%.", "",
             "| weighting | accuracy (%) | Δ vs uniform (pp) | subjects improved | Wilcoxon p |", "|---|---|---|---|---|"]
    for k in SCHEMES:
        d = subj[k] - subj["uniform"]
        p = wilcoxon(subj[k], subj["uniform"]).pvalue if k != "uniform" else float("nan")
        lines.append(f"| {k} | {100 * subj[k].mean():.2f} | {100 * d.mean():+.2f} | {int((d > 0).sum())}/{len(d)} | {p:.4f} |")
    dg = pd.DataFrame(diag).groupby("bin")[["n", "correct"]].sum()
    lines += ["", "Diagnostic: baseline single-trial test accuracy by reliability of the trial's own test group", "",
              "| group reliability | trials | accuracy (%) |", "|---|---|---|"]
    for b in ("r<=0.5", "0.5<r<=0.9", "r>0.9"):
        if b in dg.index:
            lines.append(f"| {b} | {dg.loc[b, 'n']} | {100 * dg.loc[b, 'correct'] / max(dg.loc[b, 'n'], 1):.2f} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
