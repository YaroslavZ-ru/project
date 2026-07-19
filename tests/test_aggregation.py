import numpy as np
import pytest

from src.aggregation import (
    aggregate_parameters,
    apply_feedback_correction,
    check_hints_coherence,
    detect_ambiguity,
    determine_context,
    generate_clarification_questions,
)


def make_param(name, label="Парам", desc=""):
    return {
        "name": name,
        "label_ru": label,
        "type": "string",
        "description": desc,
        "confidence": 1.0,
        "source": "knowledge_base",
    }


Cands = [
    {
        "similarity": 0.9,
        "domain": "слесарный инструмент",
        "parameters": [
            make_param("material", "Материал"),
            make_param("size", "Размер"),
        ],
    },
    {
        "similarity": 0.7,
        "domain": "слесарный инструмент",
        "parameters": [make_param("material", "Материал")],
    },
]


def test_freq_affects_rank():
    result = aggregate_parameters(Cands, [], max_parameters=10)
    names = [p["name"] for p in result]
    assert names[0] == "material"  # freq=2 побеждает


def test_source_knowledge_base():
    result = aggregate_parameters(Cands, [], max_parameters=10)
    assert all(p["source"] == "knowledge_base" for p in result)


def test_confidence_normalized():
    result = aggregate_parameters(Cands, [], max_parameters=10)
    assert result[0]["confidence"] == pytest.approx(1.0)


def test_empty_candidates():
    assert aggregate_parameters([], [], max_parameters=10) == []


def test_determine_context_single_domain():
    cands = [{"domain": "музыка", "similarity": 0.8}]
    ctx = determine_context(cands)
    assert ctx["domain"] == "музыка"


def test_determine_context_multi_domain():
    cands = [
        {"domain": "музыка", "similarity": 0.8},
        {"domain": "музыка", "similarity": 0.7},
        {"domain": "техника", "similarity": 0.9},
    ]
    ctx = determine_context(cands)
    assert ctx["domain"] == "музыка"  # sum=1.5 > 0.9


def test_determine_context_empty():
    ctx = determine_context([])
    assert ctx["domain"] == "не определено"
    assert ctx["confidence"] == 0.0


def test_hint_match_affects_rank():
    cands = [
        {
            "similarity": 0.8,
            "domain": "тест",
            "parameters": [
                {
                    "name": "material",
                    "label_ru": "Материал изготовления",
                    "description": "материал",
                    "type": "string",
                    "confidence": 1.0,
                    "source": "kb",
                },
                {
                    "name": "size",
                    "label_ru": "Размер дляноо",
                    "description": "размер",
                    "type": "float",
                    "confidence": 1.0,
                    "source": "kb",
                },
            ],
        }
    ]
    # подсказка "материал" даёт hint_match=1.0 для material
    result = aggregate_parameters(cands, hints_lemmas=[["материал"]], max_parameters=10)
    assert result[0]["name"] == "material"


# --- Тесты detect_ambiguity и generate_clarification_questions ---


def test_detect_ambiguity_two_equal_domains():
    """Два домена с близким score — неоднозначность."""
    candidates = [
        {"domain": "музыка", "similarity": 0.85},
        {"domain": "техника", "similarity": 0.83},
        {"domain": "музыка", "similarity": 0.79},
        {"domain": "техника", "similarity": 0.78},
    ]
    result = detect_ambiguity(candidates, threshold=0.7, delta=0.1)
    assert result["is_ambiguous"]
    assert result["top_domain"] in ("музыка", "техника")
    assert result["runner_up"] is not None
    assert result["top_domain"] != result["runner_up"]
    assert len(result["domains"]) >= 2


def test_detect_ambiguity_one_clear_domain():
    """Один явный домен — не неоднозначность."""
    candidates = [
        {"domain": "техника", "similarity": 0.95},
        {"domain": "техника", "similarity": 0.90},
        {"domain": "музыка", "similarity": 0.50},
    ]
    result = detect_ambiguity(candidates, threshold=0.7, delta=0.1)
    assert not result["is_ambiguous"]
    assert result["top_domain"] == "техника"


def test_detect_ambiguity_empty_candidates():
    """Пустой список — не неоднозначность."""
    result = detect_ambiguity([], threshold=0.7, delta=0.1)
    assert not result["is_ambiguous"]
    assert result["top_domain"] is None
    assert result["runner_up"] is None


def test_detect_ambiguity_below_threshold():
    """Оба домена слабые — не неоднозначность."""
    candidates = [
        {"domain": "музыка", "similarity": 0.55},
        {"domain": "техника", "similarity": 0.53},
    ]
    result = detect_ambiguity(candidates, threshold=0.7, delta=0.1)
    assert not result["is_ambiguous"]


def test_generate_clarification_questions_when_ambiguous():
    """Структура вопросов при неоднозначном термине."""
    info = {
        "is_ambiguous": True,
        "top_domain": "техника",
        "runner_up": "музыка",
        "domains": [],
    }
    questions = generate_clarification_questions(info, "ключ")
    assert isinstance(questions, list)
    assert len(questions) >= 1
    assert any("техника" in q or "музыка" in q for q in questions)


def test_generate_clarification_questions_not_ambiguous():
    """Без неоднозначности — пустой список."""
    info = {
        "is_ambiguous": False,
        "top_domain": "техника",
        "runner_up": None,
        "domains": [],
    }
    questions = generate_clarification_questions(info, "ключ")
    assert questions == []


