"""Check this kit's run against the reference run, band by band.

usage: python -I -S compare_to_reference.py [--results results] [--reference reference_results]
The reference run used the audited code (commit 0cd5df96, not included here) and the strict gate
file evaluated for the paper; this kit runs its own editions of both (PROVENANCE.md). Every cell
present in --results must match the reference exactly: each band's
outcome under each gate, the branch-label counts, the all-positive count and the e-value
equivalence counts. Prints PASSED or FAILED.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATES = ("frozen_default", "frozen_minN_auto", "frozen_declared", "strict")


def load(path):
    return {(c["dist"], c["n"]): c for c in map(json.loads, open(path, encoding="utf-8"))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "results"))
    ap.add_argument("--reference", default=os.path.join(HERE, "reference_results"))
    a = ap.parse_args()
    mine = load(os.path.join(a.results, "raw_cells.jsonl"))
    ref = load(os.path.join(a.reference, "raw_cells.jsonl"))
    bad = []
    bands = 0
    for key, c in mine.items():
        r = ref.get(key)
        if r is None:
            bad.append((key, "cell missing from the reference"))
            continue
        for f in ("seed", "reps", "all_positive", "c4"):
            if c[f] != r[f]:
                bad.append((key, f))
        for g in GATES:
            if c[g]["codes"] != r[g]["codes"]:
                diff = sum(x != y for x, y in zip(c[g]["codes"], r[g]["codes"]))
                bad.append((key, g, f"{diff} band(s) differ"))
            if g != "strict" and c[g]["gates"] != r[g]["gates"]:
                bad.append((key, g, "branch labels differ"))
        bands += c["reps"]
    me = {e["case"]: e for e in json.load(open(os.path.join(a.results, "edge_cases.json"), encoding="utf-8"))}
    re_ = {e["case"]: e for e in json.load(open(os.path.join(a.reference, "edge_cases.json"), encoding="utf-8"))}
    for k, e in me.items():
        f = re_.get(k)
        if f is None or any(e.get(g) != f.get(g) for g in ("frozen_default", "frozen_declared")) \
                or e["strict"]["status"] != f["strict"]["status"] or e["strict"]["e_value"] != f["strict"]["e_value"]:
            bad.append((k, "edge case differs"))
    print(f"compared {len(mine)} cells ({bands} bands x {len(GATES)} gates) and {len(me)} edge cases")
    for b in bad[:20]:
        print("  MISMATCH", b)
    print("PASSED" if not bad and mine else "FAILED")
    sys.exit(0 if not bad and mine else 1)


if __name__ == "__main__":
    main()
