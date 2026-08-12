# MIMIR — Korean retrieval, measured

Reproducible measurements of BM25, dense embeddings, and hybrid retrieval on
**public Korean benchmarks**, with confidence intervals and a pre-registered
hypothesis set.

> Status: **exp01–exp05 complete (2026-08-12).** BM25, dense and hybrid measured on three
> Korean datasets, 720 to 1,486,752 documents. H1–H12 decided across retrieval, chunking,
> reranking, morphological analysis and corpus size — three of them recorded as
> undecidable because of how they were written, not repaired afterwards.

## The pre-registered prediction failed

The hybrid weight was predicted, before running anything, to peak at a dense weight
of **0.2–0.4** (shaded below) and to decline above it. It peaks at **0.90, 0.90 and
0.80** instead, climbing nearly to pure dense retrieval:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/weight-curves-dark.png">
  <img src="docs/img/weight-curves-light.png"
       alt="nDCG@10 against dense weight for three datasets. The pre-registered 0.2-0.4 band is shaded. AutoRAGRetrieval is flat across the whole sweep, peaking at 0.25 and 0.60; Ko-StrategyQA rises steadily to a peak at 0.90; MIRACL-ko rises to a peak at 0.80.">
</picture>

| Dense weight | 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|
| Ko-StrategyQA / e5-large | 0.5611 | 0.6166 | 0.6796 | 0.7461 | 0.7914 | **0.8056** | 0.8035 |
| MIRACL-ko / e5-large | 0.3507 | 0.4129 | 0.5289 | 0.6572 | **0.7083** | 0.6942 | 0.6649 |

On AutoRAGRetrieval no weight is distinguishable from any other — including w = 0,
pure BM25 — so the optimum **cannot be located** and is reported as such rather than
read off a point estimate.

**That task ranks retrievers in the opposite direction from the other two.** Character-
bigram BM25, with nothing tuned, outscores **all 18** dense models KURE publishes on
AutoRAGRetrieval — and **none** of them on Ko-StrategyQA or MIRACL-ko:

| Task | BM25 bigram | best of 18 | median of 18 | models BM25 beats |
|---|---|---|---|---|
| AutoRAGRetrieval | **0.92345** | 0.87379 | 0.77996 | **18 of 18** |
| Ko-StrategyQA | 0.56108 | 0.81080 | 0.79405 | 0 of 18 |
| MIRACL-ko | 0.35067 | 0.70315 | 0.62697 | 0 of 18 |

Four explanations were tested and none accounts for it: query provenance, corpus size,
truncation, and a weakness in one model. **Cause not established** —
[`docs/results-exp05-corpus-size.md`](docs/results-exp05-corpus-size.md) records what was
ruled out and how.

The prediction came from a private measurement on Korean business documents. It does
not generalize. That result is the point of the repository, not an embarrassment to
it — see [`PREREGISTRATION.md`](PREREGISTRATION.md), whose commits predate every
number here, and [`docs/results-week3.md`](docs/results-week3.md).

## Seven published numbers reproduced, five of them exactly

The harness was validated against other people's results before it reported any of
its own — a gate fixed in advance at ±0.02 nDCG@10.

| Source | Model | Dataset | Published | Measured |
|---|---|---|---|---|
| MTEB | `baseline-bm25s` | AutoRAGRetrieval | 0.65022 | **0.65022** |
| MTEB | `baseline-bm25s` | MIRACLRetrieval ko | 0.24521 | **0.24521** |
| MTEB | `baseline-bm25s` | Ko-StrategyQA | 0.37808 | 0.37807 |
| MTEB | `baseline-bm25s` | MIRACLReranking ko | 0.3338 | 0.33979 |
| KURE | `multilingual-e5-large` | AutoRAGRetrieval | 0.81337 | **0.81337** |
| KURE | `multilingual-e5-large` | Ko-StrategyQA | 0.80348 | **0.80348** |
| KURE | `multilingual-e5-large` | MIRACL-ko | 0.66486 | **0.66486** |

**MIRACLReranking is the one that does not land.** Its +0.00599 sits inside the ±0.02
gate but well outside the precision of the other six. Two causes were tested and neither
accounts for it — tie-breaking moves the score across a 0.00595 band that still never
reaches the published value, and indexing BM25 per query instead of over the whole
candidate pool overshoots to −0.00460. **Cause not established** — see
[`docs/results-exp03-reranking.md`](docs/results-exp03-reranking.md).

The five exact matches are addressed against the pre-registered "treat 0.000 as
suspicious" rule — the dense ones in [`docs/results-week2.md`](docs/results-week2.md),
the BM25 one in [`docs/results-week1.md`](docs/results-week1.md), where it holds only
after replicating a step MTEB applies and no published result file records: removing
tokens present in ≥ 90% of documents, which it does for every language with no named
stopword list. Without that step the same harness gives 0.64342.

