"""Fast checks for fold construction (no leakage, full coverage) and both baseline models.

Run: python -m pytest -q tests
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aved.data import SESSIONS, SUBJECTS, Dataset, _neighbour_labels, make_folds  # noqa: E402
from aved.models.dcpm import DCPM  # noqa: E402
from aved.models.eegnet import EEGNet  # noqa: E402


def fake_dataset(n_per_session=10, C=4, T=8) -> Dataset:
    subj = np.repeat(SUBJECTS, 6 * n_per_session)
    sess = np.tile(np.repeat(SESSIONS, n_per_session), len(SUBJECTS))
    n = len(subj)
    y = np.arange(n) % 2
    return Dataset(np.zeros((n, C, T), np.float32), y, subj, sess, np.arange(n), y, y, [], 200.0, np.zeros(T))


@pytest.mark.parametrize("protocol, n_folds", [("within", 168), ("pooled", 6), ("loso", 28)])
def test_folds_disjoint_and_cover_all_trials(protocol, n_folds):
    ds = fake_dataset()
    folds = make_folds(protocol)
    assert len(folds) == n_folds
    tested = np.zeros(len(ds), int)
    for f in folds:
        tr, va, te = f.masks(ds)
        assert tr.any() and va.any() and te.any()
        assert not (tr & va).any() and not (tr & te).any() and not (va & te).any()
        # no test subject-session (within/pooled) or test subject (loso) appears in train or validation
        test_units = set(zip(ds.subject[te], ds.session[te])) if protocol != "loso" else set(ds.subject[te])
        for m in (tr, va):
            units = set(zip(ds.subject[m], ds.session[m])) if protocol != "loso" else set(ds.subject[m])
            assert not units & test_units
        tested += te
    assert (tested == 1).all(), "every trial must be tested exactly once"


def test_within_split_sizes():
    ds = fake_dataset()
    tr, va, te = make_folds("within", [3], [2])[0].masks(ds)
    assert set(ds.session[tr]) == {1, 4, 5, 6} and set(ds.session[va]) == {3} and set(ds.session[te]) == {2}
    assert set(ds.subject[tr | va | te]) == {3}


def test_neighbour_labels_respect_character_runs():
    y = np.arange(60) % 2
    prev_y, next_y = _neighbour_labels(y)
    assert prev_y[0] == -1 and prev_y[30] == -1 and next_y[29] == -1 and next_y[59] == -1
    assert prev_y[1] == y[0] and next_y[28] == y[29]


def test_eegnet_shapes_and_max_norm():
    model = EEGNet(21, 58)
    assert model(torch.zeros(5, 21, 58)).shape == (5, 2)
    with torch.no_grad():
        model.classifier.weight.mul_(100)
        model.spatial.weight.mul_(100)
    model.apply_max_norm()
    assert model.classifier.weight.norm(dim=1).max() <= 0.25 + 1e-6
    assert torch.linalg.vector_norm(model.spatial.weight, dim=(1, 2, 3)).max() <= 1.0 + 1e-6


@pytest.mark.parametrize("context", [False, True])
def test_dcpm_learns_lateralised_pattern(context):
    rng = np.random.default_rng(0)
    n, C, T = 400, 6, 40
    y = rng.integers(0, 2, n)
    t = np.linspace(0, 1, T)
    pattern = np.outer([1, 1, 1, -1, -1, -1], np.sin(2 * np.pi * 3 * t))
    X = rng.normal(size=(n, C, T)) * 3 + np.where(y[:, None, None] == 1, pattern, -pattern)
    prev_y, next_y = rng.integers(0, 2, n), rng.integers(0, 2, n)
    clf = DCPM(2, context).fit(X[:300], y[:300], prev_y[:300], next_y[:300])
    assert (clf.predict(X[300:]) == y[300:]).mean() > 0.9


def test_group_bank_loo_excludes_self_and_averages_correctly():
    from aved.train_red import GroupBank
    rng = np.random.default_rng(0)
    group = np.array([5, 5, 5, 7, 7, 9])                     # group 9 has a single member
    X = torch.as_tensor(rng.normal(size=(6, 2, 3)), dtype=torch.float32)
    bank = GroupBank(group, torch.device("cpu"))
    loo, valid = bank.loo_targets(X)
    assert valid.tolist() == [True, True, True, True, True, False]
    assert torch.allclose(loo[0], (X[1] + X[2]) / 2) and torch.allclose(loo[3], X[4])
    y = torch.tensor([0, 0, 0, 1, 1, 1])
    avg, ya = bank.sample_averages(X, y, [2], torch.Generator().manual_seed(0))
    assert avg.shape == (2, 2, 3) and ya.tolist() == [0, 1]   # single-member group skipped
    assert torch.allclose(avg[1], (X[3] + X[4]) / 2)         # k capped at group size 2


def test_red_student_shapes():
    from aved.models.red import REDStudent
    logits, recon = REDStudent(21, 58)(torch.zeros(4, 21, 58))
    assert logits.shape == (4, 2) and recon.shape == (4, 21, 58)
