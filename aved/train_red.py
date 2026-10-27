"""Chapter 1 training: averaged-input teacher and RED student variants for one fold.

Teacher: EEGNet trained on k-trial averages of an averaging group (same subject, session, character
and bit position: identical label and neighbouring-trial context). New random subsets are drawn
every epoch; k is sampled from ``k_set``. Trained once per fold and cached; all variants share it.

Student losses (switched on per variant, see configs/red.yaml):
    ce        cross-entropy on the single-trial label (always on)
    n2n       ||recon(x) - a||^2 + beta * ||P recon(x) - P a||^2, where a is the leave-one-out
              average of x's group (never contains x; noise independent of x), or the subject's
              class-mean ERP for target 'class_mean'; P maps channels to left-minus-right
              hemisphere differences of the mirror pairs
    critic    CE(teacher(recon(x)), y) + tau^2 KL(softmax(teacher(recon(x))/tau) || softmax(student(x)/tau)):
              the frozen teacher judges the student's own reconstruction, and its verdict on that
              reachable signal is distilled into the student's classifier
    kd_naive  tau^2 KL(softmax(teacher(a)/tau) || softmax(student(x)/tau)): classic distillation from
              the teacher's view of the averaged signal (ablation; expected to transfer poorly)
"""

from __future__ import annotations

import copy
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .data import Dataset, Fold
from .models.eegnet import EEGNet
from .models.red import REDStudent
from .train import channel_stats, set_seed

MIRROR_PAIRS = [("P7", "P8"), ("P5", "P6"), ("P3", "P4"), ("P1", "P2"), ("PO7", "PO8"),
                ("PO5", "PO6"), ("PO3", "PO4"), ("O1", "O2"), ("CB1", "CB2")]


# ----------------------------------------------------------------------------------------------
# averaging groups
# ----------------------------------------------------------------------------------------------

