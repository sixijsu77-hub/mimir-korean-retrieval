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
