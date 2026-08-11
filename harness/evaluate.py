#!/usr/bin/env python3
"""Run one BM25 configuration and score it.

Harness validation gate (PREREGISTRATION.md section 4): reproduce MTEB's
published BM25 nDCG@10 on AutoRAGRetrieval and Ko-StrategyQA, within 0.02 on
both. Usage:

    python -m harness.evaluate --dataset AutoRAGRetrieval --tokenizer word \\
        --stopwords en --stemmer english --out results/gate_bm25.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from harness import data, metrics, retrieval, tokenizers

# Published MTEB baseline-bm25s nDCG@10. Sources in docs/baselines.md.
PUBLISHED_NDCG10 = {
    "AutoRAGRetrieval": 0.65022,
    "Ko-StrategyQA": 0.37808,
}
GATE_TOLERANCE = 0.02


def build_query_texts(queries: dict[str, str]) -> tuple[list[str], list[str]]:
    ids = list(queries)
    return ids, [queries[i] for i in ids]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=data.DATASETS)
    ap.add_argument("--tokenizer", required=True, choices=tokenizers.TOKENIZERS)
    ap.add_argument("--stopwords", default="none",
                    help="'en' or 'none'. Applies to the word tokenizer only.")
    ap.add_argument("--stemmer", default="none",
                    help="'english' or 'none'. Applies to the word tokenizer only.")
    ap.add_argument("--k", type=int, default=1000, help="documents retrieved per query")
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/gate_bm25.jsonl")
    args = ap.parse_args()

    t0 = time.time()
    corpus, queries, qrels = data.load(args.dataset)
    doc_ids, doc_texts = data.corpus_texts(corpus)
    query_ids, query_texts = build_query_texts(queries)
    t_load = time.time() - t0

    tok_kwargs = {}
    if args.tokenizer == "word":
        tok_kwargs["stopwords"] = None if args.stopwords == "none" else args.stopwords
        if args.stemmer != "none":
            import Stemmer

            tok_kwargs["stemmer"] = Stemmer.Stemmer(args.stemmer)

    t1 = time.time()
    corpus_tokens = tokenizers.tokenize(args.tokenizer, doc_texts, **tok_kwargs)
    query_tokens = tokenizers.tokenize(args.tokenizer, query_texts, **tok_kwargs)
    t_tok = time.time() - t1

    t2 = time.time()
    run = retrieval.bm25_run(doc_ids, corpus_tokens, query_ids, query_tokens, k=args.k)
    t_search = time.time() - t2

    means, per_query = metrics.evaluate(run, qrels)
    lo, hi = metrics.bootstrap_ci(per_query, "ndcg_at_10",
                                  n_resamples=args.bootstrap, seed=args.seed)

    vocab = {t for toks in corpus_tokens for t in toks}
    record = {
        "dataset": args.dataset,
        "tokenizer": args.tokenizer,
        "stopwords": args.stopwords,
        "stemmer": args.stemmer,
        "k": args.k,
        "bm25": {"k1": 1.5, "b": 0.75, "method": "lucene"},
        "n_documents": len(doc_ids),
        "n_queries": len(query_ids),
        "n_queries_scored": len(qrels),
        "vocab_size": len(vocab),
        "mean_corpus_tokens": round(sum(len(t) for t in corpus_tokens) / len(corpus_tokens), 2),
        "mean_query_tokens": round(sum(len(t) for t in query_tokens) / len(query_tokens), 2),
        "empty_token_queries": sum(1 for t in query_tokens if not t),
        "metrics": {k: round(v, 5) for k, v in means.items()},
        "ndcg_at_10_ci95": [round(lo, 5), round(hi, 5)],
        "seconds": {"load": round(t_load, 2), "tokenize": round(t_tok, 2),
                    "search": round(t_search, 2)},
        "per_query_ndcg_at_10": {q: round(s["ndcg_at_10"], 5) for q, s in per_query.items()},
    }

    published = PUBLISHED_NDCG10.get(args.dataset)
    if published is not None:
        diff = means["ndcg_at_10"] - published
        record["gate"] = {
            "published_ndcg_at_10": published,
            "measured_ndcg_at_10": round(means["ndcg_at_10"], 5),
            "difference": round(diff, 5),
            "tolerance": GATE_TOLERANCE,
            "passed": abs(diff) <= GATE_TOLERANCE,
            "exact_zero": diff == 0.0,
        }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    g = record.get("gate")
    print(f"{args.dataset} | {args.tokenizer} | stopwords={args.stopwords} "
          f"stemmer={args.stemmer}", file=sys.stderr)
    print(f"  docs={len(doc_ids):,} queries={len(query_ids):,} vocab={len(vocab):,} "
          f"mean_doc_tokens={record['mean_corpus_tokens']}", file=sys.stderr)
    print(f"  nDCG@10={means['ndcg_at_10']:.5f} [{lo:.5f}, {hi:.5f}]  "
          f"R@10={means['recall_at_10']:.5f}  R@100={means['recall_at_100']:.5f}",
          file=sys.stderr)
    if g:
        verdict = "PASS" if g["passed"] else "FAIL"
        print(f"  published={g['published_ndcg_at_10']:.5f}  diff={g['difference']:+.5f}  "
              f"-> {verdict}", file=sys.stderr)
        if g["exact_zero"]:
            print("  WARNING: difference is exactly zero — verify these are not "
                  "the same code path", file=sys.stderr)
    print(f"  wrote -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
