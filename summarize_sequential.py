"""Summarize a run of protocol_sequential.json: per-cell rates with Wilson 95% intervals, status
counts, instances read, and the pre-registered criteria S1-S6.

usage: python -I summarize_sequential.py --base <protocol.json> --protocol <protocol_sequential.json> --raw <dir>
Writes summary_sequential.json and summary_sequential.md into --raw.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics

Z = 1.959963984540054
NAMES = {"C": "CONFIRMED", "N": "NOT_CONFIRMED", "U": "UNATTAINABLE", "I": "INVALID_INPUT", "S": "INVALID_SUPPORT",
         "J": "NO_JUSTIFIED_SUPPORT", "P": "INCOMPLETE", "E": "EMPTY"}
BOUNDED_NULLS = ("unif0", "skew0", "skewc0", "rademacher", "skew_mild")


def wilson(k: int, n: int):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    den = 1 + Z * Z / n
    mid = (p + Z * Z / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def pct(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    i = min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))
    return s[i]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--raw", required=True)
    a = ap.parse_args()
    proto = json.load(open(a.protocol, encoding="utf-8"))
    rows = [json.loads(ln) for ln in open(os.path.join(a.raw, "raw_sequential.jsonl"), encoding="utf-8")]
    edges = json.load(open(os.path.join(a.raw, "edge_cases_sequential.json"), encoding="utf-8"))
    cells = []
    for r in rows:
        R = r["streams"]
        sc, fc, n = r["seq_codes"], r["fix_codes"], r["seq_n"]
        k, kf = sc.count("C"), fc.count("C")
        conf_n = [t for c, t in zip(sc, n) if c == "C"]
        cells.append(dict(
            dist=r["dist"], budget=r["budget"], role=r["role"], true_mean=r["true_mean"], streams=R,
            seq_confirmed=k, seq_rate=k / R, seq_wilson=wilson(k, R),
            seq_status={NAMES[c]: sc.count(c) for c in sorted(set(sc))},
            fixed_confirmed=kf, fixed_rate=kf / R, fixed_wilson=wilson(kf, R),
            fixed_status={NAMES[c]: fc.count(c) for c in sorted(set(fc))},
            mean_read=sum(n) / R, min_stop_confirmed=min(conf_n) if conf_n else None,
            median_stop_confirmed=statistics.median(conf_n) if conf_n else None,
            p90_stop_confirmed=pct(conf_n, 0.9), s4=r["s4"], s5=r["s5"]))
    by = {(c["dist"], c["budget"]): c for c in cells}

    s1 = [c for c in cells if c["dist"] in BOUNDED_NULLS]
    s2 = [c for c in cells if c["dist"] == "gauss0"]
    crit = {
        "S1_validity": dict(passed=all(c["seq_wilson"][0] <= 0.05 for c in s1), cells=len(s1),
                            max_rate=max(c["seq_rate"] for c in s1),
                            max_cell=max(s1, key=lambda c: c["seq_rate"])["dist"] + "@" +
                            str(max(s1, key=lambda c: c["seq_rate"])["budget"]),
                            max_wilson_lower=max(c["seq_wilson"][0] for c in s1)),
        "S2_gaussian_null": dict(passed=all(c["seq_wilson"][0] <= 0.05 for c in s2), cells=len(s2),
                                 max_rate=max(c["seq_rate"] for c in s2),
                                 invalid_input=sum(c["seq_status"].get("INVALID_INPUT", 0) for c in s2)),
        "S3_capacity": dict(passed=all(c["min_stop_confirmed"] is None or c["min_stop_confirmed"] >= 8 for c in cells),
                            min_stop=min((c["min_stop_confirmed"] for c in cells if c["min_stop_confirmed"] is not None),
                                         default=None)),
        "S4_dominance": dict(passed=all(c["s4"]["fixed_confirmed_sequential_not"] == 0 and
                                        c["s4"]["prefix_not_confirmed"] == 0 for c in cells),
                             fixed_confirmed_sequential_not=sum(c["s4"]["fixed_confirmed_sequential_not"] for c in cells),
                             prefix_not_confirmed=sum(c["s4"]["prefix_not_confirmed"] for c in cells)),
        "S5_evalue": dict(passed=all(c["s5"]["mismatch"] == 0 for c in cells),
                          checked=sum(c["s5"]["checked"] for c in cells),
                          mismatch=sum(c["s5"]["mismatch"] for c in cells),
                          worst_rel=max(c["s5"]["worst_rel"] for c in cells)),
        "S6_edge_cases": dict(passed=all(e["ok"] for e in edges["cases"]) and all(e["ok"] for e in edges["errors"]),
                              cases_ok=sum(e["ok"] for e in edges["cases"]), cases=len(edges["cases"]),
                              errors_ok=sum(e["ok"] for e in edges["errors"]), errors=len(edges["errors"])),
    }
    power = {f"{c['dist']}@{c['budget']}": round(c["seq_rate"], 4) for c in cells
             if c["role"].startswith("alternative") and c["seq_wilson"][0] >= 0.5}
    out = dict(criteria=crit, all_passed=all(v["passed"] for v in crit.values()),
               power_claimable_cells=power, cells=cells)
    json.dump(out, open(os.path.join(a.raw, "summary_sequential.json"), "w", encoding="utf-8"), indent=1)

    L = ["# Sequential strict gate vs fixed-band strict gate (protocol_sequential.json)", "",
         f"All criteria passed: **{out['all_passed']}**", ""]
    for k2, v in crit.items():
        L.append(f"- {k2}: {'PASS' if v['passed'] else 'FAIL'} -- " +
                 ", ".join(f"{kk}={vv}" for kk, vv in v.items() if kk != "passed"))
    L += ["", "| distribution | role | N | sequential confirmed (Wilson 95%) | fixed confirmed | mean read | "
              "median / p90 stop (confirmed) | invalid |", "|---|---|---|---|---|---|---|---|"]
    for d in proto["dist_order"]:
        for N in proto["budgets"]:
            c = by[(d, N)]
            lo, hi = c["seq_wilson"]
            L.append(f"| {d} | {c['role'].split(' ')[0]} | {N} | {c['seq_rate']:.4f} ({lo:.4f}-{hi:.4f}) | "
                     f"{c['fixed_rate']:.4f} | {c['mean_read']:.1f} | {c['median_stop_confirmed']} / "
                     f"{c['p90_stop_confirmed']} | {c['seq_status'].get('INVALID_INPUT', 0)} |")
    open(os.path.join(a.raw, "summary_sequential.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
