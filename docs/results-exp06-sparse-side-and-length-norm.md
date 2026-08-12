# exp06 — two open questions closed: the sparse side, and length normalization

Measured 2026-08-12. Raw records: [`results/hybrid.jsonl`](../results/hybrid.jsonl) and
[`results/length_norm.jsonl`](../results/length_norm.jsonl). Registered as H9 and H10 in
[`PREREGISTRATION.md`](../PREREGISTRATION.md) section 4e, committed before either ran.

Both hypotheses target something this repository had left resting on one configuration.
H9 asks whether the hybrid-weight conclusion is a property of Korean retrieval or of the
one sparse tokenizer used throughout. H10 is the only manipulation available for the
hubness that week 3 measured and could not explain.

## H9 — supported. The weight conclusion is not an artefact of the tokenizer

Every weight curve published here fuses **character-bigram** BM25 with `multilingual-e5-large`.
The sweep was re-run with the word-level and character-unigram tokenizers on the sparse
side, changing nothing else.

| Dataset | Sparse side | w = 0 | w = 1 | Best w | Best nDCG@10 | Amplitude | Amplitude ÷ CI | Weights indistinguishable from best |
|---|---|---|---|---|---|---|---|---|
| Ko-StrategyQA | character bigram | 0.56108 | 0.80348 | 0.90 | 0.80562 | 0.24454 | 4.70 | 8 / 21 |
| | **word** | 0.37814 | 0.80348 | **0.95** | 0.80494 | **0.42680** | 8.05 | 5 / 21 |
| | character unigram | 0.30430 | 0.80348 | 1.00 | 0.80348 | 0.49918 | 9.43 | 8 / 21 |
| MIRACL-ko | character bigram | 0.35067 | 0.66486 | 0.80 | 0.70826 | 0.35759 | 4.39 | 10 / 21 |
| | **word** | 0.24541 | 0.66486 | **0.90** | 0.67785 | **0.43244** | 5.14 | 5 / 21 |
| | character unigram | 0.22280 | 0.66486 | 0.75 | 0.69673 | 0.47393 | 5.84 | 10 / 21 |

The prediction was that a weaker sparse side grows the amplitude and does not move the best
weight downward, **on each dataset where an optimum is locatable**. Both datasets where one
is: amplitude grows (0.24454 → 0.42680 and 0.35759 → 0.43244) and the best weight rises
(0.90 → 0.95 and 0.80 → 0.90). **H9 is supported.**

So "the optimum sits at 0.80–0.90" is not a property of character bigrams. Weakening the
sparse side moves it *further* toward pure dense, which is the direction the mechanism
predicts.

### AutoRAGRetrieval, where an optimum cannot be located, goes the other way

| Dataset | Sparse side | w = 0 | w = 1 | Best w | Amplitude | Indistinguishable |
|---|---|---|---|---|---|---|
| AutoRAGRetrieval | character bigram | 0.92345 | 0.81337 | 0.25 | 0.11948 | 19 / 21 |
| | word | 0.79557 | 0.81337 | 0.75 | **0.10993** | 18 / 21 |
| | character unigram | 0.64342 | 0.81337 | 0.55 | 0.23811 | 15 / 21 |

Swapping bigrams for the word tokenizer *shrinks* the amplitude here, which is the opposite
of the prediction. The mechanism explains it: on this dataset the bigram sparse side
(0.92345) is **above** dense (0.81337), so it is not the weak side, and weakening it flattens
the curve toward dense instead of steepening it away from it.

**This is why the scope clause was registered in advance.** Without "on each dataset where
an optimum is locatable", H9 would have been decided by whichever datasets were counted.
AutoRAGRetrieval's optimum is not locatable under any of the three tokenizers — 15 to 19 of
21 weights are indistinguishable from the best — so it was outside the test before the
numbers existed.

### A weaker sparse side makes the weight easier to locate, and the answer less useful

Amplitude ÷ CI width, the locatability statistic from
[`results-week4.md`](results-week4.md), rises as the sparse side weakens: 4.70 → 8.05 → 9.43
on Ko-StrategyQA, 4.39 → 5.14 → 5.84 on MIRACL-ko. The count of indistinguishable weights
tracks it only part of the way — 8 → 5 from bigrams to the word tokenizer on both datasets,
then back to 8 and 10 with character unigrams, whose curve is steep but whose peak sits in
a flat region near w = 1.

The optimum becomes easier to find and what it says is "use almost none of the sparse
side". On Ko-StrategyQA with character unigrams the best weight is **1.00** and the best
score is 0.80348 — exactly dense alone, to five decimals. A locatable optimum is not the
same as a useful hybrid.

## H10 — not falsified, half its prediction fails, and the manipulation does not explain the finding

Week 3 found character-bigram BM25 far more hub-prone than dense and could not explain it:
document length correlates at +0.016, query-generic-bigram share at +0.062. BM25's `b`
controls how much document length is normalized away, so it can be manipulated rather than
correlated. Everything else is held at the values used throughout.

| Dataset | b = 0.0 | 0.25 | 0.5 | 0.75 *(default)* | 1.0 | null p99 |
|---|---|---|---|---|---|---|
| **Ko-StrategyQA** skewness | 58.1313 | 65.1741 | 65.2418 | 63.2997 | 62.2510 | 1.34091 |
| AutoRAGRetrieval | 4.1153 | 3.4819 | 3.9546 | 4.0817 | 3.9930 | 1.07700 |
| MIRACL-ko | **502.5732** | 207.7205 | 198.9236 | 181.4347 | 177.4632 | 26.54792 |

