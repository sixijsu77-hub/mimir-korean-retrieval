# exp02 — does chunking recover dense retrieval on truncated corpora?

Measured 2026-08-12. Raw records: [`results/chunking.jsonl`](../results/chunking.jsonl).
Registered as H7 in [`PREREGISTRATION.md`](../PREREGISTRATION.md) section 4d.1, committed
and pushed before this ran.

Earlier weeks observed that the one dataset where dense loses and the weight curve is
flat is also the one whose documents the encoders truncate. That is a correlation across
three datasets. This experiment **removes the truncation** and looks at what changes —
manipulating the proposed cause rather than observing it.

Documents are split into windows of at most 400 tokens with 50-token overlap, measured
with the model's own tokenizer, and a document scores the maximum over its chunks.

## H7 — rejected

| | AutoRAGRetrieval (36.8% over the limit) | Ko-StrategyQA (1.5%, control) |
|---|---|---|
| Chunks per document | 1.66 | 1.04 |
| Dense alone, unchunked | 0.81337 | 0.80348 |
| Dense alone, chunked | **0.85206** | 0.80234 |
| Gain | **+0.03869** | −0.00114 |
| 95% CI on the gain | **[−0.0044, 0.0859]** | [−0.0024, −0.0002] |
| Excludes zero | **no** | yes |

H7 predicted a gain on AutoRAGRetrieval whose interval excludes zero. The point estimate
moved the predicted way and is not small — +0.039 nDCG@10 — but the interval includes
zero. **H7 is rejected.**

The reason is the one already documented in [`results-week4.md`](results-week4.md):
AutoRAGRetrieval has 114 queries and an amplitude-to-interval-width ratio near 1.9. It
cannot resolve differences of this size. This is a failure to demonstrate, not a
demonstration of no effect, and those are different claims.

**The control behaved as a control should.** On Ko-StrategyQA, where almost nothing is
truncated, chunking produced a tiny *decrease* — statistically distinguishable from zero
but 34× smaller than the AutoRAGRetrieval point estimate. Splitting documents that
already fit costs a little context and gains nothing, which is what should happen if
truncation is the thing chunking fixes.

## What chunking did change

| | AutoRAGRetrieval | Ko-StrategyQA |
|---|---|---|
| Best dense weight, unchunked | 0.25 | 0.90 |
| Best dense weight, chunked | **0.65** | 0.90 |
| Curve amplitude, unchunked | 0.1195 | 0.2445 |
| Curve amplitude, chunked | 0.0948 | 0.2434 |
| Amplitude ÷ interval width, chunked | 1.78 | 4.67 |

On AutoRAGRetrieval the optimum moved from 0.25 to 0.65 — the direction the mechanism
predicts, since a stronger dense side deserves more weight. But the curve got **flatter**,
not steeper: the amplitude fell and the ratio stayed below 2. Chunking makes dense better
on that dataset and still leaves the weight unlocatable.

On the control, nothing moved: same optimum, same amplitude to three decimals.

## A caveat from week 2 is now resolved

[`results-week2.md`](results-week2.md) flagged that H1 — character-bigram BM25 beating a
dense model — survived only on the dataset where truncation handicaps dense, and called
that weaker support than the bare verdict suggested.

With truncation removed:

| AutoRAGRetrieval | nDCG@10 |
|---|---|
| BM25, character bigram | **0.92345** |
| `multilingual-e5-large`, chunked | 0.85206 |
| Difference | **+0.07139**, 95% CI [0.0162, 0.1276], excludes zero |

**BM25 still wins after the handicap is removed.** That part of the caveat is answered.
The other part is not: AutoRAGRetrieval's questions were generated against its documents,
so lexical overlap may still favour the sparse side, and this experiment does not touch
that.

On Ko-StrategyQA the same comparison runs the other way by a wide margin — chunked dense
0.80234 against BM25 0.56108, difference −0.24125 — so this is a property of that one
corpus, not a general result.

## Not run

**MIRACL-ko was not run.** Its documents average 175 characters, so chunking would
produce about one chunk per document and change nothing — the same regime as the
Ko-StrategyQA control, which moved by 0.001. Encoding 1.49 M chunks costs about an hour
of GPU time for a result the control already predicts. Recorded here rather than
silently skipped.

**Only `multilingual-e5-large` was chunked.** H7 is about truncation, which affects both
models the same way, but the smaller model was not re-run.

## Reproducing

```bash
python -m harness.chunk_experiment --dataset AutoRAGRetrieval \
    --model intfloat/multilingual-e5-large --out results/chunking.jsonl
```

Swap `--dataset` for `Ko-StrategyQA`. Chunk embeddings are cached under `embeddings/`,
so a re-run does not re-encode.
