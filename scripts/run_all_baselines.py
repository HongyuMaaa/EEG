"""Run every baseline on every protocol, then summarise. Cross-platform (Windows / Linux / macOS).

Usage:
    python scripts/run_all_baselines.py --device cuda [--seeds 0] [--methods eegnet dcpm dcpm_plain]
                                        [--protocols within pooled loso]

Each run resumes where it stopped (finished folds are skipped), so this script can be re-launched
after an interruption. Console output of each run is also written to logs/<method>_<protocol>_seed<k>.log.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="auto")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--methods", nargs="+", default=["dcpm", "dcpm_plain", "eegnet"])
    ap.add_argument("--protocols", nargs="+", default=["within", "pooled", "loso"])
    args = ap.parse_args()

    (ROOT / "logs").mkdir(exist_ok=True)
    for seed in args.seeds:
        for method in args.methods:
            if method != "eegnet" and seed != args.seeds[0]:
                continue                          # DCPM is deterministic: one seed is enough
            for protocol in args.protocols:
                cmd = [sys.executable, "-u", str(ROOT / "scripts/run_baseline.py"), "--method", method,
                       "--protocol", protocol, "--seed", str(seed), "--device", args.device]
                log = ROOT / "logs" / f"{method}_{protocol}_seed{seed}.log"
                print(f"\n=== {method} / {protocol} / seed {seed}  (log: {log.relative_to(ROOT)})", flush=True)
                t0 = time.time()
                with open(log, "a", encoding="utf-8") as fh:
                    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in proc.stdout:
                        print(line, end="", flush=True)
                        fh.write(line)
                    if proc.wait() != 0:
                        sys.exit(f"run failed: {' '.join(cmd)}")
                print(f"=== finished in {(time.time() - t0) / 60:.1f} min", flush=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/summarize_results.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
