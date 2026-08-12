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

So the question changes. It is not "why is BM25 so strong on AutoRAGRetrieval".

### And it is not about one model either

*Added after the section below was first published, which framed this as a question about
`multilingual-e5-large`. That framing was too narrow and pointed readers at the wrong
place.* KURE publishes per-task nDCG@10 for **18 embedding models** on these same three
tasks; the numbers are in [`results/kure_per_task.jsonl`](../results/kure_per_task.jsonl),
read from that project's `eval/results`, not re-run here.

| Task | character-bigram BM25 | best of the 18 | median of the 18 | models BM25 beats |
|---|---|---|---|---|
| AutoRAGRetrieval | 0.92345 | 0.87379 (`dragonkue/BGE-m3-ko`) | 0.77996 | **18 of 18** |
| Ko-StrategyQA | 0.56108 | 0.81080 (`Alibaba-NLP/gte-Qwen2-7B-instruct`) | 0.79405 | 0 of 18 |
| MIRACL-ko | 0.35067 | 0.70315 (`BAAI/bge-multilingual-gemma2`) | 0.62697 | 0 of 18 |

**An untuned sparse baseline outscores every dense model on AutoRAGRetrieval and none of
them on the other two.** This is a property of the dataset, not of any model.

The comparison is only legitimate because the dense side was checked first: this harness
reproduces KURE's `multilingual-e5-large` figures on all three tasks to five decimals
(0.81337 / 0.80348 / 0.66486), so its numbers and KURE's are on the same footing.

One thing this does *not* show is a corpus-size effect on the dense side. Across all 18
models, AutoRAGRetrieval (720 documents) scores a median of only **+0.015** above
Ko-StrategyQA (9,251 documents), and 8 of the 18 score *lower* on the smaller corpus. That
matches the thinning curve above, where dense gains just 0.012 between 7,200 and 720
documents because it is already near its ceiling. The dense models are behaving normally;
what is unusual is how well lexical matching does here.

The padding direction says the same thing from the other side: dense scores **0.81337 at
every padded size, identical to five decimal places**, while BM25 falls 0.075.

**An unchanged score is not an unchanged ranking, so the added documents were counted
rather than assumed absent.** With one relevant document per query, nDCG@10 tracks only
that document's rank — distractors can fill the rest of the top 10 without moving it. At
72,000 documents (99% of the corpus added):

| | added docs in top-10 | queries with ≥1 | best rank reached | queries whose per-query nDCG@10 changed |
|---|---|---|---|---|
| BM25 character bigram | 3.38 per query | 83–90 of 114 | 1 | many — the score falls |
| dense | 0.43 per query | 16–22 of 114 | 1 | **0 of 114** |

So the padding is in the index and does reach the dense top 10; what it never does is
outrank a relevant document. Across five sizes and five seeds, **not one query's dense
per-query nDCG@10 changed**. The cases where an added document takes rank 1 are among the
7 of 114 queries where dense already placed the relevant document outside the top 10, so
they contribute 0 either way.

The pre-registration called this direction confounded because MIRACL-ko is Wikipedia and
AutoRAGRetrieval is finance, law and public administration. It was: the distractors are
out-of-domain and dense separates them almost completely, so the test is a lower bound,
and it did not bind. The same distractors displace BM25 eight times as often.

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

AutoRAGRetrieval is a dataset where an untuned sparse method beats **all 18** published
dense models, and **none of the four candidates accounts for it**: not query provenance,
not corpus size, not truncation, and not a weakness in one model. What has been ruled out
is written above so the next attempt does not repeat it.

Candidates **not** checked: domain (embedding training data against finance, legal and
public-administration Korean), and whether the relevant documents are unusually long
*given* that the queries are short. Listing them is not explaining them.

**What is established is enough to matter without the cause.** On this task the ordering
between sparse and dense inverts completely against the other two Korean retrieval tasks,
and it does so for every model measured. A benchmark aggregating AutoRAGRetrieval with
tasks like Ko-StrategyQA and MIRACL-ko is averaging over a task that ranks retrievers in
the opposite direction — which is worth knowing whether or not the reason is known.

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
