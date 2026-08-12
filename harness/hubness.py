"""Hubness: do a few documents occupy top-k for many queries they are not relevant to.

Specified in PREREGISTRATION.md section 4b.2. The counted quantity excludes a
document's own relevant queries — being retrieved for the query you answer is not
hubness — and the test is against a uniform-random null, because with 114-592
queries over 720-1.5M documents the raw counts are sparse enough that skewness has
no interpretable scale on its own.
"""

from __future__ import annotations

import numpy as np


def skewness(x: np.ndarray) -> float:
    """Fisher-Pearson standardized third moment (population form, as scipy default)."""
    x = np.asarray(x, dtype=np.float64)
    m = x.mean()
    m2 = ((x - m) ** 2).mean()
    if m2 == 0:
        return 0.0
    m3 = ((x - m) ** 3).mean()
    return float(m3 / m2 ** 1.5)


def gini(x: np.ndarray) -> float:
    """Gini coefficient of a non-negative count vector."""
    x = np.sort(np.asarray(x, dtype=np.float64))
    n = x.shape[0]
    total = x.sum()
    if n == 0 or total == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * (idx * x).sum()) / (n * total) - (n + 1) / n)


def top_k_indices(scores: np.ndarray, k: int) -> np.ndarray:
    k = min(k, scores.shape[1])
    return np.argpartition(-scores, kth=k - 1, axis=1)[:, :k]


def irrelevant_counts(
    topk: np.ndarray,
    doc_ids: list[str],
    query_ids: list[str],
    qrels: dict[str, dict[str, int]],
    n_docs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (N_k over all queries, N_k restricted to queries the doc is not relevant to)."""
    n_all = np.zeros(n_docs, dtype=np.int64)
    n_irr = np.zeros(n_docs, dtype=np.int64)
    for qi, qid in enumerate(query_ids):
        rel = qrels.get(qid, {})
        for j in topk[qi]:
            n_all[j] += 1
            if rel.get(doc_ids[j], 0) <= 0:
                n_irr[j] += 1
    return n_all, n_irr


def describe(n_irr: np.ndarray) -> dict:
    total = int(n_irr.sum())
    n_docs = n_irr.shape[0]
    top1pct = max(1, n_docs // 100)
    ordered = np.sort(n_irr)[::-1]
    return {
        "skewness": round(skewness(n_irr), 5),
        "gini": round(gini(n_irr), 5),
        "max": int(n_irr.max()) if n_docs else 0,
        "total_irrelevant_slots": total,
        "top_1pct_share": round(float(ordered[:top1pct].sum()) / total, 5) if total else 0.0,
        "never_retrieved": int((n_irr == 0).sum()),
        "documents": n_docs,
    }


def _draw_without_replacement(rng, n_docs: int, n_queries: int, k: int) -> np.ndarray:
    """k distinct document indices per query. Oversamples then de-duplicates."""
    raw = rng.integers(0, n_docs, size=(n_queries, k * 3))
    out = np.empty((n_queries, k), dtype=np.int64)
    for i in range(n_queries):
        seen, c = set(), 0
        for v in raw[i]:
            if v not in seen:
                seen.add(v)
                out[i, c] = v
                c += 1
                if c == k:
                    break
        if c < k:
            out[i] = rng.choice(n_docs, size=k, replace=False)
    return out


def null_skewness(
    doc_ids: list[str],
    query_ids: list[str],
    qrels: dict[str, dict[str, int]],
    k: int = 10,
    n_replicates: int = 1000,
    seed: int = 0,
) -> np.ndarray:
    """Skewness of N_k-irrelevant when each query's top-k is drawn uniformly."""
    rng = np.random.default_rng(seed)
    n_docs = len(doc_ids)
    out = np.empty(n_replicates, dtype=np.float64)
    for r in range(n_replicates):
        draws = _draw_without_replacement(rng, n_docs, len(query_ids), k)
        _n_all, n_irr = irrelevant_counts(draws, doc_ids, query_ids, qrels, n_docs)
        out[r] = skewness(n_irr)
    return out


def test(
    scores: np.ndarray,
    doc_ids: list[str],
    query_ids: list[str],
    qrels: dict[str, dict[str, int]],
    k: int = 10,
    null_replicates: int = 1000,
    seed: int = 0,
    null_cache: np.ndarray | None = None,
) -> dict:
    """Observed hubness against the uniform-random null. Supported at the 99th percentile."""
    topk = top_k_indices(scores, k)
    _n_all, n_irr = irrelevant_counts(topk, doc_ids, query_ids, qrels, len(doc_ids))
    stats = describe(n_irr)

    null = null_cache if null_cache is not None else null_skewness(
        doc_ids, query_ids, qrels, k=k, n_replicates=null_replicates, seed=seed
    )
    p99 = float(np.percentile(null, 99))
    stats.update({
        "null_skewness_mean": round(float(null.mean()), 5),
        "null_skewness_p99": round(p99, 5),
        "null_replicates": int(null.shape[0]),
        "exceeds_null_p99": bool(stats["skewness"] > p99),
        "percentile_in_null": round(float((null < stats["skewness"]).mean() * 100), 2),
    })
    return stats
