"""Tokenizers under comparison. Each returns list[list[str]].

- `word`: the bm25s default, which is what every published Korean BM25 number
  found so far was produced with. Delegated to bm25s so it matches exactly.
- `char_unigram`: what current MTEB versions use for Korean.
- `char_bigram`: the condition with no published Korean number.
"""

from __future__ import annotations

import unicodedata

TOKENIZERS = ("word", "char_unigram", "char_bigram")


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


def tokenize(name: str, texts: list[str], **kwargs) -> list[list[str]]:
    if name == "word":
        return word(texts, **kwargs)
    if name == "char_unigram":
        return char_unigram(texts)
    if name == "char_bigram":
        return char_bigram(texts)
    raise ValueError(f"unknown tokenizer: {name!r}; expected one of {TOKENIZERS}")
