"""Chapter 1: Recoverable-ERP Distillation (RED) — student network with an ERP reconstruction head.

The student is an unmodified EEGNet (used alone at inference) plus a training-only decoder that maps
the block-1 output (F1*D virtual-source time courses at times/pool1 resolution) back to the
channels x times ERP:

    recon[c, t] = sum_j A[c, j] * (h1[j, :] @ U)[t] + b[c]

U (times/pool1 -> times) upsamples each virtual source in time; A (channels x virtual sources) is a
learned forward model (spatial patterns). The decoder is linear, so the reconstruction is forced to
live in the subspace spanned by EEGNet's own spatial filters.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from .eegnet import EEGNet


class LinearERPDecoder(nn.Module):
    def __init__(self, n_sources: int, n_down: int, n_channels: int, n_times: int):
        super().__init__()
        self.upsample = nn.Linear(n_down, n_times, bias=False)
        self.forward_model = nn.Linear(n_sources, n_channels)

    def forward(self, h1: torch.Tensor) -> torch.Tensor:
        z = self.upsample(h1.squeeze(2))                          # (B, sources, T)
        return self.forward_model(z.transpose(1, 2)).transpose(1, 2)   # (B, C, T)


class REDStudent(nn.Module):
    def __init__(self, n_channels: int, n_times: int, **eegnet_kwargs):
        super().__init__()
        self.eegnet = EEGNet(n_channels, n_times, **eegnet_kwargs)
        with torch.no_grad():
            h1, _ = self.eegnet.encode(torch.zeros(1, n_channels, n_times))
        self.decoder = LinearERPDecoder(h1.shape[1], h1.shape[3], n_channels, n_times)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns (logits, reconstruction)."""
        h1, feat = self.eegnet.encode(x)
        return self.eegnet.classifier(feat), self.decoder(h1)

    def apply_max_norm(self) -> None:
        self.eegnet.apply_max_norm()
