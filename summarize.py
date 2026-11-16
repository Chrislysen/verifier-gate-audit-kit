"""Summarize the comparison from its raw outputs and evaluate the pre-registered criteria C1-C6.

usage: python -I summarize.py --protocol <protocol.json> --raw <results dir> [--table7 <calibration_results.json>]
Reads raw_cells.jsonl, edge_cases.json and run_meta.json; writes summary.json and summary.md
next to them. Pure standard library; recomputes everything from the per-band outcome codes.
"""
from __future__ import annotations

import argparse
import json
import math
import os

C1_DISTS = ("unif0", "skew0", "skewc0", "rademacher", "skew_mild")
C2_DISTS = ("gauss0",)
FROZEN_ROUTE_CASES = ("E01_single_positive", "E02_constant_positive_x5", "E04_single_outside_support",
                      "E05_varying_one_outside_support", "E06_malformed_support_0_1_constant",
                      "E07_single_pos_inf", "E08_two_pos_inf", "E10_pos_inf_among_finite",
                      "E13_all_positive_small_n5", "E14_failed_observation_marker",
                      "E15_shrunken_band_4_of_5", "E16_no_support_declared")
POSITIVE_CONTROLS = ("E03_constant_top_x8", "E19_constant_top_x20", "E20_asymmetric_support_n2")
STATUS_LETTERS = {"C": "CONFIRMED", "N": "NOT_CONFIRMED", "U": "UNATTAINABLE", "I": "INVALID_INPUT",
                  "S": "INVALID_SUPPORT", "J": "NO_JUSTIFIED_SUPPORT", "P": "INCOMPLETE", "E": "EMPTY"}


