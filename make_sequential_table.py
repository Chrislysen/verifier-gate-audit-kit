"""LaTeX rows of the sequential-gate table (Table 11) from summary_sequential.json.
Rates are computed from the exact counts and rounded half-up to three decimals (Decimal), so exact
ties round the same way everywhere. Stop = median (90th percentile) of the stopping index among
confirmations at N = 200, for every row with confirmations.
usage: python -I make_seq_table.py <summary_sequential.json> <out.tex>"""
import json
import sys
from decimal import ROUND_HALF_UP, Decimal

s = json.load(open(sys.argv[1], encoding="utf-8"))
by = {(c["dist"], c["budget"]): c for c in s["cells"]}
ROWS = [("nulls", None),
        ("unif0", r"$U(-1,1)$ & 0"), ("rademacher", r"$\pm1$, equal odds & 0"), ("gauss0", r"$N(0,1)$ & 0"),
        ("skew_mild", r"$+\tfrac13$ (0.75), $-1$ & 0"), ("skew0", r"$+\tfrac19$ (0.9), $-1$ & 0"),
        ("skewc0", r"skewed continuous & 0"),
        ("alts", None),
        ("skew+0.08", r"$+0.2$ (0.9), $-1$ & 0.08"), ("beta+0.2", r"$2\,\mathrm{Beta}(3,2)-1$ & 0.2"),
        ("unif+0.25", r"$U(-0.5,1)$ & 0.25"), ("unif+0.5", r"$U(0,1)$ & 0.5"),
        ("gauss+0.5", r"$N(0.5,1)$ & 0.5"), ("gauss+1.0", r"$N(1,1)$ & 1")]


def f3(k: int, n: int) -> str:
    if k == 0:
        return "0"
    if k == n:
        return "1"
    q = (Decimal(k) / Decimal(n)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if q == 0:
        return "$<$.001"
    if q == 1:
        return "$>$.999"
    return str(q).lstrip("0")


def num(x) -> str:
    return str(int(x)) if float(x).is_integer() else f"{float(x):.1f}"


lines = []
for key, label in ROWS:
    if key == "nulls":
        lines.append(r"\multicolumn{7}{@{}l}{\emph{Zero-mean nulls}} \\")
        continue
    if key == "alts":
        lines.append(r"\multicolumn{7}{@{}l}{\emph{Positive alternatives}} \\")
        continue
    cells = []
    for N in (20, 50, 200):
        c = by[(key, N)]
        assert abs(c["seq_confirmed"] / c["streams"] - c["seq_rate"]) < 1e-12
        assert abs(c["fixed_confirmed"] / c["streams"] - c["fixed_rate"]) < 1e-12
        cells.append(f"{f3(c['seq_confirmed'], c['streams'])}\\,/\\,{f3(c['fixed_confirmed'], c['streams'])}")
    c200 = by[(key, 200)]
    read = f"{c200['mean_read']:.0f}"
    if c200["seq_confirmed"]:
        stop = f"{num(c200['median_stop_confirmed'])} ({num(c200['p90_stop_confirmed'])})"
    else:
        stop = "--"
    lines.append(f"{label} & {' & '.join(cells)} & {read} & {stop} \\\\")
open(sys.argv[2], "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("\n".join(lines))
