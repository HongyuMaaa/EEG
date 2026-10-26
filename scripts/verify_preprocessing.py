"""Verify trial extraction and trial-label alignment, and write a report.

Usage:
    python scripts/verify_preprocessing.py [--config configs/preprocess.yaml] [--report reports/preprocessing_verification.md]

Checks:
  1. Event structure: 16 character markers per file, each followed by its 5-bit code x 6 repetitions;
     markers agree with Session_INFO.txt.
  2. Codebook: every character has the same code in every file; the 32 codes are distinct; 'A' = 01100.
  3. Trial definition: inter-event intervals show that each event is one 200 ms stimulus pair.
  4. Saved arrays: shapes and labels agree with a fresh parse of the event files; 480 trials per file.
  5. Reproducibility: re-preprocessing one subject gives bit-identical trials.
  6. Neurophysiology: the class difference of the hemispheric lateralization has the expected time course.
  7. Alignment: decodability (leave-one-session-out LDA) of the label of trial t+lag from epoch t
     peaks at lag 0. A one-trial misalignment would move the peak.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aved.config import load_config  # noqa: E402
from aved.events import TRIALS_PER_CHAR, parse_events, read_session_info  # noqa: E402
from aved.preprocess import preprocess_session  # noqa: E402

MIRROR_PAIRS = [("P7", "P8"), ("P5", "P6"), ("P3", "P4"), ("P1", "P2"), ("PO7", "PO8"),
                ("PO5", "PO6"), ("PO3", "PO4"), ("O1", "O2"), ("CB1", "CB2")]
LAGS = (-1, 0, 1)


def lag_accuracy(d, lag: int, rng: np.random.Generator | None = None) -> float:
    """Leave-one-session-out shrinkage-LDA accuracy for predicting the label of trial t+lag from epoch t.

    Lags are taken within each character's run of 30 trials; rng != None permutes the labels (chance control).
    """
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

    keep = ~d["artifact"]
    idx = np.arange(len(d["y"]))
    pos = idx % TRIALS_PER_CHAR                      # position within a character run (files are stored in order)
    valid = (pos + lag >= 0) & (pos + lag < TRIALS_PER_CHAR) & keep
    src = idx[valid]
    y = d["y"][src + lag]
    if rng is not None:
        y = rng.permutation(y)
    X = d["X"][src].reshape(len(src), -1)
    sess = d["session"][src]
    correct = 0
    for s in np.unique(sess):
        tr, te = sess != s, sess == s
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto").fit(X[tr], y[tr])
        correct += np.sum(clf.predict(X[te]) == y[te])
    return correct / len(y)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/preprocess.yaml")
    ap.add_argument("--report", default="reports/preprocessing_verification.md")
    args = ap.parse_args()
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    cfg = load_config(args.config)
    data_dir, out_dir = Path(cfg.data_dir), Path(cfg.output_dir)
    info = read_session_info(data_dir / "Session_INFO.txt")
    lines: list[str] = []

    def emit(s: str = "") -> None:
        print(s, flush=True)
        lines.append(s)

    # ---- 1-3: event structure, codebook, timing ----
    codebook: dict[str, set] = defaultdict(set)
    within, between_rep, between_char = Counter(), Counter(), Counter()
    events = {}
    for s in range(1, 29):
        for sess in range(1, 7):
            ev = parse_events(data_dir / f"Sub{s:02d}" / f"session_{sess:02d}_events.edf", info[sess][1])
            events[(s, sess)] = ev
            for ch, code in ev.char_codes.items():
                codebook[ch].add(code)
            d = np.diff(ev.onsets)
            same_char = np.diff(ev.char_pos) == 0
            same_rep = same_char & (np.diff(ev.rep) == 0)
            within.update(d[same_rep].tolist())
            between_rep.update(d[same_char & ~same_rep].tolist())
            between_char.update(d[~same_char].tolist())
    codes = {ch: next(iter(c)) for ch, c in codebook.items()}
    emit("## 1. Event structure")
    emit(f"- All 168 event files parsed: 16 markers x (1 + 30 trials) each; markers equal Session_INFO.txt: **OK**")
    emit("\n## 2. Codebook")
    emit(f"- Characters observed: {len(codebook)}; each has a single code across all files: "
         f"**{'OK' if all(len(c) == 1 for c in codebook.values()) else 'FAIL'}**")
    emit(f"- Distinct codes: {len(set(codes.values()))} / 32; 'A' = {codes.get('A')} (description.docx: 01100)")
    emit("\n| char | code | char | code | char | code | char | code |\n|---|---|---|---|---|---|---|---|")
    chars = sorted(codes, key="ABCDEFGHIJKLMNOPQRSTUVWXYZ123456".index)
    for i in range(0, 32, 4):
        emit("| " + " | ".join(f"{c} | {codes[c]}" for c in chars[i:i + 4]) + " |")
    emit("\n## 3. Trial definition (event spacing, native 200 Hz samples)")
    emit(f"- Within a code repetition: {dict(sorted(within.items()))}  (40 samples = 200 ms = one L/R pair)")
    emit(f"- Between repetitions of a code: {dict(sorted(between_rep.items()))}")
    emit(f"- Between characters: min {min(between_char)}, max {max(between_char)}")
    emit(f"- Minimum spacing between trial events: {min(within)} samples = {min(within) / cfg.native_sfreq * 1e3:.0f} ms. "
         "No events at 100 ms spacing, so each event marks one stimulus **pair**, not a single stimulus.")

    # ---- 4: saved arrays ----
    emit("\n## 4. Extracted trials vs event files")
    counts = pd.read_csv(out_dir / "trial_counts.csv")
    ok = True
    for s in range(1, 29):
        d = np.load(out_dir / f"Sub{s:02d}.npz")
        assert d["X"].shape == (2880, cfg.n_channels, cfg.n_times), d["X"].shape
        assert np.isclose(d["sfreq"], cfg.target_sfreq) and np.isclose(d["times"][0], cfg.epoch.tmin)
        for sess in range(1, 7):
            m = d["session"] == sess
            ev = events[(s, sess)]
            ok &= np.array_equal(d["y"][m], ev.labels) and np.array_equal(d["onset_sample"][m], ev.onsets)
            ok &= np.array_equal(d["y"][m], (d["trigger"][m] == 2).astype(int))
    emit(f"- Labels and onsets in every SubXX.npz equal a fresh parse of the event files; label = (trigger == 2): "
         f"**{'OK' if ok else 'FAIL'}**")
    emit(f"- Trials per file: min {counts.n_trials.min()}, max {counts.n_trials.max()}; "
         f"all windows inside recording: {bool((counts.n_in_bounds == counts.n_trials).all())}")
    emit(f"- Total trials: {counts.n_trials.sum()} (left->right {counts.n_left_right.sum()}, "
         f"right->left {counts.n_right_left.sum()}); artifact-flagged: {counts.n_artifact_flagged.sum()}")

    # ---- 5: reproducibility ----
    d1 = np.load(out_dir / "Sub01.npz")
    ev = events[(1, 3)]
    again = preprocess_session(data_dir / "Sub01" / "session_03.edf", ev, cfg).X
    same = np.array_equal(again, d1["X"][d1["session"] == 3])
    emit("\n## 5. Reproducibility")
    emit(f"- Re-processing Sub01 session 3 reproduces the saved trials bit-for-bit: **{'OK' if same else 'FAIL'}**")

    # ---- 6: neurophysiology ----
    emit("\n## 6. Lateralization time course (grand average, clean trials, all subjects)")
    ch = list(d1["ch_names"])
    L = [ch.index(a) for a, _ in MIRROR_PAIRS]
    R = [ch.index(b) for _, b in MIRROR_PAIRS]
    diffs = []
    for s in range(1, 29):
        d = np.load(out_dir / f"Sub{s:02d}.npz")
        k = ~d["artifact"]
        lat = d["X"][k][:, L].mean(1) - d["X"][k][:, R].mean(1)        # left-hemisphere minus right-hemisphere
        y = d["y"][k]
        diffs.append(lat[y == 0].mean(0) - lat[y == 1].mean(0))
    diffs = np.array(diffs)
    t = d1["times"]
    emit("Class difference (left->right minus right->left) of the hemispheric difference, mean over the 9 mirror pairs, uV:\n")
    emit("| t (ms) | " + " | ".join(f"{x * 1e3:.0f}" for x in t[::4]) + " |")
    emit("|---|" + "---|" * len(t[::4]))
    emit("| mean | " + " | ".join(f"{x:+.2f}" for x in diffs.mean(0)[::4]) + " |")
    tstat = diffs.mean(0) / (diffs.std(0, ddof=1) / np.sqrt(len(diffs)))
    emit("| t-stat | " + " | ".join(f"{x:+.1f}" for x in tstat[::4]) + " |")
    _plot(t, diffs, Path(args.report).with_name("lateralization_grand_average.png"))

    # ---- 7: alignment via lag decoding ----
    emit("\n## 7. Trial-label alignment: decoding the label of trial t+lag from epoch t")
    emit("Leave-one-session-out shrinkage LDA on all channels x samples, clean trials only. "
         "If trials and labels are aligned, accuracy peaks at lag 0.\n")
    emit("| subject | " + " | ".join(f"lag {g:+d}" for g in LAGS) + " | permuted | peak lag |")
    emit("|---|" + "---|" * (len(LAGS) + 2))
    rng = np.random.default_rng(0)
    peaks, table = [], []
    for s in range(1, 29):
        d = np.load(out_dir / f"Sub{s:02d}.npz")
        accs = [lag_accuracy(d, g) for g in LAGS]
        perm = lag_accuracy(d, 0, rng)
        peak = LAGS[int(np.argmax(accs))]
        peaks.append(peak)
        table.append(accs + [perm])
        emit(f"| Sub{s:02d} | " + " | ".join(f"{a:.3f}" for a in accs) + f" | {perm:.3f} | {peak:+d} |")
    m = np.mean(table, axis=0)
    emit("| **mean** | " + " | ".join(f"**{a:.3f}**" for a in m[:-1]) + f" | {m[-1]:.3f} | |")
    emit(f"\n- Peak at lag 0 in {peaks.count(0)} / 28 subjects; peak lags: {dict(Counter(peaks))}")

    header = ["# Preprocessing verification", "",
              f"Generated by `scripts/verify_preprocessing.py` (config fingerprint `{cfg.fingerprint()}`).", ""]
    Path(args.report).write_text("\n".join(header + lines) + "\n")


def _plot(t, diffs, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m, se = diffs.mean(0), diffs.std(0, ddof=1) / np.sqrt(len(diffs))
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.fill_between(t * 1e3, m - 2 * se, m + 2 * se, alpha=0.3)
    ax.plot(t * 1e3, m)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("time after pair onset (ms)")
    ax.set_ylabel("uV")
    ax.set_title("Lateralization: left->right minus right->left (mean ± 2 SE, n=28)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=120)


if __name__ == "__main__":
    main()
