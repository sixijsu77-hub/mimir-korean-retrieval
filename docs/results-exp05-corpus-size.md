# exp05 — how much of the sparse-versus-dense result is just corpus size?

Measured 2026-08-12. Raw records: [`results/corpus_size.jsonl`](../results/corpus_size.jsonl),
per-size means in [`results/corpus_size_summary.jsonl`](../results/corpus_size_summary.jsonl).
Registered as H12 in [`PREREGISTRATION.md`](../PREREGISTRATION.md) section 4g, committed and
pushed before this ran.

Character-bigram BM25 scores **0.92345** on `AutoRAGRetrieval` while `multilingual-e5-large`
scores **0.81337**. A method with no trained weights beating a Korean-tuned embedding model
by 0.11 is a large claim, and this experiment exists to try to break it.

**It survives, but not for the reason the headline implies, and the actual cause is still
not established.**

## The design

Queries and their relevant documents are held fixed; only the number of distractor
documents changes. 5 sampling seeds per size, one run where the corpus is used whole.

| Direction | What varies |
|---|---|
| thin | distractors sampled out of the dataset's own corpus |
| pad | distractors added from another dataset's corpus |

## The curve

Mean over seeds. `bm25` is character-bigram BM25, `dense` is `multilingual-e5-large`.

### Thinning MIRACL-ko

| Documents | bm25 | dense | bm25 − dense | seeds where the interval excludes 0 |
|---|---|---|---|---|
| 720 | 0.93558 | 0.95638 | −0.02080 | 2 of 5 |
| 7,200 | 0.87891 | 0.94425 | −0.06534 | 5 of 5 |
| 72,000 | 0.68909 | 0.88971 | −0.20062 | 5 of 5 |
| 720,000 | 0.41445 | 0.72694 | −0.31249 | 5 of 5 |
| 1,486,752 *(whole)* | 0.35067 | 0.66486 | −0.31419 | 1 of 1 |

### Thinning Ko-StrategyQA

| Documents | bm25 | dense | bm25 − dense | |
|---|---|---|---|---|
| 2,400 | 0.67792 | 0.85784 | −0.17992 | 5 of 5 |
| 9,251 *(whole)* | 0.56108 | 0.80348 | −0.24239 | 1 of 1 |

**720 was not run for Ko-StrategyQA.** Its 592 queries have 1,077 relevant documents
between them, so a 720-document corpus cannot hold them. The harness reports this rather
than sampling relevant documents away.

### Padding AutoRAGRetrieval with MIRACL-ko documents

| Documents | bm25 | dense | bm25 − dense | |
|---|---|---|---|---|
| 720 *(whole, unpadded)* | 0.92345 | 0.81337 | +0.11009 | 5 of 5 |
| 7,200 | 0.88933 | 0.81337 | +0.07596 | 5 of 5 |
| 72,000 | 0.84877 | 0.81337 | +0.03540 | 0 of 5 |

## Verdicts

**H12a — supported.** Both retrievers fall at every 10× step on both thinning directions.
The Ko-StrategyQA steps are smaller than 10× because its corpus is not large enough for
one, which is noted rather than counted as a step.

**H12c — falsified.** Padding AutoRAGRetrieval to 72,000 documents was predicted to make
the difference negative. It is **+0.03540**, positive, though no longer distinguishable
from zero.

**H12b — the verdict depends on the sampling seed, and the pre-registration does not say
how to combine seeds.** At 720 MIRACL-ko documents, 3 of 5 seeds give an interval that
includes 0 (the prediction) and 2 of 5 give one that excludes it favouring dense (the
falsification). The two clauses are proper complements per seed, which H8 and H11b were
not — but fixing that exposed a **third** drafting gap: a prediction about a repeated
measurement needs an aggregation rule. Reported as undecided rather than settled by
picking an aggregation after seeing the numbers.

What does not depend on the seed: the gap falls from **−0.31419** on the whole corpus to
**−0.02080** at 720 documents. Even the seed least favourable to BM25 gives −0.02424.

## What this actually shows

