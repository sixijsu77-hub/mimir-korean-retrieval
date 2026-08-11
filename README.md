# MIMIR — Korean retrieval, measured

Reproducible measurements of BM25, dense embeddings, and hybrid retrieval on
**public Korean benchmarks**, with confidence intervals and a pre-registered
hypothesis set.

> Status: **datasets measured, retrieval not yet run.**
> No retrieval score in this repository is a MIMIR result yet. The only numbers
> measured so far are dataset sizes; the only retrieval scores quoted are other
> people's published ones.

## Why this exists

Hybrid retrieval is widely recommended, but the *weight* is usually guessed.
A small private measurement on Korean business documents suggested that
character-bigram BM25 beat a small multilingual embedding model, and that the
hybrid optimum sat at a low dense weight — with accuracy **declining** as more
dense signal was mixed in.

This repository tests whether that holds on public data, against published
leaderboard numbers.

## How it is kept honest

- **Pre-registration.** [`PREREGISTRATION.md`](PREREGISTRATION.md) records the
  hypotheses and the pass/fail criteria, committed before any experiment runs.
  The git timestamp is the evidence.
- **Harness validation first.** No new number is reported until a *published*
  BM25 score is reproduced within 0.02 nDCG@10 on the same dataset.
- **Nothing is silently dropped.** Datasets that could not be indexed are listed
  with their measured size, not omitted.
- **Overlapping intervals are reported as overlapping.** Rankings are not claimed
  from point estimates.
- **Raw logs are committed.** Every table and figure can be regenerated from
  `results/*.jsonl`.

## Metrics

nDCG@10 (primary), Recall@10 / Recall@100, bootstrap CIs resampled at query level.

## Datasets

Public Korean retrieval sets from the MTEB-ko ecosystem, at the dataset
revisions MTEB evaluates:

| | Documents | Queries | Positives / query |
|---|---|---|---|
| AutoRAGRetrieval | 720 | 114 | 1.00 |
| Ko-StrategyQA | 9,251 | 592 | 1.93 |
| MIRACLRetrieval (ko) | 1,486,752 | 213 | 2.57 |

Measured, not estimated — see [`docs/datasets.md`](docs/datasets.md) for the full
inventory, the cross-check against MTEB's own published statistics, and the
indexing-cost arithmetic. Raw values: [`results/dataset_inventory.jsonl`](results/dataset_inventory.jsonl).

## Baselines to beat — or rather, to reproduce first

[`docs/baselines.md`](docs/baselines.md) records the published numbers this
harness is graded against, and the exact configuration that produced them. The
week-1 gate is MTEB's official BM25 baseline on AutoRAGRetrieval,
**nDCG@10 = 0.65022**.

That page also documents something not stated on any leaderboard: the published
Korean BM25 figures use a word-level tokenizer that discards every
single-syllable Korean token, and current MTEB versions would tokenize Korean
differently. Reproducing these numbers requires pinning the evaluation code
version, not only the dataset.

## Reproducing

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# Dataset inventory (~12 s cached; downloads 234 MB the first time)
python scripts/measure_datasets.py --out results/dataset_inventory.jsonl
# (retrieval commands added as the harness lands)
```

Hardware used: RTX 4090 (24 GB), i9-13900K, Python 3.10.
BM25 indexing runs on CPU; embedding runs on GPU. No paid API is used.

## Scope

This repository stops at the measurement report. Rerankers and embedding
fine-tuning are separate, later experiments.

## License

TBD