def wilson(k: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--table7", default=None)
    a = ap.parse_args()
    proto = json.load(open(a.protocol, encoding="utf-8"))
    cells = [json.loads(l) for l in open(os.path.join(a.raw, "raw_cells.jsonl"), encoding="utf-8")]
    edges = json.load(open(os.path.join(a.raw, "edge_cases.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(a.raw, "run_meta.json"), encoding="utf-8"))

    rows = []
    for c in cells:
        r = dict(dist=c["dist"], n=c["n"], reps=c["reps"], role=c["role"], true_mean=c["true_mean"],
                 all_positive=c["all_positive"])
        for g in ("frozen_default", "frozen_minN_auto", "frozen_declared"):
            k = c[g]["codes"].count("1")
            assert len(c[g]["codes"]) == c["reps"]
            r[g] = dict(k=k, rate=k / c["reps"], wilson95=wilson(k, c["reps"]), gates=c[g]["gates"])
        codes = c["strict"]["codes"]
        assert len(codes) == c["reps"]
        cnt = {STATUS_LETTERS[l]: codes.count(l) for l in STATUS_LETTERS if codes.count(l)}
        k = codes.count("C")
        r["strict"] = dict(k=k, rate=k / c["reps"], wilson95=wilson(k, c["reps"]), statuses=cnt)
        r["c4"] = c["c4"]
        rows.append(r)

    crit = {}
    bad = [(r["dist"], r["n"], r["strict"]["k"]) for r in rows
           if r["dist"] in C1_DISTS and r["strict"]["wilson95"][0] > proto["alpha"]]
    crit["C1_validity"] = dict(passed=not bad, cells=sum(r["dist"] in C1_DISTS for r in rows),
                               max_rate=max(r["strict"]["rate"] for r in rows if r["dist"] in C1_DISTS),
                               violations=bad)
    bad = [(r["dist"], r["n"], r["strict"]["k"]) for r in rows
           if r["dist"] in C2_DISTS and r["strict"]["wilson95"][0] > proto["alpha"]]
    crit["C2_gaussian_null"] = dict(passed=not bad, violations=bad,
                                    invalid_input=sum(r["strict"]["statuses"].get("INVALID_INPUT", 0)
                                                      for r in rows if r["dist"] in C2_DISTS))
    bad = []
    for c in cells:
        codes = c["strict"]["codes"]
        if c["n"] <= 7 and set(codes) - {"U", "I"}:
            bad.append((c["dist"], c["n"], sorted(set(codes) - {"U", "I"})))
        if c["n"] >= 8 and "U" in codes:
            bad.append((c["dist"], c["n"], "U at n>=8"))
    crit["C3_capacity"] = dict(passed=not bad, violations=bad)
    crit["C4_equivalence"] = dict(
        passed=all(r["c4"]["evalue_mismatch"] == 0 and r["c4"]["decision_disagree"] == 0 for r in rows),
        apriori_bands=sum(r["c4"]["apriori_bands"] for r in rows),
        evalue_mismatch=sum(r["c4"]["evalue_mismatch"] for r in rows),
        decision_disagree=sum(r["c4"]["decision_disagree"] for r in rows),
        max_rel_diff_below_cap=max(r["c4"]["max_rel_diff_below_cap"] for r in rows))
    by = {e["case"]: e for e in edges}
    bad = [k for k in FROZEN_ROUTE_CASES if by[k]["strict"]["confirmed"]]
    bad += [k for k in POSITIVE_CONTROLS if not by[k]["strict"]["confirmed"]]
    crit["C5_edge_cases"] = dict(passed=not bad, violations=bad,
                                 frozen_confirmed_routes=[k for k in FROZEN_ROUTE_CASES
                                                          if by[k].get("frozen_default", {}).get("confirmed")
                                                          or by[k].get("frozen_declared", {}).get("confirmed")])
    if a.table7:
        t7 = json.load(open(a.table7, encoding="utf-8"))
        ours = {(r["dist"], r["n"]): r["frozen_default"]["k"] for r in rows}
        t7rows = [x for x in t7["rows"] if x["cfg"] == "default"]
        bad = [(x["dist"], x["n"], x["confirmed"], ours.get((x["dist"], x["n"]))) for x in t7rows
               if ours.get((x["dist"], x["n"])) != x["confirmed"]]
        crit["C6_continuity"] = dict(passed=not bad and len(t7rows) == 35, cells=len(t7rows), violations=bad)
    else:
        crit["C6_continuity"] = dict(passed=None, note="Table 7 results not supplied")
    power = [dict(dist=r["dist"], n=r["n"], true_mean=r["true_mean"], rate=r["strict"]["rate"],
                  wilson95=r["strict"]["wilson95"], demonstrated=r["strict"]["wilson95"][0] >= 0.5)
             for r in rows if r["role"].startswith("alternative")]
    out = dict(protocol=proto["protocol"], protocol_version=proto["version"], run_meta=meta,
               criteria=crit, cells=rows, edge_cases=edges, power=power)
    json.dump(out, open(os.path.join(a.raw, "summary.json"), "w", encoding="utf-8"), indent=1)

    def f(x):
        return f"{x:.3f}"
    L = ["# Comparison summary (generated by summarize.py from the raw outputs)", "",
         f"Protocol {proto['protocol']} v{proto['version']}; run {meta['started']}, {meta['seconds']} s, "
         f"Python {meta['python']}; strict gate sha256 {meta['strict_sha256'][:12]}; frozen {meta['frozen_commit']}.", "",
         "## Pre-registered criteria", ""]
    for k, v in crit.items():
        L.append(f"- **{k}**: {'PASS' if v['passed'] else ('n/a' if v['passed'] is None else 'FAIL')} "
                 f"`{json.dumps({x: y for x, y in v.items() if x != 'passed'})[:300]}`")
    L += ["", "## Confirmation rate by gate (null rows: false confirmations; alternatives: power)", "",
          "| distribution | n | frozen default | frozen min-n | frozen declared | strict | strict statuses |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['dist']} ({r['role'].split()[0]}, mean {r['true_mean']}) | {r['n']} | "
                 f"{f(r['frozen_default']['rate'])} | {f(r['frozen_minN_auto']['rate'])} | "
                 f"{f(r['frozen_declared']['rate'])} | {f(r['strict']['rate'])} | "
                 + ", ".join(f"{s} {v}" for s, v in r["strict"]["statuses"].items()) + " |")
    L += ["", "## Edge cases", "", "| case | frozen default | frozen declared | strict |", "|---|---|---|---|"]
    for e in edges:
        fd, fl = e.get("frozen_default"), e.get("frozen_declared")
        L.append(f"| {e['case']} | {'-' if fd is None else ('confirmed' if fd['confirmed'] else 'not')} ({'' if fd is None else fd['gate']}) | "
                 f"{'-' if fl is None else ('confirmed' if fl['confirmed'] else 'not')} ({'' if fl is None else fl['gate']}) | "
                 f"{e['strict']['status']} |")
    open(os.path.join(a.raw, "summary.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(json.dumps({k: v["passed"] for k, v in crit.items()}))


if __name__ == "__main__":
    main()
