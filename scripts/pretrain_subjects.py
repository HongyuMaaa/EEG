"""Chapter 1, direction 4: cross-subject pretraining for within-subject fine-tuning.

For every target subject s: one EEGNet trained on the other 27 subjects. Early stopping uses the 3 subjects that
follow s, as in the LOSO protocol, so 24 are used for training. The target subject is never seen.
Every subject is z-scored per channel with its own statistics. The within-subject fine-tuning normalises the
target with the statistics of its training sessions, so the pretrained model sees data on the same scale.
Settings: configs/eegnet.yaml, training.loso.

Output:
    checkpoints/pretrain/seed<k>/sub<XX>.pt
        EEGNet state_dict + info; loaded by `run_baseline.py --init pretrain`.
    results/pretrain/seed<k>/sub<XX>.json
        Validation accuracy and zero-shot accuracy on the target (diagnostic only).

Usage:
    python scripts/pretrain_subjects.py --device cuda --seed 0
    python scripts/pretrain_subjects.py --device cpu --subjects 2 --max-epochs 1 --results-dir results_smoke   # smoke
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aved.data import SUBJECTS, load_dataset, make_folds  # noqa: E402
from aved.train import VRAM_HELP, limit_gpu_memory, resolve_device, train_eegnet  # noqa: E402


def zscore_subjects(ds):
    X = np.empty_like(ds.X)
    for s in np.unique(ds.subject):
        m = ds.subject == s
        mu, sd = ds.X[m].mean(axis=(0, 2)), ds.X[m].std(axis=(0, 2))
        X[m] = (ds.X[m] - mu[:, None]) / sd[:, None]
    return dataclasses.replace(ds, X=X)


def pretrain_path(checkpoint_dir: Path, seed: int, subject: int) -> Path:
    return checkpoint_dir / "pretrain" / f"seed{seed}" / f"sub{subject:02d}.pt"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subjects", type=int, nargs="*", default=list(SUBJECTS), help="target subjects")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--max-vram-gb", type=float, help=VRAM_HELP)
    ap.add_argument("--max-epochs", type=int)
    ap.add_argument("--checkpoint-dir", default="checkpoints")
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    device = resolve_device(args.device)
    limit_gpu_memory(device, args.max_vram_gb)
    cfg = yaml.safe_load((ROOT / "configs/eegnet.yaml").read_text())
    tcfg = dict(cfg["training"]["loso"])
    if args.max_epochs:
        tcfg["max_epochs"] = args.max_epochs
    ds = zscore_subjects(load_dataset(ROOT / "derivatives/preprocessed", SUBJECTS))
    out_dir = ROOT / args.results_dir / "pretrain" / f"seed{args.seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for fold in make_folds("loso", args.subjects):
        s = fold.test_subjects[0]
        path = pretrain_path(ROOT / args.checkpoint_dir, args.seed, s)
        if path.exists():
            continue
        print(f"Sub{s:02d}: pretraining on {len(fold.train_subjects)} subjects (val {fold.val_subjects})", flush=True)
        out = train_eegnet(fold, ds, cfg["model"], tcfg, device, args.seed, log=lambda *a, **k: None)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        torch.save({"state_dict": out["checkpoint"]["state_dict"], "model_cfg": cfg["model"], "train_cfg": tcfg,
                    "target_subject": s, "train_subjects": fold.train_subjects, "val_subjects": fold.val_subjects,
                    "info": out["info"]}, tmp)
        tmp.replace(path)
        zero_shot = float((out["pred"] == ds.y[out["test_mask"]]).mean())
        (out_dir / f"sub{s:02d}.json").write_text(json.dumps(
            {"subject": s, "seed": args.seed, "zero_shot_acc": zero_shot, **out["info"]}, indent=2))
        print(f"  val_acc {out['info']['val_acc']:.3f}  zero-shot {zero_shot:.3f}  "
              f"best epoch {out['info']['best_epoch']}", flush=True)


if __name__ == "__main__":
    main()
