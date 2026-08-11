# Pre-registration — exp01: Korean retrieval, measured

**This file is committed before any experiment is run.**
The git timestamp is the evidence. Predictions here are not edited after results exist.
If a prediction turns out wrong, it stays, and the result section records that it was wrong.

Status: **filled in before running** — see `git log --follow PREREGISTRATION.md`

---

## 1. Question

Do the retrieval findings from a private, small-scale measurement (194 chunks,
12-item golden set, internal Korean business documents) hold on public Korean
retrieval benchmarks?

## 2. Hypotheses

| ID | Prediction | How it is falsified |
|---|---|---|
| H1 | On at least one dataset, char-bigram BM25 alone scores higher (nDCG@10) than a small multilingual dense model alone | Dense ≥ BM25 on every dataset tested |
| H2 | The best hybrid weight for the dense component falls in **0.2–0.4** | Optimum lies at 0.0–0.15 or 0.45–1.0 |
| H3 | The weight/score curve is single-peaked, and score declines monotonically above the optimum | Curve is flat, multi-peaked, or still rising at w=1.0 |
| H4 | Dense retrieval shows hubness — a small number of passages appear in top-k for disproportionately many unrelated queries | Top-k passage frequency is close to uniform |

**H1–H4 are predictions, not conclusions.** Results contradicting them are published unchanged.

## 3. Metrics

- Primary: **nDCG@10**
- Secondary: Recall@10, Recall@100
- Uncertainty: bootstrap confidence intervals, resampling at the **query** level
- Hubness: distribution of per-passage top-k appearance counts (report skew, not a single number)

## 4. Harness validation gate — run before any new measurement

Reproduce a published BM25 nDCG@10 on the same dataset.

- **Pass**: absolute difference ≤ **0.02**
- **Fail**: investigate in this order — tokenizer, score normalization, index settings,
  evaluation protocol (query count, qrel handling)
- **Exactly 0.000 difference**: treat as suspicious, not as success. Verify the two runs
  are not the same code path.

No new measurement is reported until this gate passes. If it never passes, that failure
is itself the published result, with the causes investigated and written down.

## 5. Stopping rules

- Any dataset whose corpus cannot be indexed within available time/disk is **reported as
  not run**, with its measured size. It is not silently dropped.
- If confidence intervals overlap such that the optimal weight cannot be distinguished,
  the result is reported as **"not distinguishable"**. Rankings are not asserted from
  point estimates alone.
- exp01 ends at the measurement report. Rerankers and fine-tuning are separate experiments
  with their own pre-registration.

## 6. What would make me abandon the claim entirely

If BM25 loses to dense on every dataset **and** the hybrid optimum sits at w ≥ 0.5,
the original private finding does not generalize. That is written up as a negative
result, and the private measurement is reinterpreted as corpus-specific.

---

## Results

*(left empty until measurements exist — filled in a separate commit)*
