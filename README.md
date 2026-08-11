# MIMIR — Korean retrieval, measured

Reproducible measurements of BM25, dense embeddings, and hybrid retrieval on
**public Korean benchmarks**, with confidence intervals and a pre-registered
hypothesis set.

> Status: **BM25, dense and hybrid measured on two datasets (2026-08-12).**
> H1–H3 decided. Hubness (H4) and MIRACL-ko not yet run.

## The pre-registered prediction failed

The hybrid weight was predicted, before running anything, to peak at a dense
weight of **0.2–0.4** and to decline above it. On the dataset where the question
can be answered, it peaks at **0.90** and climbs nearly to pure dense retrieval:

| Dense weight | 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|
| Ko-StrategyQA / e5-large | 0.5611 | 0.6166 | 0.6796 | 0.7461 | 0.7914 | **0.8056** | 0.8035 |

On AutoRAGRetrieval, 19 of 21 weights are statistically indistinguishable from the
best, so the optimum **cannot be located** and is reported as such rather than read
off a point estimate.

The prediction came from a private measurement on Korean business documents. It does
not generalize. That result is the point of the repository, not an embarrassment to
it — see [`PREREGISTRATION.md`](PREREGISTRATION.md), whose commit predates every
number here, and [`docs/results-week2.md`](docs/results-week2.md).

## The published Korean BM25 baselines understate BM25

MTEB's published BM25 baseline scores **0.65022** nDCG@10 on AutoRAGRetrieval and
**0.37808** on Ko-StrategyQA. Both are reproduced here within the pre-registered
0.02 tolerance — and both turn out to be limited by tokenization rather than by
BM25. Switching to character bigrams, with no parameter tuning:

| Dataset | Published baseline | Character bigram | Gain |
|---|---|---|---|
| AutoRAGRetrieval | 0.64342 *(reproduced; character unigram)* | **0.92345** | +0.280 |
| Ko-StrategyQA | 0.37807 *(reproduced; word-level)* | **0.56108** | +0.183 |

95% bootstrap intervals do not overlap on either dataset. A further finding fell
out of the gate: **the two published numbers were produced with different
tokenizers**, which is not stated on any leaderboard and which this repository's
own pre-measurement notes got wrong.

So a Korean leaderboard reporting "BM25" as a baseline may be reporting a
tokenization artifact. Any margin a dense model claims over it should be read
with that in mind.

Measurements, caveats and reproduction commands: [`docs/results-week1.md`](docs/results-week1.md).

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

## Baselines

[`docs/baselines.md`](docs/baselines.md) records the published numbers this
harness is graded against and the configuration that produced them, traced
through the MTEB source. It also records where that page's own pre-measurement
prediction turned out to be wrong, annotated rather than rewritten.

Reproducing these numbers requires pinning the evaluation code version, not only
the dataset: MTEB's Korean tokenization changed across versions, and the two
published numbers reproduced here come from different sides of that change.

## Reproducing

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# Dataset inventory (~12 s cached; downloads 234 MB the first time)
python scripts/measure_datasets.py --out results/dataset_inventory.jsonl

# Harness validation gate — reproduces the two published BM25 numbers
python -m harness.evaluate --dataset AutoRAGRetrieval --tokenizer char_unigram \
    --out results/gate_bm25.jsonl
python -m harness.evaluate --dataset Ko-StrategyQA --tokenizer word \
    --stopwords en --stemmer english --out results/gate_bm25.jsonl

# Any other row in docs/results-week1.md: swap --tokenizer for
# word | char_unigram | char_bigram

# Dense and the hybrid weight sweep (needs the torch line; uses the GPU)
python -m harness.sweep --dataset Ko-StrategyQA \
    --model intfloat/multilingual-e5-large --tokenizer char_bigram \
    --out results/hybrid.jsonl
```

Reproducing the BM25 results does not require a GPU, and does not require the
`torch` line in `requirements.txt`.

Hardware used: RTX 4090 (24 GB), i9-13900K, Python 3.10.
BM25 indexing runs on CPU; embedding runs on GPU. No paid API is used.

## Scope

This repository stops at the measurement report. Rerankers and embedding
fine-tuning are separate, later experiments.

## License

[MIT](LICENSE). The datasets are not covered by it and keep their own licenses.
