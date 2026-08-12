#!/usr/bin/env python3
"""Does BM25's length normalization cause hubness? (H10, PREREGISTRATION.md section 4e.2)

Week 3 measured character-bigram BM25 as far more hub-prone than dense retrieval and could
not explain it. `b` controls how much document length is normalized away (0 = none,
1 = full), so it is the one candidate that can be manipulated rather than correlated.

Everything else is held at the values used throughout: k1 = 1.5, Lucene, character bigrams,
top-10, and the same `N10_irr` statistic and uniform-random null as section 4b.2. nDCG@10 is
reported at every `b` — a setting that removes hubness while destroying accuracy is not a
fix, and the trade-off should be visible rather than argued.

    python -m harness.length_norm --dataset Ko-StrategyQA --out results/length_norm.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from harness import data, hubness, metrics, retrieval, tokenizers

B_VALUES = [0.0, 0.25, 0.5, 0.75, 1.0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=data.DATASETS)
    ap.add_argument("--tokenizer", default="char_bigram", choices=tokenizers.TOKENIZERS)
    ap.add_argument("--b", default=",".join(str(b) for b in B_VALUES))
    ap.add_argument("--k1", type=float, default=1.5)
    ap.add_argument("--null-replicates", type=int, default=1000)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/length_norm.jsonl")
    args = ap.parse_args()
    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    corpus, queries, qrels = data.load(args.dataset)
    doc_ids, doc_texts = data.corpus_texts(corpus)
    query_ids = list(queries)
    corpus_tokens = tokenizers.tokenize(args.tokenizer, doc_texts)
    query_tokens = tokenizers.tokenize(args.tokenizer, [queries[q] for q in query_ids])
    p(f"  {args.dataset}: {len(doc_ids):,} docs, {len(query_ids)} queries, "
      f"tokenizer={args.tokenizer}")

    # The null depends only on corpus size, query count and qrels, so it is drawn once.
    t0 = time.time()
    null = hubness.null_skewness(doc_ids, query_ids, qrels, k=10,
                                 n_replicates=args.null_replicates, seed=args.seed)
    p(f"  null model ({args.null_replicates} replicates) in {time.time()-t0:.1f}s")

    rows = []
    for b in [float(x) for x in args.b.split(",")]:
        t1 = time.time()
        scores = retrieval.bm25_score_matrix(corpus_tokens, query_tokens, k1=args.k1, b=b)
        hub = hubness.test(scores, doc_ids, query_ids, qrels, k=10, null_cache=null)
        order = np.argsort(-scores, axis=1)[:, :1000]
        run = {q: [doc_ids[j] for j in order[i]] for i, q in enumerate(query_ids)}
        means, per_query = metrics.evaluate(run, qrels)
        lo, hi = metrics.bootstrap_ci(per_query, "ndcg_at_10",
                                      n_resamples=args.bootstrap, seed=args.seed)
        rows.append({
            "b": b,
            "skewness": hub["skewness"],
            "gini": hub["gini"],
            "max_n10_irr": hub["max"],
            "top_1pct_share": hub["top_1pct_share"],
            "exceeds_null_p99": hub["exceeds_null_p99"],
            "null_skewness_p99": hub["null_skewness_p99"],
            "ndcg_at_10": round(means["ndcg_at_10"], 5),
            "ndcg_at_10_ci95": [round(lo, 5), round(hi, 5)],
            "per_query_ndcg_at_10": {q: round(s["ndcg_at_10"], 5)
                                     for q, s in per_query.items()},
            "seconds": round(time.time() - t1, 1),
        })
        r = rows[-1]
        p(f"  b={b:<5} skew={r['skewness']:>10.4f} gini={r['gini']:.5f} "
          f"max={r['max_n10_irr']:>4} nDCG@10={r['ndcg_at_10']:.5f} {r['seconds']}s")

    # Accuracy against the b = 0.75 default, paired at the query level. The registration
    # asks for the trade-off to be visible; a difference is not called one without this.
    base = next((r for r in rows if r["b"] == 0.75), None)
    if base is not None:
        qs = list(base["per_query_ndcg_at_10"])
        for r in rows:
            d, lo_, hi_ = metrics.paired_bootstrap_diff(
                [r["per_query_ndcg_at_10"][q] for q in qs],
                [base["per_query_ndcg_at_10"][q] for q in qs],
                args.bootstrap, seed=args.seed)
            r["ndcg_vs_b075"] = {"difference": round(d, 5),
                                 "ci95": [round(lo_, 5), round(hi_, 5)],
                                 "distinguishable": bool(lo_ > 0 or hi_ < 0)}
            p(f"  b={r['b']:<5} nDCG vs b=0.75: {d:+.5f} [{lo_:+.5f},{hi_:+.5f}] "
              f"{'distinguishable' if r['ndcg_vs_b075']['distinguishable'] else 'not distinguishable'}")

    by_b = {r["b"]: r["skewness"] for r in rows}
    verdict = None
    if 1.0 in by_b and 0.75 in by_b:
        # H10 as registered: skewness falls as b rises, tested at 1.0 against 0.75.
        verdict = {
            "skew_b100_below_b075": bool(by_b[1.0] < by_b[0.75]),
            "skew_b000_is_highest": bool(0.0 in by_b and by_b[0.0] == max(by_b.values())),
        }

    record = {
        "dataset": args.dataset,
        "tokenizer": args.tokenizer,
        "k1": args.k1,
        "n_documents": len(doc_ids),
        "n_queries": len(query_ids),
        "seed": args.seed,
        "null_replicates": args.null_replicates,
        "by_b": rows,
        "h10": verdict,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    if verdict:
        p(f"  H10: skew(b=1.0) < skew(b=0.75) -> {verdict['skew_b100_below_b075']} | "
          f"skew(b=0.0) highest -> {verdict['skew_b000_is_highest']}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
