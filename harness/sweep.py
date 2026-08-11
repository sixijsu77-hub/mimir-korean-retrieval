#!/usr/bin/env python3
"""BM25 alone, dense alone, and the hybrid weight sweep, in one pass.

Score matrices are computed once and reused for every weight, so a fine sweep
costs no more retrieval than a coarse one. Usage:

    python -m harness.sweep --dataset AutoRAGRetrieval \\
        --model intfloat/multilingual-e5-small --tokenizer char_bigram \\
        --out results/hybrid.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from harness import data, dense, fusion, metrics, retrieval, tokenizers

WEIGHTS = [round(float(w), 2) for w in np.arange(0.0, 1.0001, 0.05)]


def slug(name: str) -> str:
    return name.replace("/", "__")


def score_condition(scores, doc_ids, qrels, query_ids, k, bootstrap, seed):
    ranked = fusion.top_k_ids(scores, doc_ids, k)
    run = {qid: ranked[i] for i, qid in enumerate(query_ids)}
    means, per_query = metrics.evaluate(run, qrels)
    lo, hi = metrics.bootstrap_ci_values(
        [s["ndcg_at_10"] for s in per_query.values()], n_resamples=bootstrap, seed=seed
    )
    return means, per_query, (lo, hi)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=data.DATASETS)
    ap.add_argument("--model", required=True)
    ap.add_argument("--tokenizer", default="char_bigram", choices=tokenizers.TOKENIZERS)
    ap.add_argument("--stopwords", default="none")
    ap.add_argument("--stemmer", default="none")
    ap.add_argument("--max-seq-length", type=int, default=512)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--k", type=int, default=1000)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-dir", default="embeddings")
    ap.add_argument("--out", default="results/hybrid.jsonl")
    args = ap.parse_args()

    corpus, queries, qrels = data.load(args.dataset)
    doc_ids, doc_texts = data.corpus_texts(corpus)
    query_ids = list(queries)
    query_texts = [queries[q] for q in query_ids]

    tok_kwargs = {}
    if args.tokenizer == "word":
        tok_kwargs["stopwords"] = None if args.stopwords == "none" else args.stopwords
        if args.stemmer != "none":
            import Stemmer

            tok_kwargs["stemmer"] = Stemmer.Stemmer(args.stemmer)

    t0 = time.time()
    sparse = retrieval.bm25_score_matrix(
        tokenizers.tokenize(args.tokenizer, doc_texts, **tok_kwargs),
        tokenizers.tokenize(args.tokenizer, query_texts, **tok_kwargs),
    )
    t_sparse = time.time() - t0

    base = os.path.join(args.cache_dir, f"{args.dataset}_{slug(args.model)}")
    t1 = time.time()
    model = dense.load_model(args.model, args.max_seq_length)
    doc_emb = dense.encode(doc_texts, dense.PASSAGE_PREFIX, model=model,
                           batch_size=args.batch_size, cache_path=f"{base}_docs.npy")
    query_emb = dense.encode(query_texts, dense.QUERY_PREFIX, model=model,
                             batch_size=args.batch_size, cache_path=f"{base}_queries.npy")
    t_encode = time.time() - t1
    dense_scores = dense.cosine_score_matrix(query_emb, doc_emb)

    curves = {}
    best = {}
    for norm_name, norm in fusion.NORMALIZERS.items():
        s_n, d_n = norm(sparse), norm(dense_scores)
        curve = []
        for w in WEIGHTS:
            means, _pq, (lo, hi) = score_condition(
                fusion.blend(s_n, d_n, w), doc_ids, qrels, query_ids,
                args.k, args.bootstrap, args.seed)
            curve.append({
                "w_dense": w,
                "ndcg_at_10": round(means["ndcg_at_10"], 5),
                "ci95": [round(lo, 5), round(hi, 5)],
                "recall_at_10": round(means["recall_at_10"], 5),
                "recall_at_100": round(means["recall_at_100"], 5),
            })
        curves[norm_name] = curve
        top = max(curve, key=lambda r: r["ndcg_at_10"])
        # Weights whose interval overlaps the best weight's interval are not
        # distinguishable from it, and are reported as such rather than ranked.
        tied = [r["w_dense"] for r in curve
                if not (r["ci95"][1] < top["ci95"][0] or top["ci95"][1] < r["ci95"][0])]
        best[norm_name] = {"w_dense": top["w_dense"], "ndcg_at_10": top["ndcg_at_10"],
                           "ci95": top["ci95"], "not_distinguishable_from_best": tied}

    sparse_only = curves["minmax"][0]
    dense_only = curves["minmax"][-1]

    record = {
        "dataset": args.dataset,
        "model": args.model,
        "tokenizer": args.tokenizer,
        "stopwords": args.stopwords,
        "stemmer": args.stemmer,
        "max_seq_length": args.max_seq_length,
        "embedding_dim": int(doc_emb.shape[1]),
        "n_documents": len(doc_ids),
        "n_queries": len(query_ids),
        "bootstrap_resamples": args.bootstrap,
        "seed": args.seed,
        "sparse_only": sparse_only,
        "dense_only": dense_only,
        "best": best,
        "curves": curves,
        "seconds": {"bm25": round(t_sparse, 2), "encode": round(t_encode, 2)},
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    p = lambda *a: print(*a, file=sys.stderr)
    p(f"{args.dataset} | {args.model} | sparse={args.tokenizer}")
    p(f"  docs={len(doc_ids):,} queries={len(query_ids):,} dim={doc_emb.shape[1]} "
      f"| bm25 {t_sparse:.1f}s, encode {t_encode:.1f}s")
    p(f"  BM25 alone  nDCG@10={sparse_only['ndcg_at_10']:.5f} {sparse_only['ci95']}")
    p(f"  dense alone nDCG@10={dense_only['ndcg_at_10']:.5f} {dense_only['ci95']}")
    for norm_name, b in best.items():
        p(f"  best[{norm_name}] w_dense={b['w_dense']} nDCG@10={b['ndcg_at_10']:.5f} "
          f"{b['ci95']} | not distinguishable: {b['not_distinguishable_from_best']}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