class GroupBank:
    """Members of each averaging group as a padded (G, M) index matrix into a trial array."""

    def __init__(self, group: np.ndarray, device: torch.device):
        ids, inv, counts = np.unique(group, return_inverse=True, return_counts=True)
        M = counts.max()
        members = np.full((len(ids), M), -1)
        order = np.argsort(inv, kind="stable")
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
        for g, (s, c) in enumerate(zip(starts, counts)):
            members[g, :c] = order[s:s + c]
        self.members = torch.as_tensor(members, device=device)
        self.counts = torch.as_tensor(counts, device=device)
        self.trial_group = torch.as_tensor(inv, device=device)

    def sample_averages(self, X: torch.Tensor, y: torch.Tensor, k_set, gen: torch.Generator):
        """One random k-subset average per group with >= 2 members; k ~ uniform(k_set), capped at group size."""
        ok = self.counts >= 2
        members, counts = self.members[ok], self.counts[ok]
        G, M = members.shape
        dev = members.device
        k_choices = torch.as_tensor(k_set, device=dev)
        k = k_choices[torch.randint(len(k_set), (G,), generator=gen).to(dev)]
        k = torch.minimum(k, counts)
        keys = torch.rand(G, M, generator=gen).to(dev).masked_fill(members < 0, 2.0)
        rank = keys.argsort(1).argsort(1)
        w = (rank < k[:, None]).float() / k[:, None]
        Xm = X[members.clamp(min=0)]                                   # (G, M, C, T)
        return torch.einsum("gm,gmct->gct", w, Xm), y[members[:, 0]]

    def loo_targets(self, X: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Leave-one-out group average for every trial, and a validity mask (group size >= 2)."""
        sums = torch.zeros((len(self.counts),) + X.shape[1:], device=X.device).index_add_(0, self.trial_group, X)
        n = self.counts[self.trial_group].float()
        valid = n >= 2
        loo = (sums[self.trial_group] - X) / (n - 1).clamp(min=1)[:, None, None]
        return loo, valid


def fixed_averages(X: torch.Tensor, y: torch.Tensor, bank: GroupBank, k: int, seed: int, draws: int = 1):
    gen = torch.Generator().manual_seed(seed)
    outs = [bank.sample_averages(X, y, [k], gen) for _ in range(draws)]
    return torch.cat([o[0] for o in outs]), torch.cat([o[1] for o in outs])


# ----------------------------------------------------------------------------------------------
# teacher
# ----------------------------------------------------------------------------------------------

def train_teacher(fold: Fold, ds: Dataset, norm, model_cfg: dict, train_cfg: dict, tcfg: dict,
                  device: torch.device, seed: int, log=print) -> tuple[EEGNet, dict]:
    set_seed(seed + 1000)
    tr, va, te = fold.masks(ds)
    mean, std = norm
    X = torch.from_numpy((ds.X - mean[:, None]) / std[:, None]).to(device)
    y = torch.from_numpy(ds.y).to(device)
    banks = {name: GroupBank(ds.group[m], device) for name, m in (("tr", tr), ("va", va), ("te", te))}
    idx = {name: torch.as_tensor(np.flatnonzero(m), device=device) for name, m in (("tr", tr), ("va", va), ("te", te))}
    Xva, yva = fixed_averages(X[idx["va"]], y[idx["va"]], banks["va"], tcfg["val_k"], seed, draws=3)

    model = EEGNet(ds.X.shape[1], ds.X.shape[2], dropout=train_cfg["dropout"], **model_cfg).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=train_cfg["lr"])
    gen = torch.Generator().manual_seed(seed + 1000)
    bs = train_cfg["batch_size"]
    best = {"val_loss": np.inf, "epoch": -1, "state": None}
    t0 = time.perf_counter()
    for epoch in range(1, tcfg["max_epochs"] + 1):
        model.train()
        Xa, ya = zip(*[banks["tr"].sample_averages(X[idx["tr"]], y[idx["tr"]], tcfg["k_set"], gen)
                       for _ in range(tcfg["draws_per_epoch"])])
        Xa, ya = torch.cat(Xa), torch.cat(ya)
        perm = torch.randperm(len(ya), generator=gen).to(device)
        for i in range(0, len(perm), bs):
            b = perm[i:i + bs]
            if len(b) < 2:
                continue
            opt.zero_grad(set_to_none=True)
            F.cross_entropy(model(Xa[b]), ya[b]).backward()
            opt.step()
            model.apply_max_norm()
        val_loss, val_acc = _eval(model, Xva, yva)
        if val_loss < best["val_loss"]:
            best = {"val_loss": val_loss, "epoch": epoch, "state": copy.deepcopy(model.state_dict())}
        if epoch % 25 == 0 or epoch == 1:
            log(f"  [teacher] epoch {epoch:3d} val_loss {val_loss:.4f} val_acc(avg{tcfg['val_k']}) {val_acc:.3f}")
        if epoch - best["epoch"] >= tcfg["patience"]:
            break
    model.load_state_dict(best["state"])
    model.eval()
    info = {"teacher_best_epoch": best["epoch"], "teacher_train_time_s": round(time.perf_counter() - t0, 1),
            "teacher_val_acc_avg": _eval(model, Xva, yva)[1]}
    for k in (1, 3, 6):    # teacher accuracy on test-session averages of k trials (k=1: single trials)
        Xt, yt = (X[idx["te"]], y[idx["te"]]) if k == 1 else fixed_averages(X[idx["te"]], y[idx["te"]], banks["te"], k, seed, 3)
        info[f"teacher_test_acc_avg{k}"] = _eval(model, Xt, yt)[1]
    log(f"  [teacher] best epoch {best['epoch']}, test acc single/avg3/avg6: "
        f"{info['teacher_test_acc_avg1']:.3f} / {info['teacher_test_acc_avg3']:.3f} / {info['teacher_test_acc_avg6']:.3f}")
    return model, info


@torch.no_grad()
def _eval(model, X, y, bs: int = 2048) -> tuple[float, float]:
    model.eval()
    logits = torch.cat([model(X[i:i + bs]) for i in range(0, len(y), bs)])
    return F.cross_entropy(logits, y).item(), float((logits.argmax(1) == y).float().mean())


# ----------------------------------------------------------------------------------------------
# student
# ----------------------------------------------------------------------------------------------

def lateral_operator(ch_names: list[str], device) -> torch.Tensor:
    P = torch.zeros(len(MIRROR_PAIRS), len(ch_names), device=device)
    for i, (a, b) in enumerate(MIRROR_PAIRS):
        P[i, ch_names.index(a)], P[i, ch_names.index(b)] = 1.0, -1.0
    return P


def train_red(fold: Fold, ds: Dataset, cfg: dict, variant: dict, device: torch.device, seed: int,
              teacher_cache: Path, log=print) -> dict:
    """Train the teacher (or load it from ``teacher_cache``) and one student variant on one fold."""
    tr, va, te = fold.masks(ds)
    mean, std = channel_stats(ds.X[tr])
    model_cfg, train_cfg = cfg["model"], cfg["training"]

    needs_teacher = variant["critic"] or variant["kd_naive"]
    teacher, tinfo = None, {}
    if needs_teacher or cfg["teacher"].get("always_train", True):
        if teacher_cache.exists():
            ck = torch.load(teacher_cache, map_location=device, weights_only=False)
            teacher = EEGNet(ds.X.shape[1], ds.X.shape[2], dropout=train_cfg["dropout"], **model_cfg).to(device)
            teacher.load_state_dict(ck["state_dict"])
            teacher.eval()
            tinfo = ck["info"]
            log(f"  [teacher] loaded {teacher_cache.name}")
        else:
            teacher, tinfo = train_teacher(fold, ds, (mean, std), model_cfg, train_cfg, cfg["teacher"], device, seed, log)
            teacher_cache.parent.mkdir(parents=True, exist_ok=True)
            torch.save({"state_dict": teacher.state_dict(), "info": tinfo, "channel_mean": mean, "channel_std": std,
                        "model_cfg": model_cfg, "dropout": train_cfg["dropout"], "fold": fold.name}, teacher_cache)
        for p in teacher.parameters():
            p.requires_grad_(False)

    set_seed(seed)
    X = torch.from_numpy((ds.X - mean[:, None]) / std[:, None]).to(device)
    y = torch.from_numpy(ds.y).to(device)
    itr, iva, ite = (torch.as_tensor(np.flatnonzero(m), device=device) for m in (tr, va, te))
    Xtr, ytr = X[itr], y[itr]
    bank = GroupBank(ds.group[tr], device)
    if variant["target"] == "group_loo":
        target, valid = bank.loo_targets(Xtr)
    elif variant["target"] == "class_mean":
        target, valid = _class_mean_targets(Xtr, ytr, ds.subject[tr]), torch.ones(len(ytr), dtype=torch.bool, device=device)
    else:
        raise ValueError(variant["target"])
    P = lateral_operator(ds.ch_names, device)

    student = REDStudent(ds.X.shape[1], ds.X.shape[2], dropout=train_cfg["dropout"], **model_cfg).to(device)
    opt = torch.optim.Adam(student.parameters(), lr=train_cfg["lr"])
    gen = torch.Generator().manual_seed(seed)
    bs, tau, lam = train_cfg["batch_size"], cfg["loss"]["tau"], cfg["loss"]
    best = {"val_loss": np.inf, "epoch": -1, "state": None}
    history = []
    t0 = time.perf_counter()
    for epoch in range(1, train_cfg["max_epochs"] + 1):
        student.train()
        perm = torch.randperm(len(ytr), generator=gen).to(device)
        sums = {"ce": 0.0, "n2n": 0.0, "critic": 0.0, "kd": 0.0}
        for i in range(0, len(perm), bs):
            b = perm[i:i + bs]
            if len(b) < 2:
                continue
            logits, recon = student(Xtr[b])
            loss = F.cross_entropy(logits, ytr[b])
            sums["ce"] += loss.item() * len(b)
            if variant["n2n"]:
                v = valid[b]
                if v.any():
                    r, t = recon[v], target[b][v]
                    l_rec = F.mse_loss(r, t) + lam["beta_lateral"] * F.mse_loss(P @ r, P @ t)
                    loss = loss + lam["lambda_n2n"] * l_rec
                    sums["n2n"] += l_rec.item() * len(b)
            if variant["critic"]:
                t_logits = teacher(recon)
                l_crit = F.cross_entropy(t_logits, ytr[b]) + tau ** 2 * _kd(logits, t_logits.detach(), tau)
                loss = loss + lam["lambda_critic"] * l_crit
                sums["critic"] += l_crit.item() * len(b)
            if variant["kd_naive"]:
                v = valid[b]
                if v.any():
                    with torch.no_grad():
                        t_logits = teacher(target[b][v])
                    l_kd = tau ** 2 * _kd(logits[v], t_logits, tau)
                    loss = loss + lam["lambda_kd"] * l_kd
                    sums["kd"] += l_kd.item() * len(b)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            student.apply_max_norm()
        val_loss, val_acc = _eval(student.eegnet, X[iva], y[iva])
        history.append({"epoch": epoch, **{f"train_{k}": v / len(ytr) for k, v in sums.items()},
                        "val_loss": val_loss, "val_acc": val_acc})
        if val_loss < best["val_loss"]:
            best = {"val_loss": val_loss, "epoch": epoch, "state": copy.deepcopy(student.state_dict())}
        if epoch % 25 == 0 or epoch == 1:
            log(f"  epoch {epoch:3d} ce {history[-1]['train_ce']:.4f} n2n {history[-1]['train_n2n']:.4f} "
                f"critic {history[-1]['train_critic']:.4f} kd {history[-1]['train_kd']:.4f} "
                f"val_loss {val_loss:.4f} val_acc {val_acc:.3f}")
        if epoch - best["epoch"] >= train_cfg["patience"]:
            log(f"  early stop at epoch {epoch} (best {best['epoch']})")
            break
    train_time = time.perf_counter() - t0
    student.load_state_dict(best["state"])
    student.eval()

    with torch.no_grad():
        logits = torch.cat([student(X[ite][i:i + 2048])[0] for i in range(0, len(ite), 2048)])
        prob = torch.softmax(logits, 1)[:, 1].cpu().numpy()
        rec_info = _reconstruction_quality(student, X[ite], ds.group[te], P, device)
    info = {"best_epoch": best["epoch"], "epochs_run": len(history), "val_acc": _eval(student.eegnet, X[iva], y[iva])[1],
            "train_time_s": round(train_time, 1), "n_train": int(tr.sum()), "n_val": int(va.sum()),
            "n_test": int(te.sum()), **tinfo, **rec_info}
    return {
        "test_mask": te, "score": prob, "pred": (prob > 0.5).astype(np.int64), "info": info, "history": history,
        "checkpoint": {"state_dict": student.state_dict(), "channel_mean": mean, "channel_std": std,
                       "model_cfg": model_cfg, "train_cfg": train_cfg, "variant": variant, "n_channels": ds.X.shape[1],
                       "n_times": ds.X.shape[2], "fold": fold.name, "student": True},
    }


def _kd(student_logits, teacher_logits, tau):
    return F.kl_div(F.log_softmax(student_logits / tau, 1), F.softmax(teacher_logits / tau, 1), reduction="batchmean")


def _class_mean_targets(X, y, subject) -> torch.Tensor:
    """Context-marginalised target: the subject's class-mean ERP over all training trials."""
    out = torch.empty_like(X)
    subject = torch.as_tensor(subject, device=X.device)
    for s in subject.unique():
        for k in (0, 1):
            m = (subject == s) & (y == k)
            out[m] = X[m].mean(0)
    return out


@torch.no_grad()
def _reconstruction_quality(student, Xte, group_te, P, device) -> dict:
    """How well single-trial reconstructions match the leave-one-out average of the test trial's group.

    R^2 = 1 - MSE(recon, a) / MSE(0, a) on all channels and on the left-right difference signals;
    the a's noise is independent of the input, so this measures recovery of the group ERP from one trial.
    """
    bank = GroupBank(group_te, device)
    a, valid = bank.loo_targets(Xte)
    recon = torch.cat([student(Xte[i:i + 2048])[1] for i in range(0, len(Xte), 2048)])[valid]
    a = a[valid]
    r2 = 1 - F.mse_loss(recon, a).item() / a.pow(2).mean().item()
    r2_lat = 1 - F.mse_loss(P @ recon, P @ a).item() / (P @ a).pow(2).mean().item()
    return {"recon_r2_test": round(r2, 4), "recon_r2_lateral_test": round(r2_lat, 4)}
