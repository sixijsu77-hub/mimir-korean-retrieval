# Published baselines — what this repository will be graded against

The harness gate in [`PREREGISTRATION.md`](../PREREGISTRATION.md) says no new
measurement is reported until a **published** BM25 nDCG@10 is reproduced within
0.02 on the same dataset. That gate is meaningless without a specific published
number, from a specific configuration, on a specific dataset revision.

This page records what was found, where, and — more importantly — the exact
configuration that produced it. Compiled 2026-08-12. No retrieval has been run
here yet; nothing on this page is a MIMIR result.

## The reproduction target

MTEB publishes an official BM25 baseline (`mteb/baseline-bm25s`) with per-task
result files. These are the Korean ones:

| Task | Split | Subset | nDCG@10 | Recall@10 | Recall@100 | mteb version | Result folder |
|---|---|---|---|---|---|---|---|
| **AutoRAGRetrieval** | test | default | **0.65022** | 0.82456 | 0.99123 | 2.12.30 | `0_3_0` |
| Ko-StrategyQA | dev | default | 0.37808 | 0.46236 | 0.57934 | 2.10.8 | `0_1_10` |
| MIRACLRetrieval (ko) | dev | ko | 0.24521 | 0.28106 | 0.41032 | 2.12.7 | `0_1_10` |
| MrTidyRetrieval (korean) | test | korean | 0.19162 | 0.23040 | 0.34402 | 2.12.30 | `0_3_0` |
| PublicHealthQA (korean) | test | korean | 0.46799 | 0.64935 | 1.00000 | 2.10.8 | `0_1_10` |

