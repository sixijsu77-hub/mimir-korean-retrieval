#!/usr/bin/env python3
"""What version does every published BM25 baseline result *say* it was produced at?

This reads `embeddings-benchmark/results` and reports nothing but recorded metadata:
`mteb_version`, `date`, and the languages each file covers. It runs no evaluation and
installs nothing.

**A stamp is not a production era.** That distinction is the entire subject of
embeddings-benchmark/mteb#5157, where four files stamped 2.12.30 cannot have been produced
by 2.12.30. Nothing here establishes when a file was produced; only reproduction does.
What it establishes is how the corpus is distributed across the stamps it carries.

Era boundaries come from the commit history of `mteb/models/model_implementations/bm25.py`
and are documented in docs/baselines.md:
  <= 2.14.1        stopwords="en" and stemmer_language="english" hardcoded for every language
  2.14.2 - 2.18.11 per-language table; frequency stopwords for languages with no named list
  >= 2.18.12       `kor` routed to character unigrams

The 2 / 3 split is only visible for a task whose language has no bm25s stopword key —
`bm25.py` gates the frequency-stopword branch on `stopwords_key is None`. Tasks whose
languages all carry a key run identically under eras 2 and 3, so they cannot discriminate.

    python scripts/stamp_pass.py --out results/baseline_stamp_pass.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections import Counter

REPO = "embeddings-benchmark/results"
MODEL_DIR = "results/mteb__baseline-bm25s"
API = f"https://api.github.com/repos/{REPO}/contents/{MODEL_DIR}"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/{MODEL_DIR}"
BM25_SRC = ("https://raw.githubusercontent.com/embeddings-benchmark/mteb/"
            "{tag}/mteb/models/model_implementations/bm25.py")

ERA_2 = (2, 14, 2)    # language table, _unicode_tokenize and freq_threshold arrive
ERA_3 = (2, 18, 12)   # `kor` enters _ISO3_TO_LANG


def get(url: str, as_json: bool = True):
    req = urllib.request.Request(url, headers={"User-Agent": "mimir-stamp-pass",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        raw = r.read().decode("utf-8")
    return json.loads(raw) if as_json else raw


def version_key(v: str | None) -> tuple[int, int, int]:
    try:
        major, minor, patch = (int(x) for x in str(v).split("."))
    except (AttributeError, ValueError):
        return (0, 0, 0)
    return (major, minor, patch)


def era_of(v: str | None) -> str:
    k = version_key(v)
    if k < ERA_2:
        return "le_2_14_1"
    return "2_14_2_to_2_18_11" if k < ERA_3 else "ge_2_18_12"


def languages_with_stopword_key(tag: str) -> set[str]:
    """ISO3 codes whose _ISO3_TO_LANG row names a bm25s stopword list."""
    src = get(BM25_SRC.format(tag=tag), as_json=False)
    match = re.search(r"_ISO3_TO_LANG.*?\n\}", src, re.S)
    if match is None:
        raise RuntimeError(f"_ISO3_TO_LANG not found in bm25.py at tag {tag}")
    return {code for code, key
            in re.findall(r'"(\w{3})": \((?:"(\w+)"|None), ', match.group()) if key}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="2.19.2", help="mteb tag to read the language table from")
    ap.add_argument("--out", default="results/baseline_stamp_pass.jsonl")
    args = ap.parse_args()
    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    with_key = languages_with_stopword_key(args.tag)
    p(f"  languages carrying a bm25s stopword key at {args.tag}: {len(with_key)}")

    revisions = [e["name"] for e in get(API) if e["type"] == "dir"]
    rows = []
    for rev in revisions:
        names = [e["name"] for e in get(f"{API}/{rev}")
                 if e["name"].endswith(".json") and e["name"] != "model_meta.json"]
        p(f"  {rev}: {len(names)} result files")
        for name in names:
            d = get(f"{RAW}/{rev}/{name}")
            langs = sorted({l.split("-")[0]
                            for scores in (d.get("scores") or {}).values()
                            for row in scores
                            for l in (row.get("languages") or [])})
            rows.append({
                "model_revision": rev,
                "task": d["task_name"],
                "recorded_mteb_version": d.get("mteb_version"),
                "recorded_era": era_of(d.get("mteb_version")),
                "recorded_date": d.get("date"),
                "languages": langs,
                # Eras 2 and 3 differ only where the frequency-stopword branch is reachable.
                "discriminates_era_2_vs_3": bool(langs) and not set(langs) <= with_key,
            })

    eras = Counter(r["recorded_era"] for r in rows)
    disc = sum(r["discriminates_era_2_vs_3"] for r in rows)
    summary = {"summary": {
        "source": f"https://github.com/{REPO}/tree/main/{MODEL_DIR}",
        "language_table_tag": args.tag,
        "n_files": len(rows),
        "n_by_recorded_era": dict(eras),
        "n_recorded_versions": len({r["recorded_mteb_version"] for r in rows}),
        "n_discriminating_era_2_vs_3": disc,
        "n_languages_seen": len({l for r in rows for l in r["languages"]}),
        "caveat": "recorded stamps only; a stamp is not a production era (see mteb#5157)",
    }}

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n")
        for r in sorted(rows, key=lambda x: (x["model_revision"], x["task"])):
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    p(f"  files {len(rows)} · eras {dict(eras)} · discriminating {disc}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
