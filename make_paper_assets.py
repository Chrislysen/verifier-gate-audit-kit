"""Generate the paper's Appendix H table, the figure's coordinates and the quoted numbers
from summary.json, so no number in the paper is copied by hand.

usage: python -I make_paper_assets.py --summary <summary.json> --out <dir>
Writes repair_table.tex, repair_figure.tex and repair_numbers.json.
"""
from __future__ import annotations

import argparse
import json
import os
from decimal import ROUND_HALF_UP, Decimal

TABLE_NS = (5, 8, 20, 50, 200)
NULLS = ("unif0", "rademacher", "gauss0", "skew_mild", "skew0", "skewc0")
ALTS = ("skew+0.08", "beta+0.2", "unif+0.25", "unif+0.5", "gauss+0.5", "gauss+1.0")
LABEL = {"unif0": r"$U(-1,1)$", "rademacher": r"$\pm1$, equal odds", "gauss0": r"$N(0,1)$",
         "skew_mild": r"$+\tfrac13$ (0.75), $-1$", "skew0": r"$+\tfrac19$ (0.9), $-1$",
         "skewc0": r"skewed continuous", "skew+0.08": r"$+0.2$ (0.9), $-1$",
         "beta+0.2": r"$2\,\mathrm{Beta}(3,2)-1$", "unif+0.25": r"$U(-0.5,1)$",
         "unif+0.5": r"$U(0,1)$", "gauss+0.5": r"$N(0.5,1)$", "gauss+1.0": r"$N(1,1)$"}
FIG_GATES = (("frozen_default", "frozen default"), ("strict", "strict"))   # the min-n line coincides
# with the default line at n >= 5 (and everywhere on the two-point nulls), so it is left to the table


def fmt(x: float) -> str:
    if x == 0:
        return "0"
    if x >= 1:
        return "1"
    # A rate is k/reps with reps 2,000 or 4,000, so repr(x) is its exact decimal. Exact ties round half up
    # (float formatting rounded some down and some up, by their binary representation).
    return str(Decimal(repr(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)).lstrip("0")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    s = json.load(open(a.summary, encoding="utf-8"))
    cell = {(c["dist"], c["n"]): c for c in s["cells"]}

    def strict_cell(c):
        st = c["strict"]["statuses"]
        if st.get("UNATTAINABLE", 0) + st.get("INVALID_INPUT", 0) == c["reps"] and st.get("UNATTAINABLE", 0):
            return r"\textsc{abst}"
        return fmt(c["strict"]["rate"])

    rows = []
    for group, dists in (("Zero-mean nulls", NULLS), ("Positive alternatives", ALTS)):
        rows.append(rf"\multicolumn{{7}}{{@{{}}l}}{{\emph{{{group}}}}} \\")
        for d in dists:
            m = cell[(d, TABLE_NS[0])]["true_mean"]
            vals = " & ".join(f"{fmt(cell[(d, n)]['frozen_default']['rate'])}\\,/\\,{strict_cell(cell[(d, n)])}"
                              for n in TABLE_NS)
            rows.append(f"{LABEL[d]} & {m:g} & {vals} \\\\")
    open(os.path.join(a.out, "repair_table.tex"), "w", encoding="utf-8", newline="\n").write("\n".join(rows) + "\n")

    figs = []
    for panel, dist in (("a", "skewc0"), ("b", "unif+0.25")):
        for g, _ in FIG_GATES:
            pts = " ".join(f"({c['n']},{c[g]['rate']:.4f})" for c in sorted(
                (c for c in s["cells"] if c["dist"] == dist), key=lambda c: c["n"]))
            figs.append(f"% panel {panel} {dist} {g}\n\\def\\repair{panel}{g.replace('_', '')}{{{pts}}}")
    open(os.path.join(a.out, "repair_figure.tex"), "w", encoding="utf-8", newline="\n").write("\n".join(figs) + "\n")

    c1 = [c for c in s["cells"] if c["dist"] in ("unif0", "skew0", "skewc0", "rademacher", "skew_mild", "gauss0")]
    alt = [c for c in s["cells"] if c["role"].startswith("alternative")]
    num = dict(
        criteria={k: v["passed"] for k, v in s["criteria"].items()},
        null_bands=sum(c["reps"] for c in c1),
        strict_null_confirmed=sum(c["strict"]["k"] for c in c1),
        strict_null_max_rate=max(c["strict"]["rate"] for c in c1),
        frozen_default_null_max_rate=max(c["frozen_default"]["rate"] for c in c1),
        frozen_default_null_max_cell=max(((c["frozen_default"]["rate"], c["dist"], c["n"]) for c in c1)),
        strict_invalid_input_gauss=sum(c["strict"]["statuses"].get("INVALID_INPUT", 0) for c in s["cells"]
                                       if c["dist"].startswith("gauss")),
        strict_power={f"{c['dist']}@{c['n']}": [round(c["strict"]["rate"], 4), [round(x, 4) for x in c["strict"]["wilson95"]],
                                                 c["strict"]["wilson95"][0] >= 0.5] for c in alt},
        frozen_default_power={f"{c['dist']}@{c['n']}": round(c["frozen_default"]["rate"], 4) for c in alt},
        c4=s["criteria"]["C4_equivalence"],
        edge_frozen_confirmed=s["criteria"]["C5_edge_cases"]["frozen_confirmed_routes"],
    )
    json.dump(num, open(os.path.join(a.out, "repair_numbers.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps(num["criteria"]), num["strict_null_confirmed"], "of", num["null_bands"])


if __name__ == "__main__":
    main()
