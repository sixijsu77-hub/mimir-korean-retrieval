"""Retrieval metrics, implemented here rather than taken from a library.

MTEB scores with pytrec_eval. Reusing it would mean the metric is never checked
against anything — so nDCG and recall are written out here, and the harness gate
tests them against MTEB's published numbers.

All qrels in the datasets used are binary (relevance 0 or 1), so linear gain and
exponential gain (2^rel - 1) give identical results.
"""

from __future__ import annotations

import math
import random


def dcg(gains: list[int]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked_ids: list[str], relevant: dict[str, int], k: int) -> float:
    gains = [relevant.get(d, 0) for d in ranked_ids[:k]]
    ideal = sorted((v for v in relevant.values() if v > 0), reverse=True)[:k]
    idcg = dcg(ideal)
    return dcg(gains) / idcg if idcg > 0 else 0.0


def recall_at_k(ranked_ids: list[str], relevant: dict[str, int], k: int) -> float:
    positives = {d for d, v in relevant.items() if v > 0}
    if not positives:
        return 0.0
    return len(positives & set(ranked_ids[:k])) / len(positives)


def evaluate(
    run: dict[str, list[str]],
    qrels: dict[str, dict[str, int]],
    ks: tuple[int, ...] = (10, 100),
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    """Score a run. Returns (means, per_query).

    `run` maps query_id to document ids in rank order. Queries present in qrels
    but missing from run are scored 0 rather than skipped.
    """
    per_query: dict[str, dict[str, float]] = {}
    for qid, relevant in qrels.items():
        ranked = run.get(qid, [])
        scores = {f"ndcg_at_{k}": ndcg_at_k(ranked, relevant, k) for k in ks}
        scores.update({f"recall_at_{k}": recall_at_k(ranked, relevant, k) for k in ks})
        per_query[qid] = scores

    names = next(iter(per_query.values())).keys() if per_query else []
    means = {
        n: sum(s[n] for s in per_query.values()) / len(per_query) for n in names
    }
    return means, per_query


def bootstrap_ci_values(
    values: list[float],
    n_resamples: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Vectorized equivalent of `bootstrap_ci`, for sweeps over many conditions.

    Uses a different RNG stream, so intervals agree only to Monte Carlo error.
    """
    import numpy as np

    arr = np.asarray(values, dtype=np.float64)
    n = arr.shape[0]
    if n == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    means = arr[rng.integers(0, n, size=(n_resamples, n))].mean(axis=1)
    means.sort()
    lo = means[int(n_resamples * alpha / 2)]
    hi = means[min(int(n_resamples * (1 - alpha / 2)), n_resamples - 1)]
    return (float(lo), float(hi))


def bootstrap_ci(
    per_query: dict[str, dict[str, float]],
    metric: str,
    n_resamples: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile confidence interval, resampling at the query level."""
    values = [s[metric] for s in per_query.values()]
    n = len(values)
    if n == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(n_resamples * alpha / 2)]
    hi = means[min(int(n_resamples * (1 - alpha / 2)), n_resamples - 1)]
    return (lo, hi)
