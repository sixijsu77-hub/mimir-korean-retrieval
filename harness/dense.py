"""Dense encoding and exact cosine search.

Search is brute force. With 213-592 queries the exhaustive product is under a
second on the GPU used, and an approximate index would fold its own recall loss
into the measurement.

e5 models require the `query: ` / `passage: ` prefixes. Omitting them lowers
scores without any error, so they are required arguments rather than defaults.
"""

from __future__ import annotations

import os

import numpy as np

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


def load_model(model_name: str, max_seq_length: int = 512):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device="cuda")
    model.max_seq_length = max_seq_length
    return model


def encode(
    texts: list[str],
    prefix: str,
    model=None,
    model_name: str | None = None,
    batch_size: int = 64,
    max_seq_length: int = 512,
    cache_path: str | None = None,
) -> np.ndarray:
    """Return L2-normalized float32 embeddings, one row per text.

    Reuses `cache_path` if it exists; embeddings are expensive and every hybrid
    weight reuses the same vectors.
    """
    if cache_path and os.path.exists(cache_path):
        emb = np.load(cache_path)
        if emb.shape[0] == len(texts):
            return emb
        raise ValueError(
            f"cache {cache_path} holds {emb.shape[0]} rows, expected {len(texts)}"
        )

    if model is None:
        model = load_model(model_name, max_seq_length)
    emb = model.encode(
        [prefix + t for t in texts],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32)

    if cache_path:
        os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
        np.save(cache_path, emb)
    return emb


def cosine_score_matrix(
    query_emb: np.ndarray, doc_emb: np.ndarray, chunk: int = 200_000
) -> np.ndarray:
    """(n_queries, n_docs) cosine similarities. Inputs must be L2-normalized.

    Documents are processed in chunks so corpora far larger than these fit.
    """
    out = np.empty((query_emb.shape[0], doc_emb.shape[0]), dtype=np.float32)
    for start in range(0, doc_emb.shape[0], chunk):
        stop = min(start + chunk, doc_emb.shape[0])
        out[:, start:stop] = query_emb @ doc_emb[start:stop].T
    return out