Source: [embeddings-benchmark/results](https://github.com/embeddings-benchmark/results),
path `results/mteb__baseline-bm25s/<revision>/<task>.json`. The AutoRAGRetrieval
run is stamped `dataset_revision: fd7df84ac089bbec763b1c6bb1b56e985df5cc5c` and
`date: 2026-07-01T07:19:19Z`, and that dataset revision is the one pinned in
[`docs/datasets.md`](datasets.md).

**AutoRAGRetrieval at 0.65022 is the primary gate target.** It is the smallest
corpus (720 documents), it runs in seconds, its dataset revision is pinned and
verified, and its published run used the most recent MTEB version of the five.

> **Update, 2026-08-12 — one claim on this page turned out to be wrong.**
> This document was written before any measurement and states that both published
> numbers come from the word-level tokenizer. That holds for Ko-StrategyQA but
> **not** for AutoRAGRetrieval, whose published number is reproduced by
> **character unigrams plus a frequency-stopword step** (0.65022, exactly), not by the
> word-level tokenizer (0.79557). The measurement is in
> [`results-week1.md`](results-week1.md).
> The original text below is left unedited; the error is part of the record.
>
> **Second update, same day.** Character unigrams alone give 0.64342. MTEB additionally
> removes tokens present in ≥ 90% of documents whenever no named stopword list applies to
> the language, Korean included, and that step appears in no published result file.
> Applying it makes the difference 0.00000.

## The configuration that produced those numbers

This is the part that decides whether a reproduction attempt can succeed, and it
is not stated on any leaderboard page. It was read out of the MTEB source at the
versions recorded in the result files.

At mteb 2.12.30 (`mteb/models/model_implementations/bm25.py`), the BM25 baseline is:

```python
stopwords: str = "en"
stemmer_language: str | None = "english"

corpus_texts = ["\n".join([doc.get("title", ""), doc["text"]]) for doc in corpus]
bm25s.tokenize(texts, stopwords=self.stopwords, stemmer=self.stemmer)
bm25s.BM25()          # method="lucene", k1=1.5, b=0.75
```

Which means, applied to Korean:

- **Tokenizer: word-level, not character n-gram.** `bm25s.tokenize` defaults to
  scikit-learn's `CountVectorizer` pattern, `r"(?u)\b\w\w+\b"`, lowercased.
  Hangul matches `\w`, so this splits on whitespace and punctuation into eojeol,
  and **drops every single-syllable token** — the `\w\w+` requires two or more
  word characters. Verified: `지방은행의 시중은행 전환 시 자본금 요건은?` tokenizes
  to `['지방은행의', '시중은행', '전환', '자본금', '요건은']`, with the
  single-syllable `시` discarded.
- **English stopwords and the English Snowball stemmer are applied to Korean
  text.** Both are near-no-ops on Hangul, but they are in the code path.
- **BM25 parameters are the bm25s defaults**: Lucene variant, k1 = 1.5, b = 0.75.
- **Documents are indexed as `title + "\n" + text`.** For AutoRAGRetrieval every
  title is empty, so each document is indexed with a leading newline.

### A version trap worth knowing about

MTEB has since added language-aware tokenization, and Korean now maps to
**character unigrams**:

```python
# mteb >= 2.18.x
"kor": (None, None, "char"),

def _unicode_tokenize(text: str) -> list[str]:
    return list(unicodedata.normalize("NFKC", text).lower().replace(" ", ""))
```

Tracing when this appeared:

Read at tags 2.12.7, 2.12.30, 2.14.0, 2.14.9, 2.15.0, 2.15.4, 2.16.0, 2.17.0, 2.18.0,
2.18.8, 2.18.11, 2.18.12 and 2.18.16 — every column below checked at every tag named,
not inferred from neighbours.

| mteb version | revision | `_ISO3_TO_LANG` | `_unicode_tokenize` | `freq_threshold` | `kor` | Korean handling |
|---|---|---|---|---|---|---|
| 2.10.8 – 2.14.0 | `0_1_10` | absent | absent | absent | — | English stopwords + English stemmer, word-level split |
| 2.14.9 – 2.18.11 | `0_3_0` | present | present | 0.9 | no | word-level split, frequency stopwords |
| 2.18.12 – 2.18.16 | `0_3_0` | present | present | 0.9 | `(None, None, "char")` | character unigram, frequency stopwords |

Four things changed at once at **2.14.9**: the revision string, the language table,
`_unicode_tokenize` and `freq_threshold`. Korean routing to characters came later, at
**2.18.12** — `kor` is absent through 2.18.11.

So **re-running `mteb/baseline-bm25s` on Korean with a current MTEB would not
reproduce 0.65022** — it would tokenize differently. Anyone comparing against
these published numbers has to pin the version, not just the dataset.

One loose end is recorded rather than guessed: the AutoRAGRetrieval result file
sits in the `0_3_0` folder but records `mteb_version: 2.12.30`, and `0_3_0` was
not introduced until 2.14.9. The folder name tracks the bm25s *library* version
(0.1.10 → 2024-07-10, 0.3.0 → 2026-05-06), not the MTEB version, so the two are
not required to agree; the file's own commit message mentions a rebase. **Which
of the two code paths produced 0.65022 is not confirmed.** It matters little in
practice — neither 2.12.30 nor 2.14.9 gives Korean a character tokenizer, and
they differ only by an English stopword list and an English stemmer, both of
which should be near-inert on Hangul. That "should" is a prediction, and it is
cheap to settle: run both configurations and see which lands on 0.65022. That is
part of the week-1 harness work.

> **Settled, 2026-08-12.** Neither. Both candidate configurations give 0.79557,
> identical to five decimals — so the English stopword/stemmer prediction was
> correct (near-inert) but irrelevant. The published 0.65022 is reproduced by the
> **character-unigram** path *plus the frequency-stopword step*, which the table above
> places at MTEB **2.18.12** and later. The `mteb_version: 2.12.30` recorded in the
> result file is therefore inconsistent with the tokenizer that produced it; the `0_3_0`
> folder name is the more reliable signal. See [`results-week1.md`](results-week1.md).

## Dense cross-check

KURE publishes per-task results for 18 embedding models. There is **no BM25 row**
in that leaderboard, but the dense numbers give a second, independent way to
check the harness — reproducing a published *dense* score validates the same
indexing, scoring and nDCG code that the BM25 gate exercises.

`intfloat/multilingual-e5-large`, mteb 1.19.4:

| Task | Split | nDCG@10 | Recall@10 | Recall@100 |
|---|---|---|---|---|
| AutoRAGRetrieval | test | 0.81337 | 0.93860 | 1.00000 |
| Ko-StrategyQA | dev | 0.80348 | 0.85400 | 0.91833 |
| MIRACLRetrieval (ko) | dev | 0.66486 | 0.75212 | 0.93362 |

Source: [nlpai-lab/KURE](https://github.com/nlpai-lab/KURE),
`eval/results/intfloat/multilingual-e5-large/…/`.

Note what these say about hypothesis **H1**, which predicts BM25 beating a small
multilingual dense model on at least one dataset. On all three public sets, the
published dense scores are far above the published BM25 scores — 0.813 vs 0.650
on AutoRAGRetrieval, 0.803 vs 0.378 on Ko-StrategyQA, 0.665 vs 0.245 on MIRACL.
Two things are worth keeping straight about that:

- `multilingual-e5-large` is a 560 M-parameter model, not the *small* model H1
  refers to. H1 is about small multilingual embedding models, so these rows do
  not test it directly.
- The BM25 side of that comparison is the word-level tokenizer described above,
  which drops every single-syllable Korean token. A character n-gram BM25 is a
  different — and unpublished — number.

Neither point rescues H1, and neither is an excuse. They are the two variables
that have to be controlled before the comparison means anything. If H1 fails
once they are, it is published as failed, per `PREREGISTRATION.md`.

## Also found

**Korean-MTEB-Retrieval-Evaluators** ([BM-K](https://github.com/BM-K/Korean-MTEB-Retrieval-Evaluators))
publishes a BM25 row aggregated across six Korean MTEB tasks (Ko-StrategyQA,
AutoRAGRetrieval, MIRACLRetrieval, PublicHealthQA, BelebeleRetrieval,
MultiLongDocRetrieval), using [bm25s](https://github.com/xhluca/bm25s):

| | Avg. NDCG | NDCG@1 | NDCG@3 | NDCG@5 | NDCG@10 |
|---|---|---|---|---|---|
| BM25 | 0.4714 | 0.4194 | 0.4708 | 0.4886 | 0.5071 |

This is an **aggregate**, not per-dataset, and the repository publishes no
per-task breakdown and no tokenizer or parameter settings. It is usable as a
sanity check on the average, not as a gate target.

## Not found

Recorded so the absence is not mistaken for an oversight:

- **No per-dataset BM25 number on the KURE / MTEB-ko leaderboard.** The
  leaderboard has no BM25 baseline row at all; its aggregate nDCG@10 figures
  (e.g. KURE-v1 at 0.69473) cover dense models only.
- **No per-dataset BM25 breakdown from BM-K.** Aggregate only, as above.
- **No usable numbers from AutoRAG's own BM25 tokenizer benchmark.** The
  write-up ("Making benchmark of different tokenizer in BM25") reports that the
  `okt` tokenizer performed best and whitespace worst, but it evaluates the
  Allganize Korean RAG leaderboard data — not AutoRAGRetrieval — and its result
  tables are images, so no figures could be extracted. Not a usable target.
- **No published character-n-gram BM25 number on any of these datasets.** Every
  published Korean BM25 figure found uses word-level or morphological
  tokenization. This is the gap exp01 measures — but only after the harness
  reproduces a published number first.

## What this fixes for week 1

1. Reproduce **AutoRAGRetrieval, BM25, nDCG@10 = 0.65022**, dataset revision
   `fd7df84a…`, split `test`, using bm25s with the word-level tokenizer, Lucene
   BM25, k1 = 1.5, b = 0.75, documents indexed as `title + "\n" + text`.
   Pass if the absolute difference is ≤ 0.02.
   *(The word-level tokenizer named here was the wrong guess — see the update at
   the top of this page. Everything else in this item held.)*
2. If it differs, the pre-registered order of suspicion applies: tokenizer,
   then normalization, then index settings, then evaluation protocol. The two
   candidate stopword/stemmer configurations above are the first thing to test.
3. Exactly 0.00000 difference is treated as suspicious, not as success.
4. Only after that gate does any character-bigram, dense, or hybrid number get
   reported.
