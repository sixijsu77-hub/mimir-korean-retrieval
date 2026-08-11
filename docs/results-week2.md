# Week 2 — dense, hybrid, and the hypotheses

Measured 2026-08-12. Raw records: [`results/hybrid.jsonl`](../results/hybrid.jsonl).
Predictions being tested were fixed in [`PREREGISTRATION.md`](../PREREGISTRATION.md)
before any of this ran.

**Headline: the prediction failed.** The hybrid optimum was pre-registered at a dense
weight of 0.2–0.4 with the curve declining above it. On the dataset where the question
can actually be answered, the optimum sits at **0.9** and the curve climbs almost all the
way to pure dense retrieval. That is the opposite of what the private measurement found,
and it is published here unchanged.

## A second reproduction, this time on the dense side

KURE publishes per-task scores for `intfloat/multilingual-e5-large`. Measured in this
harness:

| Dataset | Measured nDCG@10 | KURE published | Difference |
|---|---|---|---|
| AutoRAGRetrieval | 0.81337 | 0.81337 | **0.00000** |
| Ko-StrategyQA | 0.80348 | 0.80348 | **0.00000** |

The pre-registration says an exactly-zero difference is to be treated as suspicious
rather than as success, and that the two runs must be checked for being the same code
path. They are not:

- **MTEB was never installed in this environment.** The published values were read from
  KURE's committed result JSON; nothing here re-ran their evaluator.
- The nDCG and recall implementations here are written from scratch and were checked
  against hand-computed values (9 cases, agreement to 1e-12) before any score was
  reported. KURE's numbers come from `pytrec_eval`.
- Data loading, ranking assembly and the bootstrap are all independent.

What *is* shared is deliberate and unavoidable: the model weights, `sentence-transformers`
as the encoder, and the datasets. Dense retrieval is deterministic given those, so exact
agreement is the expected outcome when the remaining settings match — and it therefore
also confirms that KURE used the same `query: `/`passage: ` prefixes and the same 512-token
limit. Matching a mean over 114 queries to five decimals by coincidence is not plausible.

Together with the week-1 BM25 gate, the harness has now reproduced four published numbers
from two independent sources, across both sparse and dense retrieval.

## Documents are truncated, and it matters

Measured with the e5 tokenizer (XLM-RoBERTa), before any encoding:

| Dataset | Mean tokens/doc | p95 | Max | Over the 512 limit |
|---|---|---|---|---|
| AutoRAGRetrieval | 434.7 | 773 | 1,260 | **265 of 720 (36.8%)** |
| Ko-StrategyQA | 177.4 | 354 | 2,818 | 140 of 9,251 (1.5%) |

Both e5 models cap at 512 tokens, so **more than a third of the AutoRAGRetrieval corpus
is truncated before it is encoded.** Ko-StrategyQA is essentially unaffected. This was
measured rather than assumed, and it colours every AutoRAGRetrieval comparison below:
the dense side is handicapped there in a way it is not on Ko-StrategyQA. The published
KURE numbers were produced under the same limit.

## Retrieval alone

Character-bigram BM25 (no parameter tuning) against both dense models. 95% bootstrap
intervals, 10,000 resamples at the query level, seed 0.

### AutoRAGRetrieval — 720 documents, 114 queries

| Method | nDCG@10 | 95% CI |
|---|---|---|
| BM25, character bigram | **0.92345** | [0.8849, 0.9568] |
| `multilingual-e5-large` | 0.81337 | [0.7565, 0.8663] |
| `multilingual-e5-small` | 0.80068 | [0.7436, 0.8552] |

### Ko-StrategyQA — 9,251 documents, 592 queries

| Method | nDCG@10 | 95% CI |
|---|---|---|
| `multilingual-e5-large` | **0.80348** | [0.7768, 0.8297] |
| `multilingual-e5-small` | 0.75157 | [0.7236, 0.7790] |
| BM25, character bigram | 0.56108 | [0.5303, 0.5926] |

The ordering reverses completely between the two datasets.

## Hybrid weight curves

Dense weight swept 0.00 → 1.00 in steps of 0.05, fused over the full corpus with
per-query min-max normalization. `w=0` is BM25 alone, `w=1` is dense alone.

| w | AutoRAG / e5-small | AutoRAG / e5-large | Ko-SQA / e5-small | Ko-SQA / e5-large |
|---|---|---|---|---|
| 0.00 | 0.9234 | 0.9234 | 0.5611 | 0.5611 |
| 0.10 | 0.9240 | 0.9210 | 0.5834 | 0.5884 |
| 0.20 | 0.9317 | 0.9315 | 0.6063 | 0.6166 |
| 0.30 | 0.9319 | 0.9304 | 0.6310 | 0.6460 |
| 0.40 | 0.9326 | 0.9281 | 0.6525 | 0.6796 |
| 0.50 | 0.9299 | 0.9243 | 0.6859 | 0.7100 |
| 0.60 | **0.9353** | 0.9225 | 0.7161 | 0.7461 |
| 0.70 | 0.9221 | 0.9186 | 0.7379 | 0.7731 |
| 0.80 | 0.9094 | 0.9008 | 0.7543 | 0.7914 |
| 0.90 | 0.8895 | 0.8658 | **0.7601** | **0.8056** |
| 1.00 | 0.8007 | 0.8134 | 0.7516 | 0.8035 |

