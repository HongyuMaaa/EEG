"""Hyperparameter sweep for a method: every combination of a grid of config overrides, run on a subset of folds.

Usage:
    python scripts/run_sweep.py --name weights --method red \\
        --grid "loss.lambda_critic=[0.5, 1, 2]" "loss.lambda_n2n=[0.3, 1, 3]" --workers 2 --device cuda
    python scripts/run_sweep.py --name tau --method red --base-from weights \\
        --grid "loss.tau=[1, 2, 4]" --workers 2 --device cuda

Each combination is run with scripts/run_baseline.py --set ... --tag sw-<name>-<values>, so its results go to
results/<method>@sw-<name>-<values>/ (resumable, like any run). Default fold subset: within protocol, all 28
subjects, test sessions 1 and 4 (validation sessions 2 and 5) = 56 folds per combination.

Selection must use validation accuracy only: python scripts/select_config.py --method red --sweep <name>
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ABBREV = {"lambda_critic": "lc", "lambda_n2n": "ln", "lambda_kd": "lk", "beta_lateral": "bl", "tau": "tau",
          "k_set": "k", "lr": "lr", "dropout": "do", "val_k": "vk"}


def value_tag(v) -> str:
    if isinstance(v, list):
        return "".join(str(x) for x in v)
    return str(v)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="sweep name (letters/digits), part of every tag")
    ap.add_argument("--method", default="red")
    ap.add_argument("--grid", nargs="+", required=True, metavar='"KEY=[v1, v2, ...]"')
    ap.add_argument("--base", nargs="*", default=[], metavar="KEY=VALUE", help="overrides applied to every combination")
    ap.add_argument("--base-from", metavar="SWEEP", help="start from the configuration selected (by validation "
                    "accuracy) in an earlier sweep of the same method; --base items are added after it")
    ap.add_argument("--protocol", default="within")
    ap.add_argument("--sessions", type=int, nargs="+", default=[1, 4], help="test sessions of the fold subset")
    ap.add_argument("--subjects", type=int, nargs="*", help="default: all")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--workers", type=int, default=1, help="combinations trained in parallel (2-3 fit an RTX 3060)")
    ap.add_argument("--max-epochs", type=int, help="forwarded to run_baseline.py (smoke tests only)")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--checkpoint-dir", default="checkpoints")
    args = ap.parse_args()

    if args.base_from:
        sys.path.insert(0, str(ROOT))
        from aved.selection import selected_overrides
        inherited = selected_overrides(ROOT / args.results_dir, args.method, args.base_from, args.protocol)
        print(f"base from sweep {args.base_from!r}: {' '.join(inherited)}")
        grid_keys = {g.partition("=")[0] for g in args.grid}
        args.base = [s for s in inherited if s.partition("=")[0] not in grid_keys] + list(args.base)

    keys, values = [], []
    for g in args.grid:
        k, _, v = g.partition("=")
        vals = yaml.safe_load(v)
        if not isinstance(vals, list):
            sys.exit(f"--grid {g!r}: value must be a YAML list")
        keys.append(k)
        values.append(vals)

    jobs = []
    for combo in itertools.product(*values):
        sets = list(args.base) + [f"{k}={json.dumps(v)}" for k, v in zip(keys, combo)]
        tag = "sw-" + args.name + "-" + "_".join(
            f"{ABBREV.get(k.split('.')[-1], k.split('.')[-1])}{value_tag(v)}" for k, v in zip(keys, combo))
        cmd = [sys.executable, "-u", str(ROOT / "scripts/run_baseline.py"), "--method", args.method,
               "--protocol", args.protocol, "--seed", str(args.seed), "--device", args.device,
               "--sessions", *map(str, args.sessions), "--tag", tag, "--set", *sets]
        if args.subjects:
            cmd += ["--subjects", *map(str, args.subjects)]
        if args.max_epochs:
            cmd += ["--max-epochs", str(args.max_epochs)]
        cmd += ["--results-dir", args.results_dir, "--checkpoint-dir", args.checkpoint_dir]
        jobs.append((tag, cmd))

    (ROOT / "logs").mkdir(exist_ok=True)
    print(f"sweep {args.name}: {len(jobs)} combinations, {args.workers} in parallel")
    for tag, _ in jobs:
        print("  ", tag)

    def run(job):
        tag, cmd = job
        log = ROOT / "logs" / f"{args.method}@{tag}_{args.protocol}_seed{args.seed}.log"
        t0 = time.time()
        env = dict(os.environ)
        env.setdefault("OMP_NUM_THREADS", str(max(1, (os.cpu_count() or 1) // args.workers)))  # no CPU oversubscription
        with open(log, "a", encoding="utf-8") as fh:
            rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, env=env)
        print(f"[{'ok' if rc == 0 else 'FAILED'}] {tag} ({(time.time() - t0) / 60:.1f} min, log {log.name})", flush=True)
        return rc

    # The first combination runs alone: it trains (and caches) the fold teachers that combinations sharing the
    # teacher settings then reuse, instead of several workers training the same teacher at once.
    codes = [run(jobs[0])]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        codes += list(pool.map(run, jobs[1:]))
    if any(codes):
        sys.exit("some combinations failed; see logs/")
    print(f"done. Select with: python scripts/select_config.py --method {args.method} --sweep {args.name}"
          + (f" --results-dir {args.results_dir}" if args.results_dir != "results" else ""))


if __name__ == "__main__":
    main()
