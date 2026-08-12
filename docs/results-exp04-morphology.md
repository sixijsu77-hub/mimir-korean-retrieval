# exp04 — character bigrams against Korean morphological analysis

Measured 2026-08-12. Raw records: [`results/gate_bm25.jsonl`](../results/gate_bm25.jsonl).
Registered as H11 in [`PREREGISTRATION.md`](../PREREGISTRATION.md) section 4f, committed
before this ran.

Every sparse-side claim in this repository so far compares character bigrams against what
MTEB uses — word-level or character-unigram splitting. Production Korean search uses
neither; it runs a morphological analyser. If bigrams also beat morphological analysis the
upstream recommendation is sound. If not, the bigram framing is wrong.

**It is wrong, and which way it is wrong depends on the corpus.**

## Five tokenizers, three datasets

| Tokenizer | AutoRAG (720 docs) | Ko-SQA (9,251) | MIRACL-ko (1,486,752) |
|---|---|---|---|
| character bigram | **0.92345** | 0.56108 | 0.35067 |
| morphemes, content words only | 0.89007 | **0.57291** | **0.40401** |
| morphemes, all | 0.89922 | 0.49318 | 0.29666 |
| word *(MTEB, two of the four published Korean numbers)* | 0.79557 | 0.37807 | 0.24521 |
| character unigram *(MTEB, current)* | 0.64342 | 0.30430 | 0.22280 |

**The two configurations MTEB uses for Korean are the two worst of the five, on all three
datasets.** That is the finding that survives everything below.

Analyser: `kiwipiepy` 0.23.2 (Kiwi), pinned. `morph` keeps every morpheme surface form;
`morph_content` drops tags beginning `J` (particles), `E` (endings), `X` (affixes) and `S`
(symbols). BM25 settings are unchanged throughout — `bm25s` defaults, Lucene, k1 = 1.5,
b = 0.75, nothing tuned.

## H11a — supported

Both morphological variants beat the word-level tokenizer on all three datasets, all six
paired intervals excluding 0 (bootstrap, 10,000 resamples at the query level, seed 0):

| Dataset | Variant | vs word | 95% CI |
|---|---|---|---|
| AutoRAG | morph | +0.10366 | [+0.04133, +0.16881] |
| AutoRAG | morph_content | +0.09451 | [+0.03375, +0.15717] |
| Ko-SQA | morph | +0.11511 | [+0.08546, +0.14504] |
| Ko-SQA | morph_content | +0.19484 | [+0.16397, +0.22616] |
| MIRACL-ko | morph | +0.05145 | [+0.01465, +0.08827] |
| MIRACL-ko | morph_content | +0.15880 | [+0.11768, +0.20155] |

This was registered as close to certain, and it was, so that the pair was a real test
rather than only the interesting half.

## H11b — neither its prediction nor its falsification condition is met

Character bigrams against the better morphological variant on each dataset:

| Dataset | Comparison | Difference | 95% CI | |
|---|---|---|---|---|
| AutoRAG | bigram − morph | +0.02423 | [−0.01023, +0.05666] | not distinguishable |
| Ko-SQA | bigram − morph_content | −0.01183 | [−0.03392, +0.01094] | not distinguishable |
| MIRACL-ko | bigram − morph_content | −0.05334 | [−0.08839, −0.01895] | **distinguishable** |

- The **prediction** was that bigrams score at least as high on a majority of the three.
  They lead on one of three. **Not met.**
- The **falsification condition** was that morphological analysis wins on ≥ 2 of 3 with
  intervals excluding 0. It wins distinguishably on one of three. **Not met either.**

**H11b is undecidable as written**, because its two clauses were not complements — a
result in the middle satisfies neither. This is the same drafting flaw as H8 and it is
recorded rather than repaired after the fact. Section 4g fixes the practice going forward
by requiring each falsification clause to be the exact complement of its prediction.

## What was actually measured

The two tokenizers are indistinguishable on 720 and 9,251 documents, and morphological
analysis wins on 1,486,752.

The direction lines up with corpus size, and there is a mechanism that would produce it:
bigram vocabulary grows much faster than morpheme vocabulary, so coincidental partial
matches multiply as the corpus grows, while morphemes stay a bounded, cleaner term set.
On AutoRAG the bigram vocabulary is 45,719 against 9,068 morpheme types — five times
larger for the same 720 documents.

**That is three points joined by a line, not a test.** The three datasets differ in domain,
query style and judgement depth as well as size, and no manipulation here isolates size.
It is a hypothesis for a later experiment, not a result.

## Cost

Kiwi tokenized the 9,251-document Ko-StrategyQA corpus in 2.4 s against 0.2 s for
character bigrams — about 12× slower, both negligible at this scale, and a morphological
analyser is a language-specific dependency where bigrams are three lines of code.

## What this changes about the recommendation to MTEB

The plan had been to propose character bigrams. **That proposal is not supported by these
numbers and is dropped.** Character n-grams beating morphological analysis for CJK
retrieval is also long-established in the IR literature, so a claim in that direction from
one analyser and three datasets would add nothing.

What these numbers do support is narrower and stands on its own: the two configurations
MTEB currently applies to Korean are the worst of the five tested, on every dataset. Which
of the better options to adopt is a decision for that project, and both have a cost —
a morphological analyser is a per-language dependency, bigrams are not.

## Not run

**Only one analyser was measured.** Kiwi is one of several in common use for Korean
(`mecab-ko`, `Okt`, `Komoran`, `Hannanum`, `nori`), and they disagree with each other. The
`morph` and `morph_content` rows are two configurations of the same analyser, not two
analysers. Any claim of the form "morphological analysis beats X" from this table is a
claim about Kiwi.

## Reproducing

```bash
python -m harness.evaluate --dataset MIRACLRetrieval-ko --tokenizer morph_content \
    --out results/gate_bm25.jsonl
```

Swap `--dataset` and `--tokenizer` (`word` additionally takes `--stopwords en
--stemmer english`, the settings MTEB used for Korean).
