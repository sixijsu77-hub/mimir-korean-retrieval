"""Dataset loading, pinned to the revisions MTEB evaluates.

Returns BEIR-style structures:
    corpus  {doc_id: {"title": str, "text": str}}
    queries {query_id: str}
    qrels   {query_id: {doc_id: int}}
"""

from __future__ import annotations

import json

from huggingface_hub import hf_hub_download

AUTORAG = ("yjoonjang/markers_bm", "fd7df84ac089bbec763b1c6bb1b56e985df5cc5c")
KOSTRATEGY = ("taeminlee/Ko-StrategyQA", "d243889a3eb6654029dbd7e7f9319ae31d58f97c")
MIRACL_CORPUS = ("miracl/miracl-corpus", "d921ec7e349ce0d28daf30b2da9da5ee698bef0d")
MIRACL_TOPICS = ("miracl/miracl", "5be20db9509754dadad47689368639fcec739c00")

DATASETS = ("AutoRAGRetrieval", "Ko-StrategyQA", "MIRACLRetrieval-ko")


def _read_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _load_autorag():
    import pyarrow.parquet as pq

    repo, rev = AUTORAG
    get = lambda fn: hf_hub_download(repo, fn, repo_type="dataset", revision=rev)

    corpus = {
        r["_id"]: {"title": r.get("title") or "", "text": r["text"]}
        for r in pq.read_table(get("corpus/corpus-00000-of-00001.parquet")).to_pylist()
    }
    queries = {
        r["_id"]: r["text"]
        for r in pq.read_table(get("queries/queries-00000-of-00001.parquet")).to_pylist()
    }
    qrels: dict[str, dict[str, int]] = {}
    for r in pq.read_table(get("data/test-00000-of-00001.parquet")).to_pylist():
        qrels.setdefault(r["query-id"], {})[r["corpus-id"]] = int(r["score"])
    return corpus, queries, qrels


def _load_ko_strategyqa():
    repo, rev = KOSTRATEGY
    get = lambda fn: hf_hub_download(repo, fn, repo_type="dataset", revision=rev)

    corpus = {
        r["_id"]: {"title": r.get("title") or "", "text": r["text"]}
        for r in _read_jsonl(get("corpus.jsonl"))
    }
    all_queries = {r["_id"]: r["text"] for r in _read_jsonl(get("queries.jsonl"))}
    qrels: dict[str, dict[str, int]] = {}
    for r in _read_jsonl(get("qrels/dev.jsonl")):
        qrels.setdefault(r["query-id"], {})[r["corpus-id"]] = int(r["score"])
    # queries.jsonl holds train+dev (2,833); the dev split has 592.
    queries = {qid: all_queries[qid] for qid in qrels if qid in all_queries}
    return corpus, queries, qrels


def _load_miracl_ko():
    import csv
    import gzip

    corpus = {}
    for i in range(3):
        path = hf_hub_download(MIRACL_CORPUS[0], f"miracl-corpus-v1.0-ko/docs-{i}.jsonl.gz",
                               repo_type="dataset", revision=MIRACL_CORPUS[1])
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                corpus[d["docid"]] = {"title": d.get("title") or "", "text": d.get("text") or ""}

    topics = hf_hub_download(MIRACL_TOPICS[0],
                             "miracl-v1.0-ko/topics/topics.miracl-v1.0-ko-dev.tsv",
                             repo_type="dataset", revision=MIRACL_TOPICS[1])
    with open(topics, encoding="utf-8") as f:
        queries = {r[0]: r[1] for r in csv.reader(f, delimiter="\t") if len(r) > 1}

    qrels_path = hf_hub_download(MIRACL_TOPICS[0],
                                 "miracl-v1.0-ko/qrels/qrels.miracl-v1.0-ko-dev.tsv",
                                 repo_type="dataset", revision=MIRACL_TOPICS[1])
    # Every judged document is listed, relevant or not; only relevance 1 is a positive.
    qrels: dict[str, dict[str, int]] = {}
    with open(qrels_path, encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t"):
            if len(r) > 3:
                qrels.setdefault(r[0], {})[r[2]] = int(r[3])
    return corpus, queries, qrels


def load(name: str):
    if name == "AutoRAGRetrieval":
        return _load_autorag()
    if name == "Ko-StrategyQA":
        return _load_ko_strategyqa()
    if name == "MIRACLRetrieval-ko":
        return _load_miracl_ko()
    raise ValueError(f"unknown dataset: {name!r}; expected one of {DATASETS}")


def corpus_texts(corpus: dict[str, dict], join: str = "\n") -> tuple[list[str], list[str]]:
    """Documents as MTEB's BM25 model indexes them: title + "\\n" + text.

    Returns (doc_ids, texts) in a fixed, matching order.
    """
    ids = list(corpus)
    texts = [join.join([corpus[i]["title"], corpus[i]["text"]]) for i in ids]
    return ids, texts
