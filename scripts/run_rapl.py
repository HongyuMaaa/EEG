"""Chapter 2, C2.2-C2.3: repetition-averaged pseudo-labelling (RAPL) with nested selection and a safety rule.

Leave-one-subject-out. For target subject s (fold from aved.data.make_folds('loso')):
  * per-subject channel z-scoring; for the target AND the 3 validation subjects the statistics come from their
    adaptation sessions 1-3 only;
  * source model (EEGNet + ERP decoder, CE + Noise2Noise) trained on the 24 training subjects, early-stopped on
    the 3 validation subjects (as in scripts/pilot_adaptation.py);
  * every candidate RAPL setting is run on each VALIDATION subject (adapt on its sessions 1-3 without labels,
    score on its sessions 4-6 with labels); the candidate with the best mean validation accuracy is selected
    BEFORE the target is touched -> method 'rapl' (nested selection, no target labels involved);
  * on the target: all candidates, the selected one, and the references (source, AdaBN, threshold re-centring,
    single-trial balanced pseudo-labels, supervised oracle), adaptation on sessions 1-3, test on sessions 4-6;
  * label-free diagnostics on the target's adaptation data (group-level separation before/after adaptation,
    pseudo-label stability, fraction of flipped predictions).

Summary (results/rapl/summary_seed<k>.md):
  * accuracy table with paired statistics vs AdaBN;
  * safety rule 'rapl_safe' = adapt only if a label-free diagnostic exceeds a threshold, otherwise keep AdaBN.
    The diagnostic and threshold for subject s are chosen on the OTHER 27 subjects (leave-one-subject-out), so
    no information of s is used.

Usage:
    python scripts/run_rapl.py --device cuda --seed 0 [--subjects ...]
    python scripts/run_rapl.py --device cpu --subjects 1 2 --max-epochs 2 --results-dir <tmp>    # smoke test
    python scripts/run_rapl.py --summary-only --seed 0
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from scipy.stats import spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from aved.adapt import adapt, predict_proba  # noqa: E402
from aved.data import SUBJECTS, load_dataset, make_folds  # noqa: E402
from aved.train import resolve_device  # noqa: E402
from aved.train_red import GroupBank  # noqa: E402
from pilot_adaptation import ADAPT_CFG, ADAPT_SESSIONS, TEST_SESSIONS, train_source, zscore_per_subject  # noqa: E402

# candidate RAPL settings (method, cfg overrides); 'q30' is the a-priori setting of the pilot
CANDIDATES = {
    "q30": ("gpl_bal", {}),
    "q20": ("gpl_bal", {"gpl_bal_quantile": 0.2}),
    "q40": ("gpl_bal", {"gpl_bal_quantile": 0.4}),
    "sched": ("gpl_bal", {"gpl_bal_quantile": 0.2, "gpl_bal_quantile_end": 0.5}),
    "q30_e20": ("gpl_bal", {"epochs": 20}),
}
REFERENCES = ("source", "adabn", "balance", "gpl_bal_single", "oracle")
DIAGNOSTICS = ("sep_src", "sep_post", "pl_stability", "flip_rate")


@torch.no_grad()
def group_separation(model, X, groups) -> float:
    """Mean |mean P(class 1) over a group's members - 0.5| (label-free)."""
    p = predict_proba(model, X)[:, 1]
    bank = GroupBank(groups, X.device)
    gp = torch.zeros(len(bank.counts), device=X.device).index_add_(0, bank.trial_group, p) / bank.counts
    return float((gp - 0.5).abs().mean())


def accuracy(model, X, y) -> float:
    return float((predict_proba(model, X).argmax(1) == y).float().mean())


