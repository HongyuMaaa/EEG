"""Discriminative Canonical Pattern Matching (Xu et al., IEEE TBME 2018, Sec. II-E).

1. DSP spatial filters W: generalised eigenvectors of S_B w = lambda S_w w with
   S_B = (X1_bar - X2_bar)(X1_bar - X2_bar)^T and S_w = sigma_1^2 + sigma_2^2 (paper Eqs. 3-8).
2. For a test trial Y and each class template X_k_bar, five coefficients (Eqs. 9-10):
   rho1 = corr(W'X_k, W'Y), rho2 = -||W'X_k - W'Y||_F, rho3 = first canonical correlation of
   (W'X_k, W'Y), rho4 = corr(U_k'W'X_k, U_k'W'Y), rho5 = corr(V_k'W'X_k, V_k'W'Y).
3. Score_k = sum of the five; prediction = argmax_k (Eqs. 11-12).

``context=True`` follows the paper's handling of overlapping ERPs: templates are built separately
for the codes preceding and following the trial. Four binary DCPMs are fitted on the opposite
context pairs '000' vs '111', '001' vs '110', '100' vs '011', '101' vs '010' (prev, current, next),
and their class scores are summed. Context is only needed for training; prediction uses the
test trial alone.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import eigh

CONTEXT_PAIRS = ((0, 0), (0, 1), (1, 0), (1, 1))    # (prev, next) of the code-0 pattern; code 1 uses (1-prev, 1-next)


def _center(X: np.ndarray) -> np.ndarray:
    return X - X.mean(axis=-1, keepdims=True)


def _corr(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Pearson correlation over all trailing elements; A, B broadcastable (..., m, T)."""
    a = A.reshape(*A.shape[:-2], -1)
    b = B.reshape(*B.shape[:-2], -1)
    a = a - a.mean(-1, keepdims=True)
    b = b - b.mean(-1, keepdims=True)
    return (a * b).sum(-1) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1) + 1e-12)


class BinaryDCPM:
    def __init__(self, n_components: int = 2, reg: float = 1e-6):
        self.n_components, self.reg = n_components, reg

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BinaryDCPM":
        X = _center(X.astype(np.float64))
        self.templates_ = np.stack([X[y == k].mean(0) for k in (0, 1)])        # (2, C, T)
        diff = self.templates_[0] - self.templates_[1]
        S_B = diff @ diff.T
        S_w = sum(
            np.einsum("nct,ndt->cd", X[y == k] - self.templates_[k], X[y == k] - self.templates_[k]) / np.sum(y == k)
            for k in (0, 1)
        )
        S_w += self.reg * np.trace(S_w) / len(S_w) * np.eye(len(S_w))
        evals, evecs = eigh(S_B, S_w)
        self.filters_ = evecs[:, np.argsort(evals)[::-1][: self.n_components]]  # (C, m)
        return self

    def scores(self, X: np.ndarray) -> np.ndarray:
        """Summed coefficients rho_k for each trial and class: (n, 2)."""
        W = self.filters_
        Y = np.einsum("cm,nct->nmt", W, _center(X.astype(np.float64)))            # (n, m, T)
        out = np.zeros((len(X), 2))
        for k in (0, 1):
            A = W.T @ self.templates_[k]                                           # (m, T)
            rho1 = _corr(A[None], Y)
            rho2 = -np.linalg.norm((A[None] - Y).reshape(len(Y), -1), axis=1)
            rho3, U, V = _cca(A, Y)
            rho4 = _corr(np.einsum("nm,mt->nt", U, A)[:, None], np.einsum("nm,nmt->nt", U, Y)[:, None])
            rho5 = _corr(np.einsum("nm,mt->nt", V, A)[:, None], np.einsum("nm,nmt->nt", V, Y)[:, None])
            out[:, k] = rho1 + rho2 + rho3 + rho4 + rho5
        return out


def _cca(A: np.ndarray, Y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """First canonical correlation and vectors between A' (T x m) and each Y_i' (T x m)."""
    Qa, Ra = np.linalg.qr(_center(A).T)                                            # (T, m), (m, m)
    Qy, Ry = np.linalg.qr(np.transpose(_center(Y), (0, 2, 1)))                     # (n, T, m), (n, m, m)
    M = np.einsum("tm,ntk->nmk", Qa, Qy)
    u, s, vt = np.linalg.svd(M)
    U = np.linalg.solve(np.broadcast_to(Ra, (len(Y),) + Ra.shape), u[:, :, :1])[..., 0]
    V = np.linalg.solve(Ry, vt[:, :1, :].transpose(0, 2, 1))[..., 0]
    return s[:, 0], U, V


class DCPM:
    """Binary DCPM classifier; labels 0/1."""

    def __init__(self, n_components: int = 2, context: bool = True, reg: float = 1e-6):
        self.n_components, self.context, self.reg = n_components, context, reg

    def fit(self, X, y, prev_y=None, next_y=None) -> "DCPM":
        if not self.context:
            self.models_ = [BinaryDCPM(self.n_components, self.reg).fit(X, y)]
            return self
        self.models_ = []
        for p, n in CONTEXT_PAIRS:
            sel = ((y == 0) & (prev_y == p) & (next_y == n)) | ((y == 1) & (prev_y == 1 - p) & (next_y == 1 - n))
            if np.sum(sel & (y == 0)) < 2 or np.sum(sel & (y == 1)) < 2:
                raise ValueError(f"too few training trials for context pair {(p, n)}")
            self.models_.append(BinaryDCPM(self.n_components, self.reg).fit(X[sel], y[sel]))
        return self

    def decision_function(self, X) -> np.ndarray:
        """Score difference rho_1 - rho_0 (positive -> class 1)."""
        s = sum(m.scores(X) for m in self.models_)
        return s[:, 1] - s[:, 0]

    def predict(self, X) -> np.ndarray:
        return (self.decision_function(X) > 0).astype(np.int64)
