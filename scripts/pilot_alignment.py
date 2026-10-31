"""Direction 2 diagnostic: is single-trial latency jitter detectable within repetition groups?

For each subject: Woody shifts (leave-one-out, +/-3 samples) are estimated within every repetition group, and the
power gain of the aligned over the plain group average is compared between
  real        the recorded trials
  null A      phase-randomised trials (same spectra and cross-spectra, no time-locked response) - a weak null
  null B      jitter-free surrogate: group mean + phase-randomised residual (trial - group mean); same shared
              waveform and same noise spectra, but no latency jitter by construction - the proper null
Real jitter that is measurable at this SNR must give a larger gain on real data than on null B.

Usage: python scripts/pilot_alignment.py [--subjects 1 2 ...] [--out reports/pilot_alignment.md]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aved.alignment import shift_edge, woody_align  # noqa: E402
from aved.data import load_dataset  # noqa: E402


def phase_randomise(X, rng):
    F = np.fft.rfft(X, axis=-1)
    # one random phase per trial and frequency, shared by all channels: keeps cross-channel (spatial) structure
    ph = np.exp(1j * rng.uniform(0, 2 * np.pi, size=(F.shape[0], 1, F.shape[-1])))
    ph[..., 0] = 1
    return np.fft.irfft(F * ph, n=X.shape[-1], axis=-1)


def gain(X, group, rng):
    """Mean |shift| and mean relative power gain of the aligned vs plain group average."""
    shifts, gains = [], []
    for g in np.unique(group):
        m = X[group == g]
        if len(m) < 4:
            continue
        s = woody_align(m, 3, 3)
        plain = m.mean(0)
        aligned = np.mean([shift_edge(x, k) for x, k in zip(m, s)], axis=0)
        shifts.extend(np.abs(s))
        gains.append((aligned ** 2).sum() / (plain ** 2).sum() - 1)
    return np.mean(shifts), np.mean(gains)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", type=int, nargs="*", default=list(range(1, 29)))
    ap.add_argument("--out")
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    rows = []
    for s in args.subjects:
        ds = load_dataset(ROOT / "derivatives/preprocessed", [s])
        X = ds.X.astype(np.float64)
        rs, rg = gain(X, ds.group, rng)
        ss, sg = gain(phase_randomise(X, rng), ds.group, rng)
        gm = np.zeros_like(X)
        for g in np.unique(ds.group):
            m = ds.group == g
            gm[m] = X[m].mean(0)
        bs, bg = gain(gm + phase_randomise(X - gm, rng), ds.group, rng)
        rows.append((s, rs, ss, rg, sg, bs, bg))
        print(f"Sub{s:02d}: power gain real {100*rg:.1f}%  nullA {100*sg:.1f}%  nullB {100*bg:.1f}%   "
              f"|shift| {rs:.2f} / {ss:.2f} / {bs:.2f}", flush=True)
    r = np.array(rows)
    from scipy.stats import wilcoxon
    p = wilcoxon(r[:, 3], r[:, 6]).pvalue
    lines = ["# Direction 2 diagnostic: latency jitter within repetition groups", "",
             "Woody alignment (leave-one-out template, +/-3 samples = +/-15 ms) within each repetition group, on real",
             "trials vs phase-randomised surrogates (same spectra, no time-locked response).", "",
             "| | real | null A (no time-locked signal) | null B (shared waveform, no jitter) |", "|---|---|---|---|",
             f"| mean abs shift (samples) | {r[:,1].mean():.2f} | {r[:,2].mean():.2f} | {r[:,5].mean():.2f} |",
             f"| power gain of aligned vs plain average | {100*r[:,3].mean():.1f}% | {100*r[:,4].mean():.1f}% "
             f"| {100*r[:,6].mean():.1f}% |", "",
             f"Real vs null B: larger gain on real data in {int((r[:,3] > r[:,6]).sum())}/{len(r)} subjects; "
             f"Wilcoxon p = {p:.3g}.", ""]
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
