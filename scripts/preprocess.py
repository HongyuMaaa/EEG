"""Run the preprocessing pipeline over all subjects and sessions.

Usage:
    python scripts/preprocess.py [--config configs/preprocess.yaml] [--subjects 1 2 ...]

Outputs (in cfg.output_dir):
    SubXX.npz            trials, labels and per-trial metadata for one subject
    params.json          the exact configuration and environment used
    trial_counts.csv     trial counts per EDF file
    bad_channels.csv     interpolated channels per EDF file
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from pathlib import Path

import mne
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aved.config import load_config  # noqa: E402
from aved.events import parse_events, read_session_info  # noqa: E402
from aved.preprocess import preprocess_session  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/preprocess.yaml")
    ap.add_argument("--subjects", type=int, nargs="*", default=list(range(1, 29)))
    args = ap.parse_args()

    cfg = load_config(args.config)
    data_dir, out_dir = Path(cfg.data_dir), Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    session_info = read_session_info(data_dir / "Session_INFO.txt")

    count_rows, bad_rows = [], []
    taps = None
    for s in args.subjects:
        sub = f"Sub{s:02d}"
        parts = {k: [] for k in ("X", "y", "trigger", "session", "block", "char_pos", "char", "rep",
                                 "bit_pos", "onset_sample", "ptp", "artifact")}
        ch_names = None
        for sess in range(1, 7):
            edf = data_dir / sub / f"session_{sess:02d}.edf"
            block, chars = session_info[sess]
            ev = parse_events(data_dir / sub / f"session_{sess:02d}_events.edf", expected_chars=chars)
            res = preprocess_session(edf, ev, cfg)
            assert res.in_bounds.all(), f"{edf}: {np.sum(~res.in_bounds)} trials out of bounds"
            ch_names, taps = res.ch_names, res.filter_taps
            n = len(ev.labels)
            parts["X"].append(res.X)
            parts["y"].append(ev.labels)
            parts["trigger"].append(ev.triggers)
            parts["session"].append(np.full(n, sess))
            parts["block"].append(np.full(n, block))
            parts["char_pos"].append(ev.char_pos)
            parts["char"].append(ev.chars)
            parts["rep"].append(ev.rep)
            parts["bit_pos"].append(ev.bit_pos)
            parts["onset_sample"].append(ev.onsets)
            parts["ptp"].append(res.ptp)
            parts["artifact"].append(res.artifact)
            count_rows.append({
                "subject": sub, "session": sess, "edf_file": f"{sub}/session_{sess:02d}.edf", "block": block,
                "n_trials": n, "n_left_right": int(np.sum(ev.labels == 0)),
                "n_right_left": int(np.sum(ev.labels == 1)), "n_in_bounds": int(res.in_bounds.sum()),
                "n_artifact_flagged": int(res.artifact.sum()),
                "n_clean": int(np.sum(res.in_bounds & ~res.artifact)),
                "duration_s": round(res.n_samples_native / cfg.native_sfreq, 1),
            })
            bad_rows.append({"subject": sub, "session": sess, "bad_channels": " ".join(res.bad_channels)})
            print(f"{sub} session {sess}: {n} trials, {int(res.artifact.sum())} flagged, bad={res.bad_channels}",
                  flush=True)

        arrays = {k: np.concatenate(v) for k, v in parts.items()}
        np.savez_compressed(
            out_dir / f"{sub}.npz", **arrays, ch_names=np.array(ch_names), sfreq=cfg.target_sfreq,
            times=cfg.epoch.tmin + np.arange(cfg.n_times) / cfg.target_sfreq,
        )

    params = {
        "config": cfg.to_dict(), "config_fingerprint": cfg.fingerprint(),
        "derived": {"decimation_factor": cfg.decim, "epoch_window_native_samples": cfg.epoch_offsets_native,
                    "n_times": cfg.n_times, "fir_taps_at_native_sfreq": taps},
        "label_coding": {"0": "left->right (trigger 1, code '0')", "1": "right->left (trigger 2, code '1')"},
        "environment": {"python": platform.python_version(), "mne": mne.__version__, "numpy": np.__version__},
    }
    (out_dir / "params.json").write_text(json.dumps(params, indent=2))
    for name, rows in (("trial_counts.csv", count_rows), ("bad_channels.csv", bad_rows)):
        with open(out_dir / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"done; outputs in {out_dir} (config {cfg.fingerprint()})")


if __name__ == "__main__":
    main()
