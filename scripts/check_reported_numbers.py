#!/usr/bin/env python3
"""Check that every score quoted in the documentation exists in results/*.jsonl.

Written after a table in README.md was filled in by hand and five of its values
did not match the raw records (see docs/errata.md). Numbers in a measurement
repository should come from the measurement, and a machine should say so.

    python scripts/check_reported_numbers.py

Exits non-zero if a document quotes a score that appears in no raw record.
Differences, gains and correlations are computed values rather than measurements,
so they are listed as unmatched for a human to confirm rather than failing the run.
"""

from __future__ import annotations

import glob
import json
import re
import sys

SCORE = re.compile(r"(?<![\d.])(0\.\d{4,5})(?![\d])")
# Values derived from measurements rather than read from them.
DERIVED = re.compile("[+\\-\u2212\u00b1]\\s*0\\.\\d{3,5}")


def collect_values(obj, out: set[float]) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            collect_values(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_values(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.add(round(float(obj), 5))


def main() -> int:
    measured: set[float] = set()
    for path in sorted(glob.glob("results/*.jsonl")):  # includes published_baselines.jsonl
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    collect_values(json.loads(line), measured)
    rounded = {round(v, 4) for v in measured} | measured
    print(f"  {len(measured):,} distinct values in results/*.jsonl")

    # The errata page exists to record values that were published and were wrong,
    # so by construction they are absent from the raw records. Skipped, and said so.
    SKIP = {"docs/errata.md"}
    failures = 0
    for path in sorted(glob.glob("docs/*.md")) + ["README.md", "PREREGISTRATION.md"]:
        if path in SKIP:
            print(f"  skipped {path} (records values that were wrong, by design)")
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except FileNotFoundError:
            continue
        unmatched = []
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in SCORE.finditer(line):
                value = float(m.group(1))
                if round(value, 5) in rounded or round(value, 4) in rounded:
                    continue
                derived = bool(DERIVED.search(line))
                unmatched.append((line_no, m.group(1), derived))
        if unmatched:
            print(f"\n  {path}")
            for line_no, value, derived in unmatched:
                tag = "derived?" if derived else "UNMATCHED"
                print(f"    {tag:10s} line {line_no}: {value}")
                failures += 0 if derived else 1

    print(f"\n=== {'PASS' if failures == 0 else f'FAIL — {failures} unmatched'} ===")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
