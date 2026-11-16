"""Run the pre-registered comparison (protocol.json) with this kit's files only.

usage: python -I -S run_protocol.py [--out results] [--cells N]
The audited gate comes from frozen_rule.py (rewritten for this kit; see PROVENANCE.md); the repaired
gate is strict_mean_gate.py. Identical seeded bands go to every gate. Output has the same format
as reference_results/ (written by the authors' run against the original code), so
compare_to_reference.py can check every band's outcome. --cells N runs only the first N cells
(a quick check; the full run takes about a minute and a half on one core).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import platform
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frozen_rule  # noqa: E402
import strict_mean_gate as sg  # noqa: E402

CODE = {"CONFIRMED": "C", "NOT_CONFIRMED": "N", "UNATTAINABLE": "U", "INVALID_INPUT": "I",
        "INVALID_SUPPORT": "S", "NO_JUSTIFIED_SUPPORT": "J", "INCOMPLETE": "P", "EMPTY": "E"}
DRAWS = {   # keyed by the exact draw strings of protocol.json; a mismatch is a KeyError
    "rng.gauss(0.0, 1.0)": lambda r: r.gauss(0.0, 1.0),
    "rng.uniform(-1.0, 1.0)": lambda r: r.uniform(-1.0, 1.0),
    "(1.0/9.0) if rng.random() < 0.9 else -1.0": lambda r: (1.0 / 9.0) if r.random() < 0.9 else -1.0,
    "rng.uniform(0.0, 2.0/9.0) if rng.random() < 0.9 else rng.uniform(-1.5, -0.5)":
        lambda r: r.uniform(0.0, 2.0 / 9.0) if r.random() < 0.9 else r.uniform(-1.5, -0.5),
    "rng.uniform(0.0, 1.0)": lambda r: r.uniform(0.0, 1.0),
    "rng.gauss(0.5, 1.0)": lambda r: r.gauss(0.5, 1.0),
    "rng.gauss(1.0, 1.0)": lambda r: r.gauss(1.0, 1.0),
    "1.0 if rng.random() < 0.5 else -1.0": lambda r: 1.0 if r.random() < 0.5 else -1.0,
    "(1.0/3.0) if rng.random() < 0.75 else -1.0": lambda r: (1.0 / 3.0) if r.random() < 0.75 else -1.0,
    "rng.uniform(-0.5, 1.0)": lambda r: r.uniform(-0.5, 1.0),
    "0.2 if rng.random() < 0.9 else -1.0": lambda r: 0.2 if r.random() < 0.9 else -1.0,
    "2.0 * rng.betavariate(3.0, 2.0) - 1.0": lambda r: 2.0 * r.betavariate(3.0, 2.0) - 1.0,
}
FROZEN_CFGS = {"frozen_default": dict(min_n=None, declared=False),
               "frozen_minN_auto": dict(min_n="auto", declared=False),
               "frozen_declared": dict(min_n=None, declared=True)}
BASIS = "synthetic generator support"


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def frozen_call(d, cfg, support):
    c = FROZEN_CFGS[cfg]
    return frozen_rule.frozen_gate(d, alpha=0.05, min_n=c["min_n"],
                                   declared_support=tuple(support) if (c["declared"] and support is not None) else None)


def parse_vals(v):
    if v == "20 x 1.0":
        return [1.0] * 20
    return [float(x) if isinstance(x, str) and x in ("inf", "-inf", "nan") else x for x in v]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", default=os.path.join(HERE, "protocol.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--cells", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    proto = json.load(open(a.protocol, encoding="utf-8"))
    t0 = time.time()
    done = 0
    with open(os.path.join(a.out, "raw_cells.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for i_n, n in enumerate(proto["n_values"]):
            reps = proto["reps"]["n<=12"] if n <= 12 else proto["reps"]["n>=20"]
            for i_d, dist in enumerate(proto["dist_order"]):
                if a.cells is not None and done >= a.cells:
                    break
                ds = proto["distributions"][dist]
                f, sup = DRAWS[ds["draw"]], ds["support"]
                seed = 20261115 + 1000 * i_n + 10 * i_d
                rng = random.Random(seed)
                bands = [[f(rng) for _ in range(n)] for _ in range(reps)]
                rec = dict(dist=dist, n=n, seed=seed, reps=reps, support=sup, role=ds["role"],
                           true_mean=ds["mean"], all_positive=sum(all(x > 0 for x in d) for d in bands))
                fr_decl = None
                for cfg in FROZEN_CFGS:
                    rs = [frozen_call(d, cfg, sup) for d in bands]
                    rec[cfg] = dict(codes="".join("1" if r["confirmed"] else "0" for r in rs),
                                    gates=dict(collections.Counter(r["branch"] for r in rs)))
                    if cfg == "frozen_declared":
                        fr_decl = rs
                st = [sg.strict_mean_gate(d, support=tuple(sup), support_basis=BASIS, alpha=0.05,
                                          n_expected=n) for d in bands]
                rec["strict"] = dict(codes="".join(CODE[r["status"]] for r in st))
                k = mis = dis = 0
                worst = 0.0
                for fr, s in zip(fr_decl, st):
                    if fr["branch"] != frozen_rule.BY_DECLARED_SUPPORT:
                        continue
                    k += 1
                    eo, en = fr["e_declared"], s["e_value"]
                    rel = abs(eo - en) / max(1.0, abs(eo)) if (eo is not None and en is not None) else math.inf
                    if not (eo == en or (eo >= 1e6 and en >= 1e6) or rel <= 1e-12):
                        mis += 1
                    if eo is not None and en is not None and eo < 1e6:
                        worst = max(worst, rel)
                    dis += fr["confirmed"] != s["confirmed"]
                rec["c4"] = dict(apriori_bands=k, evalue_mismatch=mis, decision_disagree=dis,
                                 max_rel_diff_below_cap=worst)
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                done += 1
                print(f"n={n:3d} {dist:10s} frozen default={rec['frozen_default']['codes'].count('1'):4d} "
                      f"strict confirmed={rec['strict']['codes'].count('C'):4d}  [{time.time() - t0:5.0f}s]",
                      flush=True)

    sup0 = proto["edge_cases_support"]
    edges = []
    for name, case in proto["edge_cases"].items():
        c = case if isinstance(case, dict) else {"diffs": case}
        vals = parse_vals(c["diffs"])
        sup = c["support"] if "support" in c else sup0
        basis = c.get("support_basis", BASIS)
        n_exp = c.get("n_expected", len(vals))
        row = dict(case=name, diffs=[repr(v) for v in vals], support=sup, n_expected=n_exp)
        if not c.get("strict_only"):
            fvals = parse_vals(c["frozen_sees"]) if "frozen_sees" in c else vals
            for cfg in ("frozen_default", "frozen_declared"):
                r = frozen_call(fvals, cfg, sup)
                row[cfg] = dict(confirmed=bool(r["confirmed"]), gate=r["branch"])
        s = sg.strict_mean_gate(vals, support=None if sup is None else tuple(sup),
                                support_basis=basis, alpha=0.05, n_expected=n_exp)
        row["strict"] = dict(status=s["status"], confirmed=s["confirmed"],
                             e_value=s["e_value"], reason=s["reason"])
        edges.append(row)
    json.dump(edges, open(os.path.join(a.out, "edge_cases.json"), "w", encoding="utf-8"), indent=1)
    meta = dict(protocol_sha256=sha256(a.protocol), strict_sha256=sha256(os.path.join(HERE, "strict_mean_gate.py")),
                strict_contract=sg.CONTRACT_VERSION, frozen_commit="frozen_rule.py (a rewrite; checked against 0cd5df96's recorded outcomes)",
                frozen_rule_sha256=sha256(os.path.join(HERE, "frozen_rule.py")),
                python=sys.version.split()[0], platform=platform.platform(), cells_run=done,
                started=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0)),
                seconds=round(time.time() - t0, 1))
    json.dump(meta, open(os.path.join(a.out, "run_meta.json"), "w", encoding="utf-8"), indent=1)
    print(f"done: {done} cells in {meta['seconds']} s -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
