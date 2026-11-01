"""Chapter 2, C2.1: Lateralisation-Routed Mixture-of-Experts (LR-MoE).

Hemispheric decomposition with the montage mirror operator M (left <-> right channel pairs, midline fixed):
    x_a = (x - Mx) / 2   antisymmetric stream (lateralised activity; x_a(Mx) = -x_a(x))
    x_s = (x + Mx) / 2   symmetric stream     (x_s(Mx) = x_s(x))
Mirroring a left->right trial produces a right->left trial, i.e. flips the label.

Experts (each a small EEGNet producing 2 logits), optionally with a temporal shift d (latency variant):
    anti  out = (f(x_a shifted) - f(-x_a shifted)) / 2   exactly mirror-equivariant: logits(Mx) = -logits(x)
    sym   out = f(x_s shifted)                           mirror-invariant (subjects without lateralised coding)
    full  out = f(x shifted)                             unconstrained
Router:
    physio  MLP on mirror-invariant physiological descriptors (energy of x_a and x_s in time windows, their ratio,
            |log left/right power|, 10 Hz occipital amplitude); routing(Mx) = routing(x)
    generic MLP on learned EEGNet features (conventional MoE gate)
    none    single expert (plain EEGNet)
Output logits = sum_k gate_k * logits_k.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from .eegnet import EEGNet

MIRROR_PAIRS = [("P7", "P8"), ("P5", "P6"), ("P3", "P4"), ("P1", "P2"), ("PO7", "PO8"), ("PO5", "PO6"),
                ("PO3", "PO4"), ("O1", "O2"), ("CB1", "CB2")]


def mirror_index(ch_names: list[str]) -> list[int]:
    idx = list(range(len(ch_names)))
    for a, b in MIRROR_PAIRS:
        i, j = ch_names.index(a), ch_names.index(b)
        idx[i], idx[j] = j, i
    return idx


def time_shift(x: torch.Tensor, d: int) -> torch.Tensor:
    """Delay (d > 0) or advance x (..., T) by d samples with edge padding."""
    if d == 0:
        return x
    T = x.shape[-1]
    idx = torch.clamp(torch.arange(T, device=x.device) - d, 0, T - 1)
    return x[..., idx]


class Expert(nn.Module):
    def __init__(self, kind: str, shift: int, n_channels: int, n_times: int, **eegnet_kw):
        super().__init__()
        self.kind, self.shift = kind, shift
        self.net = EEGNet(n_channels, n_times, **eegnet_kw)

    def forward(self, x, xa, xs):
        if self.kind == "anti":
            z = time_shift(xa, self.shift)
            return (self.net(z) - self.net(-z)) / 2
        return self.net(time_shift(xs if self.kind == "sym" else x, self.shift))


class LRMoE(nn.Module):
    def __init__(self, ch_names: list[str], n_times: int, sfreq: float, experts: list[tuple[str, int]],
                 router: str = "physio", n_windows: int = 5, router_hidden: int = 16, **eegnet_kw):
        super().__init__()
        C = len(ch_names)
        self.register_buffer("mirror", torch.as_tensor(mirror_index(ch_names)))
        left = [ch_names.index(a) for a, _ in MIRROR_PAIRS]
        right = [ch_names.index(b) for _, b in MIRROR_PAIRS]
        self.register_buffer("left", torch.as_tensor(left))
        self.register_buffer("right", torch.as_tensor(right))
        self.register_buffer("occ", torch.as_tensor([ch_names.index(c) for c in ("O1", "OZ", "O2")]))
        self.n_windows = n_windows
        self.f10 = int(round(10.0 * n_times / sfreq))                      # rFFT bin closest to 10 Hz
        self.experts = nn.ModuleList([Expert(k, d, C, n_times, **eegnet_kw) for k, d in experts])
        self.router_kind = router if len(experts) > 1 else "none"
        if self.router_kind == "physio":
            n_desc = 2 * n_windows + 3
            self.router = nn.Sequential(nn.LayerNorm(n_desc), nn.Linear(n_desc, router_hidden), nn.ELU(),
                                        nn.Linear(router_hidden, len(experts)))
        elif self.router_kind == "generic":
            self.gate_net = EEGNet(C, n_times, **eegnet_kw)
            with torch.no_grad():
                n_feat = self.gate_net.features(torch.zeros(1, C, n_times)).shape[1]
            self.router = nn.Linear(n_feat, len(experts))

    def streams(self, x):
        xm = x[:, self.mirror]
        return (x - xm) / 2, (x + xm) / 2

    def descriptors(self, x, xa, xs):
        """Mirror-invariant physiological descriptors (B, 2 * n_windows + 3)."""
        def win_energy(z):
            chunks = torch.tensor_split(z.pow(2).mean(1), self.n_windows, dim=-1)
            return torch.stack([c.mean(-1) for c in chunks], 1)
        ea, es = win_energy(xa), win_energy(xs)
        ratio = torch.log(ea.sum(1) + 1e-6) - torch.log(es.sum(1) + 1e-6)
        pl, pr = x[:, self.left].pow(2).mean((1, 2)), x[:, self.right].pow(2).mean((1, 2))
        lr = (torch.log(pl + 1e-6) - torch.log(pr + 1e-6)).abs()
        a10 = torch.fft.rfft(x[:, self.occ], dim=-1)[..., self.f10].abs().mean(1)
        return torch.cat([torch.log(ea + 1e-6), torch.log(es + 1e-6), ratio[:, None], lr[:, None],
                          torch.log(a10 + 1e-6)[:, None]], 1)

    def gates(self, x, xa=None, xs=None):
        if self.router_kind == "none":
            return torch.ones(len(x), 1, device=x.device)
        if xa is None:
            xa, xs = self.streams(x)
        if self.router_kind == "physio":
            return torch.softmax(self.router(self.descriptors(x, xa, xs)), 1)
        return torch.softmax(self.router(self.gate_net.features(x)), 1)

    def forward(self, x, gates: torch.Tensor | None = None):
        """Returns (logits, gates). ``gates`` overrides the router (e.g. subject-averaged routing)."""
        xa, xs = self.streams(x)
        g = self.gates(x, xa, xs) if gates is None else gates
        out = torch.stack([e(x, xa, xs) for e in self.experts], 1)        # (B, K, 2)
        return (g[:, :, None] * out).sum(1), g

    def apply_max_norm(self):
        for e in self.experts:
            e.net.apply_max_norm()
        if self.router_kind == "generic":
            self.gate_net.apply_max_norm()


# method name -> (experts, router, losses)
SHIFTS = (-4, 0, 4)                                  # +/- 20 ms at 200 Hz
VARIANTS = {
    "eegnet_sz":        {"experts": [("full", 0)], "router": "none"},
    "eegnet_mirroraug": {"experts": [("full", 0)], "router": "none", "mirror_aug": True},
    "lrmoe":            {"experts": [("anti", d) for d in SHIFTS] + [("sym", d) for d in SHIFTS] + [("full", 0)],
                         "router": "physio"},
    "lrmoe_generic":    {"experts": [("full", 0)] * 7, "router": "generic"},
    "lrmoe_nodecomp":   {"experts": [("full", d) for d in SHIFTS] * 2 + [("full", 0)], "router": "physio"},
    "lrmoe_nolat":      {"experts": [("anti", 0), ("sym", 0), ("full", 0)], "router": "physio"},
    "lrmoe_nocoh":      {"experts": [("anti", d) for d in SHIFTS] + [("sym", d) for d in SHIFTS] + [("full", 0)],
                         "router": "physio", "lambda_coh": 0.0},
    "lrmoe_anti":       {"experts": [("anti", d) for d in SHIFTS], "router": "physio"},
}
