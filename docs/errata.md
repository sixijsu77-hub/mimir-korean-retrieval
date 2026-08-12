# Errata

Mistakes that reached a published commit, what they were, and what changed so they
do not recur. Corrections are made in place in the affected file; this page is the
index, so a reader does not have to reconstruct them from `git log`.

Wrong *predictions* are not errata — they are the output of a pre-registered
experiment and are annotated where they were made. This page is for wrong *facts*.

---

## 2026-08-12 — five values in a README table did not match the raw records

**What.** The "MIRACL-ko / e5-large" row of the hybrid weight table in `README.md`
was written by hand instead of read from `results/hybrid.jsonl`. Five of its seven
cells were wrong:

| Dense weight | Published | Actual | Error |
|---|---|---|---|
| 0.2 | 0.4127 | 0.4129 | 0.0002 |
| 0.4 | 0.4913 | **0.5289** | **0.0376** |
| 0.6 | 0.6027 | **0.6572** | **0.0545** |
| 0.8 | 0.7071 | 0.7083 | 0.0012 |
| 0.9 | 0.7014 | 0.6942 | 0.0072 |

The location of the peak (w = 0.80) and every conclusion drawn from the curve were
unaffected — the two large errors are both below the peak, on the rising side.

**Exposure.** Commit `797fc5f`, corrected in `6f957c9`, one minute later.

**How it was found.** By comparing the table against `results/hybrid.jsonl`. A
verification command had been run in the same working step and its output was not
compared against what had been written — so the check existed and was not read.
That is the actual failure, not the typing.

**What changed.**

- The table is now generated from `results/hybrid.jsonl` rather than typed.
- `scripts/check_reported_numbers.py` extracts every score quoted in `README.md`,
  `PREREGISTRATION.md` and `docs/*.md` and fails if it appears in no raw record.
  Values that are differences or gains are listed separately for a human to confirm
  rather than silently accepted.
- Numbers published by other people — MTEB's and KURE's baselines — previously
  existed only in prose and so could not be checked. They are now recorded with
  their sources in [`results/published_baselines.jsonl`](../results/published_baselines.jsonl)
  and are covered by the same check.

Run it with:

```bash
python scripts/check_reported_numbers.py
```

---

## 2026-08-12 — blamed one model for what turned out to be the dataset

[`results-exp05-corpus-size.md`](results-exp05-corpus-size.md) concluded that the question
worth asking was **"why is `multilingual-e5-large` weak on AutoRAGRetrieval"**. That named
a model when the evidence only supported naming the task, and it would have sent a reader
looking at the wrong thing.

KURE publishes per-task scores for 18 embedding models on these same three datasets. Read
rather than re-run: character-bigram BM25 beats **18 of 18** on AutoRAGRetrieval and **0 of
18** on both Ko-StrategyQA and MIRACL-ko. The best dense model on AutoRAGRetrieval reaches
0.87379 against BM25's 0.92345.

Nothing about `multilingual-e5-large` is unusual here. Corrected in place, with the
18-model table added and the raw values recorded in
[`../results/kure_per_task.jsonl`](../results/kure_per_task.jsonl).

**The check that applies:** an effect seen in one model is a fact about that run. Before
writing a sentence that names the model, ask whether published results for other models on
the same task already answer it — here they did, at no compute cost.

---

## 2026-08-12 — "changes its ranking of the top 10 not at all", which was never measured

[`results-exp05-corpus-size.md`](results-exp05-corpus-size.md) said of the padding
direction that adding 71,280 distractor documents "changes its ranking of the top 10 not
at all" for dense retrieval. **That was inferred from an unchanged nDCG@10 and is false.**

With one relevant document per query, nDCG@10 depends only on that document's rank.
Distractors can enter the top 10, and even take rank 1, without moving the metric. Counted
at 72,000 documents: added documents appear in the dense top 10 for **16–22 of 114
queries**, 0.43 per query, reaching rank 1 in two of the five seeds.

The claim the measurement does support is narrower and had to be checked separately: across
five sizes and five seeds, **no query's dense per-query nDCG@10 changed** — the added
documents never outrank a relevant one. The rank-1 cases fall among the 7 of 114 queries
where dense already placed the relevant document outside the top 10.

**Why it mattered.** An identical score to five decimals has two explanations — complete
separation, or the added documents never reaching the index at all — and nDCG@10 cannot
tell them apart. The harness had no field counting whether a distractor was ever ranked,
so the wiring was unproven in exactly the way `CLAUDE.md` rule 10 describes. `harness/
corpus_size.py` now records `distractor_reach` for both retrievers on every padded run.

