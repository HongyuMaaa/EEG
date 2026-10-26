"""Preprocessing configuration: loading, validation and derived quantities."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FilterConfig:
    l_freq: float = 1.0
    h_freq: float = 30.0
    l_trans_bandwidth: float = 1.0
    h_trans_bandwidth: float = 7.5
    filter_length: str = "auto"
    fir_window: str = "hamming"
    fir_design: str = "firwin"
    phase: str = "zero"


@dataclass(frozen=True)
class BadChannelConfig:
    std_ratio_threshold: float = 3.0
    max_iterations: int = 3
    interpolation: str = "spherical_spline"


@dataclass(frozen=True)
class EpochConfig:
    tmin: float = 0.14
    tmax: float = 0.34
    baseline: None = None


@dataclass(frozen=True)
class ArtifactConfig:
    ptp_threshold_uv: float = 100.0


@dataclass(frozen=True)
class PreprocessConfig:
    data_dir: str = "Data"
    output_dir: str = "derivatives/preprocessed"
    montage_file: str = "Data/64-channels.loc"
    native_sfreq: float = 200.0
    n_channels: int = 21
    filter: FilterConfig = field(default_factory=FilterConfig)
    bad_channels: BadChannelConfig = field(default_factory=BadChannelConfig)
    reference: str = "average"
    epoch: EpochConfig = field(default_factory=EpochConfig)
    target_sfreq: float = 200.0
    artifact: ArtifactConfig = field(default_factory=ArtifactConfig)

    # ---- derived quantities ----
    @property
    def decim(self) -> int:
        ratio = self.native_sfreq / self.target_sfreq
        if abs(ratio - round(ratio)) > 1e-9 or ratio < 1:
            raise ValueError(f"target_sfreq must divide native_sfreq exactly; got {self.target_sfreq}")
        return int(round(ratio))

    @property
    def epoch_offsets_native(self) -> tuple[int, int]:
        """Window [start, stop) in native samples relative to pair onset."""
        start = int(round(self.epoch.tmin * self.native_sfreq))
        stop = int(round(self.epoch.tmax * self.native_sfreq))
        return start, stop

    @property
    def n_times(self) -> int:
        start, stop = self.epoch_offsets_native
        return len(range(0, stop - start, self.decim))

    def to_dict(self) -> dict:
        return asdict(self)

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:12]

    def validate(self) -> None:
        f = self.filter
        if not 0 < f.l_freq < f.h_freq:
            raise ValueError("filter: need 0 < l_freq < h_freq")
        if f.h_freq + f.h_trans_bandwidth > self.target_sfreq / 2:
            raise ValueError("low-pass stop band must lie below the Nyquist frequency of target_sfreq")
        if self.epoch.tmax <= self.epoch.tmin:
            raise ValueError("epoch: tmax must exceed tmin")
        if self.reference != "average":
            raise ValueError("only the common average reference is implemented")
        _ = self.decim


def load_config(path: str | Path) -> PreprocessConfig:
    raw = yaml.safe_load(Path(path).read_text())
    cfg = PreprocessConfig(
        **{k: v for k, v in raw.items() if k not in {"filter", "bad_channels", "epoch", "artifact"}},
        filter=FilterConfig(**raw.get("filter", {})),
        bad_channels=BadChannelConfig(**raw.get("bad_channels", {})),
        epoch=EpochConfig(**raw.get("epoch", {})),
        artifact=ArtifactConfig(**raw.get("artifact", {})),
    )
    cfg.validate()
    return cfg
