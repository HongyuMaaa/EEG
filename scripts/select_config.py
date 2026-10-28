"""Select the best configuration of a sweep by VALIDATION accuracy (test accuracy is shown, never used).

Usage:
    python scripts/select_config.py --method red --sweep weights [--protocol within] [--reference eegnet red]
                                    [--out results/sweep_weights.md]

For every configuration results/<method>@sw-<sweep>-*/ the script reports, over the folds common to all
configurations: mean validation accuracy (selection criterion), mean test accuracy, and the same for the
reference runs (e.g. eegnet, red with default settings) on the same folds.

Leakage note: in leave-one-session-out, the validation sessions of the sweep folds (default 2 and 5) are test
sessions of other folds. The final evaluation therefore also reports the "clean" folds whose test session was
never a validation session during selection: compare_methods.py --exclude-sessions 2 5.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aved.selection import fold_table, sweep_table  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="red")
    ap.add_argument("--sweep", required=True)
    ap.add_argument("--protocol", default="within")
    ap.add_argument("--reference", nargs="*", default=["eegnet", "red"])
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--out")
    args = ap.parse_args()
    root = ROOT / args.results_dir

    table, common = sweep_table(root, args.method, args.sweep, args.protocol)
    vs = sorted({int(f.split("test")[1]) % 6 + 1 for _, f in common})
    lines = [f"# Sweep `{args.sweep}` — {args.method}, protocol `{args.protocol}`", "",
             f"Folds common to all configurations: {len(common)} (validation sessions {vs}). "
             "**Selection criterion: mean validation accuracy.** Test accuracy is shown for information only.", "",
             "| configuration | folds | val acc (%) | test acc (%) | overrides |", "|---|---|---|---|---|"]
    for i, r in table.iterrows():
        mark = " ← selected" if i == 0 else ""
        lines.append(f"| {r.configuration}{mark} | {r.folds} | {100 * r.val_acc:.2f} | {100 * r.test_acc:.2f} "
                     f"| `{' '.join(r.overrides)}` |")
    for ref in args.reference:
        df = fold_table(root / ref / args.protocol)
        if df.empty:
            continue
        d = df[[(s, f) in common for s, f in zip(df.seed, df.fold)]]
        if len(d):
            lines.append(f"| *reference: {ref}* | {len(d)} | {100 * d.val_acc.mean():.2f} | {100 * d.test_acc.mean():.2f} | |")
    if table.folds.nunique() != 1:
        lines += ["", "**Warning:** configurations have different numbers of finished folds; finish all runs first."]
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
