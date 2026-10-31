"""Latency-aligned leave-one-out repetition targets (Chapter 1, direction 2).

The repetitions of a code bit share label and context, but single-trial response latency varies; plain
averaging blurs the target. For each trial i, the OTHER members of its group are aligned to each other with
Woody's method (iterative cross-correlation with a leave-one-out template, integer shifts within +/- max_shift
samples), the shifts are centred (target latency = mean latency of the other members) and the aligned members
are averaged. Trial i itself never enters its own target or the alignment that produces it, so the target's
noise stays independent of the input (the Noise2Noise condition).
"""

from __future__ import annotations

import numpy as np


def shift_edge(x: np.ndarray, s: int) -> np.ndarray:
    """Delay x (..., T) by s samples (s > 0: later), padding with the edge value."""
    T = x.shape[-1]
    idx = np.clip(np.arange(T) - s, 0, T - 1)
    return x[..., idx]


def woody_align(members: np.ndarray, max_shift: int, iters: int) -> np.ndarray:
    """Integer shifts (len(members),) aligning members (m, C, T) to each other, centred to mean 0."""
    m = len(members)
    shifts = np.zeros(m, dtype=int)
    if m < 2 or max_shift == 0:
        return shifts
    cands = np.arange(-max_shift, max_shift + 1)
    shifted = np.stack([shift_edge(members, s) for s in cands], axis=1)      # (m, S, C, T)
    flat = shifted.reshape(m, len(cands), -1)
    flat = flat - flat.mean(-1, keepdims=True)
    flat /= np.linalg.norm(flat, axis=-1, keepdims=True) + 1e-12
    for _ in range(iters):
        aligned = flat[np.arange(m), shifts + max_shift]                     # (m, D) at current shifts
        total = aligned.sum(0)
        new = shifts.copy()
        for j in range(m):
            template = total - aligned[j]                                     # leave-j-out template
            new[j] = cands[np.argmax(flat[j] @ template)]
        if np.array_equal(new, shifts):
            break
        shifts = new
    return shifts - int(np.round(shifts.mean()))


def aligned_loo_targets(X: np.ndarray, group: np.ndarray, max_shift: int = 3, iters: int = 3):
    """Aligned leave-one-out targets (n, C, T), validity mask (group size >= 2), and the mean |shift| used."""
    targets = np.zeros_like(X)
    valid = np.zeros(len(X), dtype=bool)
    abs_shift = []
    for g in np.unique(group):
        idx = np.flatnonzero(group == g)
        if len(idx) < 2:
            continue
        for i in idx:
            others = idx[idx != i]
            sh = woody_align(X[others], max_shift, iters)
            targets[i] = np.mean([shift_edge(X[o], s) for o, s in zip(others, sh)], axis=0)
            valid[i] = True
            abs_shift.extend(np.abs(sh))
    return targets, valid, float(np.mean(abs_shift)) if abs_shift else 0.0