Min-max and z-score normalization give optima 0.05 apart in every case, well inside the
band where weights cannot be distinguished. **The two normalizations agree**; the
pre-registered possibility that they would disagree did not occur.

## Hypotheses

### H1 — supported, with a caveat that may swallow it

Predicted: on at least one dataset, character-bigram BM25 alone beats
`multilingual-e5-small` alone. Falsified only if dense wins everywhere.

| Dataset | BM25 bigram | e5-small | Intervals overlap |
|---|---|---|---|
| AutoRAGRetrieval | 0.92345 [0.8849, 0.9568] | 0.80068 [0.7436, 0.8552] | no |
| Ko-StrategyQA | 0.56108 [0.5303, 0.5926] | 0.75157 [0.7236, 0.7790] | no |

BM25 wins decisively on AutoRAGRetrieval and loses decisively on Ko-StrategyQA, so the
falsification condition is not met and **H1 stands**. On AutoRAGRetrieval bigram BM25 also
beats `multilingual-e5-large` with non-overlapping intervals.

The caveat: AutoRAGRetrieval is the dataset where 36.8% of documents are truncated before
encoding, and where questions were generated against the documents. Both push in BM25's
favour. **H1 survives on the one dataset where the dense side is most handicapped.** That
is weaker support than the bare verdict suggests, and it is the honest reading.

### H2 — rejected where it can be tested

Predicted: the best dense weight falls in 0.2–0.4.

| Dataset | Model | Best w | Weights indistinguishable from best | 0.2–0.4 testable |
|---|---|---|---|---|
| AutoRAGRetrieval | e5-small | 0.60 | 19 of 21 (0.00–0.90) | no |
| AutoRAGRetrieval | e5-large | 0.25 | 19 of 21 (0.00–0.90) | no |
| Ko-StrategyQA | e5-small | 0.90 | 10 of 21 (0.55–1.00) | yes |
| Ko-StrategyQA | e5-large | 0.90 | 8 of 21 (0.65–1.00) | yes |

On AutoRAGRetrieval almost every weight's interval overlaps the best one's, so the
optimum **cannot be located** — reported as not distinguishable, per the pre-registered
stopping rule, rather than read off the point estimate.

On Ko-StrategyQA the optimum is at 0.90 for both models, and the 0.2–0.4 band *is*
distinguishable from it. **H2 is rejected** on the only dataset where it could be tested.

### H3 — rejected on one dataset, shape holds on the other with the wrong peak

Predicted: single-peaked, declining monotonically above the optimum. Falsified if flat,
multi-peaked, or still rising at w=1.0.

- **AutoRAGRetrieval**: no weight below 0.95 is distinguishable from any other. The curve
  is flat in the sense that matters, which is one of the pre-registered falsification
  conditions. **H3 rejected here.**
- **Ko-StrategyQA**: single-peaked and monotonically declining after the peak, for both
  models — the predicted *shape*. But the peak is at 0.90, not near 0.30, so the shape
  being right does not rescue H2.

### H4 — not measured

Hubness is week-3 work.

## Does the private finding generalize?

The pre-registration named the condition for abandoning the claim entirely: BM25 losing
to dense on *every* dataset **and** the hybrid optimum sitting at w ≥ 0.5. Half of that
is met. BM25 does not lose everywhere — it wins clearly on AutoRAGRetrieval — but the
optimum is at 0.90 on Ko-StrategyQA, far above 0.5.

The most defensible reading of what has been measured:

- The claim that a small multilingual dense model can lose to well-tokenized BM25 **holds**,
  on a corpus with long documents that the model truncates.
- The claim that the hybrid optimum sits near a dense weight of 0.3, with accuracy falling
  as more dense signal is mixed in, **does not hold**. Where it could be tested, the
  optimum was at 0.9 and accuracy rose nearly to pure dense.
- The original private result looks corpus-specific rather than a property of Korean
  retrieval.

## Limitations

- **The overlap test is conservative.** Distinguishability is judged by whether two
  marginal bootstrap intervals overlap. Because every weight is scored on the same
  queries, a paired bootstrap of the *difference* would be more powerful and might
  separate weights this test cannot. That analysis is not run here — adding a more
  sensitive test after seeing which weights failed to separate would be exactly the
  move this repository exists to avoid. It will be pre-registered before week 3.
- **One sparse side.** All hybrid curves use character-bigram BM25. A hybrid built on
  the word-level tokenizer would start from a lower BM25 baseline and could peak
  elsewhere. Not run.
- **Two datasets.** MIRACL-ko (1,486,752 documents) is measured and in scope but not yet
  run, so no conclusion here covers a corpus of that size.
- **AutoRAGRetrieval flatters lexical matching.** Its questions were generated against
  the parsed chunks, and a third of its documents are truncated for the dense models.
  Ko-StrategyQA is the more conservative datapoint throughout.

## Reproducing

```bash
pip install -r requirements.txt   # includes torch for this stage
python -m harness.sweep --dataset AutoRAGRetrieval \
    --model intfloat/multilingual-e5-small --tokenizer char_bigram \
    --out results/hybrid.jsonl
```

Swap `--dataset` and `--model` for the other three rows. Embeddings are cached under
`embeddings/`, so re-running a sweep does not re-encode. Every table on this page derives
from `results/hybrid.jsonl`, which holds the full 21-point curve for both normalizations.
