# exp03 — does reranking make the retriever choice matter less?

Measured 2026-08-12. Raw records: [`results/reranking.jsonl`](../results/reranking.jsonl)
and [`results/rerank_gate.jsonl`](../results/rerank_gate.jsonl). Registered as H8 in
[`PREREGISTRATION.md`](../PREREGISTRATION.md) section 4d.2, committed before this ran.

Weeks 1–4 of this repository are about the first stage of retrieval: which tokenizer,
which dense model, which hybrid weight. A reranker sits after all of that. If it absorbs
the differences, most of that work matters much less in a real pipeline — a result
against this repository's own subject, which is why it was registered in advance.

**The headline is not the one that was predicted.** Reranking does compress the
differences, usually. But a reranker weaker than the retriever feeding it does not just
help less — it **destroys** a good ranking, by up to 0.37 nDCG@10.

## Gate — a sixth published number reproduced

MTEB publishes a BM25 baseline for `MIRACLReranking` ko. Reproducing it was required
before any reranked number could be reported.

| Tokenizer | nDCG@10 | Published | Difference | |
|---|---|---|---|---|
| **word (as MTEB applies it)** | **0.33979** | 0.33380 | **+0.00599** | pass |
| character unigram | 0.37152 | 0.33380 | +0.03772 | — |
| character bigram | 0.46550 | 0.33380 | +0.13170 | — |

The gate passes. The character-bigram figure repeats the pattern the retrieval tasks
showed, now on a reranking candidate set.

### The word-level baseline barely separates the candidates

On this task the word-level tokenizer gives **39.3% of the supplied candidates a score of
exactly zero** — not one query term overlaps them. Ties then reach the top 10 (0.18
zero-scored documents per query on average), so the ranking there is decided by
tie-breaking rather than by BM25.

Running the same configuration under ten different candidate orderings — changing nothing
else — moves the score:

| Tokenizer | Candidates scoring zero | nDCG@10 across 10 orderings | Spread |
|---|---|---|---|
| word | **39.3%** | 0.33384 – 0.33979 | **0.00595** |
| character unigram | 0.0% | 0.37152 – 0.37152 | 0.00000 |
| character bigram | 0.5% | 0.46550 – 0.46550 | 0.00000 |

Every one of those word-level orderings is within 0.02 of the published value, so all ten
"reproduce" it. The published 0.33380 sits essentially at the bottom of the range
(0.33384). The character tokenizers do not move at all, because they leave almost nothing
tied.

## H8 — supported in five of six conditions

The prediction: after reranking the top 100 from each of three retrievers — BM25 with
character bigrams, `multilingual-e5-large` alone, and the best hybrid weight — the spread
between them shrinks to **less than half**.

| Dataset | Documents | Reranker | Spread before | after | Ratio | |
|---|---|---|---|---|---|---|
| AutoRAGRetrieval | 720 | bge-reranker-v2-m3 (568 M) | 0.11948 | 0.00000 | 0.00 | holds |
| Ko-StrategyQA | 9,251 | bge-reranker-v2-m3 | 0.24454 | 0.04582 | 0.19 | holds |
| MIRACL-ko | 1,486,752 | bge-reranker-v2-m3 | 0.35759 | 0.07315 | 0.21 | holds |
| AutoRAGRetrieval | 720 | bge-reranker-base (278 M) | 0.11948 | 0.02164 | 0.18 | holds |
| Ko-StrategyQA | 9,251 | bge-reranker-base | 0.24454 | 0.14876 | **0.61** | **fails** |
| MIRACL-ko | 1,486,752 | bge-reranker-base | 0.35759 | 0.11334 | 0.32 | holds |

With the stronger reranker the amount of first-stage difference that survives grows with
the corpus — none at 720 documents, 0.073 at 1.49 M — which makes sense, since reranking
only sees the top 100, and 100 of 720 documents is 14% of the corpus while 100 of 1.49 M
is 0.007%.

## The finding that was not predicted

The two rerankers compress the spread in opposite directions.

