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


def test_apply_overrides_parses_yaml_and_rejects_typos():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from run_baseline import apply_overrides
    cfg = {"loss": {"tau": 2.0}, "teacher": {"k_set": [2, 3, 6]}}
    apply_overrides(cfg, ["loss.tau=4", "teacher.k_set=[1, 2]", "teacher.train=false"])
    assert cfg == {"loss": {"tau": 4}, "teacher": {"k_set": [1, 2], "train": False}}
    with pytest.raises(SystemExit):
        apply_overrides(cfg, ["loss.taus=1"])
    with pytest.raises(SystemExit):
        apply_overrides(cfg, ["los.tau=1"])


def test_aligned_targets_recover_shift_and_exclude_self():
    from aved.alignment import aligned_loo_targets, shift_edge
    rng = np.random.default_rng(0)
    t = np.linspace(0, 1, 58)
    erp = np.outer(np.ones(4), np.exp(-((t - 0.5) / 0.05) ** 2))         # (C=4, T=58) peaked template
    true = np.array([-2, 0, 2, 1, -1, 0])
    X = np.stack([shift_edge(erp, s) for s in true]) + 0.01 * rng.normal(size=(6, 4, 58))
    group = np.zeros(6, dtype=int)
    tgt, valid, mean_shift = aligned_loo_targets(X, group, max_shift=3, iters=3)
    assert valid.all() and mean_shift > 0.5
    # aligned target is sharper than the plain leave-one-out average
    plain = (X.sum(0) - X[0]) / 5
    assert tgt[0].max() > plain.max()
    # target of trial 0 does not depend on trial 0
    X2 = X.copy(); X2[0] = rng.normal(size=(4, 58))
    assert np.allclose(aligned_loo_targets(X2, group, 3, 3)[0][0], tgt[0])


def test_adaptation_controls_run_and_balance():
    from aved.adapt import adapt
    from aved.models.red import REDStudent
    torch.manual_seed(0)
    model = REDStudent(21, 58).eval()
    X = torch.randn(60, 21, 58)
    groups = np.repeat(np.array([100000 + 1000 * s + k for s in (1, 2) for k in range(5)]), 6)   # 2 sessions
    cfg = {"epochs": 1, "lr": 1e-3, "batch_size": 16, "lambda_n2n": 1.0, "gpl_threshold": 0.6, "gpl_bal_quantile": 0.3}
    bal = adapt(model, "balance", X, groups, None, cfg, 0)
    with torch.no_grad():
        logits = bal(X)[0]
    assert abs((logits.argmax(1) == 1).float().mean().item() - 0.5) <= 0.05
    for m in ("gpl_bal", "gpl_bal_single"):
        adapt(model, m, X, groups, None, cfg, 0)


CH21 = ['P7', 'P5', 'P3', 'P1', 'PZ', 'P2', 'P4', 'P6', 'P8', 'PO7', 'PO5', 'PO3', 'POZ', 'PO4', 'PO6', 'PO8',
        'CB1', 'O1', 'OZ', 'O2', 'CB2']


def test_lrmoe_mirror_equivariance_and_invariant_routing():
    from aved.models.lrmoe import LRMoE, VARIANTS, mirror_index
    torch.manual_seed(0)
    m = mirror_index(CH21)
    assert sorted(m) == list(range(21)) and all(m[m[i]] == i for i in range(21))
    assert m[CH21.index('POZ')] == CH21.index('POZ') and m[CH21.index('PO7')] == CH21.index('PO8')
    x = torch.randn(8, 21, 58)
    xm = x[:, m]
    anti = LRMoE(CH21, 58, 200.0, [("anti", d) for d in (-4, 0, 4)], "physio").eval()
    lo, g = anti(x)
    lo_m, g_m = anti(xm)
    assert torch.allclose(lo_m, -lo, atol=1e-5)              # mirrored trial -> opposite decision
    assert torch.allclose(g_m, g, atol=1e-5)                 # physiological routing is mirror-invariant
    for name, v in VARIANTS.items():
        model = LRMoE(CH21, 58, 200.0, v["experts"], v["router"]).eval()
        out, gates = model(x)
        assert out.shape == (8, 2) and gates.shape == (8, len(v["experts"]))


def test_oracle_routing_subject_selection():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import pandas as pd
    from run_oracle_routing import K_NEIGHBOURS, choose_subjects
    rng = np.random.default_rng(0)
    desc = pd.DataFrame({"mirror_corr": np.linspace(-0.5, 0.9, 28), "lat_latency": rng.uniform(0.15, 0.3, 28),
                         "anti_ratio": rng.normal(1.5, 0.5, 28)}, index=range(1, 29))
    own = choose_subjects("phen_split", 28, desc, rng)            # subject 28 has the highest mirror_corr
    wrong = choose_subjects("wrong_split", 28, desc, rng)
    assert 28 not in own and set(own).isdisjoint(wrong) and len(own) + len(wrong) == 27
    assert min(desc.mirror_corr[own]) > max(desc.mirror_corr[wrong])
    rand = choose_subjects("rand_split", 28, desc, np.random.default_rng(1))
    assert len(rand) == len(own) and 28 not in rand
    knn = choose_subjects("phen_knn", 5, desc, rng)
    assert len(knn) == K_NEIGHBOURS and 5 not in knn
    assert len(choose_subjects("phen_cond", 5, desc, rng)) == 27
