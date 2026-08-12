# Pre-registration — exp01: Korean retrieval, measured

**This file is committed before any experiment is run.**
The git timestamp is the evidence. Predictions here are not edited after results exist.
If a prediction turns out wrong, it stays, and the result section records that it was wrong.

Status: **filled in before running** — see `git log --follow PREREGISTRATION.md`
Amendments are listed at the bottom, with dates and reasons. Every amendment so
far predates any retrieval run.

---

## 1. Question

Do the retrieval findings from a private, small-scale measurement (194 chunks,
12-item golden set, internal Korean business documents) hold on public Korean
retrieval benchmarks?

## 2. Hypotheses

| ID | Prediction | How it is falsified |
|---|---|---|
| H1 | On at least one dataset, char-bigram BM25 alone scores higher (nDCG@10) than `intfloat/multilingual-e5-small` alone | Dense ≥ BM25 on every dataset tested |
| H2 | The best hybrid weight for the dense component falls in **0.2–0.4** | Optimum lies at 0.0–0.15 or 0.45–1.0 |
| H3 | The weight/score curve is single-peaked, and score declines monotonically above the optimum | Curve is flat, multi-peaked, or still rising at w=1.0 |
| H4 | Dense retrieval shows hubness — a small number of passages appear in top-k for disproportionately many unrelated queries | Top-k passage frequency is close to uniform |

**H1–H4 are predictions, not conclusions.** Results contradicting them are published unchanged.

## 2b. Fixed experimental configuration

Fixed here, before any retrieval runs, so that none of it can be chosen after
seeing a result.

**Datasets** — AutoRAGRetrieval (test), Ko-StrategyQA (dev), MIRACLRetrieval ko
(dev), at the revisions recorded in `docs/datasets.md`.

**Sparse tokenizers** — three, all over `title + "\n" + text`:

| | Why it is in |
|---|---|
| Word-level (`bm25s` default, `(?u)\b\w\w+\b`) | the tokenizer behind every published Korean BM25 number found |
| Character unigram | what current MTEB uses for Korean |
| Character bigram | the condition the private measurement used; no published Korean number exists for it |

BM25 parameters are the `bm25s` defaults throughout: Lucene variant, k1 = 1.5,
b = 0.75. Not tuned. Tuning them would make the reproduction gate meaningless.

**Dense models** — two:

| Model | Params | Role |
|---|---|---|
| `intfloat/multilingual-e5-small` | 118 M | the "small multilingual model" of H1 |
| `intfloat/multilingual-e5-large` | 560 M | contrast, and a second reproduction check against KURE's published 0.81337 on AutoRAGRetrieval |

Both use the `query: ` / `passage: ` prefixes the e5 family requires.

**Hybrid** — score-level fusion over the **full corpus**, not over a truncated
candidate list, so no candidate-set artefact enters the weight curve. Dense
weight swept 0.00 to 1.00 in steps of 0.05.

**Score normalisation** — per query, before blending. BM25 scores are unbounded
positive and cosine similarity is bounded, so an un-normalised weight has no
meaning, and the location of the optimum depends on the choice:

- **Primary: min-max per query.** Reported as the headline weight curve.
- **Robustness: z-score per query.** Reported alongside.
- If the two disagree about where the optimum lies, that disagreement is
  reported as the result — the optimal weight is then a property of the
  normalisation, not of Korean retrieval.

**Search** — exact, brute-force. No approximate index (FAISS, HNSW). With 213
queries over 1.49 M documents the exhaustive computation is under a second on
the GPU used, and an ANN index would fold its own recall loss into the
measurement.

## 3. Metrics

- Primary: **nDCG@10**
- Secondary: Recall@10, Recall@100
- Uncertainty: bootstrap confidence intervals, resampling at the **query** level
- Hubness: distribution of per-passage top-k appearance counts (report skew, not a single number)

## 4. Harness validation gate — run before any new measurement

Reproduce MTEB's published BM25 baseline (`mteb/baseline-bm25s`) on **two**
datasets. Both must pass. One dataset can be hit by luck; two of different
shape cannot.

| Dataset | Split | Published nDCG@10 | Source |
|---|---|---|---|
| AutoRAGRetrieval | test | **0.65022** | `results/mteb__baseline-bm25s/0_3_0/AutoRAGRetrieval.json` |
| Ko-StrategyQA | dev | **0.37808** | `results/mteb__baseline-bm25s/0_1_10/Ko-StrategyQA.json` |