| Dataset | Retriever | Before | v2-m3 (568 M) | base (278 M) |
|---|---|---|---|---|
| AutoRAGRetrieval | BM25 bigram | 0.92345 | 0.93955 | **0.83673** |
| | dense | 0.81337 | 0.93955 | 0.81509 |
| | hybrid w=0.25 | 0.93285 | 0.93955 | **0.82729** |
| Ko-StrategyQA | BM25 bigram | 0.56108 | 0.77942 | 0.58091 |
| | dense | 0.80348 | 0.82524 | **0.43215** |
| | hybrid w=0.9 | 0.80562 | 0.82512 | **0.43673** |
| MIRACL-ko | BM25 bigram | 0.35067 | 0.66314 | 0.54152 |
| | dense | 0.66486 | 0.72688 | **0.42818** |
| | hybrid w=0.8 | 0.70826 | 0.73629 | **0.47905** |

Bold entries are decreases whose 95% intervals exclude zero.

**A reranker pulls everything toward its own quality level.** The 568 M model's level is
above every retriever here, so it lifts all three. The 278 M model's level is around
0.43–0.58 on the larger corpora — below what dense retrieval already achieves — so it
**drags a 0.80 ranking down to 0.43**. That is not a smaller improvement; it is a 46% loss.

The same 278 M model *improves* BM25 on MIRACL-ko (+0.19), because there the retriever was
below its level. Same model, same corpus, opposite effect depending on what feeds it.

### H8's criterion cannot tell those apart

The prediction was written about the spread shrinking and says nothing about direction. A
reranker that drags everything down to a common floor passes it. Both rerankers "support
H8" on AutoRAGRetrieval while one gains 0.016 and the other loses 0.087.

This is a flaw in how the hypothesis was written, recorded rather than repaired after the
fact. The version worth carrying forward would test that the *best* retriever's score does
not fall.

### The practical statement

- **Adding a reranker is not free improvement.** A cross-encoder weaker than your
  retriever can cost you half your accuracy. Measure before deploying one.
- **If the reranker is stronger than your first stage**, first-stage choices — tokenizer,
  hybrid weight — matter much less, and the more so on small corpora.
- **Model size is a usable proxy but not a guarantee.** Here 568 M helped everywhere and
  278 M hurt wherever the retriever was already good; that ordering was not knowable in
  advance without running it.

## The zero at 720 documents is real, and it is a property of the corpus

A spread of exactly 0.00000 across three different retrievers is the kind of number this
repository's own pre-registration says to treat as suspicious. It was checked:

- All three retrievers have **recall@100 = 1.00000** on AutoRAGRetrieval — the relevant
  document is always among the candidates.
- After reranking, all three place it at rank 1 for **100 of 114** queries.
- The candidate lists overlap only **44.7%**, so the sets genuinely differ.
- Exactly **one** query ranks the answer differently between BM25 and dense candidates —
  17th versus 16th. Both are outside the top 10, so both contribute 0 to nDCG@10, and the
  means match exactly.

The reranker is not producing identical rankings; it places the same relevant document in
the same position regardless of what else is in the list. On a corpus this small that
makes the first stage irrelevant. It does not generalize — the same reranker leaves 0.073
on MIRACL-ko.

## Reproducing

```bash
python -m harness.rerank_gate --out results/rerank_gate.jsonl
python -m harness.rerank_experiment --dataset Ko-StrategyQA \
    --reranker BAAI/bge-reranker-v2-m3 --out results/reranking.jsonl
```

Swap `--dataset` and `--reranker`. Reranking 100 candidates for 592 queries across three
retrievers takes about 22 minutes on the GPU used with the 568 M model, about 9 with the
278 M one.

## Not run

**`Alibaba-NLP/gte-multilingual-reranker-base`, named in the pre-registration, was not
run.** Loading it requires `trust_remote_code=True`, which downloads and executes Python
from the model repository on the local machine. The code was downloaded and read without
executing it — 66 KB defining a model architecture, with no file, network or subprocess
calls — but the machine in question holds credentials, so the setting was left off.
`BAAI/bge-reranker-base` was substituted; it is a standard architecture needing no remote
code. **The substitution is a deviation from the pre-registration** and is marked as one
here. It also turned out to be the more informative run — the registered contrast was
another strong reranker, and the substitute is what exposed the downward-convergence case.

**`multilingual-e5-small` was not reranked.** H8 is about the spread between retrievers,
and adding a fourth would change the quantity being measured mid-experiment.
