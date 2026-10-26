"""Training and evaluation for one fold: EEGNet (gradient descent) and DCPM (closed form)."""

from __future__ import annotations

import copy
import time

import numpy as np
import torch
import torch.nn as nn

from .data import Dataset, Fold
from .models.dcpm import DCPM
from .models.eegnet import EEGNet


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def resolve_device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if name.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but torch.cuda.is_available() is False "
                           "(install a CUDA build of PyTorch, see docs/running_experiments.md)")
    return torch.device(name)


def channel_stats(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-channel mean and std over trials and time (training data only)."""
    return X.mean(axis=(0, 2)).astype(np.float32), X.std(axis=(0, 2)).astype(np.float32)


def train_eegnet(fold: Fold, ds: Dataset, model_cfg: dict, train_cfg: dict, device: torch.device,
                 seed: int, log=print) -> dict:
    set_seed(seed)
    tr, va, te = fold.masks(ds)
    mean, std = channel_stats(ds.X[tr])

    def tensor(mask):
        X = torch.from_numpy((ds.X[mask] - mean[:, None]) / std[:, None]).to(device)
        return X, torch.from_numpy(ds.y[mask]).to(device)

    (Xtr, ytr), (Xva, yva), (Xte, yte) = tensor(tr), tensor(va), tensor(te)
    model = EEGNet(ds.X.shape[1], ds.X.shape[2], dropout=train_cfg["dropout"], **model_cfg).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=train_cfg["lr"], weight_decay=train_cfg.get("weight_decay", 0.0))
    loss_fn = nn.CrossEntropyLoss()
    gen = torch.Generator(device="cpu").manual_seed(seed)
    bs = train_cfg["batch_size"]

    best = {"val_loss": np.inf, "epoch": -1, "state": None}
    history = []
    t0 = time.perf_counter()
    for epoch in range(1, train_cfg["max_epochs"] + 1):
        model.train()
        perm = torch.randperm(len(ytr), generator=gen).to(device)
        total = 0.0
        for i in range(0, len(perm), bs):
            idx = perm[i:i + bs]
            if len(idx) < 2:          # BatchNorm needs > 1 sample
                continue
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(Xtr[idx]), ytr[idx])
            loss.backward()
            opt.step()
            model.apply_max_norm()
            total += loss.item() * len(idx)
        val_loss, val_acc, _ = _evaluate(model, Xva, yva, loss_fn, bs * 8)
        history.append({"epoch": epoch, "train_loss": total / len(ytr), "val_loss": val_loss, "val_acc": val_acc})
        if val_loss < best["val_loss"]:
            best = {"val_loss": val_loss, "epoch": epoch, "state": copy.deepcopy(model.state_dict())}
        if epoch % 10 == 0 or epoch == 1:
            log(f"  epoch {epoch:3d} train_loss {history[-1]['train_loss']:.4f} "
                f"val_loss {val_loss:.4f} val_acc {val_acc:.3f}")
        if epoch - best["epoch"] >= train_cfg["patience"]:
            log(f"  early stop at epoch {epoch} (best {best['epoch']})")
            break
    train_time = time.perf_counter() - t0

    model.load_state_dict(best["state"])
    _, val_acc, _ = _evaluate(model, Xva, yva, loss_fn, bs * 8)
    test_loss, test_acc, prob = _evaluate(model, Xte, yte, loss_fn, bs * 8)
    return {
        "test_mask": te, "score": prob, "pred": (prob > 0.5).astype(np.int64),
        "info": {"best_epoch": best["epoch"], "epochs_run": len(history), "val_acc": val_acc,
                 "test_loss": test_loss, "train_time_s": round(train_time, 1),
                 "n_train": int(tr.sum()), "n_val": int(va.sum()), "n_test": int(te.sum())},
        "history": history,
        "checkpoint": {"state_dict": model.state_dict(), "channel_mean": mean, "channel_std": std,
                       "model_cfg": model_cfg, "train_cfg": train_cfg, "n_channels": ds.X.shape[1],
                       "n_times": ds.X.shape[2], "fold": fold.name},
    }


@torch.no_grad()
def _evaluate(model, X, y, loss_fn, bs) -> tuple[float, float, np.ndarray]:
    model.eval()
    logits = torch.cat([model(X[i:i + bs]) for i in range(0, len(y), bs)])
    prob = torch.softmax(logits, 1)[:, 1].cpu().numpy()
    return loss_fn(logits, y).item(), float((logits.argmax(1) == y).float().mean()), prob


def train_dcpm(fold: Fold, ds: Dataset, cfg: dict, log=print) -> dict:
    """Select the number of DSP components on the validation data, keep the model fitted on training data."""
    tr, va, te = fold.masks(ds)
    t0 = time.perf_counter()
    val_accs, models = {}, {}
    for m in cfg["n_components_grid"]:
        clf = DCPM(m, cfg["context"], cfg["reg"]).fit(ds.X[tr], ds.y[tr], ds.prev_y[tr], ds.next_y[tr])
        val_accs[m] = float((clf.predict(ds.X[va]) == ds.y[va]).mean())
        models[m] = clf
    best_m = max(val_accs, key=lambda m: (val_accs[m], -m))         # ties -> fewer components
    clf = models[best_m]
    score = clf.decision_function(ds.X[te])
    log(f"  val acc by n_components {val_accs} -> {best_m}")
    return {
        "test_mask": te, "score": score, "pred": (score > 0).astype(np.int64),
        "info": {"n_components": best_m, "val_acc": val_accs[best_m], "val_acc_grid": val_accs,
                 "train_time_s": round(time.perf_counter() - t0, 1),
                 "n_train": int(tr.sum()), "n_val": int(va.sum()), "n_test": int(te.sum())},
        "history": None,
        "checkpoint": {"model": clf, "cfg": cfg, "fold": fold.name},
    }


def load_checkpoint(path) -> dict:
    """Load a checkpoint written by scripts/run_baseline.py.

    For EEGNet, ``ckpt["model"]`` is a ready-to-use EEGNet in eval mode; inputs must be normalised with
    ``(X - ckpt["channel_mean"][:, None]) / ckpt["channel_std"][:, None]``. For DCPM, ``ckpt["model"]``
    is the fitted DCPM. Only load checkpoints you created yourself (they are pickled).
    """
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    if "state_dict" in ckpt:
        model = EEGNet(ckpt["n_channels"], ckpt["n_times"], dropout=ckpt["train_cfg"]["dropout"], **ckpt["model_cfg"])
        model.load_state_dict(ckpt["state_dict"])
        ckpt["model"] = model.eval()
    return ckpt
