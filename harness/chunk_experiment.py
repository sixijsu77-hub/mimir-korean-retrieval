#!/usr/bin/env python3
"""exp02 — does chunking recover dense retrieval on truncated corpora? (H7)

Specified in PREREGISTRATION.md section 4d.1, committed before this ran.

    python -m harness.chunk_experiment --dataset AutoRAGRetrieval \\
        --model intfloat/multilingual-e5-large --out results/chunking.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from harness import chunking, data, dense, fusion, metrics, retrieval, tokenizers

WEIGHTS = [round(float(w), 2) for w in np.arange(0.0, 1.0001, 0.05)]


def per_query_ndcg(scores, doc_ids, query_ids, qrels, k=1000) -> np.ndarray:
    ranked = fusion.top_k_ids(scores, doc_ids, k)
    return np.array([metrics.ndcg_at_k(ranked[i], qrels.get(q, {}), 10)
                     for i, q in enumerate(query_ids)], dtype=np.float64)


def curve_stats(sparse, dsc, doc_ids, query_ids, qrels, seed):
    s_n, d_n = fusion.minmax(sparse), fusion.minmax(dsc)
    per_w = np.vstack([per_query_ndcg(fusion.blend(s_n, d_n, w), doc_ids, query_ids, qrels)
                       for w in WEIGHTS])
    means = per_w.mean(axis=1)
    bi = int(np.argmax(means))
    lo, hi = metrics.bootstrap_ci_values(list(per_w[bi]), n_resamples=10000, seed=seed)
    amp = float(means.max() - means.min())
    width = hi - lo
    return {
        "best_w": WEIGHTS[bi], "best_ndcg_at_10": round(float(means[bi]), 5),
        "amplitude": round(amp, 5), "ci95_width_at_best": round(width, 5),
        "amplitude_over_ci_width": round(amp / width, 4) if width else None,
        "curve": [{"w_dense": w, "ndcg_at_10": round(float(m), 5)}
                  for w, m in zip(WEIGHTS, means)],
    }, per_w


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=data.DATASETS)
    ap.add_argument("--model", default="intfloat/multilingual-e5-large")
    ap.add_argument("--tokenizer", default="char_bigram", choices=tokenizers.TOKENIZERS)
    ap.add_argument("--max-tokens", type=int, default=chunking.MAX_TOKENS)
    ap.add_argument("--overlap", type=int, default=chunking.OVERLAP)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-dir", default="embeddings")
    ap.add_argument("--out", default="results/chunking.jsonl")
    args = ap.parse_args()
    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    corpus, queries, qrels = data.load(args.dataset)
    doc_ids, doc_texts = data.corpus_texts(corpus)
    query_ids = list(queries)
    query_texts = [queries[q] for q in query_ids]

    sparse = retrieval.bm25_score_matrix(
        tokenizers.tokenize(args.tokenizer, doc_texts),
        tokenizers.tokenize(args.tokenizer, query_texts))

    model = dense.load_model(args.model)
    base = os.path.join(args.cache_dir, f"{args.dataset}_{args.model.replace('/', '__')}")
    q_emb = dense.encode(query_texts, dense.QUERY_PREFIX, model=model,
                         cache_path=f"{base}_queries.npy")

    # unchunked — the week-2/3 configuration
    doc_emb = dense.encode(doc_texts, dense.PASSAGE_PREFIX, model=model,
                           cache_path=f"{base}_docs.npy")
    dense_plain = dense.cosine_score_matrix(q_emb, doc_emb)

    # chunked
    t0 = time.time()
    chunks, owner = chunking.chunk_texts(doc_texts, model.tokenizer,
                                         args.max_tokens, args.overlap)
    p(f"  {len(doc_texts):,} documents -> {len(chunks):,} chunks "
      f"({len(chunks)/len(doc_texts):.2f} per document) in {time.time()-t0:.0f}s")
    chunk_emb = dense.encode(chunks, dense.PASSAGE_PREFIX, model=model,
                             cache_path=f"{base}_chunks{args.max_tokens}_{args.overlap}.npy")
    dense_chunked = chunking.max_pool(
        dense.cosine_score_matrix(q_emb, chunk_emb), owner, len(doc_ids))

    plain_pq = per_query_ndcg(dense_plain, doc_ids, query_ids, qrels)
    chunk_pq = per_query_ndcg(dense_chunked, doc_ids, query_ids, qrels)
    gain, lo, hi = metrics.paired_bootstrap_diff(list(chunk_pq), list(plain_pq),
                                                 n_resamples=10000, seed=args.seed)
    h7 = {"dense_plain": round(float(plain_pq.mean()), 5),
          "dense_chunked": round(float(chunk_pq.mean()), 5),
          "gain": round(gain, 5), "gain_ci95": [round(lo, 5), round(hi, 5)],
          "excludes_zero": bool(lo > 0 or hi < 0)}

    plain_curve, _ = curve_stats(sparse, dense_plain, doc_ids, query_ids, qrels, args.seed)
    chunk_curve, _ = curve_stats(sparse, dense_chunked, doc_ids, query_ids, qrels, args.seed)

    # Week 2 flagged that H1 survived only where truncation handicapped dense.
    # With truncation removed, does the sparse side still win?
    sparse_pq = per_query_ndcg(sparse, doc_ids, query_ids, qrels)
    sd, slo, shi = metrics.paired_bootstrap_diff(list(sparse_pq), list(chunk_pq),
                                                 n_resamples=10000, seed=args.seed)
    sparse_vs_chunked = {
        "bm25_char_bigram": round(float(sparse_pq.mean()), 5),
        "dense_chunked": round(float(chunk_pq.mean()), 5),
        "difference": round(sd, 5), "ci95": [round(slo, 5), round(shi, 5)],
        "excludes_zero": bool(slo > 0 or shi < 0),
    }

    record = {
        "dataset": args.dataset, "model": args.model, "tokenizer": args.tokenizer,
        "max_tokens": args.max_tokens, "overlap": args.overlap,
        "n_documents": len(doc_ids), "n_chunks": len(chunks),
        "chunks_per_document": round(len(chunks) / len(doc_ids), 4),
        "n_queries": len(query_ids), "seed": args.seed,
        "h7": h7, "sparse_vs_chunked_dense": sparse_vs_chunked,
        "curve_plain": plain_curve, "curve_chunked": chunk_curve,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    p(f"  dense alone: {h7['dense_plain']:.5f} -> {h7['dense_chunked']:.5f}  "
      f"gain {h7['gain']:+.5f} {h7['gain_ci95']}  "
      f"{'excludes 0 (H7 holds here)' if h7['excludes_zero'] else 'includes 0'}")
    for name, c in [("plain", plain_curve), ("chunked", chunk_curve)]:
        p(f"  curve[{name}]  best_w={c['best_w']}  amplitude={c['amplitude']:.4f}  "
          f"amp/CI={c['amplitude_over_ci_width']}")
    p(f"  bm25 {sparse_vs_chunked['bm25_char_bigram']:.5f} vs chunked dense "
      f"{sparse_vs_chunked['dense_chunked']:.5f}  diff {sparse_vs_chunked['difference']:+.5f} "
      f"{sparse_vs_chunked['ci95']}  excludes 0: {sparse_vs_chunked['excludes_zero']}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
