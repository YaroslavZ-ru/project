import logging
import math

import numpy as np

logger = logging.getLogger("ai_terminator.vectorize")


def vectorize(processed_query, embedding_model, normalize=True):
    tokens_weights = processed_query.get("tokens_with_weights", [])
    dim = embedding_model.get_dimension()
    if not tokens_weights:
        logger.warning("vectorize: пустой список токенов, возвращается нулевой вектор")
        return np.zeros(dim, dtype=np.float32)
    weighted_sum = np.zeros(dim, dtype=np.float64)
    for token, weight in tokens_weights:
        if not isinstance(weight, (int, float)):
            logger.warning("vectorize: неверный тип веса %r, пропущен", weight)
            continue
        if math.isnan(weight) or math.isinf(weight):
            logger.warning("vectorize: NaN/Inf вес для %r, пропущен", token)
            continue
        if weight < 0:
            logger.warning("vectorize: отрицательный вес %r для %r, пропущен", weight, token)
            continue
        vec = embedding_model.get_phrase_vector(token)
        if np.any(np.isnan(vec) | np.isinf(vec)):
            logger.error("vectorize: NaN/Inf в векторе %r, пропущен", token)
            continue
        weighted_sum += weight * vec.astype(np.float64)
    if np.any(np.isnan(weighted_sum)):
        logger.error("vectorize: NaN в weighted_sum, сброс")
        weighted_sum = np.zeros(dim, dtype=np.float64)
    if normalize:
        norm = np.linalg.norm(weighted_sum)
        if norm > 1e-9:
            weighted_sum /= norm
        else:
            logger.warning("vectorize: нулевой вектор после взвешивания")
    return weighted_sum.astype(np.float32)
