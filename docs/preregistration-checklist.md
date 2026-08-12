# Writing a prediction that can actually be decided

Three hypotheses in this repository were written so that no outcome could decide them.
The measurements ran, the numbers came out, and there was no verdict to record. Each
failure is left in place where it happened — H8 in
[`results-exp03-reranking.md`](results-exp03-reranking.md), H11b in
[`results-exp04-morphology.md`](results-exp04-morphology.md), H12b in
[`results-exp05-corpus-size.md`](results-exp05-corpus-size.md) — and this page is what
they add up to.

It is short on purpose. These are the checks that would have caught all three.

## 1. Is the falsification clause the exact complement of the prediction?

Write both clauses, then ask whether an outcome exists that satisfies neither. If one
does, the hypothesis has a hole and the measurement can land in it.

> **H11b.** Predicted: character bigrams score at least as high as morphological analysis
> on **≥ 2 of 3** datasets. Falsified by: morphology wins **distinguishably on ≥ 2 of 3**.
>
> Measured: bigrams led on 1 of 3, morphology won distinguishably on 1 of 3. Neither
> clause fired. No verdict exists.

The complement of "bigrams win ≥ 2 of 3" is "bigrams win ≤ 1 of 3" — nothing about
significance, nothing about the other side. Adding conditions to the falsification clause
narrows it, and every condition added opens a gap.

## 2. If the measurement repeats, is there a rule for combining the repeats?

Seeds, folds and replicates all need one, decided in advance. Otherwise the verdict is
whatever aggregation is chosen after the numbers are visible.

> **H12b.** Predicted: at 720 documents the paired interval includes 0 or favours BM25.
> Registered with 5 sampling seeds and no rule for combining them.
>
> Measured: 3 seeds satisfied the prediction, 2 satisfied the falsification. Majority,
> pooled, or all-must-hold each give a different verdict, and picking one afterwards is
> picking the answer.

Say it explicitly: *majority of seeds*, or *pooled across seeds*, or *every seed must
hold*. One line, written before the run.

## 3. Does the criterion measure the thing, or a proxy that moves both ways?

A criterion that a good outcome and a bad outcome both satisfy is not a test.

> **H8.** Predicted: reranking compresses the spread between retrievers to under half.
>
> Measured: it held in 5 of 6 conditions — including one where the reranker *lifted* every
> retriever and one where it **cut dense retrieval from 0.80348 to 0.43215**. Both count
> as support, because "spread shrinks" says nothing about direction.

Ask what the prediction is really about. Here it was "the first-stage choice stops
mattering", and the criterion should have required the best retriever's score not to fall.

## 4. Is the falsifying observation one you will actually be able to make?

If falsification needs a measurement that is not in the plan, is not affordable, or is not
defined on the data at hand, the hypothesis is unfalsifiable in practice regardless of how
it reads.

## 5. Are the numbers in the prediction fixed, and is the direction stated?

A threshold decided after seeing the data is not a threshold. State the value, the metric,
the comparison, and which way the difference has to go.

---

None of these three failures was repaired after the fact, and none of the affected
verdicts was quietly rewritten to fit. Recording an undecidable hypothesis as undecidable
costs a result; changing the criterion afterwards costs the credibility of every other
result in the repository.
