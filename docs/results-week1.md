# Week 1 — harness validation gate

Measured 2026-08-12. Raw records: [`results/gate_bm25.jsonl`](../results/gate_bm25.jsonl).
Reproduce with the commands at the bottom.

The gate is defined in [`PREREGISTRATION.md`](../PREREGISTRATION.md) section 4 and was
committed before any of this ran: reproduce MTEB's published BM25 nDCG@10 on
AutoRAGRetrieval **and** Ko-StrategyQA, within 0.02 on both.

## Gate result: passed on both

| Dataset | Tokenizer | Measured | Published | Difference | Tolerance | |
|---|---|---|---|---|---|---|
| AutoRAGRetrieval (test) | character unigram | 0.64342 | 0.65022 | **−0.00680** | ±0.02 | pass |
| Ko-StrategyQA (dev) | word | 0.37807 | 0.37808 | **−0.00001** | ±0.02 | pass |

Neither difference is exactly zero, so the pre-registered "treat 0.000 as suspicious"
check does not fire. The Ko-StrategyQA match is exact at the precision the published
value is reported to. That is not a shared code path: the metrics, the data loading and
the ranking assembly here are written from scratch, and only the BM25 scoring engine
(`bm25s`) is deliberately shared with MTEB so that a mismatch would point at this
harness rather than at BM25.

Metric implementations were checked against hand-computed values before the gate ran
(with one positive per query, nDCG@10 must equal 1/log₂(rank+1); this and five other
cases match to 1e-12).

## The gate failed first, and the reason is the finding

The published configuration was documented in [`docs/baselines.md`](baselines.md)
**before** any measurement, and that document was wrong. It stated that both published
numbers came from the word-level `bm25s` tokenizer, and listed two candidate MTEB code
paths differing only in whether English stopwords and an English stemmer were applied.

Running the word tokenizer gave **0.79557** on AutoRAGRetrieval — 0.145 *above* the
published 0.65022. Both candidate configurations produced that same number to five
decimal places, so neither candidate explained the gap.

Following the pre-registered order of suspicion (tokenizer first), the full grid was run:

| Dataset | Tokenizer | nDCG@10 | vs published |
|---|---|---|---|
| AutoRAGRetrieval | character bigram | 0.92345 | +0.27323 |
| AutoRAGRetrieval | word | 0.79557 | +0.14535 |
| AutoRAGRetrieval | **character unigram** | **0.64342** | **−0.00680** |
| Ko-StrategyQA | character bigram | 0.56108 | +0.18300 |
| Ko-StrategyQA | **word** | **0.37807** | **−0.00001** |
| Ko-StrategyQA | character unigram | 0.30430 | −0.07378 |

**The two published numbers were produced with different tokenizers.** Ko-StrategyQA's
came from the word-level tokenizer; AutoRAGRetrieval's came from character unigrams.

