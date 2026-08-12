"""Tokenizers under comparison. Each returns list[list[str]].

- `word`: the bm25s default, which is what every published Korean BM25 number
  found so far was produced with. Delegated to bm25s so it matches exactly.
- `char_unigram`: what current MTEB versions use for Korean.
- `char_bigram`: the condition with no published Korean number.
- `morph` / `morph_content`: Korean morphological analysis, which is what production
  search engines use and what MTEB does not.
"""

from __future__ import annotations

import unicodedata

TOKENIZERS = ("word", "char_unigram", "char_bigram", "morph", "morph_content")

# Kiwi tags to drop for the content-word variant: particles, endings, affixes, symbols.
_FUNCTION_TAGS = ("J", "E", "X", "S")
_kiwi = None


def _normalize(text: str) -> str:
    """NFKC, lowercase, drop whitespace. Matches MTEB's `_unicode_tokenize`."""
    return unicodedata.normalize("NFKC", text).lower().replace(" ", "")


def char_unigram(texts: list[str]) -> list[list[str]]:
    return [list(_normalize(t)) for t in texts]


def char_bigram(texts: list[str]) -> list[list[str]]:
    """Adjacent character pairs, with the pair strings pooled.

    Pooling matters at MIRACL scale: 258M separate 2-character objects cost about
    20 GB, while sharing one object per distinct bigram costs about 2 GB. Token
    values are unchanged, so scores are unaffected.
    """
    pool: dict[str, str] = {}
    out = []
    for t in texts:
        s = _normalize(t)
        if len(s) < 2:
            out.append(list(s))
            continue
        row = []
        append = row.append
        for i in range(len(s) - 1):
            bg = s[i:i + 2]
            append(pool.setdefault(bg, bg))
        out.append(row)
    return out


def word(texts: list[str], stopwords=None, stemmer=None) -> list[list[str]]:
    """bm25s default tokenizer: lowercase, split on `(?u)\\b\\w\\w+\\b`.

    Single-character tokens are dropped by that pattern. `stopwords="en"` and an
    English stemmer are the settings MTEB used for Korean.
    """
    import bm25s

    return bm25s.tokenize(
        texts, stopwords=stopwords, stemmer=stemmer, return_ids=False, show_progress=False
    )


def _analyser():
    """Kiwi is loaded once; construction costs seconds and is not per-call work."""
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi

        _kiwi = Kiwi()
    return _kiwi


def morph(texts: list[str], content_only: bool = False) -> list[list[str]]:
    """Morpheme surface forms. `content_only` drops particles, endings and affixes."""
    kiwi = _analyser()
    pool: dict[str, str] = {}
    out = []
    for result in kiwi.tokenize(texts):
        row = []
        for t in result:
            if content_only and t.tag.startswith(_FUNCTION_TAGS):
                continue
            row.append(pool.setdefault(t.form, t.form))
        out.append(row)
    return out


def freq_stopwords(doc_tokens: list[list[str]], threshold: float) -> frozenset[str]:
    """Tokens present in at least `threshold` of documents.

    MTEB removes these for any language with no named stopword list, Korean
    included, and the step is not recorded in the published result files.
    Reproducing AutoRAGRetrieval needs it: 0.64342 without, 0.65022 with.
    """
    if threshold <= 0:
        return frozenset()
    n = len(doc_tokens)
    df: dict[str, int] = {}
    for toks in doc_tokens:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    return frozenset(t for t, c in df.items() if c / n >= threshold)


def drop(token_lists: list[list[str]], stops: frozenset[str]) -> list[list[str]]:
    """Remove `stops` from every token list. Applied to corpus and queries alike."""
    if not stops:
        return token_lists
    return [[t for t in toks if t not in stops] for toks in token_lists]


def tokenize(name: str, texts: list[str], **kwargs) -> list[list[str]]:
    if name == "word":
        return word(texts, **kwargs)
    if name == "char_unigram":
        return char_unigram(texts)
    if name == "char_bigram":
        return char_bigram(texts)
    if name == "morph":
        return morph(texts)
    if name == "morph_content":
        return morph(texts, content_only=True)
    raise ValueError(f"unknown tokenizer: {name!r}; expected one of {TOKENIZERS}")