in [embeddings-benchmark/results](https://github.com/embeddings-benchmark/results).
The configuration that produced these numbers, including the tokenizer, is
documented in `docs/baselines.md`; reproduction uses that configuration, not a
better one.

MIRACLRetrieval ko (published 0.24521) is **not** part of the gate. It is
attempted, and whether it reproduces is reported either way.

- **Pass**: absolute difference ≤ **0.02** on both gate datasets.
- **Fail**: investigate in this order — tokenizer, score normalization, index settings,
  evaluation protocol (query count, qrel handling).
- **Exactly 0.000 difference**: treat as suspicious, not as success. Verify the two runs
  are not the same code path.

On AutoRAGRetrieval the tolerance is tight, not generous: with 114 queries and
exactly one positive each, nDCG@10 moves in discrete steps, and roughly six
queries swapping between rank 1 and rank 2 already exceeds 0.02.

The two datasets differ in which MTEB version produced their published number
(2.12.30 and 2.10.8), so a single configuration may not clear both. If that
happens, the version difference is reported as the cause only after it has been
demonstrated, not assumed.

No new measurement is reported until this gate passes. If it never passes, that failure
is itself the published result, with the causes investigated and written down.

## 4b. Week-3 additions — registered before the measurements they govern

Added 2026-08-12, after week 2 and **before any week-3 measurement was run**. Week 2
reported that hybrid weights could not be distinguished on AutoRAGRetrieval using
overlapping marginal intervals, and flagged that a paired test would be more powerful.
The paired test is specified here, with its decision rule fixed, rather than added
after seeing which weights it happens to separate. `git log` orders this against
`results/`.

### 4b.1 Paired difference test for hybrid weights

The week-2 test compared two marginal bootstrap intervals, which is conservative
because every weight is scored on the same queries. The paired version:

- **Statistic**: per-query nDCG@10 difference between two weights,
  `d_i = s_i(w_a) − s_i(w_b)`.
- **Bootstrap**: resample queries with replacement, B = 10,000, seed 0; percentile
  interval on `mean(d)`.
- **Distinguishable**: the interval excludes 0.
- **Comparison set**: every weight against the point-estimate best — 20 comparisons
  per curve. The **primary** result uses a **Bonferroni-corrected** interval
  (α = 0.05 / 20, i.e. 99.75%). The uncorrected 95% version is reported alongside.
  Not correcting would make the indistinguishable set smaller and the claims
  stronger, which is the wrong direction for this repository.
- **Known bias**: the reference weight is the argmax of the same data, which favours
  it. The corrected set is what gets reported as the answer.
- **H2 is re-evaluated with this test.** H2 survives if any weight in 0.2–0.4 lies in
  the corrected indistinguishable set. The week-2 verdict stands unless this test
  overturns it, and if it does, both verdicts are shown.

### 4b.2 H4 — hubness, operationalized

H4 as written ("a small number of passages appear in top-k for disproportionately many
unrelated queries") has no threshold. Fixing one now.

- For each document `d`, count `N10(d)` = queries whose top-10 contains `d`, and
  **`N10_irr(d)`** = queries whose top-10 contains `d` **and** for which `d` has
  relevance 0. `N10_irr` is the primary quantity: a document legitimately retrieved
  for its own relevant query is not a hub.
- **Primary statistic**: skewness of `N10_irr` over all documents.
- **Null model**: for each query draw 10 documents uniformly without replacement from
  the corpus, recompute the statistic; 1,000 replicates, seed 0. This accounts for the
  counts being sparse (expected `N10` is 1.58 on AutoRAGRetrieval and 0.64 on
  Ko-StrategyQA), where raw skewness is otherwise hard to interpret.
- **H4 supported** if the observed skewness for the dense method exceeds the **99th
  percentile** of the null distribution.
- **Also reported**, as magnitude rather than as the test: max `N10_irr`, the share of
  irrelevant top-10 slots taken by the top 1% of documents, the Gini coefficient of
  `N10_irr`, and the number of documents never retrieved.
- **Contrast**: the same statistics for character-bigram BM25 on the same queries. The
  original observation was about a dense model specifically, so dense-vs-sparse is
  reported even though H4 does not name it.

### 4b.3 H5 — a new prediction, for a dataset not yet touched

| ID | Prediction | How it is falsified |
|---|---|---|
| H5 | On MIRACL-ko (dev, 213 queries, 1,486,752 documents), the hybrid optimum sits at dense weight **≥ 0.5**, and `multilingual-e5-large` alone scores higher than character-bigram BM25 alone | Optimum below 0.5, or BM25 ≥ dense |

Stated mechanism, so that a wrong prediction is informative: week 2 found this pattern
on Ko-StrategyQA, whose passages are short Wikipedia text that the encoders barely
truncate (1.5% over 512 tokens). MIRACL-ko has the same profile (mean 175 characters).
AutoRAGRetrieval, the one dataset where the pattern did not hold, truncates 36.8% of
its documents. If document length is what drives the difference, MIRACL-ko should
behave like Ko-StrategyQA.

**H5 is registered before MIRACL-ko has been retrieved from at all.** No BM25, dense or
hybrid number exists for it at the time of writing — only the corpus statistics in
`docs/datasets.md`.

### 4b.4 MIRACL-ko execution

Encoding throughput, BM25 index build time and peak memory are **measured first** and
reported whether or not the full run completes. If it cannot complete, section 5's
stopping rule applies: reported as not run, with the measured numbers, not silently
dropped. Published comparisons available for it — BM25 0.24521, KURE
`multilingual-e5-large` 0.66486 — are reproduction checks, not gates.

## 4c. How many queries does a hybrid weight need? — registered before running

Added 2026-08-12, **before this measurement was run**. Weeks 2 and 3 found that on
AutoRAGRetrieval (114 queries) no weight could be distinguished from any other, while
Ko-StrategyQA (592) and MIRACL-ko (213) could locate an optimum. The measurement that
motivated this repository used **12** queries. This asks the question directly instead
of leaving it as an aside.

### Procedure

Per-query nDCG@10 is computed once for all 21 weights on the full query set, then
subsamples are drawn from those columns — so subsampling changes only which queries
are scored, never how.

- **Primary condition**: Ko-StrategyQA, `multilingual-e5-large`, character-bigram
  sparse side, min-max normalization. Repeated on MIRACL-ko and AutoRAGRetrieval.
- **Sizes**: n ∈ {12, 25, 50, 100, 200, 400, all}.
- **Replicates**: 30 independent subsamples per size, drawn without replacement, seed 0.
- **Per subsample**: the argmax weight, and a paired bootstrap of every other weight
  against it (B = 10,000, α = 0.05, **uncorrected**) giving the set of weights that
  cannot be distinguished from the best.

Uncorrected is deliberate. Correction would enlarge the indistinguishable set and make
"the optimum is not locatable" easier to conclude. The permissive test biases *against*
the prediction below, so finding the optimum unlocatable under it is the stronger result.

### Reported

- Distribution of the argmax across replicates: median, interquartile range, full range.
- Median size of the indistinguishable set, per n.
- Smallest n at which the median indistinguishable set falls below one third of the 21
  weights. Descriptive; no threshold is attached to it in advance.

### H6

| ID | Prediction | How it is falsified |
|---|---|---|
| H6 | At n = 12 the optimum is not locatable: the interquartile range of the argmax across replicates is **≥ 0.30**, and the median indistinguishable set covers **≥ 90%** of the 21 weights | IQR below 0.30, or the median indistinguishable set below 90% |

If H6 holds, the reading is that a 12-query evaluation cannot support any statement
about where a hybrid weight should sit — including the one this repository was built
to test. That would explain the original finding without rescuing it, and it is a
result about evaluation design rather than about Korean retrieval.

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

## Amendment log

Amendments are only legitimate before results exist. Each entry records what
changed and why, so a reader can check the ordering against `git log` rather
than taking it on trust.

**2026-08-12 (week 4) — H6 added, before the measurement it governs.** Section 4c.
Asks how many queries are needed before a hybrid weight optimum can be located at all.
No subsampling had been run at the time of this commit. Verdicts for H1–H5 are not
touched.

**2026-08-12 (week 3) — paired test, hubness threshold, and H5 added.** Section 4b in
full. Three things are being fixed *before* the measurements they govern: the paired
difference test flagged as missing in week 2, an operational threshold for H4, and a
new prediction H5 for MIRACL-ko, which has not been retrieved from at all at the time
of this commit. H1–H3 verdicts from week 2 are **not** touched. The commit preceding
this one contains the week-2 results; the commit following it will contain the week-3
measurements, and `git log` is what orders them.

**2026-08-12 — specifics fixed before the first run.** The original version named
neither the gate dataset, the target number, the models, the tokenizers, nor the
score normalisation. Leaving those open would have allowed choosing them after
seeing results, which is the failure this document exists to prevent. Added:
section 2b in full; the two named gate targets and their published values in
section 4; and the model name in H1. No retrieval had been run at the time of
this amendment — the repository contained no retrieval code at all, and
`results/` held only the dataset inventory.

---

## Results

### Harness validation gate — passed, 2026-08-12

| Dataset | Tokenizer | Measured nDCG@10 | Published | Difference | Verdict |
|---|---|---|---|---|---|
| AutoRAGRetrieval (test) | character unigram | 0.64342 | 0.65022 | −0.00680 | pass |
| Ko-StrategyQA (dev) | word | 0.37807 | 0.37808 | −0.00001 | pass |

Both inside the ±0.02 pre-registered tolerance; neither exactly zero, so the
suspicion check does not fire.

The gate did not pass on the first attempt, and the reason became the week's
finding: **the two published numbers were produced with different tokenizers.**
`docs/baselines.md`, written before any measurement, predicted the word-level
tokenizer for both. That was right for Ko-StrategyQA and wrong for
AutoRAGRetrieval. The wrong prediction is left in place and annotated rather than
edited away.

The −0.00680 residual on AutoRAGRetrieval is **not explained**. Candidates not
yet checked are listed in `docs/results-week1.md`.

Full measurements, caveats and reproduction commands:
[`docs/results-week1.md`](docs/results-week1.md).
Raw records: `results/gate_bm25.jsonl`.

### Hypotheses — decided 2026-08-12 for H1–H3

Measured on AutoRAGRetrieval and Ko-StrategyQA with `multilingual-e5-small` and
`multilingual-e5-large`. Full tables, curves and caveats:
[`docs/results-week2.md`](docs/results-week2.md). Raw records: `results/hybrid.jsonl`.

| | Verdict | |
|---|---|---|
| H1 | **supported** | Character-bigram BM25 (0.92345) beats `multilingual-e5-small` (0.80068) on AutoRAGRetrieval with non-overlapping intervals. Dense wins decisively on Ko-StrategyQA, but the falsification condition required dense to win *everywhere*. |
| H2 | **rejected** | Predicted optimum 0.2–0.4. On Ko-StrategyQA the optimum is at **0.90** for both models, and 0.2–0.4 is distinguishable from it. On AutoRAGRetrieval 19 of 21 weights are indistinguishable from the best, so the optimum cannot be located and is reported as **not distinguishable** rather than read off the point estimate. |
| H3 | **rejected on one dataset, shape holds on the other** | AutoRAGRetrieval is flat within intervals, which is a pre-registered falsification condition. Ko-StrategyQA is single-peaked and declines after the peak — the predicted shape — but peaks at 0.90, not near 0.30. |
| H4 | **supported, but its premise is not** | Dense skewness exceeds the uniform-random null's 99th percentile on all three datasets. Character-bigram BM25 exceeds it far more (63.3 vs 4.3–8.2 on Ko-StrategyQA; one document in the top 10 of 334 of 592 queries it is not relevant to). The behaviour H4 describes is real and is *worse* on the sparse side, which is the opposite of the observation that motivated it. Cause not established: neither document length (r = +0.016) nor share of query-generic bigrams (r = +0.062) explains it. |
| H6 | **rejected** | Predicted that 12 queries could not locate a hybrid optimum. On the primary condition (Ko-StrategyQA) the argmax IQR at n=12 is 0.15 (predicted ≥ 0.30) and the indistinguishable set is 43% (predicted ≥ 90%). Both criteria fail; MIRACL-ko agrees. H6 holds only on AutoRAGRetrieval (IQR 0.39, 100% tied), which was a secondary condition. What the measurement supports instead is that locatability tracks the curve's amplitude, not the query count alone — about 50 queries suffice when moving the weight changes nDCG@10 by ≳0.25, and no tested count suffices when it does not. [`docs/results-week4.md`](docs/results-week4.md) |
| H5 | **supported, mechanism included** | Registered before MIRACL-ko had been retrieved from at all. Optimum at 0.80 (min-max) / 0.90 (z-score), both ≥ 0.5; `multilingual-e5-large` 0.66486 beats character-bigram BM25 0.35067 with non-overlapping intervals. The stated mechanism — that document length and truncation separate the datasets — also held: MIRACL-ko behaved like Ko-StrategyQA, not like the 36.8%-truncated AutoRAGRetrieval. |

**H1 carries a caveat that weakens it.** It survives only on AutoRAGRetrieval, which
is also where 36.8% of documents exceed the 512-token limit both dense models impose,
and where the questions were generated against the documents. Both favour BM25.

**The abandonment condition in section 6 is half met.** BM25 does not lose on every
dataset, but the hybrid optimum sits well above 0.5 where it could be measured. The
reading recorded in `docs/results-week2.md` is that the private measurement's weight
finding is corpus-specific and does not generalize.

### Second reproduction, on the dense side

Not planned as a gate, but it happened: `multilingual-e5-large` reproduces KURE's
published nDCG@10 exactly — 0.81337 on AutoRAGRetrieval and 0.80348 on Ko-StrategyQA,
both to five decimals. The exactly-zero difference is addressed against the suspicion
rule in `docs/results-week2.md`; MTEB was never installed here, and the metrics are
independently implemented and hand-verified.
