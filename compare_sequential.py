"""Check this kit's sequential run against the reference run, stream by stream.

usage: python -I -S compare_sequential.py [--results results_sequential]
                                          [--reference reference_results/sequential]
The reference run is the authors' single pre-registered run of protocol_sequential.json with the
gate files evaluated for the paper (sha256 values in its run_meta_sequential.json). This kit holds
its own editions of the two gates (PROVENANCE.md), so their hashes differ from the reference run's
by design; both protocols must be the reference run's. Every cell present in --results must match
the reference exactly: each stream's status and number of instances read under the sequential
gate, and its status under the fixed-band gate. A run made with --streams K is checked
on the first K streams of each cell (streams are drawn in order from the same seeds); the S4 and
S5 counts, which cover all streams, are compared only for full runs. The 15 edge cases and 3
argument errors are always compared. Prints PASSED or FAILED.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROTOCOLS = ("protocol_sha256", "base_protocol_sha256")       # must be the reference run's
GATES = ("sequential_sha256", "strict_sha256")                # the kit's editions: reported, not required


def load(path):
    return {(c["dist"], c["budget"]): c for c in map(json.loads, open(path, encoding="utf-8"))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "results_sequential"))
    ap.add_argument("--reference", default=os.path.join(HERE, "reference_results", "sequential"))
    a = ap.parse_args()
    bad = []
    meta = json.load(open(os.path.join(a.results, "run_meta_sequential.json"), encoding="utf-8"))
    ref_meta = json.load(open(os.path.join(a.reference, "run_meta_sequential.json"), encoding="utf-8"))
    for k in PROTOCOLS:
        if meta[k] != ref_meta[k]:
            bad.append(f"input {k} differs from the reference run's")
    for k in GATES:
        same = "the reference run's file" if meta[k] == ref_meta[k] else f"the kit's edition (reference run: {ref_meta[k][:12]})"
        print(f"{k[:-7]} gate: sha256 {meta[k][:12]}, {same}")
    mine = load(os.path.join(a.results, "raw_sequential.jsonl"))
    ref = load(os.path.join(a.reference, "raw_sequential.jsonl"))
    full = 0
    for key, c in sorted(mine.items()):
        r = ref.get(key)
        if r is None:
            bad.append(f"{key}: not in the reference")
            continue
        k = c["streams"]
        if (c["seed"], c["support"], c["role"]) != (r["seed"], r["support"], r["role"]):
            bad.append(f"{key}: seed, support or role differs")
        if c["seq_codes"] != r["seq_codes"][:k]:
            bad.append(f"{key}: sequential statuses differ")
        if c["seq_n"] != r["seq_n"][:k]:
            bad.append(f"{key}: instances read differ")
        if c["fix_codes"] != r["fix_codes"][:k]:
            bad.append(f"{key}: fixed-band statuses differ")
        if k == r["streams"]:
            full += 1
            if c["s4"] != r["s4"] or c["s5"] != r["s5"]:
                bad.append(f"{key}: S4/S5 counts differ: {c['s4']} {c['s5']} vs {r['s4']} {r['s5']}")
    edges = json.load(open(os.path.join(a.results, "edge_cases_sequential.json"), encoding="utf-8"))
    ref_edges = json.load(open(os.path.join(a.reference, "edge_cases_sequential.json"), encoding="utf-8"))
    pick = lambda e: (e["case"], e["status"], e["n_read"], e["e_value"], e["ok"])
    if [pick(e) for e in edges["cases"]] != [pick(e) for e in ref_edges["cases"]]:
        bad.append("edge cases differ")
    if [(e["args"], e["ok"]) for e in edges["errors"]] != [(e["args"], e["ok"]) for e in ref_edges["errors"]]:
        bad.append("argument errors differ")
    n_streams = sum(c["streams"] for c in mine.values())
    print(f"compared {len(mine)} of {len(ref)} cells ({full} full, {n_streams} streams x 2 gates), "
          f"{len(edges['cases'])} edge cases and {len(edges['errors'])} argument errors")
    for b in bad[:20]:
        print("  MISMATCH", b)
    print("PASSED" if not bad and mine else "FAILED")
    sys.exit(0 if not bad and mine else 1)


if __name__ == "__main__":
    main()
