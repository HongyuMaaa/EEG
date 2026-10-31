"""Chapter 1, direction 1: label-free adaptation of a cross-subject model to a new subject.

The target subject's adaptation trials are unlabelled, but their repetition groups are known from the stimulus
timing (session, character position, bit position): the 6 repetitions of a code bit share their (unknown) label
and context. Two label-free signals follow:
  * Noise2Noise reconstruction (leave-one-out group averages as targets) - the RED objective without labels;
  * group agreement - all members of a group must receive the same label.

Adaptation methods (all start from the same source model, use a fixed budget, never see target labels):
  source    no adaptation
  adabn     re-estimate BatchNorm statistics on the target's adaptation trials (standard baseline)
  tent      adabn + entropy minimisation with a class-diversity term, BatchNorm affine parameters only (baseline)
  n2n       adabn + Noise2Noise reconstruction on target groups (encoder + decoder; classifier frozen)
  gpl       adabn + group pseudo-labels: label of a group = argmax of its members' mean prediction (refreshed
            every epoch, groups with mean confidence >= 0.6), cross-entropy on members + class-diversity term
  n2n_gpl   n2n and gpl losses together
  oracle    supervised fine-tuning with the TRUE labels of the adaptation trials (upper reference, not a method)
"""

from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .train_red import GroupBank

ADAPT_METHODS = ("source", "adabn", "tent", "n2n", "gpl", "n2n_gpl", "oracle")


@torch.no_grad()
def predict_proba(model, X, bs=2048) -> torch.Tensor:
    model.eval()
    return torch.cat([torch.softmax(model(X[i:i + bs])[0], 1) for i in range(0, len(X), bs)])


@torch.no_grad()
def adabn(model, X, bs=256) -> None:
    """Re-estimate BatchNorm running statistics on X (cumulative average), everything else in eval mode."""
    model.eval()
    bns = [m for m in model.modules() if isinstance(m, nn.BatchNorm2d)]
    for m in bns:
        m.reset_running_stats()
        m.momentum = None
        m.train()
    for i in range(0, len(X), bs):
        model(X[i:i + bs])
    model.eval()


def _diversity(p: torch.Tensor) -> torch.Tensor:
    """Negative entropy of the batch-mean prediction (minimising it keeps both classes in use)."""
    pm = p.mean(0)
    return (pm * torch.log(pm + 1e-8)).sum()


def adapt(source, method: str, Xa: torch.Tensor, groups: np.ndarray, ya: torch.Tensor | None, cfg: dict,
          seed: int):
    """Return an adapted copy of ``source``. Xa: adaptation trials (normalised); ya only used by 'oracle'."""
    model = copy.deepcopy(source)
    if method == "source":
        return model
    adabn(model, Xa)
    if method == "adabn":
        return model

    torch.manual_seed(seed)
    if method == "tent":
        params = [p for m in model.modules() if isinstance(m, nn.BatchNorm2d) for p in m.parameters()]
    elif method == "oracle":
        params = list(model.eegnet.parameters())
    else:   # encoder (+ decoder); the classifier stays fixed so the decision space of the source model is kept
        params = [p for n, p in model.named_parameters() if not n.startswith("eegnet.classifier")]
    for p in model.parameters():
        p.requires_grad_(False)
    for p in params:
        p.requires_grad_(True)
    opt = torch.optim.Adam(params, lr=cfg["lr"])
    bank = GroupBank(groups, Xa.device)
    loo, valid = bank.loo_targets(Xa)
    gidx = bank.trial_group
    gen = torch.Generator().manual_seed(seed)
    bs = cfg["batch_size"]
    for _ in range(cfg["epochs"]):
        pseudo, keep = None, None
        if method in ("gpl", "n2n_gpl"):
            p = predict_proba(model, Xa)
            gp = torch.zeros(len(bank.counts), 2, device=Xa.device).index_add_(0, gidx, p) / bank.counts[:, None]
            conf, lab = gp.max(1)
            pseudo, keep = lab[gidx], (conf >= cfg["gpl_threshold"])[gidx]
        model.eval()    # fixed (adapted) BatchNorm statistics, no dropout
        perm = torch.randperm(len(Xa), generator=gen).to(Xa.device)
        for i in range(0, len(perm), bs):
            b = perm[i:i + bs]
            logits, recon = model(Xa[b])
            p = torch.softmax(logits, 1)
            loss = torch.zeros((), device=Xa.device)
            if method == "tent":
                loss = -(p * torch.log(p + 1e-8)).sum(1).mean() + _diversity(p)
            if method == "oracle":
                loss = F.cross_entropy(logits, ya[b])
            if method in ("n2n", "n2n_gpl"):
                v = valid[b]
                if v.any():
                    loss = loss + cfg["lambda_n2n"] * F.mse_loss(recon[v], loo[b][v])
            if method in ("gpl", "n2n_gpl"):
                k = keep[b]
                if k.any():
                    loss = loss + F.cross_entropy(logits[k], pseudo[b][k]) + _diversity(p)
            if loss.requires_grad:
                opt.zero_grad(set_to_none=True)
                loss.backward()
                opt.step()
                model.apply_max_norm()
    model.eval()
    return model
