"""BM25 retrieval.

Scoring is delegated to bm25s — the same engine MTEB's published baseline uses —
so that a mismatch against the published number points at this harness (loading,
tokenization, ranking, metrics) rather than at the BM25 implementation.
"""

from __future__ import annotations

import numpy as np


def bm25_score_matrix(
    corpus_tokens: list[list[str]],
    query_tokens: list[list[str]],
    k1: float = 1.5,
    b: float = 0.75,
    method: str = "lucene",
) -> np.ndarray:
    """(n_queries, n_docs) BM25 scores over the whole corpus.

    Hybrid fusion needs scores for every document, not just a truncated
    candidate list, so that the weight curve carries no candidate-set artifact.
    """
    import bm25s

    retriever = bm25s.BM25(k1=k1, b=b, method=method)
    retriever.index(corpus_tokens, show_progress=False)

    out = np.zeros((len(query_tokens), len(corpus_tokens)), dtype=np.float32)
    for i, q in enumerate(query_tokens):
        if q:
            out[i] = retriever.get_scores(q)
    return out


def bm25_run(
    doc_ids: list[str],
    corpus_tokens: list[list[str]],
    query_ids: list[str],
    query_tokens: list[list[str]],
    k: int = 1000,
    k1: float = 1.5,
    b: float = 0.75,
    method: str = "lucene",
) -> dict[str, list[str]]:
    """Rank documents for each query. Returns {query_id: [doc_id, ...]}.

    Defaults are the bm25s defaults, which is what the published baseline used.
    They are not tuned; tuning them would void the reproduction gate.
    """
    import bm25s

    retriever = bm25s.BM25(k1=k1, b=b, method=method)
    retriever.index(corpus_tokens, show_progress=False)

    k = min(k, len(doc_ids))
    results, _scores = retriever.retrieve(query_tokens, k=k, show_progress=False)

    return {
        qid: [doc_ids[int(j)] for j in results[qi]]
        for qi, qid in enumerate(query_ids)
    }
