"""Document chunking for dense retrieval (PREREGISTRATION.md section 4d.1, H7).

Documents longer than the encoder's limit are truncated, and the one dataset where
that happens most is also the one where dense loses. Chunking removes the truncation,
so it manipulates the proposed cause rather than observing it.

Windows of at most 400 tokens with a 50-token overlap, measured with the model's own
tokenizer. A document scores the maximum over its chunks.
"""

from __future__ import annotations

import numpy as np

MAX_TOKENS = 400
OVERLAP = 50


def chunk_texts(
    texts: list[str], tokenizer, max_tokens: int = MAX_TOKENS, overlap: int = OVERLAP
) -> tuple[list[str], np.ndarray]:
    """Split each text into overlapping windows.

    Returns the flattened chunk texts and, for each chunk, the index of the document
    it came from — so document scores can be recovered by max-pooling.
    """
    stride = max_tokens - overlap
    chunks: list[str] = []
    owner: list[int] = []
    encoded = tokenizer(texts, add_special_tokens=False)["input_ids"]
    for di, ids in enumerate(encoded):
        if len(ids) <= max_tokens:
            chunks.append(texts[di])
            owner.append(di)
            continue
        for start in range(0, len(ids), stride):
            piece = ids[start:start + max_tokens]
            if not piece:
                break
            chunks.append(tokenizer.decode(piece, skip_special_tokens=True))
            owner.append(di)
            if start + max_tokens >= len(ids):
                break
    return chunks, np.asarray(owner, dtype=np.int64)


def max_pool(chunk_scores: np.ndarray, owner: np.ndarray, n_docs: int) -> np.ndarray:
    """(n_queries, n_chunks) -> (n_queries, n_docs), taking each document's best chunk."""
    out = np.full((chunk_scores.shape[0], n_docs), -np.inf, dtype=chunk_scores.dtype)
    np.maximum.at(out.T, owner, chunk_scores.T)
    return np.where(np.isfinite(out), out, 0.0)
