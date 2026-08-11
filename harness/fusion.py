"""Score normalization and weighted fusion.

BM25 scores are unbounded positive and cosine similarity is bounded, so a hybrid
weight has no meaning until the two are put on a common scale. The choice of
scale moves the optimum, so both normalizations that were pre-registered are
implemented and reported.

Fusion runs over the full corpus rather than a truncated candidate list, so no
candidate-set artifact enters the weight curve.
"""

from __future__ import annotations

import numpy as np


def minmax(scores: np.ndarray) -> np.ndarray:
    """Per-query min-max to [0, 1]. Rows with no spread become all zeros."""
    lo = scores.min(axis=1, keepdims=True)
    hi = scores.max(axis=1, keepdims=True)
    span = hi - lo
    return np.where(span > 0, (scores - lo) / np.where(span > 0, span, 1.0), 0.0)


def zscore(scores: np.ndarray) -> np.ndarray:
    """Per-query standardization. Rows with zero variance become all zeros."""
    mu = scores.mean(axis=1, keepdims=True)
    sd = scores.std(axis=1, keepdims=True)
    return np.where(sd > 0, (scores - mu) / np.where(sd > 0, sd, 1.0), 0.0)


NORMALIZERS = {"minmax": minmax, "zscore": zscore}


def blend(sparse: np.ndarray, dense: np.ndarray, w: float) -> np.ndarray:
    """w is the dense weight: w=0 is BM25 alone, w=1 is dense alone."""
    return (1.0 - w) * sparse + w * dense


def top_k_ids(scores: np.ndarray, doc_ids: list[str], k: int) -> list[list[str]]:
    """Rank documents per query. Ties break by corpus order, as np.argsort is stable."""
    k = min(k, scores.shape[1])
    part = np.argpartition(-scores, kth=k - 1, axis=1)[:, :k]
    part_scores = np.take_along_axis(scores, part, axis=1)
    order = np.argsort(-part_scores, axis=1, kind="stable")
    ranked = np.take_along_axis(part, order, axis=1)
    return [[doc_ids[j] for j in row] for row in ranked]