def run_subject(s, ds, X, y, source, seed, log):
    fold = make_folds("loso", [s])[0]
    sel = lambda subj, sess: (ds.subject == subj) & np.isin(ds.session, sess)  # noqa: E731
    rec = {"subject": s, "seed": seed, "candidates": list(CANDIDATES), "accuracy": {}, "val_accuracy": {},
           "diagnostics": {}}

    # 1. nested selection on the validation subjects (labels of validation subjects only)
    for name, (method, over) in CANDIDATES.items():
        accs = []
        for v in fold.val_subjects:
            ad, te = sel(v, ADAPT_SESSIONS), sel(v, TEST_SESSIONS)
            m = adapt(source, method, X[ad], ds.group[ad], None, {**ADAPT_CFG, **over}, seed)
            accs.append(accuracy(m, X[te], y[te]))
        rec["val_accuracy"][name] = float(np.mean(accs))
    selected = max(CANDIDATES, key=lambda c: (rec["val_accuracy"][c], c == "q30"))
    rec["selected"] = selected
    log(f"  nested selection on validation subjects {fold.val_subjects}: "
        + " ".join(f"{c} {100 * a:.2f}" for c, a in rec["val_accuracy"].items()) + f" -> {selected}")

    # 2. target subject
    ad, te = sel(s, ADAPT_SESSIONS), sel(s, TEST_SESSIONS)
    base = adapt(source, "adabn", X[ad], ds.group[ad], None, ADAPT_CFG, seed)
    base_pred = predict_proba(base, X[ad]).argmax(1)
    rec["diagnostics"]["sep_src"] = group_separation(base, X[ad], ds.group[ad])
    for m in REFERENCES:
        model = base if m == "adabn" else adapt(source, m, X[ad], ds.group[ad], y[ad] if m == "oracle" else None,
                                                ADAPT_CFG, seed)
        rec["accuracy"][m] = accuracy(model, X[te], y[te])
    for name, (method, over) in CANDIDATES.items():
        info = {}
        model = adapt(source, method, X[ad], ds.group[ad], None, {**ADAPT_CFG, **over}, seed, info)
        rec["accuracy"][name] = accuracy(model, X[te], y[te])
        rec["diagnostics"][f"sep_post_{name}"] = group_separation(model, X[ad], ds.group[ad])
        rec["diagnostics"][f"pl_stability_{name}"] = info.get("pl_stability", float("nan"))
        rec["diagnostics"][f"flip_rate_{name}"] = float((predict_proba(model, X[ad]).argmax(1) != base_pred)
                                                        .float().mean())
    rec["accuracy"]["rapl"] = rec["accuracy"][selected]
    for d in ("sep_post", "pl_stability", "flip_rate"):            # diagnostics of the selected setting
        rec["diagnostics"][d] = rec["diagnostics"][f"{d}_{selected}"]
    return rec


def safety_rule(df: pd.DataFrame) -> tuple[pd.Series, list]:
    """Leave-one-subject-out choice of (diagnostic, threshold): for each subject, maximise the mean gain of
    'adapt if diagnostic >= threshold else AdaBN' over the other subjects, then apply it to the subject."""
    gain = df["rapl"] - df["adabn"]
    out, chosen = {}, []
    for s in df.index:
        rest = df.drop(index=s)
        g_rest = gain.drop(index=s)
        best = (g_rest.mean(), None, -np.inf)   # (mean gain over the others, diagnostic, threshold); None = always adapt
        for d in DIAGNOSTICS:
            for thr in np.unique(rest[d].dropna()):
                g = np.where(rest[d] >= thr, g_rest, 0.0).mean()
                if g > best[0] + 1e-12:
                    best = (g, d, thr)
        _, d, thr = best
        adapt_s = d is None or (not np.isnan(df.loc[s, d]) and df.loc[s, d] >= thr)
        out[s] = df.loc[s, "rapl"] if adapt_s else df.loc[s, "adabn"]
        chosen.append((s, d, thr, adapt_s))
    return pd.Series(out), chosen


