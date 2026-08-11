# Dataset inventory — measured, not estimated

Every number on this page was produced by [`scripts/measure_datasets.py`](../scripts/measure_datasets.py)
and is committed in raw form at [`results/dataset_inventory.jsonl`](../results/dataset_inventory.jsonl).

Measured 2026-08-12. Dataset revisions are pinned to the ones MTEB evaluates,
so these counts describe exactly the data a reproduction attempt would see.

This page exists because corpus size decides what is affordable to run. It was
written before any retrieval code, on purpose.

## The three datasets

| | AutoRAGRetrieval | Ko-StrategyQA | MIRACLRetrieval (ko) |
|---|---|---|---|
| HF path | `yjoonjang/markers_bm` | `taeminlee/Ko-StrategyQA` | `miracl/miracl-corpus` + `miracl/miracl` |
| Pinned revision | `fd7df84a…` | `d243889a…` | not pinned (see note) |
| Evaluation split | `test` | `dev` | `dev` |
| **Documents** | **720** | **9,251** | **1,486,752** |
| **Queries** | **114** | **592** | **213** |
| Qrel rows | 114 | 1,145 | 3,057 |
| **Positives** | **114** | **1,145** | **547** |
| Positives per query (mean / median / max) | 1.00 / 1 / 1 | 1.93 / 2 / 7 | 2.57 / 2 / 12 |
| Relevance grades present | `1.0` ×114 | `1` ×1145 | `0` ×2510, `1` ×547 |
| Download size | 0.72 MB | 7.65 MB | 226.04 MB |
| Corpus uncompressed | — | — | 673.95 MB |
| Wall clock to measure | 0.2 s | 0.8 s | 10.5 s |

## Document and query lengths (characters)

Lengths are in Unicode characters, not tokens. For Korean the two differ a lot,
and character counts are what a character n-gram tokenizer actually consumes.

| Dataset | Field | mean | median | p90 | max | min |
|---|---|---|---|---|---|---|
| AutoRAGRetrieval | document (text) | 823.60 | 870 | 1,255 | 2,484 | 7 |
| AutoRAGRetrieval | query | 69.61 | 69 | 96 | 157 | 34 |
| Ko-StrategyQA | document (title + text) | 320.26 | 275 | 526 | 5,016 | 29 |
| Ko-StrategyQA | query | 22.75 | 22 | 32 | 60 | 10 |
| MIRACL (ko) | document (title + text) | 174.98 | 134 | 351 | 25,247 | 4 |
| MIRACL (ko) | query | 21.62 | 19 | 29 | 92 | 5 |

Corpus length varies by a factor of ~4.7 across the three sets (175 → 824 mean
characters). Any claim that one retrieval method "wins on Korean" has to survive
that spread, which is part of why all three are in scope.

## Cross-check against MTEB's own published statistics

MTEB publishes descriptive statistics for its tasks. Ours were computed
independently from the source files and then compared:

| Quantity | MTEB published | Measured here | |
|---|---|---|---|
| AutoRAGRetrieval documents | 720 | 720 | match |
| AutoRAGRetrieval doc chars, mean | 823.6027777777778 | 823.6028 | match |
| AutoRAGRetrieval queries / query chars | 114 / 69.6140350877193 | 114 / 69.6140 | match |
| AutoRAGRetrieval positives per query | 1.0 (max 1) | 1.0 (max 1) | match |
| Ko-StrategyQA documents | 9,251 | 9,251 | match |
| Ko-StrategyQA doc chars, mean | 320.25953950924225 | 320.2595 | match |
| Ko-StrategyQA queries (dev) | 592 | 592 | match |
| Ko-StrategyQA positives / per query | 1,145 / 1.9341216216216217 | 1,145 / 1.9341 | match |
| MIRACL (ko) documents | 1,486,752 | 1,486,752 | match |
| MIRACL (ko) doc chars, mean | 174.97649170809927 | 174.9765 | match |
| MIRACL (ko) positives / per query | 547 / 2.568075117370892 | 547 / 2.5681 | match |

