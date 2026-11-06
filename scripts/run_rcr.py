"""Chapter 2, round 7: repetition-consistency routing (RCR) over subject-bagged experts, with RAPL on top.

Leave-one-subject-out; for target subject s:
  * expert pool: the full-data EEGNet (all 27 other subjects) + N_BAGGED EEGNets, each on a random subset of
    13 source subjects (bagging); 2 subjects of every training set are held out for early stopping;
    settings and global normalisation of the LOSO baseline (scripts/run_oracle_routing.fit_eegnet);
  * label-free router score of every expert on the target's UNLABELLED sessions 1-3:
        cons = fraction of single-trial predictions that agree with the balanced repetition-group
               pseudo-labels of the same expert (group mean prediction, split at the per-session median);
  * routing rules (fixed before any result): top1 (highest cons), top3 (mean probability of the 3 highest),
    soft (weights softmax(cons / 0.02) over all experts);
  * RAPL (setting q30_e20) on sessions 1-3 on top of the full model, of the top1 expert and of each top3 expert;
  * everything is tested on sessions 4-6.
Controls: rcr_full (full-data model), rcr_uniform (equal average of all experts), rcr_random (one expert chosen
at random), rcr_oracle (best expert on the test sessions - uses test labels, reference only).

Methods written (results/<name>/loso/seed<k>/): rcr_full, rcr_random, rcr_uniform, rcr_top1, rcr_top3, rcr_soft,
rcr_oracle, rcr_full_rapl, rcr_top1_rapl, rcr_top3_rapl. Per-subject expert scores: results/rcr_experts/seed<k>/.

Usage:
    python scripts/run_rcr.py --device cuda --seed 0
    python scripts/run_rcr.py --device cpu --subjects 18 --max-epochs 1 --n-bagged 2 --results-dir <tmp>   # smoke
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from aved.adapt import adapt  # noqa: E402
from aved.data import SUBJECTS, load_dataset  # noqa: E402
from aved.train import resolve_device, limit_gpu_memory, VRAM_HELP  # noqa: E402
from pilot_adaptation import ADAPT_CFG  # noqa: E402
from run_est_routing import RAPL, AdaptView, pseudo_labels, save  # noqa: E402
from run_oracle_routing import K_NEIGHBOURS, N_VAL, fit_eegnet, predict_prob  # noqa: E402

N_BAGGED = 8
SOFT_TAU = 0.02
EST_SESSIONS, TEST_SESSIONS = (1, 2, 3), (4, 5, 6)
METHODS = ("rcr_full", "rcr_random", "rcr_uniform", "rcr_top1", "rcr_top3", "rcr_soft", "rcr_oracle",
           "rcr_full_rapl", "rcr_top1_rapl", "rcr_top3_rapl")


def consistency(prob, groups, sessions) -> float:
    """Agreement of single-trial predictions with the balanced repetition-group pseudo-labels (label-free)."""
    return float(((prob > 0.5).astype(int) == pseudo_labels(prob, groups, sessions)).mean())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subjects", type=int, nargs="*", default=list(SUBJECTS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--max-vram-gb", type=float, help=VRAM_HELP)
    ap.add_argument("--max-epochs", type=int)
    ap.add_argument("--n-bagged", type=int, default=N_BAGGED)
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    device = resolve_device(args.device)
    limit_gpu_memory(device, args.max_vram_gb)
    cfg = yaml.safe_load((ROOT / "configs/eegnet.yaml").read_text())
    tcfg = dict(cfg["training"]["loso"])
    if args.max_epochs:
        tcfg["max_epochs"] = args.max_epochs
    results = ROOT / args.results_dir
    exp_dir = results / "rcr_experts" / f"seed{args.seed}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    ds = load_dataset(ROOT / "derivatives/preprocessed", SUBJECTS)
    for s in args.subjects:
        if (exp_dir / f"sub{s:02d}.json").exists():
            continue
        rng = np.random.default_rng(1000 * args.seed + s)
        others = [o for o in SUBJECTS if o != s]
        est_m = (ds.subject == s) & np.isin(ds.session, EST_SESSIONS)
        te = (ds.subject == s) & np.isin(ds.session, TEST_SESSIONS)
        ie, it = (torch.as_tensor(np.flatnonzero(m), device=device) for m in (est_m, te))
        y_te = ds.y[te]

        # expert pool
        pools = [others] + [sorted(rng.choice(others, size=K_NEIGHBOURS, replace=False).tolist())
                            for _ in range(args.n_bagged)]
        experts = []
        for j, pool in enumerate(pools):
            val = sorted(rng.choice(pool, size=N_VAL, replace=False).tolist())
            model, X = fit_eegnet(ds, [o for o in pool if o not in val], val, tcfg, cfg["model"], device,
                                  args.seed + 100 * j)
            Xe, Xt = X[ie].clone(), X[it].clone()     # keep only the target's trials (each expert normalises
            del X                                      # differently); the full ~0.4 GB copy is freed at once
            if device.type == "cuda":
                torch.cuda.empty_cache()
            p13, p46 = predict_prob(model, Xe), predict_prob(model, Xt)
            experts.append({"model": model, "Xe": Xe, "Xt": Xt, "p46": p46, "pool": pool,
                            "cons": consistency(p13, ds.group[est_m], ds.session[est_m]),
                            "acc46": float(((p46 > 0.5) == y_te).mean())})
        cons = np.array([e["cons"] for e in experts])
        order = np.argsort(-cons, kind="stable")
        w = np.exp((cons - cons.max()) / SOFT_TAU)
        w /= w.sum()

        def rapl(e):
            m = adapt(AdaptView(e["model"]), RAPL[0], e["Xe"], ds.group[est_m], None, {**ADAPT_CFG, **RAPL[1]},
                      args.seed)
            with torch.no_grad():
                return torch.cat([torch.softmax(m(e["Xt"][i:i + 2048])[0], 1)[:, 1]
                                  for i in range(0, len(e["Xt"]), 2048)]).cpu().numpy()

        P = np.stack([e["p46"] for e in experts])
        probs = {
            "rcr_full": P[0],
            "rcr_random": P[rng.integers(len(experts))],
            "rcr_uniform": P.mean(0),
            "rcr_top1": P[order[0]],
            "rcr_top3": P[order[:3]].mean(0),
            "rcr_soft": (w[:, None] * P).sum(0),
            "rcr_oracle": P[int(np.argmax([e["acc46"] for e in experts]))],
            "rcr_full_rapl": rapl(experts[0]),
            "rcr_top1_rapl": rapl(experts[order[0]]),
            "rcr_top3_rapl": np.mean([rapl(experts[k]) for k in order[:3]], axis=0),
        }
        info = {"cons": cons.tolist(), "selected_top1": int(order[0]), "weights_soft": w.round(4).tolist()}
        accs = {name: save(results, name, args.seed, s, ds, te, p, info) for name, p in probs.items()}
        (exp_dir / f"sub{s:02d}.json").write_text(json.dumps(
            {"subject": s, "experts": [{"index": j, "n_subjects": len(e["pool"]), "pool": e["pool"],
                                        "cons": e["cons"], "acc46": e["acc46"]} for j, e in enumerate(experts)],
             "selected_top1": int(order[0]), "accuracy": accs}, indent=2))
        print(f"Sub{s:02d}: top1 = expert {order[0]} (cons {cons[order[0]]:.3f}) | "
              + " ".join(f"{k[4:]} {100 * v:.2f}" for k, v in accs.items()), flush=True)


if __name__ == "__main__":
    main()
