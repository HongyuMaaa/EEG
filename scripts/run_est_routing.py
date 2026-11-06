"""Chapter 2: label-free phenotype routing - estimate the new subject's phenotype from repetition-averaged
pseudo-labels, train on its nearest subjects, optionally adapt with RAPL.

Leave-one-subject-out; for target subject s:
  1. source model: EEGNet on all 27 other subjects (2 held out for early stopping), as in the oracle test;
  2. pseudo-labels on the target's sessions 1-3 WITHOUT labels: mean source prediction over each repetition group,
     balanced split at the per-session median (each session is 240/240 by design);
  3. estimated phenotype of s from its pseudo-labelled trials (aved/phenotype.py): mirror_corr and anti_ratio
     (lat_latency is not used: its label-free estimate does not correlate with the truth, r = -0.05, decided
     before any accuracy result - see reports/round5_analysis.md);
  4. phenotype routing: EEGNet trained on the 13 subjects nearest to the estimate;
  5. RAPL (balanced group pseudo-labels, setting q30_e20) on sessions 1-3 on top of steps 1 and 4.
All methods are tested on sessions 4-6 of s. References trained in the same run: oracle routing with the same
two descriptors (true values of s) and 13 random subjects.

Methods written (results/<name>/loso/seed<k>/, layout of run_baseline.py):
  est_full, est_full_rapl, est_knn, est_knn_rapl, est_oracle_knn, est_rand_knn

Usage:
    python scripts/run_est_routing.py --device cuda --seed 0
    python scripts/run_est_routing.py --device cpu --subjects 18 --max-epochs 1 --results-dir <tmp>   # smoke
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from aved.adapt import adapt  # noqa: E402
from aved.data import SUBJECTS, load_dataset  # noqa: E402
from aved.phenotype import descriptor_table, subject_descriptors  # noqa: E402
from aved.train import resolve_device, limit_gpu_memory, VRAM_HELP  # noqa: E402
from pilot_adaptation import ADAPT_CFG  # noqa: E402
from run_oracle_routing import K_NEIGHBOURS, N_VAL, fit_eegnet, knn_subjects, predict_prob  # noqa: E402

COLS = ("mirror_corr", "anti_ratio")
EST_SESSIONS, TEST_SESSIONS = (1, 2, 3), (4, 5, 6)
RAPL = ("gpl_bal", {"epochs": 20})                  # q30_e20, the most frequently selected setting in round 4
METHODS = ("est_full", "est_full_rapl", "est_knn", "est_knn_rapl", "est_oracle_knn", "est_rand_knn")


class AdaptView(nn.Module):
    """Expose a CondEEGNet (n_cond = 0) with the (logits, recon) interface expected by aved.adapt."""

    def __init__(self, model):
        super().__init__()
        self.eegnet = model.eegnet

    def forward(self, x):
        return self.eegnet(x), None

    def apply_max_norm(self):
        self.eegnet.apply_max_norm()


def pseudo_labels(prob, groups, sessions):
    """Balanced group pseudo-labels: group mean of P(class 1), split at the per-session median."""
    df = pd.DataFrame({"p": prob, "g": groups, "s": sessions})
    gm = df.groupby("g").agg(p=("p", "mean"), s=("s", "first"))
    gm["lab"] = gm.groupby("s").p.transform(lambda v: (v > v.median()).astype(int))
    return gm.lab.loc[groups].to_numpy()


def save(results, name, seed, s, ds, te, prob, info):
    run_dir = results / name / "loso" / f"seed{seed}"
    for d in ("folds", "predictions"):
        (run_dir / d).mkdir(parents=True, exist_ok=True)
    pred = pd.DataFrame({"subject": ds.subject[te], "session": ds.session[te], "trial": ds.trial[te],
                         "y": ds.y[te], "pred": (prob > 0.5).astype(int), "score": np.round(prob, 6)})
    pred.to_csv(run_dir / "predictions" / f"sub{s:02d}.csv", index=False)
    acc = float((pred.y == pred.pred).mean())
    (run_dir / "folds" / f"sub{s:02d}.json").write_text(json.dumps(
        {"fold": f"sub{s:02d}", "test_session": None, "accuracy": acc,
         "per_subject": {str(s): {"accuracy": acc, "n_test": int(len(pred))}}, **info}, indent=2, default=float))
    return acc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subjects", type=int, nargs="*", default=list(SUBJECTS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--max-vram-gb", type=float, help=VRAM_HELP)
    ap.add_argument("--max-epochs", type=int)
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    device = resolve_device(args.device)
    limit_gpu_memory(device, args.max_vram_gb)
    cfg = yaml.safe_load((ROOT / "configs/eegnet.yaml").read_text())
    tcfg = dict(cfg["training"]["loso"])
    if args.max_epochs:
        tcfg["max_epochs"] = args.max_epochs
    results = ROOT / args.results_dir
    ds = load_dataset(ROOT / "derivatives/preprocessed", SUBJECTS)
    true = descriptor_table(ROOT / "derivatives/preprocessed")
    y = torch.from_numpy(ds.y).to(device)
    for s in args.subjects:
        if (results / METHODS[-1] / "loso" / f"seed{args.seed}" / "folds" / f"sub{s:02d}.json").exists():
            continue
        rng = np.random.default_rng(1000 * args.seed + s)
        others = [o for o in SUBJECTS if o != s]
        est_m = (ds.subject == s) & np.isin(ds.session, EST_SESSIONS)
        te = (ds.subject == s) & np.isin(ds.session, TEST_SESSIONS)
        ie, it = (torch.as_tensor(np.flatnonzero(m), device=device) for m in (est_m, te))

        def train_on(pool):
            val = sorted(rng.choice(pool, size=N_VAL, replace=False).tolist())
            model, X = fit_eegnet(ds, [o for o in pool if o not in val], val, tcfg, cfg["model"], device, args.seed)
            return model, X, val

        def rapl(model, X):
            m = adapt(AdaptView(model), RAPL[0], X[ie], ds.group[est_m], None, {**ADAPT_CFG, **RAPL[1]}, args.seed)
            with torch.no_grad():
                return torch.cat([torch.softmax(m(X[it][i:i + 2048])[0], 1)[:, 1]
                                  for i in range(0, len(it), 2048)]).cpu().numpy()

        # 1-3: source model, pseudo-labels, estimated phenotype (no target labels)
        src, Xs, val = train_on(others)
        pl = pseudo_labels(predict_prob(src, Xs[ie]), ds.group[est_m], ds.session[est_m])
        est = subject_descriptors(ds.X[est_m], pl, ds.ch_names, ds.times)
        nb_est = knn_subjects(s, true, COLS, target_desc=est)
        nb_true = knn_subjects(s, true, COLS)
        info = {"estimated": {c: est[c] for c in COLS}, "true": {c: float(true.loc[s, c]) for c in COLS},
                "neighbours_est": nb_est, "neighbours_true": nb_true,
                "neighbour_overlap": len(set(nb_est) & set(nb_true)) / K_NEIGHBOURS,
                "pseudo_label_accuracy": float((pl == ds.y[est_m]).mean())}      # reported only, never used
        accs = {"est_full": save(results, "est_full", args.seed, s, ds, te, predict_prob(src, Xs[it]), info),
                "est_full_rapl": save(results, "est_full_rapl", args.seed, s, ds, te, rapl(src, Xs), info)}
        # 4-5: routing on the estimate, + RAPL
        knn, Xk, _ = train_on(nb_est)
        accs["est_knn"] = save(results, "est_knn", args.seed, s, ds, te, predict_prob(knn, Xk[it]), info)
        accs["est_knn_rapl"] = save(results, "est_knn_rapl", args.seed, s, ds, te, rapl(knn, Xk), info)
        # references: oracle routing (same two descriptors), random 13
        orc, Xo, _ = train_on(nb_true)
        accs["est_oracle_knn"] = save(results, "est_oracle_knn", args.seed, s, ds, te, predict_prob(orc, Xo[it]), info)
        rnd_pool = sorted(rng.choice(others, size=K_NEIGHBOURS, replace=False).tolist())
        rnd, Xr, _ = train_on(rnd_pool)
        accs["est_rand_knn"] = save(results, "est_rand_knn", args.seed, s, ds, te, predict_prob(rnd, Xr[it]), info)
        print(f"Sub{s:02d}: pseudo-label acc {info['pseudo_label_accuracy']:.3f}, neighbour overlap "
              f"{info['neighbour_overlap']:.2f} | " + " ".join(f"{k} {100 * v:.2f}" for k, v in accs.items()), flush=True)


if __name__ == "__main__":
    main()
