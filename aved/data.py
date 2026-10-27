"""Loading preprocessed trials and building leakage-safe evaluation folds.

Protocols
---------
within  Within-subject, leave-one-session-out. For subject s and test session k:
        validation = session (k mod 6) + 1, training = the remaining 4 sessions.
        28 subjects x 6 folds = 168 models.
pooled  Pooled across subjects, leave-one-session-out. For test session k, one model is
        trained on the same 4 training sessions of *all* subjects, validated on session
        (k mod 6) + 1, and tested on session k of every subject. 6 models.
loso    Leave-one-subject-out. For test subject s: validation = the next 3 subjects
        (cyclic), training = the remaining 24 subjects. 28 models.

Whole sessions (or subjects) are always held out, so trials whose epochs overlap in time,
or that share a character, never end up on different sides of a split.
Artifact-flagged trials are excluded from training, validation and testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .events import TRIALS_PER_CHAR

PROTOCOLS = ("within", "pooled", "loso")
SUBJECTS = tuple(range(1, 29))
SESSIONS = tuple(range(1, 7))
N_LOSO_VAL_SUBJECTS = 3


@dataclass
class Dataset:
    X: np.ndarray           # (n, C, T) float32
    y: np.ndarray           # (n,) int64
    subject: np.ndarray     # (n,)
    session: np.ndarray     # (n,)
    trial: np.ndarray       # (n,) index of the trial within its subject file (0..2879)
    prev_y: np.ndarray      # (n,) label of the preceding trial of the same character run, -1 if none
    next_y: np.ndarray      # (n,) label of the following trial of the same character run, -1 if none
    ch_names: list[str]
    sfreq: float
    times: np.ndarray
    group: np.ndarray | None = None   # (n,) averaging group: same subject, session, character and bit position,
                                      # i.e. the (up to) 6 repetitions of one code bit; same label and context

    def subset(self, mask: np.ndarray) -> "Dataset":
        return Dataset(self.X[mask], self.y[mask], self.subject[mask], self.session[mask],
                       self.trial[mask], self.prev_y[mask], self.next_y[mask], self.ch_names, self.sfreq,
                       self.times, None if self.group is None else self.group[mask])

    def __len__(self) -> int:
        return len(self.y)


def load_dataset(data_dir: str | Path, subjects=SUBJECTS, drop_artifacts: bool = True) -> Dataset:
    parts = []
    for s in subjects:
        d = np.load(Path(data_dir) / f"Sub{s:02d}.npz")
        y = d["y"].astype(np.int64)
        prev_y, next_y = _neighbour_labels(y)
        keep = ~d["artifact"] if drop_artifacts else np.ones(len(y), bool)
        parts.append(dict(
            X=d["X"][keep], y=y[keep], subject=np.full(keep.sum(), s), session=d["session"][keep],
            trial=np.flatnonzero(keep), prev_y=prev_y[keep], next_y=next_y[keep],
            group=(s * 100_000 + d["session"] * 1000 + d["char_pos"] * 10 + d["bit_pos"])[keep],
        ))
        meta = (list(d["ch_names"]), float(d["sfreq"]), d["times"])
    cat = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    return Dataset(**cat, ch_names=meta[0], sfreq=meta[1], times=meta[2])


def _neighbour_labels(y: np.ndarray, run: int = TRIALS_PER_CHAR) -> tuple[np.ndarray, np.ndarray]:
    """Labels of the adjacent trials within each character's run of 30 trials (files are stored in order)."""
    pos = np.arange(len(y)) % run
    prev_y = np.where(pos > 0, np.roll(y, 1), -1)
    next_y = np.where(pos < run - 1, np.roll(y, -1), -1)
    return prev_y, next_y


@dataclass(frozen=True)
class Fold:
    protocol: str
    name: str                  # unique, filesystem-safe fold id
    test_subjects: tuple
    test_session: int | None   # None for loso (all sessions)
    val_subjects: tuple
    val_session: int | None
    train_subjects: tuple
    train_sessions: tuple

    def masks(self, ds: Dataset) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        def sel(subjects, sessions):
            return np.isin(ds.subject, subjects) & np.isin(ds.session, sessions)

        if self.protocol == "loso":
            return (sel(self.train_subjects, SESSIONS), sel(self.val_subjects, SESSIONS),
                    sel(self.test_subjects, SESSIONS))
        return (sel(self.train_subjects, self.train_sessions), sel(self.val_subjects, [self.val_session]),
                sel(self.test_subjects, [self.test_session]))


def make_folds(protocol: str, subjects=SUBJECTS, sessions=SESSIONS) -> list[Fold]:
    """All folds of a protocol; ``subjects``/``sessions`` restrict which folds are returned
    (for within/loso: which test subjects; for within/pooled: which test sessions)."""
    folds = []
    if protocol == "within":
        for s in subjects:
            for k in sessions:
                v = k % 6 + 1
                folds.append(Fold(protocol, f"sub{s:02d}_test{k}", (s,), k, (s,), v, (s,),
                                  tuple(x for x in SESSIONS if x not in (k, v))))
    elif protocol == "pooled":
        for k in sessions:
            v = k % 6 + 1
            folds.append(Fold(protocol, f"test{k}", SUBJECTS, k, SUBJECTS, v, SUBJECTS,
                              tuple(x for x in SESSIONS if x not in (k, v))))
    elif protocol == "loso":
        for s in subjects:
            i = SUBJECTS.index(s)
            val = tuple(SUBJECTS[(i + j) % len(SUBJECTS)] for j in range(1, N_LOSO_VAL_SUBJECTS + 1))
            train = tuple(x for x in SUBJECTS if x != s and x not in val)
            folds.append(Fold(protocol, f"sub{s:02d}", (s,), None, val, None, train, SESSIONS))
    else:
        raise ValueError(f"unknown protocol {protocol!r}; choose from {PROTOCOLS}")
    return folds


def fold_subjects(fold: Fold) -> tuple:
    """Subjects whose data the fold needs (train + val + test)."""
    return tuple(sorted(set(fold.train_subjects) | set(fold.val_subjects) | set(fold.test_subjects)))
