"""Chapter 2 feasibility gate: can subject-phenotype routing beat a single model, given ORACLE phenotypes?

Leave-one-subject-out; test = all 6 sessions of subject s; EEGNet with the settings and global (training-set)
channel normalisation of the original LOSO baseline (configs/eegnet.yaml, loso). Phenotype descriptors from
aved/phenotype.py are computed with labels - for the test subject too, which is what makes this an oracle test.

Variants (each also defines its own training subjects; 2 of them are held out for early stopping):
  phen_split   27 other subjects split at the median mirror_corr; train on the test subject's own group
  rand_split   random group of the same size (seeded per fold)                - control for less data
  wrong_split  train on the OPPOSITE phenotype group                           - control for direction
  phen_knn     the 13 subjects nearest in standardised descriptor space
  rand_knn     13 random subjects                                              - control for less data
  phen_cond    all 27 subjects, classifier conditioned on the subject's standardised descriptors:
               logits = W0 f + sum_j d_j W_j f  (subject-specific reweighting of the same EEGNet features)
Reference: results/eegnet/loso (original baseline, 3 seeds).

Usage:
    python scripts/run_oracle_routing.py --variant phen_split --device cuda [--seed 0]
    python scripts/run_oracle_routing.py --variant phen_cond --device cpu --subjects 2 --max-epochs 2 --results-dir <tmp>
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aved.data import SUBJECTS, load_dataset  # noqa: E402
from aved.models.eegnet import EEGNet  # noqa: E402
from aved.phenotype import DESCRIPTORS, descriptor_table  # noqa: E402
from aved.train import resolve_device, set_seed, limit_gpu_memory, VRAM_HELP  # noqa: E402

VARIANTS = ("phen_split", "rand_split", "wrong_split", "phen_knn", "rand_knn", "phen_cond")
K_NEIGHBOURS = 13
N_VAL = 2


class CondEEGNet(nn.Module):
    """EEGNet whose linear read-out is modulated by subject descriptors d: W0 f + sum_j d_j W_j f."""

    def __init__(self, n_channels, n_times, n_cond, **kw):
        super().__init__()
        self.eegnet = EEGNet(n_channels, n_times, **kw)
        n_feat = self.eegnet.classifier.in_features
        self.cond = nn.Linear(n_feat, 2 * n_cond, bias=False) if n_cond else None
        self.n_cond = n_cond
        if self.cond is not None:
            nn.init.zeros_(self.cond.weight)            # starts as the plain EEGNet

    def forward(self, x, d=None):
        f = self.eegnet.features(x)
        out = self.eegnet.classifier(f)
        if self.cond is not None:
            out = out + (self.cond(f).view(len(x), self.n_cond, 2) * d[:, :, None]).sum(1)
        return out

    def apply_max_norm(self):
        self.eegnet.apply_max_norm()


def knn_subjects(s, desc, cols=DESCRIPTORS, k=K_NEIGHBOURS, target_desc=None):
    """The k subjects nearest to s in standardised descriptor space (standardised over the other subjects).
    ``target_desc`` replaces the descriptors of s (e.g. a label-free estimate)."""
    others = [o for o in SUBJECTS if o != s]
    d = desc[list(cols)].copy()
    if target_desc is not None:
        d.loc[s, list(cols)] = [target_desc[c] for c in cols]
    z = (d - d.loc[others].mean()) / d.loc[others].std()
    return ((z.loc[others] - z.loc[s]) ** 2).sum(axis=1).nsmallest(k).index.tolist()


def choose_subjects(variant, s, desc, rng):
    """Training subjects (incl. validation) for test subject s."""
    others = [o for o in SUBJECTS if o != s]
    mc = desc["mirror_corr"]
    thr = mc.loc[others].median()
    high = [o for o in others if mc[o] >= thr]
    low = [o for o in others if mc[o] < thr]
    own, opposite = (high, low) if mc[s] >= thr else (low, high)
    if variant == "phen_split":
        return own
    if variant == "wrong_split":
        return opposite
    if variant == "rand_split":
        return sorted(rng.choice(others, size=len(own), replace=False).tolist())
    if variant in ("phen_knn", "rand_knn"):
        if variant == "rand_knn":
            return sorted(rng.choice(others, size=K_NEIGHBOURS, replace=False).tolist())
        return knn_subjects(s, desc)
    return others                                       # phen_cond


def fit_eegnet(ds, train, val, tcfg, model_cfg, device, seed, D=None, n_cond=0):
    """Train (Cond)EEGNet on subjects ``train``, early-stopped on ``val``; global channel normalisation from the
    training subjects. Returns the model (eval mode) and the normalised data tensor X of all trials."""
    tr, va = np.isin(ds.subject, train), np.isin(ds.subject, val)
    mean, std = ds.X[tr].mean(axis=(0, 2)), ds.X[tr].std(axis=(0, 2))
    X = torch.from_numpy((ds.X - mean[:, None]) / std[:, None]).float().to(device)
    y = torch.from_numpy(ds.y).to(device)
    if D is None:
        D = torch.zeros(len(ds.y), max(n_cond, 1), device=device)
    set_seed(seed)
    model = CondEEGNet(X.shape[1], X.shape[2], n_cond, dropout=tcfg["dropout"], **model_cfg).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=tcfg["lr"])
    itr, iva = (torch.as_tensor(np.flatnonzero(m), device=device) for m in (tr, va))
    gen = torch.Generator().manual_seed(seed)
    best = {"loss": np.inf, "epoch": 0, "state": copy.deepcopy(model.state_dict())}
    for epoch in range(1, tcfg["max_epochs"] + 1):
        model.train()
        perm = itr[torch.randperm(len(itr), generator=gen).to(device)]
        for i in range(0, len(perm), tcfg["batch_size"]):
            b = perm[i:i + tcfg["batch_size"]]
            if len(b) < 2:
                continue
            loss = F.cross_entropy(model(X[b], D[b]), y[b])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            model.apply_max_norm()
        model.eval()
        with torch.no_grad():
            vl = F.cross_entropy(torch.cat([model(X[iva][i:i + 2048], D[iva][i:i + 2048])
                                            for i in range(0, len(iva), 2048)]), y[iva]).item()
        if vl < best["loss"]:
            best = {"loss": vl, "epoch": epoch, "state": copy.deepcopy(model.state_dict())}
        if epoch - best["epoch"] >= tcfg["patience"]:
            break
    model.load_state_dict(best["state"])
    model.best_epoch = best["epoch"]
    return model.eval(), X


@torch.no_grad()
def predict_prob(model, X, D=None):
    D = torch.zeros(len(X), max(model.n_cond, 1), device=X.device) if D is None else D
    return torch.cat([torch.softmax(model(X[i:i + 2048], D[i:i + 2048]), 1)[:, 1]
                      for i in range(0, len(X), 2048)]).cpu().numpy()


def run_fold(variant, s, ds, desc, tcfg, model_cfg, device, seed, log):
    rng = np.random.default_rng(1000 * seed + s)
    pool = choose_subjects(variant, s, desc, rng)
    val = sorted(rng.choice(pool, size=N_VAL, replace=False).tolist())
    train = [o for o in pool if o not in val]
    others = [o for o in SUBJECTS if o != s]
    z = (desc - desc.loc[others].mean()) / desc.loc[others].std()
    D = torch.from_numpy(z.loc[ds.subject, list(DESCRIPTORS)].to_numpy(np.float32)).to(device)
    n_cond = len(DESCRIPTORS) if variant == "phen_cond" else 0
    model, X = fit_eegnet(ds, train, val, tcfg, model_cfg, device, seed, D if n_cond else None, n_cond)
    te = ds.subject == s
    ite = torch.as_tensor(np.flatnonzero(te), device=device)
    prob = predict_prob(model, X[ite], D[ite] if n_cond else None)
    log(f"  {variant} Sub{s:02d}: {len(train)} train + {len(val)} val subjects, best epoch {model.best_epoch}")
    return te, prob, {"train_subjects": train, "val_subjects": val, "best_epoch": model.best_epoch}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", choices=VARIANTS, required=True)
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
    run_dir = ROOT / args.results_dir / f"oracle_{args.variant}" / "loso" / f"seed{args.seed}"
    for d in ("folds", "predictions"):
        (run_dir / d).mkdir(parents=True, exist_ok=True)
    (run_dir / "run_info.json").write_text(json.dumps({"variant": args.variant, "training": tcfg, "seed": args.seed,
                                                       "device": str(device)}, indent=2))
    ds = load_dataset(ROOT / "derivatives/preprocessed", SUBJECTS)
    desc = descriptor_table(ROOT / "derivatives/preprocessed")[list(DESCRIPTORS)]
    for s in args.subjects:
        name = f"sub{s:02d}"
        if (run_dir / "folds" / f"{name}.json").exists():
            continue
        te, prob, info = run_fold(args.variant, s, ds, desc, tcfg, cfg["model"], device, args.seed, print)
        pred = pd.DataFrame({"subject": ds.subject[te], "session": ds.session[te], "trial": ds.trial[te],
                             "y": ds.y[te], "pred": (prob > 0.5).astype(int), "score": np.round(prob, 6)})
        pred.to_csv(run_dir / "predictions" / f"{name}.csv", index=False)
        acc = float((pred.y == pred.pred).mean())
        (run_dir / "folds" / f"{name}.json").write_text(json.dumps(
            {"fold": name, "test_session": None, "accuracy": acc,
             "per_subject": {str(s): {"accuracy": acc, "n_test": int(len(pred))}}, **info}, indent=2))
        print(f"  test accuracy {acc:.4f}", flush=True)


if __name__ == "__main__":
    main()