**The check that applies:** when a metric is unchanged, say what was held constant and
count it. "Nothing changed" is a measurement, not an inference from a summary statistic.

---

## 2026-08-12 — a version-trace table with rows that were not read

A table tracing MTEB's Korean handling across versions appeared in
[`baselines.md`](baselines.md), in [`results-week1.md`](results-week1.md) and in the
upstream issue. Parts of it were wrong, and the reason is worse than the error.

| Where | Said | Actually |
|---|---|---|
| the upstream issue | `_unicode_tokenize` absent at 2.14.9, 2.15.0, 2.16.0 | present at all three |
| `baselines.md`, `results-week1.md` | `kor` → character unigram at 2.18.16 | first at **2.18.12**; absent through 2.18.11 |
| `baselines.md` | `0_3_0` introduced at 2.15.0 | present at **2.14.9** |
| the upstream issue | character unigram first exists at 2.18.12 | asserted before 2.18.9–2.18.11 were checked; they were checked afterwards and it holds |

**How it happened.** The tags 2.14.9, 2.15.0 and 2.16.0 were opened to read one thing —
the `ModelMeta` revision string — and the other columns of the row were filled in from
what neighbouring versions did. The issue text then said "Every row was read at the tag
named", which was not true of those rows. Separately, "first exists at 2.18.12" was
written without opening 2.18.9, 2.18.10 or 2.18.11, which exist.

**What changed.** All thirteen tags were re-read with every column checked at every tag:
2.12.7, 2.12.30, 2.14.0, 2.14.9, 2.15.0, 2.15.4, 2.16.0, 2.17.0, 2.18.0, 2.18.8, 2.18.11,
2.18.12, 2.18.16. The corrected trace is in [`baselines.md`](baselines.md) and the
upstream issue body was edited to match.

**The argument was not affected, and is now stronger.** At 2.12.30 there is no language
table, no `_unicode_tokenize` and no `freq_threshold` — none of the three ingredients the
published AutoRAGRetrieval score requires. All three arrive together at 2.14.9, and `kor`
routing at 2.18.12.

**The check that applies:** a table cell is a claim. Opening a file to read one column
does not verify the others, and a row assembled from neighbouring versions is inference,
not a reading. Either check every cell or say which ones were checked.

---

## 2026-08-12 — an unsupported claim about how AutoRAGRetrieval was built

`PREREGISTRATION.md` said, as part of the caveat weakening H1, that AutoRAGRetrieval's
"questions were generated against the documents". **That was never checked.** The
dataset's HuggingFace card contains no construction notes, and no source stating it was
ever read. It was an assumption about why lexical matching does well there, written as a
fact, and it did work in the argument — it was one of the two reasons given for
discounting H1.

It is also not supported by measurement. Query-to-relevant-document character-bigram
coverage, above a random-document null, is +0.420 on AutoRAGRetrieval and **+0.443 on
MIRACL-ko** — highest on the dataset where BM25 does *worst*.

Withdrawn in place, with the measurement recorded in
[`results-exp05-corpus-size.md`](results-exp05-corpus-size.md).

**This is the second unsupported provenance claim on this page.** The first concerned the
private corpus. Both were inferences about how a dataset was made, stated as facts,
supporting a conclusion. The check that applies: if a sentence describes how a corpus was
constructed and no cited source or measurement in this repository establishes it, it does
not go in.

---

## 2026-08-12 — an unsupported claim about the private corpus

`docs/results-week3.md` said the private measurement "was made on long internal
documents". Nothing in this repository records that corpus's document length; the
only recorded facts are its 194 chunks and 12-item golden set. The sentence was an
inference presented as a fact, and it did real work in the argument — it was the
bridge from "these three public datasets differ by document length" to "so that is
why the private result disagreed".

Corrected in place. The mechanism that document length separates the three *public*
datasets was pre-registered as H5 and held; the extension of it to the private corpus
is now marked as a hypothesis rather than a finding.

---

## 2026-08-12 — `docs/baselines.md` named the wrong tokenizer, before measuring

Not an erratum in the strict sense — it was a prediction, made before any
measurement and recorded as such — but it stated a fact about someone else's
published configuration, and that fact was wrong. `docs/baselines.md` said both
published Korean BM25 numbers came from the word-level tokenizer. That holds for
Ko-StrategyQA and not for AutoRAGRetrieval, whose published score is reproduced by
character unigrams.

The original text is left unedited with a correction box at the top of the page,
rather than rewritten. The measurement that settled it is in
[`results-week1.md`](results-week1.md).
