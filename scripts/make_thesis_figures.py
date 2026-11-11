"""Thesis figures for Chapters 1 and 2, computed from the committed results (nothing is hard-coded).

Statistics: subject-level accuracy (seeds averaged, trial-weighted over the test sessions), paired differences
with 95% bootstrap CIs of the mean (4000 resamples of subjects) and Wilcoxon signed-rank tests.
Palette: validated categorical slots 1-3 of the dataviz reference palette (blue = proposed, orange = EEGNet
baseline, aqua = DCPM) plus neutral gray for controls. Aqua is below 3:1 contrast on white, so its marks always
carry direct labels / markers and every value is also given in the chapter tables.

Usage: python scripts/make_thesis_figures.py [--out docs/thesis/figures]
Writes <name>.png (300 dpi) and <name>.pdf, and figure_data.json with every plotted number.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr, wilcoxon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from char_level import char_accuracy, codebook, itr, load_meta  # noqa: E402
from compare_methods import subject_accuracy, unit_accuracy  # noqa: E402

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRAY, LIGHT_GRAY = "#8a8985", "#d9d8d4"
INK, INK_2, INK_3 = "#0b0b0b", "#52514e", "#8a8985"
SURFACE = "#ffffff"
RESULTS = ROOT / "results"
DATA: dict = {}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.edgecolor": INK_3, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#ecebe8", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "legend.frameon": False, "axes.titlepad": 20, "legend.fontsize": 8.5, "font.family": "DejaVu Sans",
})


# ------------------------------------------------------------------ data helpers
def subj(method: str, protocol: str, sessions=None) -> pd.Series:
    """Subject-level accuracy (%) of a method, seeds averaged, optionally restricted to test sessions."""
    u = unit_accuracy(RESULTS, method, protocol)
    keep = u.index if sessions is None else u.index[u.index.get_level_values("session").isin(sessions)]
    return subject_accuracy(u, keep) * 100


def paired(a: pd.Series, b: pd.Series) -> dict:
    common = a.index.intersection(b.index)
    d = (a[common] - b[common]).astype(float)
    rng = np.random.default_rng(0)
    boot = [d.to_numpy()[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
    p = wilcoxon(a[common], b[common]).pvalue if (d != 0).any() else 1.0
    return {"mean": float(d.mean()), "lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5)),
            "p": float(p), "improved": int((d > 0).sum()), "n": int(len(d))}


def forest(ax, rows, ref_label, xlabel="Δ accuracy vs reference (pp)"):
    """rows: list of (label, stats, color) or (header, None, None). Filled marker = p < 0.05, open = n.s."""
    y = 0
    ticks, labels = [], []
    for label, st, color in rows:
        if st is None:
            ax.text(-0.01, y, label, transform=ax.get_yaxis_transform(), ha="right", va="center",
                    fontsize=8.5, fontweight="bold", color=INK)
            y -= 1
            continue
        ax.plot([st["lo"], st["hi"]], [y, y], color=color, lw=2, solid_capstyle="round", zorder=2)
        sig = st["p"] < 0.05
        ax.plot(st["mean"], y, "o", ms=6.5, mfc=color if sig else SURFACE, mec=color, mew=1.6, zorder=3)
        ax.text(1.01, y, f"{st['mean']:+.2f}  ({st['improved']}/{st['n']})", transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=8, color=INK_2)
        ticks.append(y)
        labels.append(label)
        y -= 1
    ax.axvline(0, color=INK_3, lw=1)
    ax.set_yticks(ticks, labels)
    ax.set_ylim(y + 0.4, 0.6)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(xlabel + f"  — reference: {ref_label}")
    ax.tick_params(axis="y", length=0)


def legend_markers(ax):
    h1, = ax.plot([], [], "o", ms=6.5, mfc=INK_2, mec=INK_2, mew=1.6, ls="none")
    h2, = ax.plot([], [], "o", ms=6.5, mfc=SURFACE, mec=INK_2, mew=1.6, ls="none")
    # placed above the plot area (right-aligned, opposite the left-aligned title) so it never covers a CI
    ax.legend([h1, h2], ["p < 0.05 (Wilcoxon)", "n.s."], loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2,
              borderaxespad=0.2, handletextpad=0.3, columnspacing=1.0)


def save(fig, out: Path, name: str):
    fig.savefig(out / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def dumbbell(ax, base: pd.Series, new: pd.Series, base_label, new_label):
    common = base.index.intersection(new.index)
    order = base[common].sort_values().index
    y = np.arange(len(order))
    for yi, s in zip(y, order):
        ax.plot([base[s], new[s]], [yi, yi], color=LIGHT_GRAY, lw=2, zorder=1)
    ax.plot(base[order], y, "o", ms=6, color=ORANGE, mec=SURFACE, mew=1, label=base_label, zorder=3)
    ax.plot(new[order], y, "o", ms=6, color=BLUE, mec=SURFACE, mew=1, label=new_label, zorder=3)
    ax.set_yticks(y, [f"S{s:02d}" for s in order])
    ax.tick_params(axis="y", labelsize=7, length=0)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("accuracy (%)")
    ax.legend(loc="lower right")


# ------------------------------------------------------------------ Chapter 1
def fig_ch1_headroom(out):
    eeg = subj("eegnet", "within")
    t = {k: [] for k in (1, 3, 6)}
    for f in glob.glob(str(RESULTS / "red/within/seed*/folds/*.json")):
        r = json.loads(Path(f).read_text())
        for k in t:
            t[k].append(100 * r[f"teacher_test_acc_avg{k}"])
    vals = [eeg.mean(), np.mean(t[1]), np.mean(t[3]), np.mean(t[6])]
    names = ["EEGNet\nsingle trial", "teacher\n1 trial", "teacher\n3-trial avg.", "teacher\n6-trial avg."]
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    colors = [ORANGE, GRAY, GRAY, GRAY]
    bars = ax.bar(names, vals, width=0.55, color=colors, edgecolor=SURFACE, linewidth=2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_ylim(50, 95)
    ax.set_ylabel("accuracy (%)")
    ax.set_title("Averaging headroom (within subject, test sessions)", loc="left")
    ax.grid(axis="x", visible=False)
    DATA["ch1_headroom"] = dict(zip(["eegnet_single", "teacher_avg1", "teacher_avg3", "teacher_avg6"], vals))
    save(fig, out, "ch1_averaging_headroom")


def fig_ch1_ablation(out):
    ref = subj("eegnet", "within")
    groups = [
        ("Using averages directly", [("kd_naive", "distillation from averaged-trial teacher"),
                                     ("eegnet_avgaug", "averaged trials as extra training data")]),
        ("RED components", [("red_n2n", "reconstruction of averaged repetitions only"),
                            ("red_critic", "frozen critic only"),
                            ("red", "RED (averaged-trial critic)"),
                            ("red_selfteacher", "RED (single-trial critic)")]),
        ("Controls", [("red_randteacher", "random frozen critic"),
                      ("red_classmean", "class-mean target"),
                      ("red_autoenc_self@ln0.3", "input trial as target, λ = 0.3"),
                      ("red_autoenc_self", "input trial as target, λ = 1"),
                      ("red_aligned", "latency-aligned targets")]),
    ]
    rows, data = [], {}
    for header, items in groups:
        rows.append((header, None, None))
        for m, label in items:
            st = paired(subj(m, "within"), ref)
            data[m] = st
            rows.append((label, st, BLUE if m in ("red", "red_selfteacher") else GRAY))
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    forest(ax, rows, "EEGNet")
    legend_markers(ax)
    ax.set_title("Chapter 1 ablations — within subject, leave-one-session-out", loc="left")
    DATA["ch1_ablation"] = data
    save(fig, out, "ch1_ablation")


def fig_ch1_subjects(out):
    e, r = subj("eegnet", "within"), subj("red_selfteacher", "within")
    fig, ax = plt.subplots(figsize=(4.8, 5.6))
    dumbbell(ax, e, r, "EEGNet", "RED (single-trial critic)")
    ax.set_title("Per-subject accuracy, within subject", loc="left")
    DATA["ch1_subjects"] = {"eegnet": e.round(2).to_dict(), "red_selfteacher": r.round(2).to_dict()}
    save(fig, out, "ch1_per_subject")


def fig_ch1_character(out):
    meta = load_meta(ROOT / "derivatives/preprocessed")
    codes = codebook(meta)
    methods = [("dcpm", "DCPM", AQUA, "s"), ("eegnet", "EEGNet", ORANGE, "o"),
               ("red_selfteacher", "RED", BLUE, "D")]
    reps = np.arange(1, 7)
    acc = {m: [100 * char_accuracy(RESULTS, m, meta, codes, R).mean() for R in reps] for m, *_ in methods}
    rate = {m: [np.mean([itr(p, t=1.2 * R + 1.0) for p in char_accuracy(RESULTS, m, meta, codes, R)])
                for R in reps] for m, *_ in methods}
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    for m, label, color, mk in methods:
        axes[0].plot(reps, acc[m], marker=mk, ms=6, lw=2, color=color, mec=SURFACE, label=label)
        axes[1].plot(reps, rate[m], marker=mk, ms=6, lw=2, color=color, mec=SURFACE, label=label)
        axes[0].text(6.15, acc[m][-1], label, va="center", fontsize=8, color=INK_2)
        axes[1].text(6.15, rate[m][-1], label, va="center", fontsize=8, color=INK_2)
    axes[0].set_ylabel("character accuracy (%)")
    axes[1].set_ylabel("ITR (bits/min)")
    for ax, t in zip(axes, ["(a) 32-class character accuracy", "(b) information transfer rate"]):
        ax.set_xlabel("repetitions per character")
        ax.set_xticks(reps)
        ax.set_xlim(0.7, 6.9)
        ax.set_title(t, loc="left")
    axes[0].legend(loc="upper left")
    DATA["ch1_character"] = {"accuracy": acc, "itr": rate}
    save(fig, out, "ch1_character_level")


# ------------------------------------------------------------------ Chapter 2
S46 = [4, 5, 6]


def fig_ch2_pipeline(out):
    names = [("rcr_full", "EEGNet (all 27 subjects)", ORANGE), ("rcr_uniform", "equal average of 9 experts", GRAY),
             ("rcr_top3", "RCR (top-3 experts)", BLUE), ("rcr_full_rapl", "EEGNet + RAPL", BLUE),
             ("rcr_top3_rapl", "RCR + RAPL", BLUE), ("rcr_oracle", "best expert (oracle)", LIGHT_GRAY)]
    acc = {m: subj(m, "loso", S46) for m, *_ in names}
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    vals = [acc[m].mean() for m, *_ in names]
    bars = ax.barh(range(len(names))[::-1], vals, color=[c for *_, c in names], edgecolor=SURFACE, linewidth=2,
                   height=0.62)
    bars[-1].set_hatch("////")
    bars[-1].set_edgecolor(GRAY)
    for b, v in zip(bars, vals):
        ax.text(v + 0.3, b.get_y() + b.get_height() / 2, f"{v:.1f}", va="center", fontsize=8.5)
    ax.set_yticks(range(len(names))[::-1], [n for _, n, _ in names])
    ax.set_xlim(55, 74)
    ax.set_xlabel("accuracy (%)")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("(a) new subject, no target labels", loc="left")
    rows, data = [], {}
    for m, label, color in names[1:]:
        st = paired(acc[m], acc["rcr_full"])
        data[m] = st
        rows.append((label, st, color if color != LIGHT_GRAY else GRAY))
    forest(axes[1], rows, "EEGNet (all subjects)")
    legend_markers(axes[1])
    axes[1].set_title("(b) paired gain", loc="left")
    DATA["ch2_pipeline"] = {"accuracy": dict(zip([m for m, *_ in names], vals)), "gain": data}
    save(fig, out, "ch2_pipeline")


def fig_ch2_router(out):
    xs, ys, ranks, rhos = [], [], [], []
    for f in glob.glob(str(RESULTS / "rcr_experts/seed*/*.json")):
        r = json.loads(Path(f).read_text())
        E = pd.DataFrame(r["experts"])
        xs.extend(E.cons - E.cons.mean())
        ys.extend(100 * (E.acc46 - E.acc46.mean()))
        ranks.append(int(E.acc46.rank(ascending=False, method="min")[r["selected_top1"]]))
        rhos.append(spearmanr(E.cons, E.acc46)[0])
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0))
    axes[0].plot(xs, ys, "o", ms=3.5, color=BLUE, alpha=0.45, mec="none")
    axes[0].axhline(0, color=INK_3, lw=0.8)
    axes[0].axvline(0, color=INK_3, lw=0.8)
    axes[0].set_xlabel("repetition consistency (centred within subject)")
    axes[0].set_ylabel("test accuracy (pp, centred)")
    axes[0].set_title(f"(a) router score vs expert accuracy\nmean within-subject Spearman ρ = {np.nanmean(rhos):.2f}",
                      loc="left")
    counts = np.bincount(ranks, minlength=10)[1:]
    axes[1].bar(np.arange(1, 10), counts, color=BLUE, edgecolor=SURFACE, linewidth=2, width=0.7)
    axes[1].axhline(len(ranks) / 9, color=INK_2, lw=1, ls="--")
    axes[1].text(9.4, len(ranks) / 9, "random choice", va="bottom", ha="right", fontsize=8, color=INK_2)
    axes[1].set_xticks(np.arange(1, 10))
    axes[1].set_xlabel("true rank of the chosen expert (1 = best of 9)")
    axes[1].set_ylabel("subject × seed cases")
    axes[1].set_title(f"(b) top-1 choice is the best expert in {100 * counts[0] / len(ranks):.0f}% of cases",
                      loc="left")
    axes[1].grid(axis="x", visible=False)
    DATA["ch2_router"] = {"rank_counts": counts.tolist(), "mean_spearman": float(np.nanmean(rhos))}
    save(fig, out, "ch2_router")


def fig_ch2_rapl_controls(out):
    rows_data = {}
    for f in glob.glob(str(RESULTS / "adapt_pilot_v2/seed*/Sub*.json")):
        r = json.loads(Path(f).read_text())
        rows_data.setdefault(r["subject"], []).append(r["accuracy"])
    acc = pd.DataFrame({s: pd.DataFrame(v).mean() for s, v in rows_data.items()}).T * 100
    items = [("tent", "entropy minimisation (Tent)", GRAY), ("balance", "threshold re-centring only", GRAY),
             ("n2n", "label-free reconstruction", GRAY), ("gpl", "group pseudo-labels, confidence threshold", GRAY),
             ("gpl_bal_single", "balanced pseudo-labels, single trials", GRAY),
             ("gpl_bal", "RAPL: balanced pseudo-labels, repetition groups", BLUE),
             ("oracle", "supervised fine-tuning (oracle)", LIGHT_GRAY)]
    rows, data = [], {}
    for m, label, c in items:
        st = paired(acc[m], acc["adabn"])
        data[m] = st
        rows.append((label, st, c if c != LIGHT_GRAY else GRAY))
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    forest(ax, rows, "AdaBN")
    legend_markers(ax)
    ax.set_title("RAPL and its controls — new subject, 3 seeds", loc="left")
    DATA["ch2_rapl_controls"] = data
    save(fig, out, "ch2_rapl_controls")


def fig_ch2_negative(out):
    ref = subj("eegnet", "loso")
    moe = [("eegnet_sz", "EEGNet, per-subject normalisation"), ("eegnet_mirroraug", "EEGNet + mirror augmentation"),
           ("lrmoe", "LR-MoE (proposed in the design)"), ("lrmoe_generic", "generic MoE, learned gate"),
           ("lrmoe_nodecomp", "LR-MoE without hemispheric streams"), ("lrmoe_nolat", "LR-MoE without latency experts"),
           ("lrmoe_nocoh", "LR-MoE without coherence loss"), ("lrmoe_anti", "antisymmetric experts only")]
    rows_a, data_a = [], {}
    for m, label in moe:
        st = paired(subj(m, "loso"), ref)
        data_a[m] = st
        rows_a.append((label, st, GRAY))
    full = subj("est_full", "loso", S46)
    rout = [("oracle_phen_knn", "oracle descriptors incl. latency"),
            ("est_oracle_knn", "oracle descriptors, no latency"),
            ("est_knn", "estimated descriptors (label-free)"), ("est_rand_knn", "13 random subjects")]
    rows_b, data_b = [], {}
    for m, label in rout:
        st = paired(subj(m, "loso", S46), full)
        data_b[m] = st
        rows_b.append((label, st, GRAY))
    fig, axes = plt.subplots(2, 1, figsize=(6.6, 5.6), gridspec_kw={"height_ratios": [8, 4.6]})
    forest(axes[0], rows_a, "EEGNet (LOSO, all sessions)")
    axes[0].set_title("(a) trial-level physiological routing (seed 0)", loc="left")
    forest(axes[1], rows_b, "EEGNet on all 27 subjects (sessions 4–6)")
    axes[1].set_title("(b) routing by subject phenotype: train on the 13 nearest subjects", loc="left")
    legend_markers(axes[0])
    fig.tight_layout()
    DATA["ch2_negative"] = {"lrmoe": data_a, "phenotype_routing": data_b}
    save(fig, out, "ch2_negative_results")


def fig_ch2_subjects(out):
    a, b = subj("rcr_full", "loso", S46), subj("rcr_top3_rapl", "loso", S46)
    fig, ax = plt.subplots(figsize=(4.8, 5.6))
    dumbbell(ax, a, b, "EEGNet (all subjects)", "RCR + RAPL")
    ax.set_title("Per-subject accuracy, new subject", loc="left")
    DATA["ch2_subjects"] = {"rcr_full": a.round(2).to_dict(), "rcr_top3_rapl": b.round(2).to_dict()}
    save(fig, out, "ch2_per_subject")


def fig_ch2_red_experts(out):
    items = [("full", "full-data model"), ("top3", "RCR top-3"), ("full_rapl", "full-data model + RAPL"),
             ("top3_rapl", "RCR + RAPL")]
    rows, data = [], {}
    for v, label in items:
        st = paired(subj(f"rcr_red_{v}", "loso", S46), subj(f"rcr_{v}", "loso", S46))
        data[v] = st
        rows.append((label, st, BLUE if "rapl" in v else GRAY))
    fig, ax = plt.subplots(figsize=(6.2, 2.4))
    forest(ax, rows, "same pipeline with EEGNet experts", xlabel="Δ accuracy, RED − EEGNet experts (pp)")
    legend_markers(ax)
    ax.set_title("Chapter 1 objective inside the Chapter 2 pipeline", loc="left")
    DATA["ch2_red_experts"] = data
    save(fig, out, "ch2_red_experts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/thesis/figures")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    for f in (fig_ch1_headroom, fig_ch1_ablation, fig_ch1_subjects, fig_ch1_character, fig_ch2_pipeline,
              fig_ch2_router, fig_ch2_rapl_controls, fig_ch2_negative, fig_ch2_subjects, fig_ch2_red_experts):
        f(out)
    (out / "figure_data.json").write_text(json.dumps(DATA, indent=1, default=float))


if __name__ == "__main__":
    main()
