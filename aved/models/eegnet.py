"""EEGNet (Lawhern et al., J. Neural Eng. 2018), PyTorch port of the reference EEGNet-8,2.

Block 1: temporal conv (F1 kernels, length kern_length) -> BN -> depthwise spatial conv (D per kernel,
         max-norm 1) -> BN -> ELU -> AvgPool(1, pool1) -> Dropout
Block 2: depthwise temporal conv (length sep_length) + pointwise conv (F2) -> BN -> ELU
         -> AvgPool(1, pool2) -> Dropout
Head:    flatten -> linear (max-norm 0.25)
"""

from __future__ import annotations

import torch
import torch.nn as nn


class EEGNet(nn.Module):
    def __init__(self, n_channels: int, n_times: int, n_classes: int = 2, F1: int = 8, D: int = 2,
                 F2: int = 16, kern_length: int = 32, sep_length: int = 16, pool1: int = 4, pool2: int = 8,
                 dropout: float = 0.5, spatial_max_norm: float = 1.0, dense_max_norm: float = 0.25):
        super().__init__()
        self.spatial_max_norm, self.dense_max_norm = spatial_max_norm, dense_max_norm
        self.block1 = nn.Sequential(
            nn.ZeroPad2d((kern_length // 2 - 1, kern_length - kern_length // 2, 0, 0)),   # 'same' padding
            nn.Conv2d(1, F1, (1, kern_length), bias=False),
            nn.BatchNorm2d(F1),
        )
        self.spatial = nn.Conv2d(F1, F1 * D, (n_channels, 1), groups=F1, bias=False)
        self.block1b = nn.Sequential(
            nn.BatchNorm2d(F1 * D), nn.ELU(), nn.AvgPool2d((1, pool1)), nn.Dropout(dropout),
        )
        self.block2 = nn.Sequential(
            nn.ZeroPad2d((sep_length // 2 - 1, sep_length - sep_length // 2, 0, 0)),
            nn.Conv2d(F1 * D, F1 * D, (1, sep_length), groups=F1 * D, bias=False),
            nn.Conv2d(F1 * D, F2, 1, bias=False),
            nn.BatchNorm2d(F2), nn.ELU(), nn.AvgPool2d((1, pool2)), nn.Dropout(dropout),
            nn.Flatten(),
        )
        with torch.no_grad():
            n_feat = self.features(torch.zeros(1, n_channels, n_times)).shape[1]
        if n_feat == 0:
            raise ValueError(f"n_times={n_times} too short for pooling {pool1}x{pool2}")
        self.classifier = nn.Linear(n_feat, n_classes)

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """x: (batch, channels, times) -> (block-1 output (batch, F1*D, 1, times/pool1), features (batch, n_feat))."""
        h1 = self.block1b(self.spatial(self.block1(x.unsqueeze(1))))
        return h1, self.block2(h1)

    def features(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, channels, times) -> (batch, n_feat)."""
        return self.encode(x)[1]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))

    @torch.no_grad()
    def apply_max_norm(self) -> None:
        """Renormalise constrained weights after each optimiser step (Keras max_norm semantics)."""
        for w, c, dims in ((self.spatial.weight, self.spatial_max_norm, (1, 2, 3)),
                           (self.classifier.weight, self.dense_max_norm, (1,))):
            norm = torch.linalg.vector_norm(w, dim=dims, keepdim=True).clamp(min=1e-8)
            w.mul_(torch.clamp(c / norm, max=1.0))
