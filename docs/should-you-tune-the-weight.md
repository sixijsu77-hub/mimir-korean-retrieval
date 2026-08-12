# Should you tune the hybrid weight at all?

A practitioner-facing reading of the measurements in this repository. Everything here
derives from [`results/hybrid.jsonl`](../results/hybrid.jsonl) and
[`results/subsample.jsonl`](../results/subsample.jsonl); the reasoning is in
[`results-week2.md`](results-week2.md), [`results-week3.md`](results-week3.md) and
[`results-week4.md`](results-week4.md).

Hybrid retrieval mixes a lexical score and a dense score with a weight, and that weight
is usually guessed or tuned on a handful of questions. The measurements here suggest a
different first question: **is there anything to tune?**

## The procedure

1. **Sweep the whole range, finely.** 0.00 to 1.00 in steps of 0.05. This is cheap:
   compute the sparse and dense score matrices once, then every weight is a weighted sum.
   A 21-point sweep costs no more retrieval than a 3-point one.
2. **Measure the amplitude** — the highest point of the curve minus the lowest.
3. **Compare it to your uncertainty.** Bootstrap the queries and take the 95% interval
   width at the best weight. Divide the amplitude by that width.
4. **Decide before tuning.**

| Amplitude ÷ interval width | What it means | What to do |
|---|---|---|
| around 2 or below | The whole curve fits inside the noise | Stop. Pick anything; report that the weight does not matter |
| around 4 or above | The curve clears the noise | Tuning is worthwhile; ~50 queries suffice to place it |

## What that table is based on

Three public Korean datasets, character-bigram BM25 fused with
`multilingual-e5-large`, min-max normalized per query:

| Dataset | Queries | Amplitude | 95% CI width | Ratio | Weights tied with the best |
|---|---|---|---|---|---|
| MIRACL-ko | 213 | 0.3576 | 0.0814 | **4.39** | 10 of 21 |
| Ko-StrategyQA | 592 | 0.2445 | 0.0521 | **4.70** | 8 of 21 |
| AutoRAGRetrieval | 114 | 0.1195 | 0.0629 | **1.90** | **19 of 21** |

On the two datasets with a ratio near 4.5, the optimum is locatable and subsampling
shows **50 queries are enough** to narrow it to about a third of the range. On the one
with a ratio near 1.9, no weight is distinguishable from any other — including
w = 0, pure BM25 — and that does not change even using all 114 of its queries.

**Only three datasets, so the boundary between 1.9 and 4.4 is not located.** The table
says what to do at the ends, not where the switch happens.

## Why "how many queries?" is the wrong first question

The obvious instinct is to collect more questions. Subsampling says that helps only when
there is a signal to resolve:

| Queries | Ko-StrategyQA (ratio 4.7) | AutoRAGRetrieval (ratio 1.9) |
|---|---|---|
| 12 | argmax 0.55 – 1.00, 43% tied | argmax **0.00 – 0.75**, **100% tied** |
| 50 | argmax 0.75 – 1.00, 29% tied | argmax 0.00 – 0.65, 81% tied |
| 100 | argmax 0.75 – 1.00, 19% tied | argmax 0.25 – 0.65, 71% tied |

Where the curve clears the noise, **12 questions already put the weight in the right
region** — no 12-query subsample of Ko-StrategyQA ever produced an argmax below 0.55.
Where it does not, 100 questions still leave 71% of the range tied, and 12 questions
produce a number anywhere from 0.00 to 0.75 that looks like an answer.

So a small evaluation set is not automatically useless, and a large one is not
automatically enough. The amplitude is what decides, and it costs one sweep to see.

## Two things worth knowing before you sweep

**Check your tokenizer first.** On these datasets, switching the sparse side from the
tokenizer behind the published Korean BM25 baselines to character bigrams gained 0.105
to 0.273 nDCG@10 — far more than any weight choice. Tuning a weight on top of a weak
lexical side optimizes the wrong thing. See [`results-week1.md`](results-week1.md).

**Check whether your documents fit the encoder.** Dense models used here cap at 512
tokens. On AutoRAGRetrieval 36.8% of documents exceed that and are truncated — and that
is the dataset where BM25 wins and the weight curve is flat. If a large share of your
corpus is being cut off, the fix is to change how documents are split, not to shift
weight toward BM25. That specific comparison is not measured here; it is the obvious
next experiment.

## What this does not say

- It does not say a low dense weight is wrong in general. It says that on these three
  datasets the optimum sat at 0.80–0.90 where it could be located at all, and that this
  repository's own pre-registered prediction of 0.2–0.4 was rejected.
- It does not give a threshold you can apply blindly. Three datasets, one language, one
  dense model family, one normalization as the headline.
- The ratio rule is a summary of what was measured, not something derived from theory.
  It was not pre-registered, and it should be treated as a hypothesis for anyone else to
  test on their own corpus — which the sweep makes cheap.