# --- Изменение 63: Тесты check_hints_coherence ---


class MockEmbeddingModel:
    """Мок модели эмбеддингов для тестов coherence."""

    def __init__(self, vectors: dict[str, np.ndarray] | None = None):
        self._vectors = vectors or {}

    def get_phrase_vector(self, phrase: str) -> np.ndarray:
        if phrase in self._vectors:
            return self._vectors[phrase]
        # Генерируем детерминированный вектор на основе хеша
        rng = np.random.RandomState(abs(hash(phrase)) % (2**31))
        vec = rng.randn(300).astype(np.float32)
        vec /= np.linalg.norm(vec) + 1e-9
        return vec


def test_check_hints_coherent_similar():
    """Похожие подсказки (высокое сходство) -> coherent=True."""
    # Два почти одинаковых вектора (малый угол)
    base = np.ones(300, dtype=np.float32)
    base /= np.linalg.norm(base)
    vec_a = base.copy()
    vec_b = base.copy()
    vec_b[0] += 0.01  # минимум отличий
    vec_b /= np.linalg.norm(vec_b)

    model = MockEmbeddingModel({"техника": vec_a, "инструмент": vec_b})
    result = check_hints_coherence(["техника", "инструмент"], model, threshold=0.2)
    assert result["coherent"] is True
    assert result["avg_similarity"] > 0.99


def test_check_hints_incoherent():
    """Различные подсказки (низкое сходство) -> coherent=False."""
    vec_a = np.array([1, 0, 0] + [0] * 297, dtype=np.float32)
    vec_b = np.array([0, 1, 0] + [0] * 297, dtype=np.float32)
    model = MockEmbeddingModel({"техника": vec_a, "рецепт": vec_b})
    result = check_hints_coherence(["техника", "рецепт"], model, threshold=0.2)
    assert result["coherent"] is False
    assert result["avg_similarity"] < 0.2


def test_check_hints_single():
    """Одна подсказка -> всегда coherent."""
    model = MockEmbeddingModel()
    result = check_hints_coherence(["техника"], model)
    assert result["coherent"] is True
    assert result["pairs"] == []


def test_check_hints_empty():
    """Пустой список -> всегда coherent."""
    model = MockEmbeddingModel()
    result = check_hints_coherence([], model)
    assert result["coherent"] is True
    assert result["pairs"] == []


def test_check_hints_coherence_structure():
    """Проверка структуры ответа."""
    model = MockEmbeddingModel()
    result = check_hints_coherence(["а", "б"], model)
    assert "coherent" in result
    assert "avg_similarity" in result
    assert "pairs" in result
    assert "reason" in result
    assert len(result["pairs"]) == 1  # C(2,2) = 1 пара


# --- Изменение 67: Тесты domain_candidates в detect_ambiguity ---


def test_detect_ambiguity_returns_domain_candidates():
    """detect_ambiguity возвращает domain_candidates с confidence и example_term."""
    candidates = [
        {"domain": "музыка", "similarity": 0.85, "term": "нота"},
        {"domain": "техника", "similarity": 0.83, "term": "ключ"},
        {"domain": "музыка", "similarity": 0.79, "term": "нота"},
        {"domain": "техника", "similarity": 0.78, "term": "ключ"},
    ]
    result = detect_ambiguity(candidates, threshold=0.7, delta=0.1)
    assert "domain_candidates" in result
    assert len(result["domain_candidates"]) >= 2
    for dc in result["domain_candidates"]:
        assert "domain" in dc
        assert "confidence" in dc
        assert "example_term" in dc


# --- Изменение 68: Тесты apply_feedback_correction ---


class MockKB:
    """Мок KnowledgeBase для тестов feedback."""

    def __init__(self, feedback_data: dict):
        self._feedback = feedback_data

    def get_feedback_stats(self, concept_id: str) -> dict:
        return self._feedback.get(concept_id, {"avg_rating": None, "votes": 0})


def test_feedback_correction_boosts_high_rated():
    """Высокий рейтинг (5) увеличивает similarity."""
    kb = MockKB({"c1": {"avg_rating": 5.0, "votes": 5}})
    candidates = [{"concept_id": "c1", "similarity": 0.5}]
    result = apply_feedback_correction(candidates, kb, weight=0.1, min_votes=3)
    assert result[0]["similarity"] > 0.5


def test_feedback_correction_penalizes_low_rated():
    """Низкий рейтинг (1) уменьшает similarity."""
    kb = MockKB({"c1": {"avg_rating": 1.0, "votes": 5}})
    candidates = [{"concept_id": "c1", "similarity": 0.5}]
    result = apply_feedback_correction(candidates, kb, weight=0.1, min_votes=3)
    assert result[0]["similarity"] < 0.5


def test_feedback_correction_ignores_insufficient_votes():
    """Недостаточно голосов — без изменений."""
    kb = MockKB({"c1": {"avg_rating": 5.0, "votes": 2}})
    candidates = [{"concept_id": "c1", "similarity": 0.5}]
    result = apply_feedback_correction(candidates, kb, weight=0.1, min_votes=3)
    assert result[0]["similarity"] == 0.5


def test_feedback_correction_empty():
    """Пустой список кандидатов — без ошибок."""
    kb = MockKB({})
    result = apply_feedback_correction([], kb, weight=0.1, min_votes=3)
    assert result == []