The b = 0.75 column reproduces week 3 exactly on both datasets it measured — 63.29973 and
4.08174 — so the two code paths agree.

The registered test names Ko-StrategyQA and has two clauses:

| | Clause | Ko-StrategyQA | AutoRAG | MIRACL-ko |
|---|---|---|---|---|
| a | skewness at b = 1.0 below b = 0.75 | **holds** | holds | holds |
| b | skewness at b = 0.0 is the highest of the three | **fails — it is the lowest** | holds | holds |

The falsification condition is clause (a) alone — "skewness at b = 1.0 is not below
b = 0.75" — and it is not met on any dataset. **So H10 is not rejected, while half of what
it predicted is wrong on the dataset it names.** Recorded as it stands; the falsification
clause was written narrower than the prediction, which is the third time that pattern has
cost a clean verdict here — see
[`preregistration-checklist.md`](preregistration-checklist.md).

### The verdict matters less than the effect size

On Ko-StrategyQA the observed skewness is **47× the null 99th percentile**, and sweeping `b`
across its entire range moves it by 7.11 — **12%**, non-monotonically, rising before it
falls. Length normalization cannot account for a 47× effect by moving it 12%.

**MIRACL-ko is the exception and it is a large one.** Turning normalization off entirely
(b = 0) nearly triples skewness, 177.46 → 502.57, and the worst document goes from
appearing in 25 top-10 lists it is irrelevant to, to 82. There, length normalization is
clearly doing work. It is doing that work at the default already; moving from 0.75 to 1.0
buys a further 2%.

So the honest statement is narrower than H10's: **length normalization prevents a large
amount of hubness on the largest corpus, and explains almost none of the hubness that
remains.** Turning it off makes things much worse; turning it up does not make them much
better.

### The statistic changes the answer

Skewness is what section 4b.2 registered, and it is non-monotone in `b` on two of the three
datasets. Two other concentration measures from the same records are not:

| Ko-StrategyQA | b = 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---|---|---|---|---|---|
| skewness | 58.1313 | 65.1741 | 65.2418 | 63.2997 | 62.2510 |
| Gini | 0.88158 | 0.82239 | 0.80486 | 0.79334 | **0.78820** |
| worst document's irrelevant top-10 appearances | 419 | 416 | 388 | 334 | **281** |

By Gini and by the worst document, hubness falls monotonically as `b` rises, on both
AutoRAGRetrieval and Ko-StrategyQA. By skewness it does not. Skewness is dominated by the
extreme tail; Gini and the maximum describe the bulk. **Which statistic is registered
decides what this experiment concludes**, and only one of them was registered.

### The accuracy trade-off, paired at the query level

A `b` that removes hubness while destroying accuracy is not a fix, so the registration asks
for this to be visible. Differences against the b = 0.75 default, paired bootstrap, 10,000
resamples:

| Dataset | b = 0.0 | 0.25 | 0.5 | 1.0 |
|---|---|---|---|---|
| Ko-StrategyQA | −0.07465 * | −0.02891 * | −0.01279 * | +0.00386 |
| AutoRAGRetrieval | +0.00405 | +0.00541 | +0.00471 | −0.01044 * |
| MIRACL-ko | −0.00164 | **+0.07017** * | +0.04613 * | −0.05705 * |

`*` marks intervals excluding 0.

The trade-off is different on every dataset:

- **Ko-StrategyQA — none.** b = 1.0 is the least hub-prone by every measure and is not
  distinguishably worse than the default.
- **AutoRAGRetrieval — small.** b = 1.0 costs −0.01044, interval excluding 0.
- **MIRACL-ko — severe, and it cuts both ways.** b = 1.0 minimises skewness and costs
  **0.05705**. Meanwhile **b = 0.25 beats the `bm25s` default by 0.07017** [+0.04469,
  +0.09756] while leaving skewness at 207.7 against 177.5.

That last row is worth stating plainly: on MIRACL-ko the untuned default `b = 0.75` is
**distinguishably worse than b = 0.25 by 0.070 nDCG@10**. No number published anywhere else
in this repository was re-tuned on the back of it — every result here still uses the
`bm25s` defaults, and this is reported because H10 asked for the trade-off to be visible,
not as a tuning recommendation. It does mean that "BM25 with default parameters" is leaving
something on the table on that corpus, in the same way the tokenizer choice was.

## What is still not explained

Three explanations for the hubness of character-bigram BM25 have now failed: document
length (r = +0.016), query-generic-bigram share (r = +0.062), and length normalization as a
manipulation. **Cause not established.** Two failed correlations and one failed
manipulation is the record; it is more useful than a plausible story, and it is left here
rather than replaced by one.

## Reproducing

```bash
# H9 — swap the sparse side, change nothing else
python -m harness.sweep --dataset Ko-StrategyQA \
    --model intfloat/multilingual-e5-large --tokenizer word --out results/hybrid.jsonl

# H10 — sweep b, measure hubness and accuracy at each value
python -m harness.length_norm --dataset Ko-StrategyQA --out results/length_norm.jsonl
```

The MIRACL-ko runs take roughly 15 minutes each on the machine used; the other two are
seconds. `--b` accepts any comma-separated list.