Source: `mteb/descriptive_stats/Retrieval/{AutoRAGRetrieval,Ko-StrategyQA,MIRACLRetrieval}.json`
in [embeddings-benchmark/mteb](https://github.com/embeddings-benchmark/mteb).

This is not yet evidence that the retrieval harness is correct — no retrieval has
run. It is evidence that the data is being **read** the same way MTEB reads it,
which is the prerequisite for the harness gate in
[`PREREGISTRATION.md`](../PREREGISTRATION.md) to mean anything.

Two definitional details fell out of that comparison, both of which matter later:

- **Documents are indexed as title + separator + text, not text alone.** The
  agreement above only holds under that join. Indexing `text` alone would change
  Ko-StrategyQA's mean document length by 15 characters and MIRACL's by 8.
  MTEB's BM25 model joins with `"\n"`; its descriptive statistics use
  `(title + " " + text).strip()`. The two differ by one character whenever the
  title is non-empty, which is why both are recorded in the raw JSONL.
- **AutoRAGRetrieval has no titles.** All 720 title fields are empty strings, so
  for that set the join is a no-op — except that MTEB's BM25 path prepends a bare
  newline, giving a mean of 824.60 rather than 823.60.

Unique-text counts are *not* listed as a cross-check above because the two sides
count different things: MTEB counts unique joined documents (9,251 and 1,481,128),
this repository counts unique `text` fields (9,246 and 1,460,133). Titles
disambiguate documents whose body text is identical. Neither number is wrong;
they answer different questions.

## Notes on each set

**AutoRAGRetrieval** — 720 documents, 114 queries, and **exactly one positive per
query**. Parsed from PDFs across finance, government, healthcare, legal and
commerce; the document IDs carry the source filename and chunk index. With a
single positive per query, nDCG@10 here is a function of the rank of one document,
so it moves in large discrete steps and its confidence interval will be wide.
That is a property of the dataset, not of the method being measured, and it is
the main reason bootstrap intervals are pre-registered rather than optional.

**Ko-StrategyQA** — 9,251 documents, 592 dev queries, 1.93 positives per query.
Note that `queries.jsonl` contains 2,833 queries spanning train and dev; the
evaluation split is dev, so query counts here are scoped to the queries appearing
in `qrels/dev.jsonl`. Counting all 2,833 would overstate the evaluation set by
4.8×.

**MIRACLRetrieval (ko)** — 1,486,752 documents, 213 dev queries. Its qrels file
lists every **judged** document, relevant or not: 3,057 rows, of which only 547
are relevance 1 and 2,510 are judged negatives. Counting rows instead of positives
gives 14.35 "positives" per query instead of the true 2.57 — a 5.6× error. Judged
negatives contribute zero gain to nDCG, so their presence does not change the
metric, but it does change any statistic computed off the qrels file directly.

The MIRACL revision is not pinned because MTEB serves this task from its own
mirror (`mteb/MIRACLRetrieval`, revision `9c09abc1…`) rather than from the
upstream `miracl/*` repositories measured here. The document count, query count,
positive count and mean document length all agree exactly with MTEB's published
statistics for the ko subset, so the two are the same data for our purposes.
This should be re-verified when the harness actually loads the mirror.

## Is MIRACL-ko affordable?

The plan flagged MIRACL as the set that might be too large to index. Measured, it
is not. The arithmetic below follows from the measured 1,486,752 documents and
260.1 M total characters:

| | Result |
|---|---|
| Dense index, 1024-dim fp32 | 6.09 GB |
| Dense index, 1024-dim fp16 | 3.04 GB |
| Dense index, 768-dim fp32 | 4.57 GB |
| Character-bigram postings, upper bound | 258.7 M tokens → ~2.07 GB sparse |
| Disk free at time of writing | 1.2 TB |

Encoding time is **not** yet measured — throughput on this hardware has not been
run. Conditional on throughput, the corpus takes:

| Throughput | Wall clock |
|---|---|
| 200 docs/s | 124 min |
| 500 docs/s | 50 min |
| 1,000 docs/s | 25 min |
| 2,000 docs/s | 12 min |

The bigram figure is an upper bound: it counts every adjacent character pair
including repeats, before per-document deduplication merges them.

**Conclusion: all three datasets stay in scope.** MIRACL-ko needs one 226 MB
download and a few GB of index, both of which fit comfortably. If encoding
throughput turns out to be far below 200 docs/s, that will be reported as a
measured number and the stopping rule in `PREREGISTRATION.md` applies — the set is
reported as not run, with its size, rather than quietly dropped.

## Reproducing this page

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/measure_datasets.py --out results/dataset_inventory.jsonl
```

Add `--skip-miracl` to avoid the 226 MB download. Total runtime is about
12 seconds once the files are cached.
