# Week 3 — a sharper test, hubness, and MIRACL

Measured 2026-08-12. Raw records: [`results/week3.jsonl`](../results/week3.jsonl) and
[`results/hybrid.jsonl`](../results/hybrid.jsonl).

Everything on this page was specified in [`PREREGISTRATION.md`](../PREREGISTRATION.md)
section 4b, which was committed and pushed **before any of these measurements ran** —
`git log` puts that commit between the week-2 results and this one. That ordering is the
point: week 2 noted that a paired test would be more sensitive than the one used, and
adding a more sensitive test *after* seeing which comparisons failed to separate is
exactly the move this repository exists to avoid.

## The sharper test does not rescue the prediction

Week 2 judged two weights distinguishable only if their marginal bootstrap intervals
failed to overlap. That is conservative, because every weight is scored on the same
queries. The paired version bootstraps the per-query *difference*, with a Bonferroni
correction for the 20 comparisons each curve makes against its own best weight.

It is indeed more sensitive — the set of weights that cannot be told apart from the best
shrinks everywhere:

| Dataset | Model | Best w | Week 2 (marginal) | Week 3 (paired, Bonferroni) |
|---|---|---|---|---|
| AutoRAGRetrieval | e5-small | 0.60 | 0.00–0.90 (19 of 21) | 0.00–0.70 (15 of 21) |
| AutoRAGRetrieval | e5-large | 0.25 | 0.00–0.90 (19 of 21) | 0.00–0.85 (18 of 21) |
| Ko-StrategyQA | e5-small | 0.90 | 0.55–1.00 (10 of 21) | 0.75–1.00 (6 of 21) |
| Ko-StrategyQA | e5-large | 0.90 | 0.65–1.00 (8 of 21) | 0.85–1.00 (4 of 21) |

**No verdict changes.** H2 is still rejected on Ko-StrategyQA — the pre-registered
0.2–0.4 band sits outside the indistinguishable set by a wider margin than before — and
the optimum on AutoRAGRetrieval still cannot be located.

One thing the sharper test makes clearer: on AutoRAGRetrieval, **w = 0 remains
indistinguishable from the best hybrid** under the more powerful test. Adding dense
signal to character-bigram BM25 buys nothing measurable on that dataset, for either
model.

### The pre-registered resample count was too small, and it shows

Bonferroni at α = 0.05/20 puts the interval endpoints at the 0.125th and 99.875th
percentiles. With the pre-registered B = 10,000 that is **12 resamples in each tail** —
too few to place the endpoint reliably. Re-running at B = 100,000 was added as a
Monte-Carlo precision check (not pre-registered, and it tests the same quantity rather
than a different one):

| Dataset | Model | B = 10,000 (registered) | B = 100,000 |
|---|---|---|---|
| Ko-StrategyQA | e5-small | 0.75–1.00 | **0.80–1.00** |
| all other conditions | | agree | agree |

One boundary weight moves. No verdict depends on it. The registered value is what the
tables above report; the disagreement is recorded rather than quietly resolved in favour
of the larger run. **A future pre-registration should set B from the corrected α, not
from habit.**

## H4 — hubness is real, and the sparse method has it worse

Counting only appearances in the top 10 of queries the document is *not* relevant to,
against a uniform-random null of 1,000 replicates:

| Dataset | Method | Skewness | Null p99 | Exceeds | Gini | Max | Top 1% share |
|---|---|---|---|---|---|---|---|
| AutoRAGRetrieval | BM25 char-bigram | 4.08 | 1.08 | yes | 0.630 | 26 | 9.3% |
| AutoRAGRetrieval | e5-small | 1.58 | 1.08 | yes | 0.583 | 11 | 5.5% |
| AutoRAGRetrieval | e5-large | 1.57 | 1.08 | yes | 0.592 | 11 | 5.2% |
| Ko-StrategyQA | BM25 char-bigram | **63.30** | 1.34 | yes | 0.793 | **334** | **24.2%** |
| Ko-StrategyQA | e5-small | 4.31 | 1.34 | yes | 0.745 | 21 | 10.4% |
| Ko-StrategyQA | e5-large | 8.21 | 1.34 | yes | 0.736 | 38 | 10.4% |

**H4 is supported.** Dense retrieval's skewness exceeds the null 99th percentile on both
datasets, for both models.

**But the framing behind it does not survive.** The private observation that motivated
H4 was about a dense model returning the same passage for unrelated questions. On public
data, character-bigram BM25 does that far more: on Ko-StrategyQA its skewness is 63.3
against dense's 4.3–8.2, one document appears in the top 10 of **334 of 592 queries it is
not relevant to**, and the top 1% of documents take a quarter of all irrelevant top-10
slots. Hubness is not a dense-specific pathology here; it is worse on the sparse side.

That matters practically, because character-bigram BM25 is the configuration this
repository has been recommending on accuracy grounds since week 1. It wins on nDCG@10 and
it is the more hub-prone of the two.

### What causes it — not established

Two candidate mechanisms were checked on Ko-StrategyQA, and neither explains it:

| Candidate | Correlation with the irrelevant-top-10 count |
|---|---|
| Document length in bigrams | **+0.016** |
| Share of the document's bigrams that appear in ≥10% of queries | **+0.062** |

Long documents are not the cause: the top 50 hubs have the same median length as the
corpus. The "shares surface form with many questions" story fares slightly better — those
14 query-generic bigrams are Korean interrogative endings (`나요`, `무엇`, `어떤`, `었나`),
and the top 50 hubs carry 1.68× the corpus-median share of them — but a correlation of
0.06 explains almost none of the variance. The single worst hub is the Korean page for
*Who's on First?*, whose text is largely question forms, which is suggestive; five
examples are not evidence.

**Cause not established.** Recorded as open rather than attributed to the more appealing
of two weak candidates.

## Figure

![Hybrid weight curves](img/weight-curves-light.png)

Regenerate with `python scripts/plot_weight_curves.py`. The shaded band is the
pre-registered 0.2–0.4 prediction; the marked point is each curve's measured optimum.

## H5 and MIRACL-ko

*(This section is filled in when the MIRACL-ko run completes. Corpus statistics, the
measured cost of running it, and the H5 prediction are already recorded — the prediction
in `PREREGISTRATION.md` section 4b.3, committed before the corpus was retrieved from at
all.)*