This was reported to the MTEB project as
[embeddings-benchmark/mteb#5157](https://github.com/embeddings-benchmark/mteb/issues/5157),
with the reproduction commands below.

This matches how MTEB's Korean handling changed over time, traced through the source in
`docs/baselines.md`: versions up to 2.18.0 had no Korean entry in the tokenizer language
table and fell through to the word-level default, while 2.18.16 maps `kor` to character
unigrams. Ko-StrategyQA's result file records `mteb_version: 2.10.8`, which is in the
word-level era — consistent. AutoRAGRetrieval's records `2.12.30`, which is *also* in
the word-level era, and that is **not** consistent with its measured tokenizer. Its
result sits in the `0_3_0` folder, a revision string that did not exist before MTEB
2.15.0, so the recorded `mteb_version` field appears stale and the run was almost
certainly made with a later version.

That metadata inconsistency was noticed and written down before any measurement — it is
in the commit that first published `docs/baselines.md`, which predates this one. What
was not anticipated is that the answer would be a third option (character unigrams)
rather than either of the two candidates listed. The prediction was wrong; it is left
in place and corrected here rather than edited away.

### On selecting the tokenizer by which one matched

Three tokenizers were tried and the matching one was kept, which on its own is weak
evidence. Three things make it more than curve-fitting:

- Ko-StrategyQA matches to **1e-5**. A coincidental fit inside a ±0.02 window would not
  land at five decimal places.
- Ko-StrategyQA's tokenizer is **predicted independently** by its recorded MTEB version,
  with no reference to the score.
- Our character unigram implementation was checked against MTEB's `_unicode_tokenize`
  directly: **0 mismatches across all 720 documents and 114 queries.** The tokenizer is
  not approximately right, it is identical.

### The −0.00680 residual on AutoRAGRetrieval is not explained

It is inside tolerance, and it is not zero. On 114 queries with one positive each, 0.0068
corresponds to roughly two queries differing by a single rank position. **Cause not
established.** Candidates that have *not* been checked: the `bm25s` version (0.3.10 here;
the result folder name suggests 0.3.0), how MTEB combines any task-level prompt into
query text, and tie-breaking between equal scores. These are listed as open, not as
explanations.

## Published Korean BM25 baselines understate BM25

With the gate passed, new numbers can be reported. Character-bigram tokenization beats
the tokenizer behind each published baseline, on both datasets, with non-overlapping
95% confidence intervals (bootstrap, 10,000 resamples at the query level, seed 0):

### AutoRAGRetrieval — 720 documents, 114 queries

| Tokenizer | nDCG@10 | 95% CI | Recall@10 | Recall@100 | Vocabulary | Tokens/doc |
|---|---|---|---|---|---|---|
| character bigram | **0.92345** | [0.8848, 0.9572] | 0.9825 | 1.0000 | 45,719 | 661.6 |
| word | 0.79557 | [0.7319, 0.8572] | 0.8947 | 0.9737 | 36,076 | 169.8 |
| character unigram *(published baseline)* | 0.64342 | [0.5725, 0.7149] | 0.8246 | 0.9912 | 1,112 | 662.6 |

### Ko-StrategyQA — 9,251 documents, 592 queries

| Tokenizer | nDCG@10 | 95% CI | Recall@10 | Recall@100 | Vocabulary | Tokens/doc |
|---|---|---|---|---|---|---|
| character bigram | **0.56108** | [0.5308, 0.5927] | 0.6663 | 0.8248 | 121,930 | 250.8 |
| word *(published baseline)* | 0.37807 | [0.3471, 0.4095] | 0.4624 | 0.5823 | 149,152 | 67.2 |
| character unigram | 0.30430 | [0.2765, 0.3324] | 0.4186 | 0.6519 | 2,569 | 251.8 |

The gap is large: **+0.280 nDCG@10 on AutoRAGRetrieval and +0.183 on Ko-StrategyQA**
over the respective published baseline, from tokenization alone. No BM25 parameter was
tuned — k1 = 1.5, b = 0.75, Lucene variant, the `bm25s` defaults, throughout.

The practical consequence: **a Korean retrieval leaderboard that reports "BM25" as a
baseline may be reporting a tokenization artifact rather than what BM25 can do.** Any
claimed margin of a dense model over that baseline should be read with that in mind.

English stopwords and an English stemmer — which MTEB applies to Korean — turn out to be
nearly inert, as expected but now measured. On AutoRAGRetrieval they change nothing to
five decimals. On Ko-StrategyQA they move nDCG@10 by 0.00006, because that corpus is
Wikipedia-derived and contains English titles for the stemmer to act on.

## Caveats

- **AutoRAGRetrieval may favour lexical matching.** Its questions were generated against
  the parsed PDF chunks, so query and document wording may overlap more than in
  naturally-occurring search. A 0.92 nDCG@10 should be read with that in mind. Ko-StrategyQA,
  where the same tokenizer reaches 0.56, is the more conservative datapoint.
- **Character bigrams cost more.** Vocabulary grows from 1,112 to 45,719 on
  AutoRAGRetrieval, and documents produce ~660 tokens instead of ~170 at word level.
  This is cheap at these corpus sizes and is measured, not estimated, before MIRACL.
- **Nothing dense has been measured here yet.** KURE publishes `multilingual-e5-large` at
  0.81337 nDCG@10 on AutoRAGRetrieval, which is *below* the 0.92345 that character-bigram
  BM25 reaches here. That comparison crosses two different harnesses and is suggestive
  only; it is also not a test of hypothesis H1, which names
  `multilingual-e5-small`. Dense models are measured in week 2, in this harness.
- **MIRACL has not been run.** Its size was measured (1,486,752 documents) and it is in
  scope; it is not part of the gate.

## Reproducing

```bash
pip install -r requirements.txt
python -m harness.evaluate --dataset AutoRAGRetrieval --tokenizer char_unigram \
    --out results/gate_bm25.jsonl
python -m harness.evaluate --dataset Ko-StrategyQA --tokenizer word \
    --stopwords en --stemmer english --out results/gate_bm25.jsonl
```

Swap `--tokenizer` for `word`, `char_unigram` or `char_bigram` to reproduce any row above.
Every table on this page is derived from `results/gate_bm25.jsonl`, which holds the full
record including per-query nDCG@10.
