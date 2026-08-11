# MIMIR — Korean retrieval, measured

Reproducible measurements of BM25, dense embeddings, and hybrid retrieval on
**public Korean benchmarks**, with confidence intervals and a pre-registered
hypothesis set.

> Status: **planning complete, measurement not yet run.**
> Nothing in this README should be read as a result yet.

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

Public Korean retrieval sets from the MTEB-ko ecosystem — AutoRAGRetrieval,
Ko-StrategyQA, MIRACL-ko. See
[KURE](https://github.com/nlpai-lab/KURE) and
[Korean-MTEB-Retrieval-Evaluators](https://github.com/BM-K/Korean-MTEB-Retrieval-Evaluators).

## Reproducing

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
# (commands added as the harness lands)
```

Hardware used: RTX 4090 (24 GB), i9-13900K, Python 3.10.
BM25 indexing runs on CPU; embedding runs on GPU. No paid API is used.

## Scope

This repository stops at the measurement report. Rerankers and embedding
fine-tuning are separate, later experiments.

## License

TBD
