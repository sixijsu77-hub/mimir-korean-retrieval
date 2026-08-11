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

### Hypotheses

H1–H4 are not yet decided. Nothing dense has been measured in this harness, so no
hypothesis is resolved by the gate. One observation bearing on H1 is recorded in
`docs/results-week1.md` and is explicitly marked as a cross-harness comparison,
not a test.
