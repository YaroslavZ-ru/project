import numpy as np
import pytest
import logging
from src.vectorize import vectorize


class MockEmbedding:
    def get_phrase_vector(self, phrase):
        v = np.zeros(300, dtype=np.float32)
        if phrase == 'a':
            v[0] = 1.0
        elif phrase == 'b':
            v[1] = 1.0
        return v
    def get_dimension(self): return 300


@pytest.fixture
def mock(): return MockEmbedding()


def test_single_no_normalize(mock):
    r = vectorize({'tokens_with_weights': [('a', 1.0)]}, mock, normalize=False)
    assert r[0] == pytest.approx(1.0)
    assert r[1] == pytest.approx(0.0)


def test_two_tokens_normalized(mock):
    r = vectorize({'tokens_with_weights': [('a', 0.7), ('b', 0.3)]}, mock, normalize=True)
    assert r[0] == pytest.approx(0.919, abs=1e-3)
    assert r[1] == pytest.approx(0.394, abs=1e-3)
    assert np.linalg.norm(r) == pytest.approx(1.0, abs=1e-6)


def test_scale_invariance(mock):
    r1 = vectorize({'tokens_with_weights': [('a', 0.7), ('b', 0.3)]}, mock)
    r2 = vectorize({'tokens_with_weights': [('a', 1.4), ('b', 0.6)]}, mock)
    assert np.allclose(r1, r2, atol=1e-6)


def test_empty_returns_zeros(mock, caplog):
    with caplog.at_level(logging.WARNING, logger='ai_terminator.vectorize'):
        r = vectorize({'tokens_with_weights': []}, mock)
    assert np.all(r == 0)
    assert any('пустой' in rec.message for rec in caplog.records)


def test_nan_weight_skipped(mock, caplog):
    with caplog.at_level(logging.WARNING, logger='ai_terminator.vectorize'):
        r = vectorize({'tokens_with_weights': [('a', float('nan')), ('b', 0.3)]}, mock, normalize=False)
    assert r[1] == pytest.approx(0.3)
    assert any('NaN' in rec.message for rec in caplog.records)


def test_negative_weight_skipped(mock, caplog):
    with caplog.at_level(logging.WARNING, logger='ai_terminator.vectorize'):
        r = vectorize({'tokens_with_weights': [('a', -0.5)]}, mock)
    assert np.all(r == 0)
    assert any('отрицательн' in rec.message for rec in caplog.records)