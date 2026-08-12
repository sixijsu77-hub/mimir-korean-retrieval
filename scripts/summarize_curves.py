#!/usr/bin/env python3
"""Derive per-curve summary quantities from results/hybrid.jsonl.

Amplitude and interval width are arithmetic on the stored curve, not separate
measurements — but documentation quotes them, so they are written to a raw record
that scripts/check_reported_numbers.py can verify against.

    python scripts/summarize_curves.py --out results/curve_summary.jsonl
"""
from __future__ import annotations

import argparse
import json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="results/hybrid.jsonl")
    ap.add_argument("--out", default="results/curve_summary.jsonl")
    args = ap.parse_args()

    rows = []
    with open(args.inp, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            for norm, curve in r["curves"].items():
                best = r["best"][norm]
                ys = [e["ndcg_at_10"] for e in curve]
                lo, hi = best["ci95"]
                width = hi - lo
                rows.append({
                    "dataset": r["dataset"], "model": r["model"], "normalization": norm,
                    "n_queries": r["n_queries"],
                    "best_w": best["w_dense"],
                    "curve_min": round(min(ys), 5), "curve_max": round(max(ys), 5),
                    "amplitude": round(max(ys) - min(ys), 5),
                    "ci95_width_at_best": round(width, 5),
                    "amplitude_over_ci_width": round((max(ys) - min(ys)) / width, 4) if width else None,
                    "n_indistinguishable": len(best["not_distinguishable_from_best"]),
                })
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"  wrote {len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
