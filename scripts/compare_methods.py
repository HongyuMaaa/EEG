"""Paired comparison of methods against a reference on one protocol (subject-level statistics).

Usage:
    python scripts/compare_methods.py --protocol within [--reference eegnet] [--methods red red_n2n ...]
                                      [--out results/compare_within.md]

For each method: mean accuracy over subjects (seeds averaged per subject), paired difference to the
reference, number of subjects improved, Wilcoxon signed-rank p-value, and mean fold diagnostics
(teacher accuracy on single trials / 3- / 6-trial averages, single-trial ERP reconstruction R^2).
Only (subject, test session) units present for both methods are compared.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

DIAGNOSTICS = ("teacher_test_acc_avg1", "teacher_test_acc_avg3", "teacher_test_acc_avg6",
               "recon_r2_test", "recon_r2_lateral_test", "best_epoch")


def unit_accuracy(root: Path, method: str, protocol: str, exclude_sessions=()) -> pd.DataFrame:
    """Accuracy per (subject, test session), averaged over seeds; columns acc, n (trials), seeds."""
    parts = []
    for run in sorted((root / method / protocol).glob("seed*")):
        files = sorted((run / "predictions").glob("*.csv"))
        if files:
            p = pd.concat([pd.read_csv(f) for f in files])
            p = p[~p.session.isin(exclude_sessions)]
            g = p.assign(correct=p.y == p.pred).groupby(["subject", "session"]).correct.agg(["mean", "size"])
            parts.append(g.rename(columns={"mean": "acc", "size": "n"}))
    if not parts:
        return pd.DataFrame(columns=["acc", "n", "seeds"])
    allp = pd.concat(parts, keys=range(len(parts)), names=["run"])
    return allp.groupby(["subject", "session"]).agg(acc=("acc", "mean"), n=("n", "first"), seeds=("acc", "size"))


def subject_accuracy(units: pd.DataFrame, keep) -> pd.Series:
    """Trial-weighted subject accuracy over the given (subject, session) units."""
    u = units.loc[keep]
    return (u.acc * u.n).groupby(level="subject").sum() / u.n.groupby(level="subject").sum()


def diagnostics(root: Path, method: str, protocol: str) -> dict:
    vals: dict[str, list] = {k: [] for k in DIAGNOSTICS}
    for f in (root / method / protocol).glob("seed*/folds/*.json"):
        rec = json.loads(f.read_text())
        for k in DIAGNOSTICS:
            if k in rec:
                vals[k].append(rec[k])
    return {k: float(np.mean(v)) for k, v in vals.items() if v}


def trains_decoder(root: Path, method: str, protocol: str) -> bool:
    """R^2 is only meaningful when the reconstruction loss trains the decoder."""
    for f in (root / method / protocol).glob("seed*/run_info.json"):
        return bool(json.loads(f.read_text())["method_config"].get("variant", {}).get("n2n", False))
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--reference", default="eegnet")
    ap.add_argument("--methods", nargs="*")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--exclude-sessions", type=int, nargs="*", default=[],
                    help="drop these test sessions, e.g. the validation sessions used for hyperparameter selection")
    ap.add_argument("--out")
    args = ap.parse_args()
    root = Path(args.results_dir)
    methods = args.methods or sorted(p.name for p in root.iterdir()
                                     if (p / args.protocol).is_dir() and "@sw-" not in p.name)
    ref_units = unit_accuracy(root, args.reference, args.protocol, args.exclude_sessions)
    if ref_units.empty:
        raise SystemExit(f"no results for reference {args.reference}/{args.protocol}")

    lines = [f"# Paired comparison — protocol `{args.protocol}`, reference `{args.reference}`", "",
             (f"Test sessions excluded: {args.exclude_sessions}. " if args.exclude_sessions else "")
             + "Each comparison uses the (subject, test session) units present for both methods; seeds are averaged.", "",
             "| method | seeds | subjects | units | accuracy (%) | Δ vs ref (pp) | improved | Wilcoxon p "
             "| teacher single / avg3 / avg6 (%) | recon R² (all / lateral) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for m in methods:
        units = unit_accuracy(root, m, args.protocol, args.exclude_sessions)
        keep = units.index.intersection(ref_units.index)
        if keep.empty:
            continue
        a, r = subject_accuracy(units, keep), subject_accuracy(ref_units, keep)
        common = a.index
        d = a - r
        p = wilcoxon(a, r).pvalue if m != args.reference and len(common) > 5 and (d != 0).any() else float("nan")
        dg = diagnostics(root, m, args.protocol)
        teacher = (" / ".join(f"{100 * dg[k]:.1f}" for k in DIAGNOSTICS[:3]) if "teacher_test_acc_avg1" in dg else "")
        recon = (f"{dg['recon_r2_test']:.3f} / {dg['recon_r2_lateral_test']:.3f}"
                 if "recon_r2_test" in dg and trains_decoder(root, m, args.protocol) else "")
        lines.append(f"| {m} | {int(units.seeds.max())} | {len(common)} | {len(keep)} "
                     f"| {100 * a.mean():.2f} ± {100 * a.std():.2f} | {100 * d.mean():+.2f} "
                     f"| {int((d > 0).sum())}/{len(common)} | {p:.4f} | {teacher} | {recon} |")
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
