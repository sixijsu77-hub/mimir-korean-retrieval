#!/usr/bin/env python3
"""Week-3 analyses: paired weight comparison and hubness.

Both are specified in PREREGISTRATION.md section 4b, committed before this ran.

    python -m harness.analyze --dataset Ko-StrategyQA \\
        --model intfloat/multilingual-e5-large --out results/week3.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from harness import data, dense, fusion, hubness, metrics, retrieval, tokenizers

WEIGHTS = [round(float(w), 2) for w in np.arange(0.0, 1.0001, 0.05)]
N_COMPARISONS = len(WEIGHTS) - 1  # each weight against the point-estimate best
ALPHA = 0.05
ALPHA_BONF = ALPHA / N_COMPARISONS


def per_query_ndcg(scores, doc_ids, query_ids, qrels, k) -> np.ndarray:
    ranked = fusion.top_k_ids(scores, doc_ids, k)
    return np.array(
        [metrics.ndcg_at_k(ranked[i], qrels.get(q, {}), 10) for i, q in enumerate(query_ids)],
        dtype=np.float64,
    )


def paired_block(curve: np.ndarray, weights, resamples, seed):
    """curve is (n_weights, n_queries) of per-query nDCG@10."""
    weight_means = curve.mean(axis=1)
    bi = int(np.argmax(weight_means))
    rows = []
    for i, w in enumerate(weights):
        if i == bi:
            rows.append({"w_dense": w, "mean_diff": 0.0, "ci95": [0.0, 0.0],
                         "ci_bonferroni": [0.0, 0.0], "is_best": True})
            continue
        md, boot = metrics.paired_bootstrap_means(
            curve[bi], curve[i], n_resamples=resamples, seed=seed)
        lo95, hi95 = metrics.percentile_interval(boot, ALPHA)
        lob, hib = metrics.percentile_interval(boot, ALPHA_BONF)
        rows.append({"w_dense": w, "mean_diff": round(md, 5),
                     "ci95": [round(lo95, 5), round(hi95, 5)],
                     "ci_bonferroni": [round(lob, 5), round(hib, 5)], "is_best": False})
    indist95 = [r["w_dense"] for r in rows if r["is_best"] or r["ci95"][0] <= 0 <= r["ci95"][1]]
    indistb = [r["w_dense"] for r in rows
               if r["is_best"] or r["ci_bonferroni"][0] <= 0 <= r["ci_bonferroni"][1]]
    return {
        "best_w": weights[bi],
        "best_ndcg_at_10": round(float(weight_means[bi]), 5),
        "n_comparisons": N_COMPARISONS,
        "alpha_bonferroni": round(ALPHA_BONF, 6),
        "bootstrap_resamples": resamples,
        "indistinguishable_uncorrected": indist95,
        "indistinguishable_bonferroni": indistb,
        "h2_band_survives": any(0.2 <= w <= 0.4 for w in indistb),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=data.DATASETS)
    ap.add_argument("--model", required=True)
    ap.add_argument("--tokenizer", default="char_bigram", choices=tokenizers.TOKENIZERS)
    ap.add_argument("--k", type=int, default=1000)
    ap.add_argument("--resamples", type=int, default=10000, help="pre-registered value")
    ap.add_argument("--resamples-highb", type=int, default=100000,
                    help="Monte-Carlo precision check on the Bonferroni tail; not pre-registered")
    ap.add_argument("--null-replicates", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-dir", default="embeddings")
    ap.add_argument("--out", default="results/week3.jsonl")
    args = ap.parse_args()

    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    corpus, queries, qrels = data.load(args.dataset)
    doc_ids, doc_texts = data.corpus_texts(corpus)
    query_ids = list(queries)
    query_texts = [queries[q] for q in query_ids]

    t0 = time.time()
    sparse = retrieval.bm25_score_matrix(
        tokenizers.tokenize(args.tokenizer, doc_texts),
        tokenizers.tokenize(args.tokenizer, query_texts))
    base = os.path.join(args.cache_dir, f"{args.dataset}_{args.model.replace('/', '__')}")
    model = dense.load_model(args.model)
    doc_emb = dense.encode(doc_texts, dense.PASSAGE_PREFIX, model=model,
                           cache_path=f"{base}_docs.npy")
    query_emb = dense.encode(query_texts, dense.QUERY_PREFIX, model=model,
                             cache_path=f"{base}_queries.npy")
    dense_scores = dense.cosine_score_matrix(query_emb, doc_emb)
    p(f"  scores ready in {time.time()-t0:.1f}s")

    paired = {}
    for norm_name, norm in fusion.NORMALIZERS.items():
        s_n, d_n = norm(sparse), norm(dense_scores)
        curve = np.vstack([
            per_query_ndcg(fusion.blend(s_n, d_n, w), doc_ids, query_ids, qrels, args.k)
            for w in WEIGHTS])
        block = paired_block(curve, WEIGHTS, args.resamples, args.seed)
        block_high = paired_block(curve, WEIGHTS, args.resamples_highb, args.seed)
        block["highb_check"] = {
            "bootstrap_resamples": args.resamples_highb,
            "indistinguishable_bonferroni": block_high["indistinguishable_bonferroni"],
            "agrees_with_preregistered_b": (
                block_high["indistinguishable_bonferroni"]
                == block["indistinguishable_bonferroni"]),
        }
        paired[norm_name] = block
        p(f"  paired[{norm_name}] best_w={block['best_w']} "
          f"indist(bonf)={block['indistinguishable_bonferroni']}")

    t1 = time.time()
    null = hubness.null_skewness(doc_ids, query_ids, qrels, k=10,
                                 n_replicates=args.null_replicates, seed=args.seed)
    p(f"  null model ({args.null_replicates} replicates) in {time.time()-t1:.1f}s")
    hub = {
        "dense": hubness.test(dense_scores, doc_ids, query_ids, qrels, null_cache=null),
        "bm25_char_bigram": hubness.test(sparse, doc_ids, query_ids, qrels, null_cache=null),
    }

    record = {
        "dataset": args.dataset,
        "model": args.model,
        "tokenizer": args.tokenizer,
        "n_documents": len(doc_ids),
        "n_queries": len(query_ids),
        "seed": args.seed,
        "paired": paired,
        "hubness": hub,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    for name, h in hub.items():
        p(f"  hubness[{name}] skew={h['skewness']} null_p99={h['null_skewness_p99']} "
          f"exceeds={h['exceeds_null_p99']} gini={h['gini']} max={h['max']} "
          f"top1%={h['top_1pct_share']}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
