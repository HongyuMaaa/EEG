"""Continuous-signal preprocessing and epoch extraction for one session.

Order of operations (all linear except the bad-channel decision):
    load (uV) -> band-pass FIR -> detect bad channels -> spherical-spline interpolation
    -> common average reference -> epoch [tmin, tmax) at 200 Hz -> decimate to target_sfreq
    -> peak-to-peak artifact flag
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mne
import numpy as np

from .config import PreprocessConfig
from .events import SessionEvents

mne.set_log_level("ERROR")


@dataclass
class SessionResult:
    X: np.ndarray            # (n_trials, n_channels, n_times) float32, uV
    ptp: np.ndarray          # (n_trials,) max peak-to-peak over channels, uV
    artifact: np.ndarray     # (n_trials,) bool
    in_bounds: np.ndarray    # (n_trials,) bool, window fully inside the recording
    bad_channels: list[str]
    ch_names: list[str]
    n_samples_native: int
    filter_taps: int


def load_montage(path: str | Path, ch_names: list[str]) -> mne.channels.DigMontage:
    """EEGLAB .loc montage, renamed to the EDF channel names (case-insensitive match, e.g. POz -> POZ)."""
    montage = mne.channels.read_custom_montage(str(path))
    lookup = {name.upper(): name for name in montage.ch_names}
    missing = [c for c in ch_names if c.upper() not in lookup]
    if missing:
        raise ValueError(f"channels missing from montage: {missing}")
    montage.rename_channels({lookup[c.upper()]: c for c in ch_names if lookup[c.upper()] != c})
    return montage


def detect_bad_channels(data: np.ndarray, cfg: PreprocessConfig) -> list[int]:
    """Iteratively flag the channel whose std after CAR exceeds threshold x median std of the good channels.

    ``data`` is band-passed and restricted to the task interval. The CAR is recomputed
    over the remaining good channels at each iteration, so a single broken channel
    cannot contaminate the reference used to judge the others.
    """
    bad: list[int] = []
    for _ in range(cfg.bad_channels.max_iterations):
        good = [i for i in range(data.shape[0]) if i not in bad]
        car = data - data[good].mean(axis=0, keepdims=True)
        std = car.std(axis=1)
        med = np.median(std[good])
        cand = [i for i in good if std[i] > cfg.bad_channels.std_ratio_threshold * med]
        if not cand:
            break
        bad.append(max(cand, key=lambda i: std[i]))
    return sorted(bad)


def preprocess_session(edf_path: str | Path, events: SessionEvents, cfg: PreprocessConfig) -> SessionResult:
    raw = mne.io.read_raw_edf(str(edf_path), preload=True)
    assert raw.info["sfreq"] == cfg.native_sfreq, f"{edf_path}: sfreq {raw.info['sfreq']}"
    assert len(raw.ch_names) == cfg.n_channels, f"{edf_path}: {len(raw.ch_names)} channels"
    raw.set_montage(load_montage(cfg.montage_file, raw.ch_names))

    f = cfg.filter
    raw.filter(
        l_freq=f.l_freq, h_freq=f.h_freq,
        l_trans_bandwidth=f.l_trans_bandwidth, h_trans_bandwidth=f.h_trans_bandwidth,
        filter_length=f.filter_length, fir_window=f.fir_window, fir_design=f.fir_design,
        phase=f.phase, method="fir",
    )
    taps = len(mne.filter.create_filter(
        None, cfg.native_sfreq, f.l_freq, f.h_freq,
        l_trans_bandwidth=f.l_trans_bandwidth, h_trans_bandwidth=f.h_trans_bandwidth,
        filter_length=f.filter_length, fir_window=f.fir_window, fir_design=f.fir_design, phase=f.phase,
    ))

    start, stop = cfg.epoch_offsets_native
    task = slice(max(int(events.onsets[0]) + start, 0), int(events.onsets[-1]) + stop)
    bad_idx = detect_bad_channels(raw.get_data(units="uV")[:, task], cfg)
    bad = [raw.ch_names[i] for i in bad_idx]
    if bad:
        raw.info["bads"] = bad
        raw.interpolate_bads(reset_bads=True, method={"eeg": "spline"})
    raw.set_eeg_reference("average", projection=False)

    data = raw.get_data(units="uV")
    n_native = data.shape[1]
    in_bounds = (events.onsets + start >= 0) & (events.onsets + stop <= n_native)
    X = np.zeros((len(events.onsets), data.shape[0], cfg.n_times), dtype=np.float32)
    for i, on in enumerate(events.onsets):
        if in_bounds[i]:
            X[i] = data[:, on + start: on + stop: cfg.decim]
    ptp = np.ptp(X, axis=2).max(axis=1)
    artifact = ptp > cfg.artifact.ptp_threshold_uv
    return SessionResult(X, ptp, artifact, in_bounds, bad, list(raw.ch_names), n_native, taps)