def summarise(out_dir: Path, seed: int) -> str:
    rows = [json.loads(p.read_text()) for p in sorted(out_dir.glob("Sub*.json"))]
    if not rows:
        return "no results"
    acc = pd.DataFrame([r["accuracy"] for r in rows], index=[r["subject"] for r in rows]) * 100
    diag = pd.DataFrame([{d: r["diagnostics"][d] for d in DIAGNOSTICS} for r in rows], index=acc.index)
    acc["rapl_safe"], chosen = safety_rule(pd.concat([acc, diag], axis=1))
    order = list(REFERENCES[:4]) + list(CANDIDATES) + ["rapl", "rapl_safe", "oracle"]
    lines = [f"# RAPL — label-free adaptation to a new subject (seed {seed}, {len(acc)} subjects)", "",
             "Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. "
             "`rapl` = candidate selected on the fold's validation subjects; `rapl_safe` = rapl or AdaBN by a "
             "label-free rule fitted on the other subjects.", "",
             "| method | accuracy (%) | Δ vs AdaBN (pp) | improved | worse | Wilcoxon p | Δ vs oracle gap recovered |",
             "|---|---|---|---|---|---|---|"]
    gap = (acc["oracle"] - acc["adabn"]).mean()
    for m in order:
        d = acc[m] - acc["adabn"]
        p = wilcoxon(acc[m], acc["adabn"]).pvalue if m != "adabn" and (d != 0).any() else float("nan")
        lines.append(f"| {m} | {acc[m].mean():.2f} | {d.mean():+.2f} | {int((d > 0).sum())} | {int((d < 0).sum())} "
                     f"| {p:.3g} | {d.mean() / gap:.2f} |")
    sel = pd.Series([r["selected"] for r in rows]).value_counts()
    gain = acc["rapl"] - acc["adabn"]
    lines += ["", f"Nested selection picked: {dict(sel)}", "",
              "Label-free diagnostics vs RAPL gain (Spearman):", ""]
    for d in DIAGNOSTICS:
        r, p = spearmanr(diag[d], gain, nan_policy="omit")
        lines.append(f"- {d}: r = {r:.2f}, p = {p:.3g}")
    n_skip = sum(not a for *_, a in chosen)
    lines += ["", f"Safety rule: adaptation skipped for {n_skip} subject(s): "
              + ", ".join(f"Sub{s:02d} ({d} < {t:.3f})" for s, d, t, a in chosen if not a)]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subjects", type=int, nargs="*", default=list(SUBJECTS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--max-epochs", type=int, help="override source max_epochs (smoke tests)")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()
    out_dir = ROOT / args.results_dir / "rapl" / f"seed{args.seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.summary_only:
        device = resolve_device(args.device)
        model_cfg = yaml.safe_load((ROOT / "configs/eegnet.yaml").read_text())["model"]
        tcfg = dict(yaml.safe_load((ROOT / "configs/red.yaml").read_text())["training"]["loso"])
        if args.max_epochs:
            tcfg["max_epochs"] = args.max_epochs
        ds = load_dataset(ROOT / "derivatives/preprocessed", SUBJECTS)
        for s in args.subjects:
            f = out_dir / f"Sub{s:02d}.json"
            if f.exists():
                continue
            t0 = time.time()
            fold = make_folds("loso", [s])[0]
            held = np.isin(ds.subject, (s,) + tuple(fold.val_subjects)) & np.isin(ds.session, TEST_SESSIONS)
            X = torch.from_numpy(zscore_per_subject(ds, ~held)).to(device)
            y = torch.from_numpy(ds.y).to(device)
            tr, va = np.isin(ds.subject, fold.train_subjects), np.isin(ds.subject, fold.val_subjects)
            print(f"Sub{s:02d}: training source model", flush=True)
            source = train_source(X[tr], y[tr], ds.group[tr], X[va], y[va], model_cfg, tcfg, device, args.seed, print)
            rec = run_subject(s, ds, X, y, source, args.seed, print)
            rec["minutes"] = round((time.time() - t0) / 60, 1)
            print("  target: " + " ".join(f"{m} {100 * a:.2f}" for m, a in rec["accuracy"].items()), flush=True)
            f.write_text(json.dumps(rec, indent=2))
    text = summarise(out_dir, args.seed)
    print(text)
    (out_dir.parent / f"summary_seed{args.seed}.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
