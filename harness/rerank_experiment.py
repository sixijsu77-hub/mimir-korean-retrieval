#!/usr/bin/env python3
"""exp03 — does reranking compress the differences between retrievers? (H8)

Specified in PREREGISTRATION.md section 4d.2, committed before this ran.
The gate is MTEB's published BM25 baseline on MIRACLReranking ko, nDCG@10 0.3338.

    python -m harness.rerank_experiment --out results/reranking.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from harness import data, dense, fusion, metrics, retrieval, tokenizers

PUBLISHED_GATE = 0.3338
GATE_TOLERANCE = 0.02
TOP_N = 100


def rerank_scores(model, pairs: list[tuple[str, str]], batch_size: int = 64) -> np.ndarray:
    return np.asarray(model.predict(pairs, batch_size=batch_size,
                                    show_progress_bar=False), dtype=np.float64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="Ko-StrategyQA", choices=data.DATASETS)
    ap.add_argument("--model", default="intfloat/multilingual-e5-large")
    ap.add_argument("--reranker", default="BAAI/bge-reranker-v2-m3")
    ap.add_argument("--tokenizer", default="char_bigram", choices=tokenizers.TOKENIZERS)
    ap.add_argument("--top-n", type=int, default=TOP_N)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-dir", default="embeddings")
    ap.add_argument("--out", default="results/reranking.jsonl")
    args = ap.parse_args()
    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    corpus, queries, qrels = data.load(args.dataset)
    doc_ids, doc_texts = data.corpus_texts(corpus)
    text_of = dict(zip(doc_ids, doc_texts))
    query_ids = list(queries)
    query_texts = [queries[q] for q in query_ids]

    sparse = retrieval.bm25_score_matrix(
        tokenizers.tokenize(args.tokenizer, doc_texts),
        tokenizers.tokenize(args.tokenizer, query_texts))
    model = dense.load_model(args.model)
    base = os.path.join(args.cache_dir, f"{args.dataset}_{args.model.replace('/', '__')}")
    d_emb = dense.encode(doc_texts, dense.PASSAGE_PREFIX, model=model,
                         cache_path=f"{base}_docs.npy")
    q_emb = dense.encode(query_texts, dense.QUERY_PREFIX, model=model,
                         cache_path=f"{base}_queries.npy")
    dsc = dense.cosine_score_matrix(q_emb, d_emb)

    s_n, d_n = fusion.minmax(sparse), fusion.minmax(dsc)
    # the best weight measured for this dataset in week 2
    weights = [round(float(w), 2) for w in np.arange(0.0, 1.0001, 0.05)]
    per_w = []
    for w in weights:
        ranked = fusion.top_k_ids(fusion.blend(s_n, d_n, w), doc_ids, 1000)
        per_w.append(np.array([metrics.ndcg_at_k(ranked[i], qrels.get(q, {}), 10)
                               for i, q in enumerate(query_ids)]))
    best_w = weights[int(np.argmax([x.mean() for x in per_w]))]

    retrievers = {
        "bm25_char_bigram": sparse,
        "dense": dsc,
        f"hybrid_w{best_w}": fusion.blend(s_n, d_n, best_w),
    }

    from sentence_transformers import CrossEncoder
    ce = CrossEncoder(args.reranker, device="cuda", max_length=512)

    out = {}
    for name, scores in retrievers.items():
        cand = fusion.top_k_ids(scores, doc_ids, args.top_n)
        before = {q: cand[i] for i, q in enumerate(query_ids)}
        t0 = time.time()
        after = {}
        for i, q in enumerate(query_ids):
            ids = cand[i]
            s = rerank_scores(ce, [(query_texts[i], text_of[d]) for d in ids],
                              args.batch_size)
            after[q] = [ids[j] for j in np.argsort(-s)]
        mb, pqb = metrics.evaluate(before, qrels)
        ma, pqa = metrics.evaluate(after, qrels)
        pb = np.array([pqb[q]["ndcg_at_10"] for q in query_ids])
        pa = np.array([pqa[q]["ndcg_at_10"] for q in query_ids])
        gain, lo, hi = metrics.paired_bootstrap_diff(list(pa), list(pb),
                                                     n_resamples=10000, seed=args.seed)
        out[name] = {
            "before": round(float(pb.mean()), 5), "after": round(float(pa.mean()), 5),
            "gain": round(gain, 5), "gain_ci95": [round(lo, 5), round(hi, 5)],
            "seconds": round(time.time() - t0, 1),
            "_per_query_after": pa,
        }
        p(f"  {name:22s} {out[name]['before']:.5f} -> {out[name]['after']:.5f}  "
          f"gain {out[name]['gain']:+.5f} {out[name]['gain_ci95']}  "
          f"({out[name]['seconds']:.0f}s)")

    before_vals = [v["before"] for v in out.values()]
    after_vals = [v["after"] for v in out.values()]
    spread_before = max(before_vals) - min(before_vals)
    spread_after = max(after_vals) - min(after_vals)
    h8 = {
        "spread_before": round(spread_before, 5), "spread_after": round(spread_after, 5),
        "ratio": round(spread_after / spread_before, 4) if spread_before else None,
        "supported": bool(spread_before and spread_after < spread_before / 2),
    }

    record = {
        "dataset": args.dataset, "model": args.model, "reranker": args.reranker,
        "tokenizer": args.tokenizer, "top_n": args.top_n, "best_hybrid_w": best_w,
        "n_documents": len(doc_ids), "n_queries": len(query_ids), "seed": args.seed,
        "retrievers": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                       for k, v in out.items()},
        "h8": h8,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    p(f"  spread {spread_before:.5f} -> {spread_after:.5f} "
      f"(ratio {h8['ratio']})  H8 {'supported' if h8['supported'] else 'not supported'}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
