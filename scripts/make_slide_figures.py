"""Figures for the mid-term defense (slide 4), computed from the preprocessed data.

Usage:
    python scripts/make_slide_figures.py [--data derivatives/preprocessed] [--out presentation/figures]

Signal used throughout: the hemispheric difference (left minus right channel) averaged over the
9 mirror pairs, clean trials only, as in scripts/verify_preprocessing.py section 6.

Outputs:
    slide4_snr.png          class averages and their difference vs. single trials (all subjects)
    slide4_variability.png  four example subjects + distributions of mirror correlation and peak latency
    slide4_stats.csv        per-subject statistics behind the figures
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

MIRROR_PAIRS = [("P7", "P8"), ("P5", "P6"), ("P3", "P4"), ("P1", "P2"), ("PO7", "PO8"),
                ("PO5", "PO6"), ("PO3", "PO4"), ("O1", "O2"), ("CB1", "CB2")]
PEAK_WINDOW_MS = (80, 300)
EXAMPLES = (18, 22, 17, 5)          # strong mirror lateralizer, early peak, inverted pattern, weak responder
C0, C1, GRAY = "#B00000", "#1F4E79", "#808080"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif"],
    "font.size": 11, "axes.titlesize": 11, "axes.labelsize": 11, "legend.fontsize": 9.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.8,
    "xtick.major.width": 0.8, "ytick.major.width": 0.8, "savefig.dpi": 300,
})


def load_subject(path: Path):
    d = np.load(path)
    ch = list(d["ch_names"])
    left = [ch.index(a) for a, _ in MIRROR_PAIRS]
    right = [ch.index(b) for _, b in MIRROR_PAIRS]
    keep = ~d["artifact"]
    hd = d["X"][keep][:, left] - d["X"][keep][:, right]          # trials x 9 pairs x time, uV
    return hd, d["y"][keep], d["times"] * 1e3


def subject_stats(hd, y, t):
    a0, a1 = hd[y == 0].mean(0), hd[y == 1].mean(0)
    # Mirror rule: mirroring a left->right trial gives a right->left trial, so the class-1
    # hemispheric difference should be the negative of the class-0 one (r = 1).
    r_mirror = np.corrcoef(a0.ravel(), -a1.ravel())[0, 1]
    diff = a0.mean(0) - a1.mean(0)
    w = (t >= PEAK_WINDOW_MS[0]) & (t <= PEAK_WINDOW_MS[1])
    i = np.argmax(np.abs(diff[w]))
    return {"r_mirror": r_mirror, "peak_ms": t[w][i], "peak_uv": diff[w][i],
            "lat0": a0.mean(0), "lat1": a1.mean(0), "diff": diff}


def fig_snr(subjects, t, out: Path, rng):
    """Main panel: single trials and class averages on one linear scale. Zoom panel: the averages magnified
    10x (also linear), linked to a box on the main panel."""
    from matplotlib.patches import ConnectionPatch, Rectangle

    lat0 = np.mean([s["lat0"] for s in subjects.values()], 0)
    lat1 = np.mean([s["lat1"] for s in subjects.values()], 0)
    diff = lat0 - lat1
    big, small = 15.0, 1.5

    fig = plt.figure(figsize=(6.1, 3.75))
    ax = fig.add_axes([0.10, 0.31, 0.40, 0.60])
    az = fig.add_axes([0.575, 0.31, 0.35, 0.60])

    # 40 random single trials drawn across all subjects
    for _ in range(40):
        hd, _, _ = subjects[rng.integers(1, 29)]["raw"]
        ax.plot(t, hd[rng.integers(len(hd))].mean(0), color=GRAY, lw=0.6, alpha=0.3, zorder=1)
    for a, lw in ((ax, 1.3), (az, 2.0)):
        a.plot(t, lat0, color=C0, lw=lw, zorder=3)
        a.plot(t, lat1, color=C1, lw=lw, zorder=3)
        a.plot(t, diff, color="black", lw=lw, ls="--", zorder=4)
        a.axhline(0, color="black", lw=0.5, zorder=2)
        a.set_xlim(t[0], t[-1])
        a.set_xticks([100, 200, 300])
        a.set_xlabel("Time after pair onset (ms)")
    ax.set_ylim(-big, big)
    az.set_ylim(-small, small)
    az.yaxis.tick_right()                 # keeps the left edge free for the zoom connectors
    ax.set_ylabel("Hemispheric difference (µV)")
    ax.set_title("All signals (±15 µV)", pad=4)
    az.set_title("Zoom ×10: averages (±1.5 µV)", pad=4)

    # Zoom box on the main panel, connected to the zoom panel
    ax.add_patch(Rectangle((t[0], -small), t[-1] - t[0], 2 * small, fill=False, ec="black", lw=0.9, zorder=5))
    for yv in (small, -small):
        fig.add_artist(ConnectionPatch(xyA=(t[-1], yv), coordsA=ax.transData, xyB=(t[0], yv), coordsB=az.transData,
                                       color="black", lw=0.7, ls=(0, (3, 2))))
    for sp in az.spines.values():
        sp.set_visible(True)
        sp.set_linewidth(0.9)

    # Peaks of the class difference
    for lo, hi in ((80, 150), (180, 240)):
        w = (t >= lo) & (t <= hi)
        k = np.argmax(np.abs(diff[w]))
        tp, vp = t[w][k], diff[w][k]
        az.annotate(f"{vp:+.2f} µV\n{tp:.0f} ms".replace("-", "−"), xy=(tp, vp), xytext=(tp + 28, vp * 1.12),
                    fontsize=9, ha="left", va="center", arrowprops=dict(arrowstyle="-", lw=0.6, color="black"))

    handles = [plt.Line2D([], [], color=GRAY, lw=0.9, alpha=0.7), plt.Line2D([], [], color=C0, lw=2),
               plt.Line2D([], [], color=C1, lw=2), plt.Line2D([], [], color="black", lw=2, ls="--")]
    fig.legend(handles, ["Single trials (n = 40, random)", "Class 0 average (left → right)",
                         "Class 1 average (right → left)", "Difference (0 − 1)"],
               loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False,
               handlelength=1.8, columnspacing=1.2)
    fig.savefig(out)
    plt.close(fig)


def fig_variability(subjects, t, out: Path):
    fig = plt.figure(figsize=(6.1, 3.75))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.42], hspace=0.62, wspace=0.22)
    axes = []
    for k, sid in enumerate(EXAMPLES):
        s = subjects[sid]
        ax = fig.add_subplot(gs[k // 2, k % 2], sharex=axes[0] if axes else None,
                             sharey=axes[0] if axes else None)
        axes.append(ax)
        ax.plot(t, s["lat0"], color=C0, lw=1.4)
        ax.plot(t, s["lat1"], color=C1, lw=1.4)
        ax.axvline(s["peak_ms"], color="black", lw=0.8, ls=":")
        ax.axhline(0, color="black", lw=0.4)
        ax.set_title(f"Sub{sid:02d}:  r = {s['r_mirror']:+.2f},  peak {s['peak_ms']:.0f} ms", pad=2)
        ax.tick_params(labelsize=9)
        if k % 2 == 0:
            ax.set_ylabel("µV", fontsize=10, labelpad=1)
        else:
            ax.tick_params(labelleft=False)
        if k < 2:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("Time after pair onset (ms)", fontsize=10, labelpad=1)
    axes[0].set_xlim(t[0], t[-1])
    axes[0].set_ylim(-3.2, 3.2)
    rng = np.random.default_rng(1)
    for k, (key, label, lim) in enumerate([("r_mirror", "Mirror-symmetry correlation r", (-1, 1)),
                                            ("peak_ms", "Peak latency (ms)", (PEAK_WINDOW_MS[0], PEAK_WINDOW_MS[1] + 10))]):
        ax = fig.add_subplot(gs[2, k])
        v = np.array([s[key] for s in subjects.values()])
        ids = np.array(list(subjects))
        jit = rng.uniform(-0.6, 0.6, len(v))
        ex = np.isin(ids, EXAMPLES)
        ax.scatter(v[~ex], jit[~ex], s=14, color=GRAY, alpha=0.75, lw=0, zorder=2)
        ax.scatter(v[ex], jit[ex], s=22, facecolor="none", edgecolor="black", lw=1.0, zorder=3)
        ax.set_xlim(*lim)
        ax.set_ylim(-1.2, 1.2)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.set_xlabel(f"{label} (28 subjects)", fontsize=10, labelpad=1)
        ax.tick_params(labelsize=9)
    handles = [plt.Line2D([], [], color=C0, lw=1.6), plt.Line2D([], [], color=C1, lw=1.6),
               plt.Line2D([], [], color="black", lw=0.8, ls=":"),
               plt.Line2D([], [], marker="o", ls="", mfc="none", mec="black", ms=5)]
    fig.legend(handles, ["Class 0 average", "Class 1 average", "Peak latency", "Example subject"],
               loc="upper center", ncol=4, frameon=False, fontsize=9.5, handlelength=1.6, columnspacing=1.0)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.86, bottom=0.12)
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="derivatives/preprocessed")
    ap.add_argument("--out", default="presentation/figures")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    subjects, t = {}, None
    for sid in range(1, 29):
        hd, y, t = load_subject(Path(args.data) / f"Sub{sid:02d}.npz")
        subjects[sid] = {**subject_stats(hd, y, t), "raw": (hd, y, t)}

    fig_snr(subjects, t, out / "slide4_snr.png", np.random.default_rng(args.seed))
    fig_variability(subjects, t, out / "slide4_variability.png")

    with open(out / "slide4_stats.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "r_mirror", "peak_ms", "peak_uv", "single_trial_sd_uv"])
        for sid, s in subjects.items():
            hd = s["raw"][0].mean(1)
            w.writerow([sid, f"{s['r_mirror']:.3f}", f"{s['peak_ms']:.0f}", f"{s['peak_uv']:.3f}", f"{hd.std():.3f}"])
    r = np.array([s["r_mirror"] for s in subjects.values()])
    p = np.array([s["peak_ms"] for s in subjects.values()])
    a = np.abs([s["peak_uv"] for s in subjects.values()])
    sd = np.array([s["raw"][0].mean(1).std() for s in subjects.values()])
    print(f"mirror r: {r.min():.2f} .. {r.max():.2f} (median {np.median(r):.2f})")
    print(f"peak latency: {p.min():.0f} .. {p.max():.0f} ms (median {np.median(p):.0f})")
    print(f"|peak class difference|: {a.min():.2f} .. {a.max():.2f} uV (median {np.median(a):.2f})")
    print(f"single-trial SD: {sd.min():.2f} .. {sd.max():.2f} uV (median {np.median(sd):.2f})")
    gd = np.mean([s["diff"] for s in subjects.values()], 0)
    print(f"grand-average difference: min {gd.min():.2f}, max {gd.max():.2f} uV")


if __name__ == "__main__":
    main()
