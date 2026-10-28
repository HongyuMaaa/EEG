"""Hyperparameter selection from sweep results, by validation accuracy only."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

CONFIG_DIR = Path(__file__).resolve().parents[1] / "configs"


def fold_table(run_dir: Path) -> pd.DataFrame:
    rows = []
    for f in run_dir.glob("seed*/folds/*.json"):
        r = json.loads(f.read_text())
        rows.append({"seed": int(f.parts[-3][4:]), "fold": r["fold"], "val_acc": r["val_acc"],
                     "test_acc": r["accuracy"], "val_session": r.get("val_session")})
    return pd.DataFrame(rows)


def sweep_table(root: Path, method: str, sweep: str, protocol: str = "within") -> tuple[pd.DataFrame, set]:
    """One row per configuration (mean val / test accuracy over the folds common to all configurations)."""
    runs = {p.name: fold_table(p / protocol) for p in sorted(Path(root).glob(f"{method}@sw-{sweep}-*"))}
    runs = {k: v for k, v in runs.items() if not v.empty}
    if not runs:
        raise SystemExit(f"no sweep results for {method}@sw-{sweep}-* in {root}")
    common = set.intersection(*(set(zip(v.seed, v.fold)) for v in runs.values()))
    rows = []
    for name, df in runs.items():
        d = df[[(s, f) in common for s, f in zip(df.seed, df.fold)]]
        rows.append({"configuration": name, "folds": len(d), "val_acc": d.val_acc.mean(), "test_acc": d.test_acc.mean(),
                     "overrides": json.loads(next((Path(root) / name / protocol).glob("seed*/run_info.json"))
                                             .read_text())["overrides"]})
    table = pd.DataFrame(rows)
    table["n_changed"] = [n_changed_from_defaults(o, protocol) for o in table.overrides]
    # highest validation accuracy; ties -> fewest settings changed from the defaults, then name
    table = table.sort_values(["val_acc", "n_changed", "configuration"], ascending=[False, True, True],
                              kind="stable").reset_index(drop=True)
    return table, common


def n_changed_from_defaults(overrides: list[str], protocol: str) -> int:
    """Number of overrides whose value differs from configs/red.yaml (training.* looked up per protocol)."""
    import yaml
    defaults = yaml.safe_load((CONFIG_DIR / "red.yaml").read_text())
    n = 0
    for item in overrides:
        key, _, raw = item.partition("=")
        node = defaults
        path = key.split(".")
        if path[0] == "training":
            path = ["training", protocol] + path[1:]
        for k in path:
            node = node.get(k) if isinstance(node, dict) else None
        n += node != yaml.safe_load(raw)
    return n


def selected_overrides(root: Path, method: str, sweep: str, protocol: str = "within") -> list[str]:
    """Overrides of the configuration with the highest mean validation accuracy."""
    table, common = sweep_table(root, method, sweep, protocol)
    if table.folds.nunique() != 1 or table.folds.iloc[0] == 0:
        raise SystemExit(f"sweep {sweep}: configurations do not share their folds; finish all runs first")
    return list(table.overrides.iloc[0])
