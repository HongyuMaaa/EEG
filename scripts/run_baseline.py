"""Train and evaluate a baseline on one evaluation protocol, saving models and results.

Usage examples:
    python scripts/run_baseline.py --method eegnet --protocol within --device cuda
    python scripts/run_baseline.py --method dcpm   --protocol loso
    python scripts/run_baseline.py --method eegnet --protocol within --subjects 1 2 --sessions 1 --max-epochs 5   # smoke test

Methods:   eegnet | dcpm (with context templates, as in the paper) | dcpm_plain (without)
Protocols: within | pooled | loso   (see aved/data.py)

Outputs (finished folds are skipped on re-run, so an interrupted run can simply be restarted):
    results/<method>/<protocol>/seed<seed>/
        run_info.json          configuration, preprocessing fingerprint, git commit, environment
        folds/<fold>.json      per-fold info and accuracy per test subject
        predictions/<fold>.csv per-trial labels, predictions and scores
        history/<fold>.csv     EEGNet training curves
        subject_results.csv    accuracy per test subject (and test session), rebuilt after every fold
    checkpoints/<method>/<protocol>/seed<seed>/<fold>.pt   trained model (torch.save; DCPM is pickled)
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aved.config import load_config  # noqa: E402
from aved.data import PROTOCOLS, SESSIONS, SUBJECTS, fold_subjects, load_dataset, make_folds  # noqa: E402
from aved.train import resolve_device, train_dcpm, train_eegnet  # noqa: E402

METHODS = ("eegnet", "dcpm", "dcpm_plain")


def git_commit() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.call(["git", "diff", "--quiet", "--", "aved", "scripts", "configs"], cwd=ROOT) != 0
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", choices=METHODS, required=True)
    ap.add_argument("--protocol", choices=PROTOCOLS, required=True)
    ap.add_argument("--subjects", type=int, nargs="*", default=list(SUBJECTS),
                    help="test subjects to run (within, loso)")
    ap.add_argument("--sessions", type=int, nargs="*", default=list(SESSIONS),
                    help="test sessions to run (within, pooled)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto", help="auto | cpu | cuda | cuda:0 ... (EEGNet only)")
    ap.add_argument("--max-epochs", type=int, help="override max_epochs (smoke tests)")
    ap.add_argument("--preprocess-config", default="configs/preprocess.yaml")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--checkpoint-dir", default="checkpoints")
    ap.add_argument("--overwrite", action="store_true", help="re-run folds that already have results")
    args = ap.parse_args()

    pre_cfg = load_config(ROOT / args.preprocess_config)
    data_dir = ROOT / pre_cfg.output_dir
    params_file = data_dir / "params.json"
    if not params_file.exists():
        sys.exit(f"{params_file} not found: run `python scripts/preprocess.py` first")
    data_fp = json.loads(params_file.read_text())["config_fingerprint"]
    if data_fp != pre_cfg.fingerprint():
        sys.exit(f"preprocessed data (config {data_fp}) do not match {args.preprocess_config} "
                 f"({pre_cfg.fingerprint()}): re-run `python scripts/preprocess.py`")

    if args.method == "eegnet":
        cfg = yaml.safe_load((ROOT / "configs/eegnet.yaml").read_text())
        method_cfg = {"model": cfg["model"], "training": dict(cfg["training"][args.protocol])}
        if args.max_epochs:
            method_cfg["training"]["max_epochs"] = args.max_epochs
        device = resolve_device(args.device)
    else:
        method_cfg = yaml.safe_load((ROOT / "configs/dcpm.yaml").read_text())
        method_cfg["context"] = args.method == "dcpm"
        device = torch.device("cpu")

    run_dir = ROOT / args.results_dir / args.method / args.protocol / f"seed{args.seed}"
    ckpt_dir = ROOT / args.checkpoint_dir / args.method / args.protocol / f"seed{args.seed}"
    for d in (run_dir / "folds", run_dir / "predictions", run_dir / "history", ckpt_dir):
        d.mkdir(parents=True, exist_ok=True)

    run_info = {
        "method": args.method, "protocol": args.protocol, "seed": args.seed, "method_config": method_cfg,
        "preprocessing_fingerprint": data_fp, "preprocessing_config": pre_cfg.to_dict(),
        "git_commit": git_commit(), "device": str(device),
        "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
                        "platform": platform.platform()},
        "max_epochs_override": args.max_epochs,
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (run_dir / "run_info.json").write_text(json.dumps(run_info, indent=2))

    folds = make_folds(args.protocol, args.subjects, args.sessions)
    todo = [f for f in folds if args.overwrite or not (run_dir / "folds" / f"{f.name}.json").exists()]
    print(f"{args.method} / {args.protocol} / seed {args.seed} on {device}: "
          f"{len(folds)} folds selected, {len(folds) - len(todo)} already done, {len(todo)} to run")

    cache: dict[tuple, object] = {}
    for i, fold in enumerate(todo, 1):
        subjects = fold_subjects(fold)
        if subjects not in cache:
            cache.clear()
            cache[subjects] = load_dataset(data_dir, subjects)
        ds = cache[subjects]
        print(f"[{i}/{len(todo)}] fold {fold.name}", flush=True)
        out = (train_eegnet(fold, ds, method_cfg["model"], method_cfg["training"], device, args.seed)
               if args.method == "eegnet" else train_dcpm(fold, ds, method_cfg))
        out["info"].update(device=str(device), git_commit=run_info["git_commit"])
        save_fold(fold, ds, out, run_dir, ckpt_dir)
        write_subject_results(run_dir)
    write_subject_results(run_dir)
    print(f"done -> {run_dir}")


def save_fold(fold, ds, out, run_dir: Path, ckpt_dir: Path) -> None:
    te = out["test_mask"]
    pred = pd.DataFrame({
        "subject": ds.subject[te], "session": ds.session[te], "trial": ds.trial[te],
        "y": ds.y[te], "pred": out["pred"], "score": np.round(out["score"], 6),
    })
    pred.to_csv(run_dir / "predictions" / f"{fold.name}.csv", index=False)
    if out["history"]:
        pd.DataFrame(out["history"]).to_csv(run_dir / "history" / f"{fold.name}.csv", index=False)
    torch.save(out["checkpoint"], ckpt_dir / f"{fold.name}.pt")

    per_subject = {
        int(s): {"accuracy": float((g.y == g.pred).mean()), "n_test": int(len(g))}
        for s, g in pred.groupby("subject")
    }
    acc = float((pred.y == pred.pred).mean())
    record = {"fold": fold.name, "test_session": fold.test_session, "val_subjects": list(fold.val_subjects),
              "val_session": fold.val_session, "train_sessions": list(fold.train_sessions),
              "accuracy": acc, "per_subject": per_subject, **out["info"]}
    (run_dir / "folds" / f"{fold.name}.json").write_text(json.dumps(record, indent=2))
    print(f"  test accuracy {acc:.4f} (n={len(pred)})", flush=True)


def write_subject_results(run_dir: Path) -> None:
    rows = []
    for f in sorted((run_dir / "folds").glob("*.json")):
        rec = json.loads(f.read_text())
        for s, r in rec["per_subject"].items():
            rows.append({"fold": rec["fold"], "subject": int(s), "test_session": rec["test_session"],
                         "accuracy": r["accuracy"], "n_test": r["n_test"]})
    if rows:
        pd.DataFrame(rows).sort_values(["subject", "test_session"], na_position="first").to_csv(
            run_dir / "subject_results.csv", index=False)


if __name__ == "__main__":
    main()
