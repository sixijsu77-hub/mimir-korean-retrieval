#!/usr/bin/env python3
"""Reranking gate — reproduce MTEB's published BM25 baseline on MIRACLReranking ko.

PREREGISTRATION.md section 4d.2 requires this before any reranked number is reported.
The task supplies a candidate list per query; BM25 is indexed over the whole candidate
pool and then restricted to each query's list, as MTEB's BM25 model does.

Also records the tokenizer comparison on the same task, so the numbers quoted for it
elsewhere come from a raw record rather than an ad-hoc run.

    python -m harness.rerank_gate --out results/rerank_gate.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

from harness import metrics, retrieval, tokenizers

REPO = "mteb/MIRACLReranking"
REVISION = "d11a14c74e8bd448cedab0c1d9a720040535f228"
PUBLISHED = 0.3338
TOLERANCE = 0.02


def load(subset: str = "ko"):
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    def get(kind):
        return hf_hub_download(REPO, f"{subset}-{kind}/dev-00000-of-00001.parquet",
                               repo_type="dataset", revision=REVISION)

    corpus = pq.read_table(get("corpus")).to_pylist()
    queries = pq.read_table(get("queries")).to_pylist()
    qrels_rows = pq.read_table(get("qrels")).to_pylist()
    top_ranked = pq.read_table(get("top_ranked")).to_pylist()

    qrels: dict[str, dict[str, int]] = {}
    for r in qrels_rows:
        qrels.setdefault(r["query-id"], {})[r["corpus-id"]] = int(r["score"])
    candidates = {r["query-id"]: list(r["corpus-ids"]) for r in top_ranked}
    return corpus, queries, qrels, candidates


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", default="ko")
    ap.add_argument("--order-variants", type=int, default=10,
                    help="candidate orderings to try; measures tie-breaking sensitivity")
    ap.add_argument("--out", default="results/rerank_gate.jsonl")
    args = ap.parse_args()
    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    corpus, queries, qrels, candidates = load(args.subset)
    doc_ids = [c["_id"] for c in corpus]
    doc_texts = ["\n".join([c.get("title") or "", c["text"]]) for c in corpus]
    query_ids = [q["_id"] for q in queries]
    query_texts = [q["text"] for q in queries]
    index_of = {d: i for i, d in enumerate(doc_ids)}
    n_pos = sum(1 for q in qrels for v in qrels[q].values() if v > 0)
    p(f"  candidates {len(doc_ids):,} · queries {len(query_ids)} · positives {n_pos:,} "
      f"· {np.mean([len(v) for v in candidates.values()]):.1f} candidates per query")

    configs = [("word", {"stopwords": "en", "stemmer": "english"}),
               ("word", {"stopwords": None}),
               ("char_unigram", {}), ("char_bigram", {})]
    rows = []
    for tok, kw in configs:
        kwargs = dict(kw)
        if kwargs.pop("stemmer", None):
            import Stemmer
            kwargs["stemmer"] = Stemmer.Stemmer("english")
        scores = retrieval.bm25_score_matrix(
            tokenizers.tokenize(tok, doc_texts, **kwargs),
            tokenizers.tokenize(tok, query_texts, **kwargs))
        # Ties are broken by candidate order. Where many candidates score zero that
        # order decides the top 10, so the sensitivity is measured rather than assumed.
        order_scores = []
        for variant in range(args.order_variants):
            rng = np.random.default_rng(variant)
            run_v = {}
            for qi, q in enumerate(query_ids):
                cand = list(candidates[q])
                if variant > 0:
                    cand = [cand[j] for j in rng.permutation(len(cand))]
                s = scores[qi, [index_of[d] for d in cand]]
                run_v[q] = [cand[j] for j in np.argsort(-s)]
            m_v, pq_v = metrics.evaluate(run_v, qrels)
            order_scores.append(round(m_v["ndcg_at_10"], 5))
            if variant == 0:
                run, means, per_query = run_v, m_v, pq_v
        lo, hi = metrics.bootstrap_ci_values(
            [v["ndcg_at_10"] for v in per_query.values()], n_resamples=10000, seed=0)
        diff = means["ndcg_at_10"] - PUBLISHED
        rows.append({
            "tokenizer": tok, "stopwords": str(kw.get("stopwords")),
            "ndcg_at_10": round(means["ndcg_at_10"], 5),
            "ci95": [round(lo, 5), round(hi, 5)],
            "recall_at_10": round(means["recall_at_10"], 5),
            "published_ndcg_at_10": PUBLISHED,
            "difference": round(diff, 5),
            "gate_passed": bool(abs(diff) <= TOLERANCE),
            "candidate_order_variants": order_scores,
            "order_spread": round(max(order_scores) - min(order_scores), 5),
            "zero_score_fraction": round(float(np.mean([
                (scores[qi, [index_of[d] for d in candidates[q]]] == 0).mean()
                for qi, q in enumerate(query_ids)])), 5),
        })
        r = rows[-1]
        p(f"  {tok:13s} sw={str(kw.get('stopwords')):5s} nDCG@10={r['ndcg_at_10']:.5f} "
          f"diff={diff:+.5f} {'PASS' if r['gate_passed'] else 'FAIL'}  "
          f"zero-score {r['zero_score_fraction']*100:4.1f}%  "
          f"order spread {r['order_spread']:.5f} "
          f"({min(order_scores):.5f}-{max(order_scores):.5f})")

    record = {
        "task": "MIRACLReranking", "subset": args.subset, "split": "dev",
        "dataset_path": REPO, "dataset_revision": REVISION,
        "n_candidates": len(doc_ids), "n_queries": len(query_ids), "n_positives": n_pos,
        "published_ndcg_at_10": PUBLISHED, "tolerance": TOLERANCE,
        "configurations": rows,
        "gate_passed": any(r["gate_passed"] for r in rows),
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
