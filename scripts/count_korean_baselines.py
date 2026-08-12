#!/usr/bin/env python3
"""Inventory every Korean result published for MTEB's BM25 baseline.

Reads `embeddings-benchmark/results` directly. A row counts as Korean when any entry in
its `languages` list starts with `kor`, which is how the result files themselves mark it.
The recorded `mteb_version` is copied verbatim — this inventory records what the files
*say*, which is a different thing from when they were produced.

    python scripts/count_korean_baselines.py --out results/korean_baseline_inventory.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

REPO = "embeddings-benchmark/results"
MODEL_DIR = "results/mteb__baseline-bm25s"
API = f"https://api.github.com/repos/{REPO}/contents/{MODEL_DIR}"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/{MODEL_DIR}"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "mimir-inventory",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/korean_baseline_inventory.jsonl")
    args = ap.parse_args()
    p = lambda *a: print(*a, file=sys.stderr, flush=True)

    revisions = [e["name"] for e in get_json(API) if e["type"] == "dir"]
    p(f"  baseline revisions: {revisions}")

    rows = []
    for rev in revisions:
        files = [e["name"] for e in get_json(f"{API}/{rev}")
                 if e["name"].endswith(".json") and e["name"] != "model_meta.json"]
        p(f"  {rev}: {len(files)} result files")
        for name in files:
            d = get_json(f"{RAW}/{rev}/{name}")
            for split, scores in (d.get("scores") or {}).items():
                for s in scores:
                    if not any((l or "").startswith("kor") for l in (s.get("languages") or [])):
                        continue
                    rows.append({
                        "model_revision": rev,
                        "task": d["task_name"],
                        "split": split,
                        "hf_subset": s.get("hf_subset"),
                        "languages": s.get("languages"),
                        "ndcg_at_10": s.get("ndcg_at_10"),
                        "recorded_mteb_version": d.get("mteb_version"),
                        "recorded_date": d.get("date"),
                    })

    def ver_key(v: str) -> tuple[int, int, int]:
        try:
            major, minor, patch = (int(x) for x in v.split("."))
        except (AttributeError, ValueError):
            return (0, 0, 0)
        return (major, minor, patch)

    versions = sorted({r["recorded_mteb_version"] for r in rows}, key=ver_key)
    # 2.18.12 is where `kor` first enters `_ISO3_TO_LANG`; see docs/baselines.md.
    at_or_after = [r for r in rows if ver_key(r["recorded_mteb_version"]) >= (2, 18, 12)]
    monolingual = [r for r in rows if all(l.startswith("kor") for l in r["languages"])]
    # 2.14.2 is where the language table, the character tokenizer and freq_threshold arrive.
    eras = {
        "le_2_14_1": sum(1 for r in rows if ver_key(r["recorded_mteb_version"]) < (2, 14, 2)),
        "2_14_2_to_2_18_11": sum(
            1 for r in rows
            if (2, 14, 2) <= ver_key(r["recorded_mteb_version"]) < (2, 18, 12)),
        "ge_2_18_12": len(at_or_after),
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"summary": {
            "source": f"https://github.com/{REPO}/tree/main/{MODEL_DIR}",
            "n_korean_results": len(rows),
            "n_korean_only": len(monolingual),
            "n_cross_lingual": len(rows) - len(monolingual),
            "n_tasks": len({r["task"] for r in rows}),
            "model_revisions": revisions,
            "recorded_mteb_versions": versions,
            "n_by_recorded_version_era": eras,
            "n_recording_2_18_12_or_later": len(at_or_after),
        }}, ensure_ascii=False, sort_keys=True) + "\n")
        for r in sorted(rows, key=lambda x: (x["task"], x["model_revision"], str(x["hf_subset"]))):
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    p(f"  Korean results: {len(rows)} across {len({r['task'] for r in rows})} tasks "
      f"({len(monolingual)} Korean-only, {len(rows) - len(monolingual)} cross-lingual)")
    p(f"  recorded mteb_version values: {versions}")
    p(f"  by era: {eras}")
    p(f"  recording 2.18.12 or later: {len(at_or_after)}")
    p(f"  wrote -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
