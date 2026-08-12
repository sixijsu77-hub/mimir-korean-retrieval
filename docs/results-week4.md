# Week 4 — how many queries does a hybrid weight need?

Measured 2026-08-12. Raw records: [`results/subsample.jsonl`](../results/subsample.jsonl).
Registered as H6 in [`PREREGISTRATION.md`](../PREREGISTRATION.md) section 4c, committed
and pushed before this ran.

**H6 was rejected on its primary condition.** It predicted that 12 queries could not
locate a hybrid weight optimum at all. On two of three datasets, 12 queries locate it
about as well as 400 do. The prediction was wrong, and what replaced it is more useful:
**what decides whether a weight can be located is not the query count on its own, but
the query count relative to how much the weight actually changes the score.**

## The measurement

Per-query nDCG@10 was computed once for all 21 weights, then queries were subsampled
from those columns — so sample size is the only thing that varies. 30 independent
subsamples per size, drawn without replacement. For each subsample: the argmax weight,
and a paired bootstrap (B = 10,000, α = 0.05, uncorrected) of every weight against it.

### Ko-StrategyQA — 592 queries, `multilingual-e5-large`, curve amplitude 0.245

| Queries | argmax median | argmax IQR | argmax range | Weights indistinguishable from best |
|---|---|---|---|---|
| 12 | 0.95 | 0.15 | 0.55 – 1.00 | 9 of 21 (43%) |
| 25 | 0.95 | 0.10 | 0.65 – 1.00 | 8 of 21 (36%) |
| 50 | 0.90 | 0.14 | 0.75 – 1.00 | 6 of 21 (29%) |
| 100 | 0.93 | 0.05 | 0.75 – 1.00 | 4 of 21 (19%) |
| 200 | 0.90 | 0.05 | 0.85 – 1.00 | 4 of 21 (19%) |
| 400 | 0.90 | 0.05 | 0.90 – 1.00 | 4 of 21 (19%) |
| 592 (all) | 0.90 | — | — | 3 of 21 (14%) |

### MIRACL-ko — 213 queries, curve amplitude 0.358

| Queries | argmax median | argmax IQR | argmax range | Indistinguishable |
|---|---|---|---|---|
| 12 | 0.78 | 0.14 | 0.60 – 1.00 | 8 of 21 (38%) |
| 25 | 0.80 | 0.14 | 0.65 – 1.00 | 7 of 21 (33%) |
| 50 | 0.80 | 0.05 | 0.75 – 0.90 | 6 of 21 (31%) |
| 100 | 0.80 | 0.00 | 0.70 – 0.90 | 5 of 21 (24%) |
| 200 | 0.80 | 0.00 | 0.80 – 0.80 | 3 of 21 (14%) |

### AutoRAGRetrieval — 114 queries, curve amplitude 0.120

| Queries | argmax median | argmax IQR | argmax range | Indistinguishable |
|---|---|---|---|---|
| 12 | 0.15 | **0.39** | **0.00 – 0.75** | **21 of 21 (100%)** |
| 25 | 0.28 | 0.31 | 0.00 – 0.75 | 19 of 21 (90%) |
| 50 | 0.30 | 0.14 | 0.00 – 0.65 | 17 of 21 (81%) |
| 100 | 0.25 | 0.04 | 0.25 – 0.65 | 15 of 21 (71%) |
| 114 (all) | 0.25 | — | — | 14 of 21 (67%) |

## H6 — rejected

| Condition at n = 12 | Predicted | Ko-StrategyQA (primary) | MIRACL-ko | AutoRAGRetrieval |
|---|---|---|---|---|
| argmax IQR | ≥ 0.30 | 0.15 | 0.14 | **0.39** |
| Indistinguishable set | ≥ 90% | 43% | 38% | **100%** |
| | | **fails** | fails | holds |

The pre-registration named Ko-StrategyQA as the primary condition, and both criteria
fail there. **H6 is falsified.** It holds on AutoRAGRetrieval, which is reported as a
secondary result and is not what was predicted.

## What the measurement says instead

The three datasets differ by how much the weight matters at all — the amplitude of the
curve from its lowest point to its highest:

| Dataset | Curve amplitude | argmax IQR at n = 12 | Smallest n with the set below one third |
|---|---|---|---|
| MIRACL-ko | 0.358 | 0.14 | 50 |
| Ko-StrategyQA | 0.245 | 0.15 | 50 |
| AutoRAGRetrieval | 0.120 | 0.39 | **never, up to 114** |

Where the weight matters a lot, 12 queries already put the optimum in the right region:
**no 12-query subsample of Ko-StrategyQA produced an argmax below 0.55, and none of
MIRACL-ko below 0.60.** Neither could have produced an optimum in the 0.2–0.4 band that
this repository pre-registered.

Where the weight barely matters, 12 queries produce an argmax anywhere from 0.00 to 0.75
with every weight statistically tied — a number that looks like an answer and is not one.
And AutoRAGRetrieval never resolves, even using all 114 of its queries.

So the practical rule is not "collect N queries". It is:

- **About 50 queries suffice** to place a hybrid weight *when the weight is worth
  tuning* — when moving it changes nDCG@10 by roughly 0.25 or more end to end.
- **When the curve is flat, no realistic query count helps.** The correct output is
  "the weight does not matter here", not a tuned value. AutoRAGRetrieval says this at
  every sample size tested.
- **The check is cheap and comes first**: sweep the weight, look at the amplitude. If
  it is small, stop — there is nothing to tune, and any optimum you report is noise.

## What this does and does not say about the original finding

This experiment was run because the measurement that motivated this repository used a
12-item golden set and reported an optimum near 0.3, which weeks 2 and 3 did not
reproduce.

- It **does not** show that 12 queries are inherently too few. On two datasets they were
  enough.
- It **does** show that on a dataset shaped like AutoRAGRetrieval — small, with questions
  written against the documents, and a shallow weight curve — a 12-query evaluation
  produces an argmax scattered across 0.00–0.75 with every weight tied. A value near 0.3
  is an unremarkable draw from that distribution.
- Whether the original corpus was shaped that way is **not recorded here**, so this
  remains a plausible account rather than a demonstrated one. See
  [`errata.md`](errata.md) for a claim of that kind that was previously overstated.

## Reproducing

```bash
python -m harness.subsample --dataset Ko-StrategyQA \
    --model intfloat/multilingual-e5-large --out results/subsample.jsonl
```

Swap `--dataset` for `MIRACLRetrieval-ko` or `AutoRAGRetrieval`. Every table here derives
from `results/subsample.jsonl`.
