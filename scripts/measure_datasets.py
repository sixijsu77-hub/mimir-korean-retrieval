#!/usr/bin/env python3
"""Measure corpus size, document length, and qrel counts for the Korean
retrieval datasets. Produces results/dataset_inventory.jsonl.

Usage: python scripts/measure_datasets.py --out results/dataset_inventory.jsonl

Rationale and the comparison against MTEB's published statistics: docs/datasets.md
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import statistics as st
import sys
import time
from collections import Counter

from huggingface_hub import hf_hub_download

# Dataset revisions pinned to the ones MTEB evaluates.
AUTORAG = ("yjoonjang/markers_bm", "fd7df84ac089bbec763b1c6bb1b56e985df5cc5c")
KOSTRATEGY = ("taeminlee/Ko-StrategyQA", "d243889a3eb6654029dbd7e7f9319ae31d58f97c")
# MTEB serves MIRACL from its own mirror; these are the upstream sources.
MIRACL_CORPUS = "miracl/miracl-corpus"
MIRACL_TOPICS = "miracl/miracl"


def length_stats(values: list[int]) -> dict:
    """Summary statistics for a length distribution."""
    if not values:
        return {}
    values = sorted(values)
    return {
        "n": len(values),
        "mean": round(st.mean(values), 4),
        "median": st.median(values),
        "p90": values[int(len(values) * 0.9)],
        "max": values[-1],
        "min": values[0],
    }


def fetch(repo: str, filename: str, revision: str | None = None) -> str:
    return hf_hub_download(repo, filename, repo_type="dataset", revision=revision)


def read_jsonl(path: str, gz: bool = False):
    opener = gzip.open if gz else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def doc_lengths(docs) -> tuple[list[int], list[int], list[int], int]:
    """Return (text-only, indexer-join, stats-join) char lengths and unique text count.

    MTEB uses two different title/text joins: the BM25 model indexes
    "\\n".join([title, text]); descriptive_stats use (title + " " + text).strip().
    """
    text_lens, index_lens, stats_lens = [], [], []
    seen = set()
    for d in docs:
        title = d.get("title") or ""
        text = d.get("text") or ""
        text_lens.append(len(text))
        index_lens.append(len("\n".join([title, text])))
        stats_lens.append(len((title + " " + text).strip()))
        seen.add(text)
    return text_lens, index_lens, stats_lens, len(seen)


def measure_autorag() -> dict:
    repo, rev = AUTORAG
    paths = {
        "corpus": fetch(repo, "corpus/corpus-00000-of-00001.parquet", rev),
        "queries": fetch(repo, "queries/queries-00000-of-00001.parquet", rev),
        "qrels": fetch(repo, "data/test-00000-of-00001.parquet", rev),
    }
    import pyarrow.parquet as pq

    corpus = pq.read_table(paths["corpus"]).to_pylist()
    queries = pq.read_table(paths["queries"]).to_pylist()
    qrels = pq.read_table(paths["qrels"]).to_pylist()

    text_lens, index_lens, stats_lens, uniq = doc_lengths(corpus)
    positives = [r for r in qrels if float(r["score"]) > 0]
    per_query = Counter(r["query-id"] for r in positives)

    return {
        "dataset": "AutoRAGRetrieval",
        "hf_path": repo,
        "hf_revision": rev,
        "eval_split": "test",
        "n_documents": len(corpus),
        "n_unique_texts": uniq,
        "doc_chars_text_only": length_stats(text_lens),
        "doc_chars_indexer_join": length_stats(index_lens),
        "doc_chars_mteb_stats_join": length_stats(stats_lens),
        "n_queries": len(queries),
        "query_chars": length_stats([len(q["text"]) for q in queries]),
        "n_qrel_rows": len(qrels),
        "n_positives": len(positives),
        "positives_per_query": length_stats(list(per_query.values())),
        "relevance_values": dict(Counter(str(r["score"]) for r in qrels)),
        "disk_bytes_download": sum(os.path.getsize(p) for p in paths.values()),
    }


def measure_ko_strategyqa() -> dict:
    repo, rev = KOSTRATEGY
    paths = {
        "corpus": fetch(repo, "corpus.jsonl", rev),
        "queries": fetch(repo, "queries.jsonl", rev),
        "qrels_dev": fetch(repo, "qrels/dev.jsonl", rev),
    }
    corpus = list(read_jsonl(paths["corpus"]))
    queries = {q["_id"]: q for q in read_jsonl(paths["queries"])}
    qrels = list(read_jsonl(paths["qrels_dev"]))

    text_lens, index_lens, stats_lens, uniq = doc_lengths(corpus)
    positives = [r for r in qrels if float(r["score"]) > 0]
    per_query = Counter(r["query-id"] for r in positives)
    # queries.jsonl holds train+dev (2,833); the dev split has 592.
    dev_ids = set(per_query)
    dev_query_chars = [len(queries[q]["text"]) for q in dev_ids if q in queries]

    return {
        "dataset": "Ko-StrategyQA",
        "hf_path": repo,
        "hf_revision": rev,
        "eval_split": "dev",
        "n_documents": len(corpus),
        "n_unique_texts": uniq,
        "doc_chars_text_only": length_stats(text_lens),
        "doc_chars_indexer_join": length_stats(index_lens),
        "doc_chars_mteb_stats_join": length_stats(stats_lens),
        "n_queries_all_splits": len(queries),
        "n_queries": len(dev_ids),
        "query_chars": length_stats(dev_query_chars),
        "n_qrel_rows": len(qrels),
        "n_positives": len(positives),
        "positives_per_query": length_stats(list(per_query.values())),
        "relevance_values": dict(Counter(str(r["score"]) for r in qrels)),
        "disk_bytes_download": sum(os.path.getsize(p) for p in paths.values()),
    }


def measure_miracl_ko() -> dict:
    shards = [
        fetch(MIRACL_CORPUS, f"miracl-corpus-v1.0-ko/docs-{i}.jsonl.gz") for i in range(3)
    ]
    text_lens, index_lens, stats_lens = [], [], []
    seen = set()
    uncompressed = 0
    for shard in shards:
        with gzip.open(shard, "rt", encoding="utf-8") as f:
            for line in f:
                uncompressed += len(line.encode("utf-8"))
                d = json.loads(line)
                title, text = d.get("title") or "", d.get("text") or ""
                text_lens.append(len(text))
                index_lens.append(len("\n".join([title, text])))
                stats_lens.append(len((title + " " + text).strip()))
                seen.add(text)

    topics = fetch(MIRACL_TOPICS, "miracl-v1.0-ko/topics/topics.miracl-v1.0-ko-dev.tsv")
    qrels_path = fetch(MIRACL_TOPICS, "miracl-v1.0-ko/qrels/qrels.miracl-v1.0-ko-dev.tsv")
    topic_rows = list(csv.reader(open(topics, encoding="utf-8"), delimiter="\t"))
    qrel_rows = list(csv.reader(open(qrels_path, encoding="utf-8"), delimiter="\t"))

    # MIRACL qrels list every judged document; only relevance 1 is a positive.
    positives = [r for r in qrel_rows if r[3] == "1"]
    per_query = Counter(r[0] for r in positives)
    judged_per_query = Counter(r[0] for r in qrel_rows)

    disk = sum(os.path.getsize(p) for p in shards) + os.path.getsize(topics) + os.path.getsize(qrels_path)
    return {
        "dataset": "MIRACLRetrieval-ko",
        "hf_path": f"{MIRACL_CORPUS} + {MIRACL_TOPICS}",
        "hf_revision": "not pinned (MTEB serves this via its mteb/MIRACLRetrieval mirror)",
        "eval_split": "dev",
        "n_documents": len(text_lens),
        "n_unique_texts": len(seen),
        "doc_chars_text_only": length_stats(text_lens),
        "doc_chars_indexer_join": length_stats(index_lens),
        "doc_chars_mteb_stats_join": length_stats(stats_lens),
        "n_queries": len(topic_rows),
        "query_chars": length_stats([len(r[1]) for r in topic_rows if len(r) > 1]),
        "n_qrel_rows": len(qrel_rows),
        "n_positives": len(positives),
        "positives_per_query": length_stats(list(per_query.values())),
        "judged_per_query": length_stats(list(judged_per_query.values())),
        "relevance_values": dict(Counter(r[3] for r in qrel_rows if len(r) > 3)),
        "disk_bytes_download": disk,
        "disk_bytes_uncompressed_corpus": uncompressed,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/dataset_inventory.jsonl")
    ap.add_argument("--skip-miracl", action="store_true",
                    help="skip MIRACL-ko (downloads ~226 MB and parses 1.5M documents)")
    args = ap.parse_args()

    jobs = [("AutoRAGRetrieval", measure_autorag), ("Ko-StrategyQA", measure_ko_strategyqa)]
    if not args.skip_miracl:
        jobs.append(("MIRACLRetrieval-ko", measure_miracl_ko))

    records = []
    for name, fn in jobs:
        t0 = time.time()
        print(f"measuring {name} ...", file=sys.stderr, flush=True)
        rec = fn()
        rec["measured_in_seconds"] = round(time.time() - t0, 2)
        records.append(rec)
        print(
            f"  {name}: {rec['n_documents']:,} docs, {rec['n_queries']:,} queries, "
            f"{rec['n_positives']:,} positives, "
            f"{rec['disk_bytes_download']/1e6:.2f} MB  ({rec['measured_in_seconds']}s)",
            file=sys.stderr, flush=True,
        )

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} records -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
