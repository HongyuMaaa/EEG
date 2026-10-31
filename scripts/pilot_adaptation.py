"""Direction 1 pilot: label-free adaptation to a new subject using repetition structure (see aved/adapt.py).

Protocol per target subject s (leave-one-subject-out):
  * every subject is z-scored per channel with its own statistics (label-free; for the target, computed on its
    adaptation sessions only);
  * source model (EEGNet + linear ERP decoder, cross-entropy + Noise2Noise on averaged repetition targets) trained
    on 24 source subjects, early-stopped on the 3 validation subjects of the LOSO fold (configs/red.yaml, loso);
  * adaptation data: the target's sessions 1-3, WITHOUT labels (repetition groups from stimulus timing);
  * test: the target's sessions 4-6 (single trials). Fixed adaptation budget for every method; no target labels
    are used for any choice (the 'oracle' row uses them on purpose, as an upper reference).

Outputs (resumable): results/adapt_pilot/seed<k>/Sub<XX>.json, and results/adapt_pilot/summary_seed<k>.md

Usage:
    python scripts/pilot_adaptation.py --device cuda [--subjects 1 2 ...] [--seed 0]
    python scripts/pilot_adaptation.py --device cpu --subjects 1 --max-epochs 3      # smoke test
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
import torch.nn.functional as F
import yaml
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aved.adapt import ADAPT_METHODS, adapt, predict_proba  # noqa: E402
from aved.data import SUBJECTS, load_dataset, make_folds  # noqa: E402
from aved.models.red import REDStudent  # noqa: E402
from aved.train import resolve_device, set_seed  # noqa: E402
from aved.train_red import GroupBank  # noqa: E402

ADAPT_CFG = {"epochs": 10, "lr": 5e-4, "batch_size": 64, "lambda_n2n": 1.0, "gpl_threshold": 0.6}
ADAPT_SESSIONS, TEST_SESSIONS = (1, 2, 3), (4, 5, 6)


def zscore_per_subject(ds, stats_mask):
    """Normalise each subject with channel statistics computed on stats_mask trials of that subject."""
    X = np.empty_like(ds.X)
    for s in np.unique(ds.subject):
        m, ms = ds.subject == s, (ds.subject == s) & stats_mask
        mu, sd = ds.X[ms].mean(axis=(0, 2)), ds.X[ms].std(axis=(0, 2))
        X[m] = (ds.X[m] - mu[:, None]) / sd[:, None]
    return X


def train_source(Xtr, ytr, gtr, Xva, yva, model_cfg, tcfg, device, seed, log):
    set_seed(seed)
    model = REDStudent(Xtr.shape[1], Xtr.shape[2], dropout=tcfg["dropout"], **model_cfg).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=tcfg["lr"])
    loo, valid = GroupBank(gtr, device).loo_targets(Xtr)
    gen = torch.Generator().manual_seed(seed)
    best = {"loss": np.inf, "epoch": 0, "state": copy.deepcopy(model.state_dict())}
    for epoch in range(1, tcfg["max_epochs"] + 1):
        model.train()
        perm = torch.randperm(len(ytr), generator=gen).to(device)
        for i in range(0, len(perm), tcfg["batch_size"]):
            b = perm[i:i + tcfg["batch_size"]]
            if len(b) < 2:
                continue
            logits, recon = model(Xtr[b])
            v = valid[b]
            loss = F.cross_entropy(logits, ytr[b]) + F.mse_loss(recon[v], loo[b][v])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            model.apply_max_norm()
        p = predict_proba(model, Xva)
        vl = F.nll_loss(torch.log(p + 1e-8), yva).item()
        if vl < best["loss"]:
            best = {"loss": vl, "epoch": epoch, "state": copy.deepcopy(model.state_dict())}
        if epoch - best["epoch"] >= tcfg["patience"]:
            break
    model.load_state_dict(best["state"])
    log(f"  source model: best epoch {best['epoch']}, val acc {(p.argmax(1) == yva).float().mean():.3f}")
    return model.eval()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subjects", type=int, nargs="*", default=list(SUBJECTS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--max-epochs", type=int, help="override source max_epochs (smoke tests)")
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    device = resolve_device(args.device)
    model_cfg = yaml.safe_load((ROOT / "configs/eegnet.yaml").read_text())["model"]
    tcfg = dict(yaml.safe_load((ROOT / "configs/red.yaml").read_text())["training"]["loso"])
    if args.max_epochs:
        tcfg["max_epochs"] = args.max_epochs
    out_dir = ROOT / args.results_dir / "adapt_pilot" / f"seed{args.seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset(ROOT / "derivatives/preprocessed", SUBJECTS)
    for s in args.subjects:
        f = out_dir / f"Sub{s:02d}.json"
        if f.exists():
            continue
        t0 = time.time()
        fold = make_folds("loso", [s])[0]
        stats_mask = ~((ds.subject == s) & np.isin(ds.session, TEST_SESSIONS))   # target stats from adaptation sessions
        X = torch.from_numpy(zscore_per_subject(ds, stats_mask)).to(device)
        y = torch.from_numpy(ds.y).to(device)
        tr = np.isin(ds.subject, fold.train_subjects)
        va = np.isin(ds.subject, fold.val_subjects)
        ad = (ds.subject == s) & np.isin(ds.session, ADAPT_SESSIONS)
        te = (ds.subject == s) & np.isin(ds.session, TEST_SESSIONS)
        print(f"Sub{s:02d}: source {tr.sum()} trials, adaptation {ad.sum()} (unlabelled), test {te.sum()}", flush=True)
        source = train_source(X[tr], y[tr], ds.group[tr], X[va], y[va], model_cfg, tcfg, device, args.seed, print)
        rec = {"subject": s, "seed": args.seed, "adapt_cfg": ADAPT_CFG, "accuracy": {}}
        for m in ADAPT_METHODS:
            model = adapt(source, m, X[ad], ds.group[ad], y[ad] if m == "oracle" else None, ADAPT_CFG, args.seed)
            acc = float((predict_proba(model, X[te]).argmax(1) == y[te]).float().mean())
            rec["accuracy"][m] = acc
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        print("  " + "  ".join(f"{m} {100 * a:.2f}" for m, a in rec["accuracy"].items()), flush=True)
        f.write_text(json.dumps(rec, indent=2))

    rows = [json.loads(p.read_text()) for p in sorted(out_dir.glob("Sub*.json"))]
    acc = pd.DataFrame([r["accuracy"] for r in rows], index=[r["subject"] for r in rows])
    lines = [f"# Direction 1 pilot: label-free adaptation to a new subject (seed {args.seed})", "",
             f"Leave-one-subject-out; adaptation on the target's sessions 1-3 without labels; test on sessions 4-6. "
             f"Subjects: {len(acc)}. Adaptation budget: {ADAPT_CFG}.", "",
             "| method | accuracy (%) | Δ vs source (pp) | Δ vs adabn (pp) | improved vs adabn | Wilcoxon p vs adabn |",
             "|---|---|---|---|---|---|"]
    for m in ADAPT_METHODS:
        d0, d1 = acc[m] - acc["source"], acc[m] - acc["adabn"]
        p = wilcoxon(acc[m], acc["adabn"]).pvalue if m not in ("source", "adabn") and len(acc) > 5 and (d1 != 0).any() else float("nan")
        lines.append(f"| {m} | {100 * acc[m].mean():.2f} | {100 * d0.mean():+.2f} | {100 * d1.mean():+.2f} "
                     f"| {int((d1 > 0).sum())}/{len(acc)} | {p:.4f} |")
    text = "\n".join(lines) + "\n"
    print(text)
    (out_dir.parent / f"summary_seed{args.seed}.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
