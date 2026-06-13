"""src/config.py -- загрузка и валидация конфигурации AI-Terminator.

Единственный способ доступа к настройкам во всём проекте:
    from src.config import get_config
    cfg = get_config()  # повторные вызовы читают из кэша

Или напрямую через фабрику:
    cfg = Config.from_json("configs/config.json", project_root=Path(__file__).parent.parent)
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("ai_terminator.config")

_VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

# Поля с суффиксом _path которые преобразуются в abs Path (кроме faiss_index_path)
_AUTO_PATH_FIELDS = (
    "db_path",
    "fasttext_model_path",
    "synonyms_path",
    "domain_templates_path",
    "domain_keywords_path",
)


@dataclass
class Config:
    """\u0412се настройки AI-Terminator.

    Поля-пути хранятся как абсолютные Path (преобразуются в from_json).
    fallback_embeddings_path хранится как str: пустая строка = нет fallback.
    faiss_index_path хранится как str: пустая строка = FAISS не используется.
    """

    # --- Пути (обязательные) ---
    db_path: Path
    fasttext_model_path: Path
    synonyms_path: Path
    domain_templates_path: Path
    domain_keywords_path: Path

    # --- Параметры поиска (обязательные) ---
    min_confidence: float
    max_candidates: int
    max_parameters: int

    # --- Генеративный модуль (обязательные) ---
    use_generative: bool
    generative_model: str
    generative_max_new_tokens: int
    generative_temperature: float
    generative_max_new_params: int
    generative_timeout_seconds: float
    min_parameters_for_generative: int
    generative_keywords: list[str]

    # --- Технические (обязательные) ---
    timeout_seconds: float
    cache_embeddings: bool
    log_level: str
    cache_lemma_size: int
    max_synonyms_per_token: int
    use_synonyms: bool
    max_term_length: int
    max_hint_length: int
    word_vector_cache_size: int
    query_cache_size: int

    # --- Опциональные с дефолтами ---
    fallback_embeddings_path: str = ""
    use_faiss: bool = False
    faiss_index_path: str = ""
    session_ttl_seconds: int = 1800
    session_cache_size: int = 1000
    session_cleanup_interval_seconds: int = 60
    auto_save_domain_on_ok: bool = True
    ambiguity_threshold: float = 0.7
    ambiguity_delta: float = 0.1
    domain_centroid_threshold: float = 0.3
    auto_save_domain_on_fallback: bool = False
    use_relations: bool = False
    relation_max_depth: int = 1
    relation_decay_factor: float = 0.5
    domain_centroids_min_concepts: int = 2

    # ------------------------------------------------------------------
    @classmethod
    def from_json(cls, config_path: str | Path, project_root: Path) -> "Config":
        """Загрузить, преобразовать пути и валидировать конфиг.

        Args:
            config_path:  путь к configs/config.json (относительный или абсолютный).
            project_root: корень проекта (папка, где лежит main.py).

        Returns:
            Сконфигурированный экземпляр Config.

        Raises:
            FileNotFoundError: файл конфига не найден.
            ValueError:       невалидный JSON или ошибка валидации.
        """
        config_path = Path(config_path)
        if not config_path.is_absolute():
            config_path = (project_root / config_path).resolve()

        # 1. Чтение файла
        if not config_path.exists():
            raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")

        try:
            with open(config_path, encoding="utf-8") as f:
                data: dict = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ошибка парсинга config.json: {exc}") from exc

        # 2. Преобразование обязательных _path-полей в abs Path
        for key in _AUTO_PATH_FIELDS:
            if key not in data:
                raise ValueError(f"Обязательное поле отсутствует в config.json: {key!r}")
            data[key] = (project_root / data[key]).resolve()

        # 3. fallback_embeddings_path: пустая строка = нет fallback
        fb = data.get("fallback_embeddings_path", "")
        if fb:
            data["fallback_embeddings_path"] = str((project_root / fb).resolve())
        else:
            data["fallback_embeddings_path"] = ""

        # 4. faiss_index_path: аналогично
        fi = data.get("faiss_index_path", "")
        data["faiss_index_path"] = str((project_root / fi).resolve()) if fi else ""

        # 5. Валидация
        cls._validate(data)

        # 6. Предупреждение если db_path.parent не существует
        db_parent = data["db_path"].parent
        if not db_parent.exists():
            logger.warning(
                "Папка для БД не существует: %s. Запустите setup_project.py.",
                db_parent,
            )

        return cls(**data)

    # ------------------------------------------------------------------
    @staticmethod
    def _validate(data: dict) -> None:
        """Проверяет типы и допустимые значения полей.

        Args:
            data: словарь из json.load с уже преобразованными _path-полями.

        Raises:
            ValueError: если любое значение недопустимо.
        """
        # min_confidence: float в [0.0, 1.0]
        v = data.get("min_confidence")
        if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
            raise ValueError(
                f"Ошибка: min_confidence должен быть от 0 до 1, получено: {v!r}"
            )

        # Положительные целые int > 0
        positive_ints = [
            "max_candidates", "max_parameters", "cache_lemma_size",
            "max_synonyms_per_token", "max_term_length", "max_hint_length",
            "word_vector_cache_size", "query_cache_size",
            "session_ttl_seconds", "session_cache_size",
            "session_cleanup_interval_seconds", "relation_max_depth",
            "domain_centroids_min_concepts", "generative_max_new_tokens",
            "generative_max_new_params", "min_parameters_for_generative",
        ]
        for key in positive_ints:
            val = data.get(key)
            if val is None:
                raise ValueError(f"Обязательное поле отсутствует: {key!r}")
            if not isinstance(val, int) or val <= 0:
                raise ValueError(f"{key!r} должен быть целым положительным числом, получено: {val!r}")

        # Таймауты: float > 0
        for key in ("timeout_seconds", "generative_timeout_seconds"):
            val = data.get(key)
            if not isinstance(val, (int, float)) or float(val) <= 0:
                raise ValueError(f"Таймаут {key!r} должен быть положительным")

        # log_level: одно из четырёх
        ll = data.get("log_level")
        if ll not in _VALID_LOG_LEVELS:
            raise ValueError(
                f"Ошибка: log_level должен быть одним из DEBUG/INFO/WARNING/ERROR, получено: {ll!r}"
            )

        # use_generative: если true -- generative_model не пуста
        if data.get("use_generative") and not data.get("generative_model", "").strip():
            raise ValueError("Генеративная модель не задана: заполните generative_model")

        # generative_keywords: list[непустых str]
        kws = data.get("generative_keywords", [])
        if not isinstance(kws, list):
            raise ValueError("generative_keywords должен быть списком")
        for i, kw in enumerate(kws):
            if not isinstance(kw, str) or not kw.strip():
                raise ValueError(f"generative_keywords[{i}] должен быть непустой строкой")

        # generative_temperature: float в (0.0, 2.0]
        gt = data.get("generative_temperature")
        if not isinstance(gt, (int, float)) or not (0.0 < float(gt) <= 2.0):
            raise ValueError(f"generative_temperature должна быть в диапазоне (0.0, 2.0], получено: {gt!r}")

        # float в [0.0, 1.0]
        for key in ("ambiguity_threshold", "ambiguity_delta", "domain_centroid_threshold", "relation_decay_factor"):
            val = data.get(key)
            if val is None:
                continue  # опциональные, будет дефолт
            if not isinstance(val, (int, float)) or not (0.0 <= float(val) <= 1.0):
                raise ValueError(f"{key!r} должно быть float в [0.0, 1.0], получено: {val!r}")

        # bool-поля
        for key in (
            "use_synonyms", "cache_embeddings", "use_faiss",
            "auto_save_domain_on_ok", "auto_save_domain_on_fallback", "use_relations",
        ):
            val = data.get(key)
            if val is None:
                continue
            if not isinstance(val, bool):
                raise ValueError(f"{key!r} должно быть true или false, получено: {val!r}")


# ---------------------------------------------------------------------------
# Глобальный кэш конфига
# ---------------------------------------------------------------------------

_config: Config | None = None


def get_config() -> Config:
    """Вернуть глобальный экземпляр Config.

    При первом вызове загружает configs/config.json относительно корня
    проекта (родитель папки src/). Повторные вызовы читают из кэша.

    Returns:
        Сконфигурированный экземпляр Config.
    """
    global _config
    if _config is None:
        project_root = Path(__file__).parent.parent
        _config = Config.from_json("configs/config.json", project_root=project_root)
    return _config


def reset_config() -> None:
    """Сбросить кэш конфига (используется в тестах)."""
    global _config
    _config = None