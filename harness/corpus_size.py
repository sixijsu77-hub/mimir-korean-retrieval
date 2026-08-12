#!/usr/bin/env python3
"""Does corpus size decide whether sparse or dense retrieval wins? (H12, section 4g)

Queries and their relevant documents are held fixed; only the number of distractor
documents changes. Two directions:

  * thin   — sample distractors out of the dataset's own corpus
  * pad    — add distractors drawn from another dataset's corpus (--pad-from)

The corpus is tokenized and embedded once, then every size and seed selects rows from
that, so tokenization differences cannot leak into the comparison.

    python -m harness.corpus_size --dataset MIRACLRetrieval-ko \\
        --sizes 720,7200,72000,720000 --seeds 5 --out results/corpus_size.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from harness import data, dense, metrics, retrieval, tokenizers

MODEL = "intfloat/multilingual-e5-large"
EMB_DIR = "embeddings"


def emb_path(dataset: str, model: str, kind: str) -> str:
    return os.path.join(EMB_DIR, f"{dataset}_{model.replace('/', '__')}_{kind}.npy")


def positives(qrels: dict[str, dict[str, int]], corpus: dict) -> set[str]:
    """Documents judged relevant. Unjudged and judged-non-relevant both score 0 in
    nDCG, so only these have to survive subsampling."""
    return {d for q in qrels for d, g in qrels[q].items() if g > 0 and d in corpus}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=data.DATASETS)
    ap.add_argument("--pad-from", choices=data.DATASETS,
                    help="draw distractors from this dataset instead of thinning")
    ap.add_argument("--pad-pool", type=int, default=0,
                    help="cap the padding pool at this many documents (0 = all). "
                         "Recorded in the output; seeds draw from the capped pool.")
    ap.add_argument("--sizes", required=True, help="comma-separated corpus sizes")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--tokenizer", default="char_bigram", choices=tokenizers.TOKENIZERS)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--out", default="results/corpus_size.jsonl")
    args = ap.parse_args()
    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    corpus, queries, qrels = data.load(args.dataset)
    doc_ids, doc_texts = data.corpus_texts(corpus)
    keep = positives(qrels, corpus)
    qids = [q for q in queries if any(g > 0 for g in qrels.get(q, {}).values())]
    p(f"  {args.dataset}: {len(doc_ids):,} docs, {len(qids)} scored queries, "
      f"{len(keep):,} relevant documents held fixed")

    q_emb = np.load(emb_path(args.dataset, args.model, "queries"))
    d_emb = np.load(emb_path(args.dataset, args.model, "docs"))
    q_row = {q: i for i, q in enumerate(queries)}
    q_emb = q_emb[[q_row[q] for q in qids]]

    if args.pad_from:
        pad_corpus, _, _ = data.load(args.pad_from)
        pad_ids, pad_texts = data.corpus_texts(pad_corpus)
        pad_emb = np.load(emb_path(args.pad_from, args.model, "docs"))
        if args.pad_pool and args.pad_pool < len(pad_ids):
            pick = np.sort(np.random.default_rng(0).choice(
                len(pad_ids), size=args.pad_pool, replace=False))
            pad_ids = [pad_ids[i] for i in pick]
            pad_texts = [pad_texts[i] for i in pick]
            pad_emb = pad_emb[pick]
        doc_ids = doc_ids + [f"PAD::{i}" for i in pad_ids]
        doc_texts = doc_texts + pad_texts
        d_emb = np.vstack([d_emb, pad_emb])
        p(f"  padding pool: {len(pad_ids):,} documents from {args.pad_from}")

    t0 = time.time()
    all_tokens = tokenizers.tokenize(args.tokenizer, doc_texts)
    p(f"  tokenized {len(all_tokens):,} documents in {time.time()-t0:.1f}s")
    q_tokens = tokenizers.tokenize(args.tokenizer, [queries[q] for q in qids])

    # Thinning holds the relevant documents and samples distractors out of the rest.
    # Padding holds the whole original corpus and draws distractors only from the pad
    # pool, so the original task is intact and additions are the only change.
    if args.pad_from:
        pos_at = [i for i, d in enumerate(doc_ids) if not d.startswith("PAD::")]
        other = np.array([i for i, d in enumerate(doc_ids) if d.startswith("PAD::")])
    else:
        pos_at = [i for i, d in enumerate(doc_ids) if d in keep]
        other = np.array([i for i, d in enumerate(doc_ids) if d not in keep])
    sizes = [int(s) for s in args.sizes.split(",")]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    for size in sizes:
        if size < len(pos_at):
            p(f"  size {size:,} < {len(pos_at):,} relevant documents — NOT RUN")
            continue
        full = size >= len(doc_ids)
        n_seeds = 1 if full else args.seeds
        for seed in range(n_seeds):
            rng = np.random.default_rng(seed)
            if full:
                sel = np.arange(len(doc_ids))
            else:
                extra = rng.choice(other, size=size - len(pos_at), replace=False)
                sel = np.sort(np.concatenate([np.array(pos_at), extra]))
            sub_ids = [doc_ids[i] for i in sel]

            t1 = time.time()
            s_sparse = retrieval.bm25_score_matrix([all_tokens[i] for i in sel], q_tokens)
            s_dense = dense.cosine_score_matrix(q_emb, d_emb[sel])
            is_pad = np.array([d.startswith("PAD::") for d in sub_ids])
            scores, reach = {}, {}
            for label, S in (("bm25", s_sparse), ("dense", s_dense)):
                order = np.argsort(-S, axis=1)
                run = {q: [sub_ids[j] for j in order[i][:100]]
                       for i, q in enumerate(qids)}
                m, pq = metrics.evaluate(run, qrels)
                scores[label] = (m["ndcg_at_10"], {q: v["ndcg_at_10"] for q, v in pq.items()})
                # An unchanged nDCG@10 does not mean an unchanged ranking: with one
                # relevant document per query the metric only tracks that document's
                # rank. Count how far the added documents actually reach.
                if is_pad.any():
                    t10, t100 = is_pad[order[:, :10]], is_pad[order[:, :100]]
                    first = [np.where(is_pad[o])[0] for o in order]
                    best = [int(w[0]) + 1 for w in first if len(w)]
                    reach[label] = {
                        "pad_in_top10_mean": round(float(t10.sum(1).mean()), 3),
                        "pad_in_top100_mean": round(float(t100.sum(1).mean()), 3),
                        "queries_with_pad_in_top10": int((t10.sum(1) > 0).sum()),
                        "pad_best_rank_min": min(best) if best else None,
                        "pad_best_rank_median": int(np.median(best)) if best else None,
                    }

            a = [scores["bm25"][1][q] for q in qids]
            b = [scores["dense"][1][q] for q in qids]
            diff, lo, hi = metrics.paired_bootstrap_diff(a, b, args.bootstrap, seed=0)
            record = {
                "dataset": args.dataset,
                "direction": "pad" if args.pad_from else "thin",
                "pad_from": args.pad_from,
                "pad_pool": args.pad_pool or None,
                "tokenizer": args.tokenizer,
                "model": args.model,
                "corpus_size": int(len(sel)),
                "full_corpus": bool(full),
                "seed": None if full else seed,
                "n_queries": len(qids),
                "n_documents_held_fixed": len(pos_at),
                "ndcg_at_10": {"bm25": round(scores["bm25"][0], 5),
                               "dense": round(scores["dense"][0], 5)},
                "paired_bm25_minus_dense": round(diff, 5),
                "ci95": [round(lo, 5), round(hi, 5)],
                "distinguishable": bool(lo > 0 or hi < 0),
                "distractor_reach": reach or None,
                "seconds": round(time.time() - t1, 1),
                "per_query_ndcg_at_10": {
                    "bm25": {q: round(v, 5) for q, v in scores["bm25"][1].items()},
                    "dense": {q: round(v, 5) for q, v in scores["dense"][1].items()},
                },
            }
            with open(args.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            p(f"  {len(sel):>9,} docs seed={record['seed']}  "
              f"bm25={record['ndcg_at_10']['bm25']:.5f}  "
              f"dense={record['ndcg_at_10']['dense']:.5f}  "
              f"diff={diff:+.5f} [{lo:+.5f},{hi:+.5f}] "
              f"{'distinguishable' if record['distinguishable'] else 'not distinguishable'}  "
              f"{record['seconds']}s")
            for label, r in (reach or {}).items():
                p(f"      {label:5s} added docs in top-10: {r['pad_in_top10_mean']:.2f}/query, "
                  f"{r['queries_with_pad_in_top10']}/{len(qids)} queries, best rank "
                  f"{r['pad_best_rank_min']}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
