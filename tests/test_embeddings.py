import numpy as np
from src.embeddings import FastTextWrapper


def make_wrapper(tmp_path, cache_size=100):
    return FastTextWrapper(
        model_path=tmp_path / 'nonexistent.bin',
        fallback_path=None,
        cache_size=cache_size,
    )


def test_no_model_returns_zeros(tmp_path):
    w = make_wrapper(tmp_path)
    vec = w.get_word_vector('ключ')
    assert vec.shape == (300,)
    assert np.all(vec == 0)


def test_empty_word_returns_zeros(tmp_path):
    w = make_wrapper(tmp_path)
    assert np.all(w.get_word_vector('') == 0)


def test_phrase_vector_is_mean(tmp_path):
    w = make_wrapper(tmp_path)
    v1 = w.get_word_vector('ключ')
    v2 = w.get_word_vector('гаечный')
    pv = w.get_phrase_vector('ключ гаечный')
    assert np.allclose(pv, np.mean([v1, v2], axis=0).astype(np.float32))


def test_lru_eviction(tmp_path):
    w = make_wrapper(tmp_path, cache_size=2)
    w.get_word_vector('а')
    w.get_word_vector('б')
    w.get_word_vector('в')
    assert len(w._word_cache) == 2
    assert 'а' not in w._word_cache


def test_warning_once_per_word(tmp_path, caplog):
    import logging
    w = make_wrapper(tmp_path)
    with caplog.at_level(logging.WARNING, logger='ai_terminator.embeddings'):
        w.get_word_vector('тест')
        w.get_word_vector('тест')
    warns = [r for r in caplog.records if 'тест' in r.message]
    assert len(warns) == 1


def test_get_dimension_default(tmp_path):
    assert make_wrapper(tmp_path).get_dimension() == 300


def test_fallback_loaded(tmp_path):
    fb = {'ключ': np.ones(300, dtype=np.float32)}
    np.save(str(tmp_path / 'fb.npy'), fb)
    w = FastTextWrapper(
        model_path=tmp_path / 'nonexistent.bin',
        fallback_path=tmp_path / 'fb.npy',
        cache_size=100,
    )
    assert np.allclose(w.get_word_vector('ключ'), np.ones(300, dtype=np.float32))