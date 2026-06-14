"""tests/test_generative.py -- тесты GenerativeExpander.

Все тесты работают БЕЗ реальной LLM (transformers не требуется).
Использует unittest.mock для подмены pipeline.
"""

import sys
from pathlib import Path
from concurrent.futures import TimeoutError as FuturesTimeoutError
from unittest.mock import MagicMock, patch

import pytest

# Добавляем корень проекта в sys.path для запуска без -m
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import Config  # noqa: E402
from src.generative import GenerativeExpander  # noqa: E402


@pytest.fixture
def cfg():
    """Config с use_generative=True, загруженный из файла."""
    config_path = _ROOT / "configs" / "config.json"
    c = Config.from_json(str(config_path), project_root=_ROOT)
    # Переопределяем поля для тестов
    object.__setattr__(c, "use_generative", True)
    object.__setattr__(c, "generative_keywords", ["материал", "размер", "тип", "форма", "цвет"])
    object.__setattr__(c, "generative_max_new_params", 5)
    object.__setattr__(c, "generative_timeout_seconds", 30.0)
    return c


@pytest.fixture
def expander(cfg):
    """GenerativeExpander с use_generative=True, но без реальной модели."""
    ex = GenerativeExpander(config=cfg)
    return ex


class TestExpandReturnsEmpty:
    def test_expand_returns_empty_when_unavailable(self, expander):
        """если _available=False -- expand возвращает []"""
        expander._available = False
        result = expander.expand("ключ", [], [])
        assert result == []

    def test_expand_returns_empty_when_pipe_is_none(self, expander):
        """если _pipe is None (модель не загрузилась) -- возвращает []"""
        expander._available = True
        expander._model_loaded = True
        expander._pipe = None
        result = expander.expand("ключ", [], [])
        assert result == []

    def test_expand_returns_empty_on_timeout(self, expander):
        """при TimeoutError возвращает [] без исключений"""
        expander._available = True
        expander._model_loaded = True
        expander._pipe = MagicMock()

        mock_future = MagicMock()
        mock_future.result.side_effect = FuturesTimeoutError()

        mock_executor = MagicMock()
        mock_executor.__enter__ = MagicMock(return_value=mock_executor)
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.submit.return_value = mock_future

        with patch("src.generative.ThreadPoolExecutor", return_value=mock_executor):
            result = expander.expand("ключ", [], [])

        assert result == []


class TestParseResponse:
    def test_parse_response_filters_by_keywords(self, expander):
        """парсер оставляет только элементы с ключевыми словами"""
        text = "Предложения: материал, xyz_nonsense, размер, тип"
        result = expander._parse_response(text, set())
        names = [p["label_ru"] for p in result]
        assert "xyz_nonsense" not in names
        assert len(result) >= 2
        assert all(p["source"] == "generative" for p in result)

    def test_parse_response_respects_max_new_params(self, expander):
        """ограничение generative_max_new_params=1"""
        object.__setattr__(expander._cfg, "generative_max_new_params", 1)
        text = "материал, размер, тип, форма, цвет"
        result = expander._parse_response(text, set())
        assert len(result) <= 1

    def test_parse_response_skips_existing_names(self, expander):
        """existing_names исключаются из результата"""
        existing = {"материал"}
        text = "материал, размер"
        result = expander._parse_response(text, existing)
        slugs = [p["name"] for p in result]
        assert "материал" not in slugs


class TestBuildPrompt:
    def test_build_prompt_contains_term_and_max_512(self, expander):
        """prompt содержит term и не превышает 512 символов"""
        prompt = expander._build_prompt("ключ", ["техника"], [])
        assert "ключ" in prompt
        assert len(prompt) <= 512