## The Korean BM25 baseline is configured for English

The published Korean BM25 numbers come from three different configurations, and two of
them apply **English stopwords and an English Snowball stemmer to Korean**:

| Task | Published | Configuration that reproduces it | mteb version recorded |
|---|---|---|---|
| MIRACLRetrieval ko | 0.24521 | word split, English stopwords, English stemmer | 2.12.7 |
| Ko-StrategyQA | 0.37808 | word split, English stopwords, English stemmer | 2.10.8 |
| AutoRAGRetrieval | 0.65022 | character unigram + frequency stopwords | 2.12.30 |

At 2.12.30 the codebase has no language table, no character tokenizer and no
frequency-stopword step; all three arrive at 2.14.9, and Korean is not routed to
characters until 2.18.12. So the third row's recorded version cannot have produced its own
score. That is the substance of the report filed upstream.

Against a tokenizer chosen for Korean rather than inherited from English, the same BM25 —
no parameter tuned — scores far higher:

| Dataset | Published baseline | Character bigram | Kiwi morphemes | Best gain |
|---|---|---|---|---|
| AutoRAGRetrieval | 0.65022 | **0.92345** | 0.89922 | +0.273 |
| Ko-StrategyQA | 0.37808 | **0.56108** | 0.57291 | +0.195 |
| MIRACL-ko | 0.24521 | 0.35067 | **0.40401** | +0.159 |

95% bootstrap intervals do not overlap on any dataset. **Which of the two better
tokenizers wins depends on the corpus** — see
[`docs/results-exp04-morphology.md`](docs/results-exp04-morphology.md); this repository
does not recommend one over the other.

So a Korean leaderboard reporting "BM25" as a baseline is reporting a configuration
artifact. Any margin a dense model claims over it should be read with that in mind.

Reported upstream: [embeddings-benchmark/mteb#5157](https://github.com/embeddings-benchmark/mteb/issues/5157).

Measurements, caveats and reproduction commands: [`docs/results-week1.md`](docs/results-week1.md).

## If you are here to tune your own system

[`docs/should-you-tune-the-weight.md`](docs/should-you-tune-the-weight.md) turns these
measurements into a procedure: sweep the whole weight range, compare the curve's
amplitude to your confidence interval, and decide whether there is anything to tune
before collecting more evaluation queries. On one of the three datasets here, no weight
is distinguishable from any other — the correct output is "it does not matter", not a
tuned value.

## What is measured here

| | |
|---|---|
| [`docs/datasets.md`](docs/datasets.md) | Corpus sizes, lengths and qrel counts, cross-checked against MTEB's own published statistics |
| [`docs/baselines.md`](docs/baselines.md) | The published numbers this harness is graded against, and the configuration that produced them |
| [`docs/results-week1.md`](docs/results-week1.md) | Harness gate — two published BM25 numbers reproduced; the tokenizer finding |
| [`docs/results-week2.md`](docs/results-week2.md) | Dense and the hybrid weight sweep; H1–H3 decided |
| [`docs/results-week3.md`](docs/results-week3.md) | Paired testing, hubness, MIRACL-ko; H4–H5 decided |
| [`docs/results-week4.md`](docs/results-week4.md) | How many queries a weight needs; H6 decided |
| [`docs/results-exp02-chunking.md`](docs/results-exp02-chunking.md) | Chunking as a manipulation of the truncation story; H7 decided |
| [`docs/results-exp03-reranking.md`](docs/results-exp03-reranking.md) | Reranking, and how a weak reranker destroys a good ranking; H8 decided |
| [`docs/results-exp04-morphology.md`](docs/results-exp04-morphology.md) | Character bigrams against Kiwi morphological analysis; H11 decided |
| [`docs/results-exp05-corpus-size.md`](docs/results-exp05-corpus-size.md) | Corpus size swept over four orders of magnitude, both directions; H12 decided; BM25 against all 18 published dense models |
| [`docs/should-you-tune-the-weight.md`](docs/should-you-tune-the-weight.md) | The practitioner procedure the above adds up to |
| [`docs/preregistration-checklist.md`](docs/preregistration-checklist.md) | The five checks that would have caught three undecidable hypotheses here |
| [`docs/errata.md`](docs/errata.md) | What was published wrong, for how long, and what changed |

Every hypothesis and its verdict is in [`PREREGISTRATION.md`](PREREGISTRATION.md);
every number is in `results/*.jsonl`.

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
  `results/*.jsonl`, and `scripts/check_reported_numbers.py` fails if any score
  quoted in the documentation appears in no raw record.
- **Mistakes are listed, not quietly fixed.** [`docs/errata.md`](docs/errata.md)
  records what was published wrong, for how long, and what changed as a result.

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
