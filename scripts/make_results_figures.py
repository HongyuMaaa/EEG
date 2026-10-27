"""Expected-results figures for the mid-term defense (RED and LR-MoE slides).

RED and LR-MoE have not been evaluated yet. These figures show how their results will be presented:

* MEASURED (solid bars / filled markers): baseline accuracies from results/summary_per_subject.csv,
  per-subject mirror correlations from the preprocessed data, and a linear Noise2Noise estimate
  (ridge regression from a single trial to the leave-one-out group average) fitted on real trials.
* ILLUSTRATIVE (hatched bars / open markers / panels tagged "Illustrative"): placeholder values for
  RED, its ablations and LR-MoE, chosen only to show the figure layout. Replace them with real
  results before any use beyond the mid-term defense.

Usage:
    python scripts/make_results_figures.py [--data derivatives/preprocessed] [--out presentation/figures]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_slide_figures import C0, C1, GRAY, MIRROR_PAIRS, load_subject, plt, subject_stats  # noqa: E402

RED_HATCH = dict(facecolor="white", edgecolor=C0, hatch="///", lw=1.2)
MEAS = dict(color="#7F7F7F", edgecolor="black", lw=0.8)
RECON_SUBJECT = 18


def tag(ax, text="Illustrative"):
    ax.text(0.98, 0.98, text, transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color="#595959",
            bbox=dict(boxstyle="square,pad=0.25", fc="#F2F2F2", ec="#A6A6A6", lw=0.6), zorder=10)


def per_subject(path: Path, method: str, protocol: str) -> dict[int, float]:
    out = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            if row["method"] == method and row["protocol"] == protocol and row["seed"] == "0":
                out[int(row["subject"])] = float(row["accuracy"]) * 100
    return out


def bars(ax, labels, values, errs, measured, ylim, ylabel=None):
    x = np.arange(len(labels))
    for i, (v, e, m) in enumerate(zip(values, errs, measured)):
        ax.bar(i, v, 0.62, **(MEAS if m else RED_HATCH), zorder=2)
        ax.errorbar(i, v, yerr=e, color="black", capsize=3, lw=0.8, zorder=3)
        ax.text(i, v + e + 0.6, f"{v:.1f}", ha="center", va="bottom", fontsize=9.5,
                color="black" if m else C0, fontweight="bold" if not m else "normal", zorder=4,
                bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none"))
    ax.set_xticks(x, labels, fontsize=9.5)
    ax.set_ylim(*ylim)
    ax.axhline(50, color="#A6A6A6", lw=0.6, ls=":")
    if ylabel:
        ax.set_ylabel(ylabel)


def linear_n2n(data: Path, sid: int):
    """Ridge regression x -> leave-one-out group average, leave-one-session-out. Returns R^2 per session
    (hemispheric-difference signal) and one example test trial."""
    d = np.load(data / f"Sub{sid:02d}.npz")
    ch = list(d["ch_names"])
    left = [ch.index(a) for a, _ in MIRROR_PAIRS]
    right = [ch.index(b) for _, b in MIRROR_PAIRS]
    k = ~d["artifact"]
    X, ses = d["X"][k], d["session"][k]
    key = ses * 10000 + d["char_pos"][k] * 10 + d["bit_pos"][k]      # same session, character, bit position
    _, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    S = np.zeros((cnt.size,) + X.shape[1:])
    np.add.at(S, inv, X)
    loo = (S[inv] - X) / np.maximum(cnt[inv] - 1, 1)[:, None, None]
    lat = lambda Z: Z[:, left].mean(1) - Z[:, right].mean(1)       # noqa: E731
    r2, r2_raw, example = [], [], None
    for test in range(1, 7):
        tr, te = ses != test, ses == test
        m = Ridge(alpha=1e4).fit(X[tr].reshape(tr.sum(), -1), loo[tr].reshape(tr.sum(), -1))
        pred = m.predict(X[te].reshape(te.sum(), -1)).reshape(-1, *X.shape[1:])
        a, p, x = lat(loo[te]), lat(pred), lat(X[te])
        r2.append(1 - ((p - a) ** 2).mean() / ((a - a.mean()) ** 2).mean())
        r2_raw.append(1 - ((x - a) ** 2).mean() / ((a - a.mean()) ** 2).mean())
        if test == 1:
            i = int(np.argmax(np.abs(a).max(1)))                       # trial with the clearest target
            example = (x[i], a[i], p[i])
    return np.array(r2), np.array(r2_raw), example, d["times"] * 1e3


def fig_red(res_csv: Path, data: Path, out: Path, rng):
    eeg = per_subject(res_csv, "eegnet", "within")
    dcpm = per_subject(res_csv, "dcpm", "within")
    subs = sorted(eeg)
    e = np.array([eeg[s] for s in subs])
    gain = 2.0 + 0.12 * (85 - e) + rng.normal(0, 1.0, e.size)        # illustrative: larger gain for weak subjects
    red = e + gain

    fig = plt.figure(figsize=(12.4, 4.0))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1.15, 1, 1.15], wspace=0.42)

    ax = fig.add_subplot(gs[0])
    bars(ax, ["DCPM", "EEGNet", "Naive\nKD", "RED"],
         [np.mean(list(dcpm.values())), e.mean(), e.mean() + 0.2, red.mean()],
         [np.std(list(dcpm.values())), e.std(), e.std(), red.std()],
         [True, True, False, False], (50, 95), "Accuracy (%)")
    ax.set_title("(a) Within-subject accuracy", loc="left")
    tag(ax, "Hatched: illustrative")

    ax = fig.add_subplot(gs[1])
    names = ["EEGNet (L$_{CE}$ only)", "+ L$_{N2N}$", "+ L$_{critic}$", "RED (all)", "Class-mean target", "Naive KD"]
    vals = [e.mean(), e.mean() + 1.7, e.mean() + 0.9, red.mean(), red.mean() - 1.2, e.mean() + 0.2]
    y = np.arange(len(names))[::-1]
    for yi, v, n in zip(y, vals, names):
        ax.barh(yi, v - 70, left=70, height=0.6, **(MEAS if n.startswith("EEGNet") else RED_HATCH), zorder=2)
        ax.text(v + 0.2, yi, f"{v:.1f}", va="center", fontsize=9.5)
    ax.set_yticks(y, names, fontsize=9.5)
    ax.set_xlim(70, 81)
    ax.set_xlabel("Within-subject accuracy (%)")
    ax.set_title("(b) Ablation", loc="left")
    tag(ax)

    ax = fig.add_subplot(gs[2])
    ax.axhline(0, color="black", lw=0.6)
    ax.scatter(e, gain, s=24, facecolor="white", edgecolor=C0, lw=1.1, zorder=3)
    ax.set_xlabel("EEGNet accuracy (%), measured")
    ax.set_ylabel("RED − EEGNet (points)")
    ax.set_ylim(-3, 10)
    ax.set_title("(c) Per-subject gain", loc="left")
    tag(ax)

    r2, r2_raw, (x, a, p), t = linear_n2n(data, RECON_SUBJECT)
    ax = fig.add_subplot(gs[3])
    ax.plot(t, x, color=GRAY, lw=1.0, alpha=0.8, label="Single trial x")
    ax.plot(t, a, color="black", lw=1.6, label="Target ā (others in group)")
    ax.plot(t, p, color=C0, lw=1.8, label="Linear N2N estimate x̂")
    ax.axhline(0, color="black", lw=0.4)
    ax.set_xlim(t[0], t[-1])
    ax.set_xlabel("Time after pair onset (ms)")
    ax.set_ylabel("Hemispheric difference (µV)")
    ax.set_title("(d) Recoverable ERP", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.19), fontsize=8.5, frameon=False, handlelength=1.5,
              ncol=1, labelspacing=0.25)
    ax.text(0.98, 0.98, f"Measured, Sub{RECON_SUBJECT:02d}\nR² of x̂: {r2.mean():.2f}\nR² of raw x: {r2_raw.mean():.1f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
            bbox=dict(boxstyle="square,pad=0.25", fc="white", ec="#A6A6A6", lw=0.6))

    fig.subplots_adjust(left=0.05, right=0.99, top=0.9, bottom=0.3)
    fig.savefig(out)
    plt.close(fig)
    return r2, r2_raw


def fig_moe(res_csv: Path, data: Path, out: Path, rng):
    eeg = per_subject(res_csv, "eegnet", "loso")
    dcpm = per_subject(res_csv, "dcpm", "loso")
    within = np.mean(list(per_subject(res_csv, "eegnet", "within").values()))
    subs = sorted(eeg)
    e = np.array([eeg[s] for s in subs])
    r = np.array([subject_stats(*load_subject(data / f"Sub{s:02d}.npz"))["r_mirror"] for s in subs])
    gain = 2.5 + 3.0 * (1 - r) / 2 + rng.normal(0, 1.0, e.size)     # illustrative: atypical subjects gain more
    moe = e + gain

    fig = plt.figure(figsize=(12.4, 4.0))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1.1, 1.25, 1.05], wspace=0.42)

    ax = fig.add_subplot(gs[0])
    bars(ax, ["DCPM", "EEGNet", "Generic\nMoE", "LR-MoE"],
         [np.mean(list(dcpm.values())), e.mean(), e.mean() + 1.2, moe.mean()],
         [np.std(list(dcpm.values())), e.std(), e.std(), moe.std()],
         [True, True, False, False], (50, 88), "LOSO accuracy (%)")
    ax.axhline(within, color="black", lw=0.9, ls="--")
    ax.text(-0.45, within + 0.6, "within-subject EEGNet", ha="left", fontsize=8.5)
    ax.set_title("(a) Unseen subjects", loc="left")
    tag(ax, "Hatched: illustrative")

    ax = fig.add_subplot(gs[1])
    n = np.array([0, 24, 48, 96, 192, 480])
    base = e.mean() + (within - e.mean()) * (1 - np.exp(-n / 260))
    ours = moe.mean() + (within + 1 - moe.mean()) * (1 - np.exp(-n / 120))
    ax.plot(n, base, color="#595959", marker="s", ms=5, mfc="white", ls="--", lw=1.4, label="EEGNet, fine-tuned")
    ax.plot(n, ours, color=C0, marker="o", ms=5, mfc="white", ls="--", lw=1.6, label="LR-MoE, router only")
    ax.plot([0], [e.mean()], marker="s", ms=6, color="#595959", ls="")
    ax.axhline(within, color="black", lw=0.9, ls=":")
    ax.set_xlabel("Labelled target trials")
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(58, 80)
    ax.legend(loc="lower right", fontsize=8.5, frameon=False)
    ax.set_title("(b) Few-shot calibration", loc="left")
    tag(ax)

    ax = fig.add_subplot(gs[2])
    order = np.argsort(r)
    w_eq = 1 / (1 + np.exp(-4 * r[order])) * 0.85
    w_sym = (1 - w_eq) * np.clip(0.55 + rng.normal(0, 0.1, r.size), 0.2, 0.8)
    w_dom = 1 - w_eq - w_sym
    xs = np.arange(r.size)
    ax.bar(xs, w_eq, 0.8, color=C0, label="Mirror-equivariant")
    ax.bar(xs, w_dom, 0.8, bottom=w_eq, color="#D9A0A0", label="Hemisphere-dominant")
    ax.bar(xs, w_sym, 0.8, bottom=w_eq + w_dom, color="#BFBFBF", label="Symmetric / context")
    ax.set_xticks([0, r.size - 1], [f"r = {r[order][0]:+.2f}", f"r = {r[order][-1]:+.2f}"], fontsize=9)
    ax.set_xlabel("Subjects, sorted by measured mirror r")
    ax.set_ylabel("Mean routing weight")
    ax.set_ylim(0, 1.55)
    ax.set_yticks([0, 0.5, 1])
    ax.legend(loc="upper left", fontsize=8.2, frameon=False, ncol=1, handlelength=1, borderaxespad=0.2)
    ax.set_title("(c) Expert routing", loc="left")
    tag(ax)

    ax = fig.add_subplot(gs[3])
    ax.plot([45, 85], [45, 85], color="black", lw=0.6)
    sc = ax.scatter(e, moe, c=r, cmap="RdGy_r", vmin=-1, vmax=1, s=26, edgecolor="black", lw=0.5, zorder=3)
    cb = fig.colorbar(sc, ax=ax, fraction=0.05, pad=0.03)
    cb.set_label("measured mirror r", fontsize=9)
    cb.ax.tick_params(labelsize=8.5)
    ax.set_xlim(45, 85)
    ax.set_ylim(45, 85)
    ax.set_xlabel("EEGNet LOSO (%), measured")
    ax.set_ylabel("LR-MoE LOSO (%)")
    ax.set_title("(d) Per-subject", loc="left")
    tag(ax)

    fig.subplots_adjust(left=0.05, right=0.945, top=0.9, bottom=0.2)
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="derivatives/preprocessed")
    ap.add_argument("--results", default="results/summary_per_subject.csv")
    ap.add_argument("--out", default="presentation/figures")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    r2, r2_raw = fig_red(Path(args.results), Path(args.data), out / "red_results.png", np.random.default_rng(0))
    print(f"linear N2N, Sub{RECON_SUBJECT:02d}: R2 per session {np.round(r2, 3)}, mean {r2.mean():.3f}; "
          f"raw x mean {r2_raw.mean():.3f}")
    fig_moe(Path(args.results), Path(args.data), out / "moe_results.png", np.random.default_rng(1))


if __name__ == "__main__":
    main()
