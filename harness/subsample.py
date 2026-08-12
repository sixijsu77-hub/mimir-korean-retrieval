#!/usr/bin/env python3
"""How many queries does a hybrid weight need? (PREREGISTRATION.md section 4c, H6)

Per-query nDCG@10 is computed once for every weight, then queries are subsampled
from those columns — so sample size is the only thing that varies.

    python -m harness.subsample --dataset Ko-StrategyQA \\
        --model intfloat/multilingual-e5-large --out results/subsample.jsonl
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
SIZES = [12, 25, 50, 100, 200, 400]
REPLICATES = 30
ALPHA = 0.05  # uncorrected on purpose; see section 4c
THIRD = len(WEIGHTS) / 3


def curve_matrix(sparse, dense_scores, doc_ids, query_ids, qrels, k, norm):
    s_n, d_n = norm(sparse), norm(dense_scores)
    rows = []
    for w in WEIGHTS:
        ranked = fusion.top_k_ids(fusion.blend(s_n, d_n, w), doc_ids, k)
        rows.append([metrics.ndcg_at_k(ranked[i], qrels.get(q, {}), 10)
                     for i, q in enumerate(query_ids)])
    return np.asarray(rows, dtype=np.float64)


def analyse(curve: np.ndarray, resamples: int, seed: int) -> dict:
    """argmax weight and the set of weights indistinguishable from it."""
    means = curve.mean(axis=1)
    bi = int(np.argmax(means))
    indist = [WEIGHTS[bi]]
    for i in range(len(WEIGHTS)):
        if i == bi:
            continue
        _, boot = metrics.paired_bootstrap_means(curve[bi], curve[i],
                                                 n_resamples=resamples, seed=seed)
        lo, hi = metrics.percentile_interval(boot, ALPHA)
        if lo <= 0 <= hi:
            indist.append(WEIGHTS[i])
    return {"argmax": WEIGHTS[bi], "indistinguishable": sorted(indist)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=data.DATASETS)
    ap.add_argument("--model", default="intfloat/multilingual-e5-large")
    ap.add_argument("--tokenizer", default="char_bigram", choices=tokenizers.TOKENIZERS)
    ap.add_argument("--k", type=int, default=1000)
    ap.add_argument("--resamples", type=int, default=10000)
    ap.add_argument("--replicates", type=int, default=REPLICATES)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cache-dir", default="embeddings")
    ap.add_argument("--out", default="results/subsample.jsonl")
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
    q_emb = dense.encode(query_texts, dense.QUERY_PREFIX, model=model,
                         cache_path=f"{base}_queries.npy")
    curve = curve_matrix(sparse, dense.cosine_score_matrix(q_emb, doc_emb),
                         doc_ids, query_ids, qrels, args.k, fusion.minmax)
    n_all = curve.shape[1]
    p(f"  per-query curve {curve.shape} in {time.time()-t0:.0f}s")

    rng = np.random.default_rng(args.seed)
    results = []
    for n in [s for s in SIZES if s < n_all] + [n_all]:
        reps = 1 if n == n_all else args.replicates
        argmaxes, sizes, full_cover = [], [], 0
        for r in range(reps):
            idx = (np.arange(n_all) if n == n_all
                   else rng.choice(n_all, size=n, replace=False))
            a = analyse(curve[:, idx], args.resamples, args.seed)
            argmaxes.append(a["argmax"])
            sizes.append(len(a["indistinguishable"]))
            full_cover += int(len(a["indistinguishable"]) == len(WEIGHTS))
        q1, q3 = np.percentile(argmaxes, [25, 75])
        results.append({
            "n_queries": int(n), "replicates": reps,
            "argmax_median": float(np.median(argmaxes)),
            "argmax_iqr": round(float(q3 - q1), 4),
            "argmax_min": float(min(argmaxes)), "argmax_max": float(max(argmaxes)),
            "indistinguishable_median": float(np.median(sizes)),
            "indistinguishable_median_pct": round(float(np.median(sizes)) / len(WEIGHTS), 4),
            "all_weights_covered_fraction": round(full_cover / reps, 4),
        })
        r0 = results[-1]
        p(f"  n={n:>4} reps={reps:>2}  argmax median={r0['argmax_median']:.2f} "
          f"IQR={r0['argmax_iqr']:.2f} range=[{r0['argmax_min']:.2f},{r0['argmax_max']:.2f}]  "
          f"indist median={r0['indistinguishable_median']:.0f}/{len(WEIGHTS)} "
          f"({r0['indistinguishable_median_pct']*100:.0f}%)")

    below_third = [r["n_queries"] for r in results
                   if r["indistinguishable_median"] < THIRD]
    at12 = next((r for r in results if r["n_queries"] == 12), None)
    record = {
        "dataset": args.dataset, "model": args.model, "tokenizer": args.tokenizer,
        "normalization": "minmax", "alpha": ALPHA, "corrected": False,
        "bootstrap_resamples": args.resamples, "seed": args.seed,
        "n_queries_total": int(n_all), "weights": len(WEIGHTS),
        "by_size": results,
        "smallest_n_below_one_third": min(below_third) if below_third else None,
        "h6": None if at12 is None else {
            "argmax_iqr": at12["argmax_iqr"],
            "indistinguishable_median_pct": at12["indistinguishable_median_pct"],
            "supported": bool(at12["argmax_iqr"] >= 0.30
                              and at12["indistinguishable_median_pct"] >= 0.90),
        },
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    if record["h6"]:
        p(f"  H6 (n=12): IQR={record['h6']['argmax_iqr']:.2f} (>=0.30?) "
          f"indist={record['h6']['indistinguishable_median_pct']*100:.0f}% (>=90%?) "
          f"-> {'supported' if record['h6']['supported'] else 'not supported'}")
    p(f"  smallest n with median indistinguishable set below one third: "
      f"{record['smallest_n_below_one_third']}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
