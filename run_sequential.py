"""Run the pre-registered comparison of docs/paper236/protocol_sequential.json: the sequential
strict gate against the fixed-band strict gate, on identical synthetic streams.

usage: python -I run_sequential.py --base <protocol.json> --protocol <protocol_sequential.json>
         --sequential <sequential_mean_gate.py> --strict <strict_mean_gate.py> --out <dir>
         [--streams K]   (K < 10,000 only for a dry run into a different --out)
Writes raw_sequential.jsonl (one line per distribution x budget: every stream's outcome under
both gates, in order), edge_cases_sequential.json and run_meta_sequential.json. Summaries come
from summarize_sequential.py.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import random
import sys
import time
import os

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
BASIS = "synthetic generator support"


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Tail:
    """Yields `values`, then raises if read again (edge case Q03)."""

    def __init__(self, values):
        self.values, self.i = list(values), 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= len(self.values):
            raise RuntimeError("read past the stopping value")
        v = self.values[self.i]
        self.i += 1
        return v


def edge_stream(spec):
    if spec == "8 x 1.0":
        return [1.0] * 8
    if spec == "8 x 1.0, then an item whose read raises":
        return Tail([1.0] * 8)
    if spec == "5 x 1.0":
        return [1.0] * 5
    if spec == "20 x -1.0":
        return [-1.0] * 20
    if spec == "8 x 1.0, then 5.0":
        return [1.0] * 8 + [5.0]
    return [float(x) if isinstance(x, str) and x in ("inf", "-inf", "nan") else x for x in spec]


def rel(x, y):
    return abs(x - y) / max(1.0, abs(y))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--sequential", required=True)
    ap.add_argument("--strict", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--streams", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    base = json.load(open(a.base, encoding="utf-8"))
    proto = json.load(open(a.protocol, encoding="utf-8"))
    sq = load(a.sequential, "sequential_mean_gate_eval")
    sg = load(a.strict, "strict_mean_gate_eval")
    R = proto["streams_per_distribution"] if a.streams is None else a.streams
    L = proto["stream_length"]
    budgets = proto["budgets"]
    assert max(budgets) <= L
    t0 = time.time()

    with open(os.path.join(a.out, "raw_sequential.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for i_d, dist in enumerate(proto["dist_order"]):
            ds = base["distributions"][dist]
            f, sup = DRAWS[ds["draw"]], tuple(ds["support"])
            seed = 20261116 + 10 * i_d
            rng = random.Random(seed)
            cells = {N: dict(seq_codes=[], seq_n=[], fix_codes=[], s4_fixed_not_seq=0, s4_prefix_not_confirmed=0,
                             s5_mismatch=0, s5_checked=0, s5_worst=0.0) for N in budgets}
            for _ in range(R):
                stream = [f(rng) for _ in range(L)]
                for N in budgets:
                    c = cells[N]
                    r = sq.sequential_mean_gate(iter(stream), support=sup, support_basis=BASIS, alpha=0.05,
                                                budget=N)
                    x = sg.strict_mean_gate(stream[:N], support=sup, support_basis=BASIS, alpha=0.05,
                                            n_expected=N)
                    c["seq_codes"].append(CODE[r["status"]])
                    c["seq_n"].append(r["n_read"])
                    c["fix_codes"].append(CODE[x["status"]])
                    if x["status"] == "CONFIRMED" and r["status"] != "CONFIRMED":
                        c["s4_fixed_not_seq"] += 1
                    if r["status"] == "CONFIRMED":
                        t = r["n_read"]
                        p = x if t == N else sg.strict_mean_gate(stream[:t], support=sup, support_basis=BASIS,
                                                                 alpha=0.05, n_expected=t)
                        if p["status"] != "CONFIRMED":
                            c["s4_prefix_not_confirmed"] += 1
                        ref = p["e_value"]
                    elif r["status"] == "NOT_CONFIRMED":
                        ref = x["e_value"]
                    else:
                        ref = None
                    if ref is not None:
                        c["s5_checked"] += 1
                        d = rel(r["e_value"], ref)
                        c["s5_worst"] = max(c["s5_worst"], d)
                        c["s5_mismatch"] += d > 1e-12
            for N in budgets:
                c = cells[N]
                rec = dict(dist=dist, budget=N, seed=seed, streams=R, support=list(sup), role=ds["role"],
                           true_mean=ds["mean"], seq_codes="".join(c["seq_codes"]), seq_n=c["seq_n"],
                           fix_codes="".join(c["fix_codes"]),
                           s4=dict(fixed_confirmed_sequential_not=c["s4_fixed_not_seq"],
                                   prefix_not_confirmed=c["s4_prefix_not_confirmed"]),
                           s5=dict(checked=c["s5_checked"], mismatch=c["s5_mismatch"], worst_rel=c["s5_worst"]))
                fh.write(json.dumps(rec) + "\n")
                print(f"{dist:10s} N={N:3d} seq C={rec['seq_codes'].count('C'):5d} I={rec['seq_codes'].count('I'):4d} "
                      f"fixed C={rec['fix_codes'].count('C'):5d}  mean read {sum(c['seq_n']) / R:6.1f}  "
                      f"s4 {c['s4_fixed_not_seq']}/{c['s4_prefix_not_confirmed']} s5 {c['s5_mismatch']}/{c['s5_checked']}"
                      f"  [{time.time() - t0:5.0f}s]", flush=True)
            fh.flush()

    sup0 = tuple(proto["edge_cases_support"])
    edges = []
    for name, case in proto["edge_cases"].items():
        sup = case["support"] if "support" in case else sup0
        basis = case.get("support_basis", BASIS)
        stream = edge_stream(case["stream"])
        try:
            r = sq.sequential_mean_gate(stream, support=None if sup is None else tuple(sup), support_basis=basis,
                                        alpha=0.05, budget=case["budget"])
            got = dict(status=r["status"], n_read=r["n_read"], e_value=r["e_value"], reason=r["reason"])
        except Exception as e:  # noqa: BLE001 -- an exception is an outcome to report
            got = dict(status=f"EXCEPTION {type(e).__name__}: {e}", n_read=None, e_value=None, reason="")
        edges.append(dict(case=name, expect=case["expect"], expect_n_read=case["n_read"], **got,
                          ok=got["status"] == case["expect"] and got["n_read"] == case["n_read"]))
    errors = []
    for bad in (dict(budget=0), dict(budget=True), dict(budget=8, alpha=0.0)):
        try:
            sq.sequential_mean_gate([1.0], support=sup0, support_basis=BASIS, **{"alpha": 0.05, **bad})
            errors.append(dict(args=repr(bad), raised=None, ok=False))
        except ValueError as e:
            errors.append(dict(args=repr(bad), raised=f"ValueError: {e}", ok=True))
    json.dump(dict(cases=edges, errors=errors), open(os.path.join(a.out, "edge_cases_sequential.json"), "w",
                                                     encoding="utf-8"), indent=1)

    meta = dict(protocol_sha256=sha256(a.protocol), base_protocol_sha256=sha256(a.base),
                sequential_sha256=sha256(a.sequential), strict_sha256=sha256(a.strict),
                sequential_contract=sq.CONTRACT_VERSION, strict_contract=sg.CONTRACT_VERSION,
                streams=R, dry_run=a.streams is not None, python=sys.version.split()[0],
                platform=platform.platform(), started=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0)),
                seconds=round(time.time() - t0, 1))
    json.dump(meta, open(os.path.join(a.out, "run_meta_sequential.json"), "w", encoding="utf-8"), indent=1)
    print(f"done in {meta['seconds']} s; edge cases {sum(e['ok'] for e in edges)}/{len(edges)} ok; "
          f"errors {sum(e['ok'] for e in errors)}/{len(errors)} ok", flush=True)


if __name__ == "__main__":
    main()