**Corpus size explains the level, not the ordering.** Compare the two datasets at the same
720 documents:

| At 720 documents | bm25 | dense | |
|---|---|---|---|
| MIRACL-ko, thinned | 0.93558 | 0.95638 | dense ahead |
| AutoRAGRetrieval, whole | 0.92345 | 0.81337 | **bm25 ahead** |

BM25 scoring 0.92 on a 720-document corpus is **ordinary** — thin MIRACL-ko to the same
size and BM25 gets 0.94. The number that is out of line is **dense at 0.81337**, against
0.95638 for the same model on a same-size corpus.

So the question changes. It is not "why is BM25 so strong on AutoRAGRetrieval"; it is
**"why is `multilingual-e5-large` weak on AutoRAGRetrieval"**.

The padding direction says the same thing from the other side, and more bluntly: dense
scores **0.81337 at every padded size, identical to five decimal places**. Adding 71,280
distractor documents changes its ranking of the top 10 not at all, while BM25 falls 0.075.
The pre-registration called this direction confounded because MIRACL-ko is Wikipedia and
AutoRAGRetrieval is finance, law and public administration; a distractor set that leaves
dense literally unmoved confirms it was. It is a lower bound, and it did not bind.

## Two explanations tested, neither sufficient

**Lexical leakage — rejected.** If AutoRAGRetrieval's queries had been generated from the
passages that answer them, bigrams would exploit the overlap. Query→relevant bigram
coverage above a random-document null is +0.420 on AutoRAGRetrieval, +0.234 on
Ko-StrategyQA and **+0.443 on MIRACL-ko** — highest where BM25 does worst. (Run as a
diagnostic before section 4g was written, so recorded as context, not as a registered
prediction.)

**Truncation — real, and insufficient.** `multilingual-e5-large` truncates at 512 tokens.
The fraction of documents past that limit:

| Dataset | mean tokens | over 512 |
|---|---|---|
| AutoRAGRetrieval | 434.7 | **36.8%** |
| Ko-StrategyQA | 179.4 | 1.9% |
| MIRACL-ko | 106.1 | 0.7% |

More than a third of AutoRAGRetrieval's documents lose their tail before the model sees
them, against under 2% for the others — so dense really is handicapped on this dataset in
a way it is not on the others. But chunking removes that handicap and does not close the
gap. From [`results-exp02-chunking.md`](results-exp02-chunking.md), already measured:

| | nDCG@10 | |
|---|---|---|
| dense, whole documents | 0.81337 | |
| dense, chunked to 400 tokens | 0.85206 | gain +0.03869, CI [−0.0044, +0.08592] — not distinguishable |
| BM25 character bigram | 0.92345 | vs chunked dense +0.07139, CI [+0.01617, +0.12757] — **distinguishable** |

Chunking recovers about a third of the gap, not distinguishably, and BM25 stays
distinguishably ahead.

## Cause not established

AutoRAGRetrieval remains a dataset where an untuned sparse method beats a tuned Korean
embedding model, and **none of the three candidates accounts for it**: not query
provenance, not corpus size, not truncation. What has been ruled out is written above so
the next attempt does not repeat it.

Candidates **not** checked: domain (the model's training data against finance, legal and
public-administration Korean), whether the relevant documents are unusually long *given*
that the queries are short, and whether the same pattern appears for other embedding
models on this dataset. Listing them is not explaining them.

## Reproducing

```bash
python -m harness.corpus_size --dataset MIRACLRetrieval-ko \
    --sizes 720,7200,72000,720000,1486752 --seeds 5 --out results/corpus_size.jsonl

python -m harness.corpus_size --dataset AutoRAGRetrieval \
    --pad-from MIRACLRetrieval-ko --pad-pool 200000 --sizes 720,7200,72000 --seeds 5 \
    --out results/corpus_size.jsonl
```

The full MIRACL-ko run takes about 12 minutes on the machine used, most of it the five
720,000-document BM25 indexes. `--pad-pool` caps the padding pool at 200,000 documents so
its tokenization is affordable; the cap is recorded in every output row.
