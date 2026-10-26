"""Parsing and structural validation of the event files.

The ``session_XX_events.edf`` files are plain-text tables (not EDF) with three
columns: ``sample_index  0  code``. The sample index refers to the 200 Hz EEG
recording of the same session. Codes:

* ``> 50``  target-character marker, followed by that character's 5-bit code
  repeated 6 times (30 trial events);
* ``1``     code '0' = left -> right stimulus pair  -> class label 0;
* ``2``     code '1' = right -> left stimulus pair  -> class label 1.

Each code event is one 200 ms stimulus *pair*, i.e. one trial.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
N_CHARS_PER_SESSION = 16
N_BITS = 5
N_REPS = 6
TRIALS_PER_CHAR = N_BITS * N_REPS
TRIGGER_TO_LABEL = {1: 0, 2: 1}            # 1: left->right (code 0), 2: right->left (code 1)
LABEL_NAMES = {0: "left->right", 1: "right->left"}


def marker_to_char(marker: int) -> str:
    """Characters are marked in groups of four per decade: A-D = 51-54, E-H = 61-64, ...

    description.docx states A-D = 52-55. That is off by one: with 52, no session's
    markers match Session_INFO.txt; with 51, all 168 sessions match.
    """
    offset = marker - 51
    group, pos = divmod(offset, 10)
    if not (0 <= pos < 4 and 0 <= group < 8):
        raise ValueError(f"invalid character marker {marker}")
    return ALPHABET[group * 4 + pos]


@dataclass
class SessionEvents:
    onsets: np.ndarray        # (480,) native sample index of each trial (pair onset)
    triggers: np.ndarray      # (480,) 1 or 2
    labels: np.ndarray        # (480,) 0 or 1
    char_pos: np.ndarray      # (480,) 0..15, target-character index in the session
    chars: np.ndarray         # (480,) target character
    rep: np.ndarray           # (480,) 0..5, code repetition
    bit_pos: np.ndarray       # (480,) 0..4, bit position within the 5-bit code
    char_list: str            # the 16 target characters, in order
    char_codes: dict          # char -> 5-bit code string


def read_session_info(path: str | Path) -> dict[int, tuple[int, str]]:
    """session index -> (block, character list)."""
    out = {}
    for line in Path(path).read_text().splitlines()[1:]:
        parts = line.split()
        if len(parts) == 3:
            out[int(parts[0])] = (int(parts[1]), parts[2])
    return out


def parse_events(path: str | Path, expected_chars: str | None = None) -> SessionEvents:
    """Parse one event file and assert the paradigm's structure. Raises AssertionError on any violation."""
    table = np.loadtxt(path, dtype=np.int64)
    assert table.ndim == 2 and table.shape[1] == 3, f"{path}: unexpected table shape {table.shape}"
    assert np.all(table[:, 1] == 0), f"{path}: second column is not all zero"
    samples, codes = table[:, 0], table[:, 2]
    assert np.all(np.diff(samples) > 0), f"{path}: event samples not strictly increasing"

    marker_idx = np.flatnonzero(codes > 50)
    assert len(marker_idx) == N_CHARS_PER_SESSION, f"{path}: {len(marker_idx)} character markers"
    assert len(table) == N_CHARS_PER_SESSION * (1 + TRIALS_PER_CHAR), f"{path}: {len(table)} events"

    fields = {k: [] for k in ("onsets", "triggers", "char_pos", "chars", "rep", "bit_pos")}
    char_list, char_codes = "", {}
    for k, mi in enumerate(marker_idx):
        ch = marker_to_char(int(codes[mi]))
        block = codes[mi + 1: mi + 1 + TRIALS_PER_CHAR]
        assert np.all(np.isin(block, (1, 2))), f"{path}: char {k} has non-code events"
        seq = block.reshape(N_REPS, N_BITS)
        assert np.all(seq == seq[0]), f"{path}: char {ch} code differs between repetitions"
        char_list += ch
        char_codes[ch] = "".join(str(TRIGGER_TO_LABEL[int(b)]) for b in seq[0])
        on = samples[mi + 1: mi + 1 + TRIALS_PER_CHAR]
        fields["onsets"].append(on)
        fields["triggers"].append(block)
        fields["char_pos"].append(np.full(TRIALS_PER_CHAR, k))
        fields["chars"].append(np.full(TRIALS_PER_CHAR, ch))
        fields["rep"].append(np.repeat(np.arange(N_REPS), N_BITS))
        fields["bit_pos"].append(np.tile(np.arange(N_BITS), N_REPS))

    if expected_chars is not None:
        assert char_list == expected_chars, f"{path}: markers {char_list} != Session_INFO {expected_chars}"

    f = {k: np.concatenate(v) for k, v in fields.items()}
    return SessionEvents(
        onsets=f["onsets"],
        triggers=f["triggers"],
        labels=np.vectorize(TRIGGER_TO_LABEL.get)(f["triggers"]),
        char_pos=f["char_pos"],
        chars=f["chars"],
        rep=f["rep"],
        bit_pos=f["bit_pos"],
        char_list=char_list,
        char_codes=char_codes,
    )
