"""Chapter 2, C2.1: train and evaluate LR-MoE variants and matched baselines, leave-one-subject-out (zero-shot).

Every variant uses the same data handling: per-subject channel z-scoring (label-free, statistics from each
subject's own trials), LOSO folds from aved.data (24 training subjects, 3 validation subjects for early stopping,
test = all 6 sessions of the held-out subject), training settings of configs/red.yaml (loso).

Variants (aved/models/lrmoe.py): eegnet_sz, eegnet_mirroraug, lrmoe, lrmoe_generic, lrmoe_nodecomp, lrmoe_nolat,
lrmoe_nocoh, lrmoe_anti. Losses: cross-entropy + lambda_lb * load balance (KL of the batch-mean gate to uniform)
+ lambda_coh * subject coherence (variance of the gates within each subject of the batch).

Two test-time routings are evaluated: per trial (method name) and subject-averaged (<method>_subjgate: the router
output averaged over the target subject's trials - label-free, transductive). Results use the layout of
scripts/run_baseline.py, so compare_methods.py --protocol loso --reference eegnet_sz works; mean gates per test
subject are saved for the interpretability analysis.

Usage:
    python scripts/run_moe.py --method lrmoe --device cuda [--seed 0] [--subjects ...]
    python scripts/run_moe.py --method lrmoe --device cpu --subjects 2 --max-epochs 2 --results-dir <tmp>   # smoke
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from aved.data import SUBJECTS, load_dataset, make_folds  # noqa: E402
from aved.models.lrmoe import VARIANTS, LRMoE  # noqa: E402
from aved.train import resolve_device, set_seed, limit_gpu_memory, VRAM_HELP  # noqa: E402

LOSS = {"lambda_lb": 0.1, "lambda_coh": 0.1}


def zscore_all(ds) -> np.ndarray:
    X = np.empty_like(ds.X)
    for s in np.unique(ds.subject):
        m = ds.subject == s
        mu, sd = ds.X[m].mean(axis=(0, 2)), ds.X[m].std(axis=(0, 2))
        X[m] = (ds.X[m] - mu[:, None]) / sd[:, None]
    return X


@torch.no_grad()
def predict(model, X, bs=1024, gates=None):
    model.eval()
    logits, gs = [], []
    for i in range(0, len(X), bs):
        lo, g = model(X[i:i + bs], None if gates is None else gates.expand(len(X[i:i + bs]), -1))
        logits.append(lo)
        gs.append(g)
    return torch.cat(logits), torch.cat(gs)


def train(variant, ds, X, y, subj, tr, va, tcfg, device, seed, log):
    set_seed(seed)
    model = LRMoE(ds.ch_names, X.shape[2], ds.sfreq, variant["experts"], variant["router"],
                  dropout=tcfg["dropout"], **MODEL_CFG).to(device)
    lam_lb = variant.get("lambda_lb", LOSS["lambda_lb"])
    lam_coh = variant.get("lambda_coh", LOSS["lambda_coh"])
    opt = torch.optim.Adam(model.parameters(), lr=tcfg["lr"])
    itr = torch.as_tensor(np.flatnonzero(tr), device=device)
    iva = torch.as_tensor(np.flatnonzero(va), device=device)
    gen = torch.Generator().manual_seed(seed)
    best = {"loss": np.inf, "epoch": 0, "state": copy.deepcopy(model.state_dict())}
    for epoch in range(1, tcfg["max_epochs"] + 1):
        model.train()
        perm = itr[torch.randperm(len(itr), generator=gen).to(device)]
        for i in range(0, len(perm), tcfg["batch_size"]):
            b = perm[i:i + tcfg["batch_size"]]
            if len(b) < 2:
                continue
            xb, yb, sb = X[b], y[b], subj[b]
            if variant.get("mirror_aug"):
                flip = torch.rand(len(b), generator=gen).to(device) < 0.5
                xb = torch.where(flip[:, None, None], xb[:, model.mirror], xb)
                yb = torch.where(flip, 1 - yb, yb)
            logits, g = model(xb)
            loss = F.cross_entropy(logits, yb)
            if g.shape[1] > 1:
                gm = g.mean(0)
                loss = loss + lam_lb * (gm * torch.log(gm * g.shape[1] + 1e-8)).sum()
                if lam_coh > 0:
                    coh = [g[sb == s].var(0, unbiased=False).sum() for s in torch.unique(sb)]
                    loss = loss + lam_coh * torch.stack(coh).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            model.apply_max_norm()
        lo, _ = predict(model, X[iva])
        vl = F.cross_entropy(lo, y[iva]).item()
        if vl < best["loss"]:
            best = {"loss": vl, "epoch": epoch, "state": copy.deepcopy(model.state_dict())}
        if epoch - best["epoch"] >= tcfg["patience"]:
            break
    model.load_state_dict(best["state"])
    log(f"  best epoch {best['epoch']}, val loss {best['loss']:.4f}")
    return model.eval(), best["epoch"]


def save(run_dir: Path, fold, ds, te, logits, info, gates_mean, kinds):
    for d in ("folds", "predictions"):
        (run_dir / d).mkdir(parents=True, exist_ok=True)
    prob = torch.softmax(logits, 1)[:, 1].cpu().numpy()
    pred = pd.DataFrame({"subject": ds.subject[te], "session": ds.session[te], "trial": ds.trial[te],
                         "y": ds.y[te], "pred": (prob > 0.5).astype(int), "score": np.round(prob, 6)})
    pred.to_csv(run_dir / "predictions" / f"{fold.name}.csv", index=False)
    acc = float((pred.y == pred.pred).mean())
    rec = {"fold": fold.name, "test_session": None, "val_subjects": list(fold.val_subjects), "accuracy": acc,
           "per_subject": {str(fold.test_subjects[0]): {"accuracy": acc, "n_test": int(len(pred))}},
           "mean_gate": gates_mean, "expert_kinds": kinds, **info}
    (run_dir / "folds" / f"{fold.name}.json").write_text(json.dumps(rec, indent=2))
    return acc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", choices=list(VARIANTS), required=True)
    ap.add_argument("--subjects", type=int, nargs="*", default=list(SUBJECTS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--max-vram-gb", type=float, help=VRAM_HELP)
    ap.add_argument("--max-epochs", type=int)
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    device = resolve_device(args.device)
    limit_gpu_memory(device, args.max_vram_gb)
    tcfg = dict(yaml.safe_load((ROOT / "configs/red.yaml").read_text())["training"]["loso"])
    if args.max_epochs:
        tcfg["max_epochs"] = args.max_epochs
    variant = VARIANTS[args.method]
    dirs = {r: ROOT / args.results_dir / name / "loso" / f"seed{args.seed}"
            for r, name in (("trial", args.method), ("subject", f"{args.method}_subjgate"))}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
        (d / "run_info.json").write_text(json.dumps({"method": args.method, "variant": variant, "loss": LOSS,
                                                     "training": tcfg, "model": MODEL_CFG, "seed": args.seed,
                                                     "device": str(device), "normalisation": "per-subject z-score"},
                                                    indent=2, default=str))
    ds = load_dataset(ROOT / "derivatives/preprocessed", SUBJECTS)
    X = torch.from_numpy(zscore_all(ds)).to(device)
    y = torch.from_numpy(ds.y).to(device)
    subj = torch.from_numpy(ds.subject).to(device)
    kinds = [f"{k}{d:+d}" for k, d in variant["experts"]]
    for s in args.subjects:
        fold = make_folds("loso", [s])[0]
        if (dirs["trial"] / "folds" / f"{fold.name}.json").exists():
            continue
        t0 = time.time()
        tr, va, te = fold.masks(ds)
        print(f"{args.method} seed {args.seed} fold {fold.name}", flush=True)
        model, best_epoch = train(variant, ds, X, y, subj, tr, va, tcfg, device, args.seed, print)
        ite = torch.as_tensor(np.flatnonzero(te), device=device)
        logits, g = predict(model, X[ite])
        info = {"best_epoch": best_epoch, "train_time_s": round(time.time() - t0, 1)}
        gm = g.mean(0, keepdim=True)
        a1 = save(dirs["trial"], fold, ds, te, logits, info, gm[0].tolist(), kinds)
        logits_s, _ = predict(model, X[ite], gates=gm)
        a2 = save(dirs["subject"], fold, ds, te, logits_s, info, gm[0].tolist(), kinds)
        print(f"  test accuracy per-trial routing {a1:.4f}, subject-averaged routing {a2:.4f}", flush=True)


MODEL_CFG = yaml.safe_load((ROOT / "configs/eegnet.yaml").read_text())["model"]

if __name__ == "__main__":
    main()
