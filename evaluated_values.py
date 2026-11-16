"""Check the kit's two gates against values recorded from the gate files evaluated for the paper.

The kit holds its own editions of the strict and sequential gates (PROVENANCE.md says why). The
evaluated files are not included, but reference_results/evaluated_gate_values.json holds what they
returned on 4,000 seeded bands. This script redraws the bands, calls the kit's gates and requires
every status and count to be the same and every e-value to agree to a relative 1e-12. It also
reports how many e-values are identical to the last bit: all of them on the platform of the
reference file; elsewhere the math library may round a logarithm differently in the last place.
Prints PASSED or FAILED.

usage: python -I -S evaluated_values.py
       python -I -S evaluated_values.py --record STRICT.py SEQUENTIAL.py OUT.json
The second form is how the reference file was made, from the evaluated files.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE = os.path.join(HERE, "reference_results", "evaluated_gate_values.json")
SEED = 2026111608
CASES = 4000
SUPPORTS = ([-1.0, 1.0], [-4.0, 4.0], [-0.5, 0.5], [-1.5, 1.5], [-0.1, 1.0], [-1.0, 0.1], [-2.5, 0.75])
ALPHAS = (0.05, 0.01, 0.1, 0.2)
SIZES = (1, 2, 3, 5, 7, 8, 9, 12, 20, 50, 100, 200)
BASIS = "synthetic generator support"
TOLERANCE = 1e-12


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def draw(rng: random.Random):
    """One case: a support, a level, a band and a budget. Only rng.random() is used, with exact
    arithmetic, so the bands are the same on every platform."""
    low, high = SUPPORTS[int(rng.random() * len(SUPPORTS))]
    alpha = ALPHAS[int(rng.random() * len(ALPHAS))]
    n = SIZES[int(rng.random() * len(SIZES))]
    kind = int(rng.random() * 6)
    span = high - low
    if kind == 0:                                     # anywhere on the support
        band = [low + span * rng.random() for _ in range(n)]
    elif kind == 1:                                   # near the top: confirmations
        band = [high - 0.1 * span * rng.random() for _ in range(n)]
    elif kind == 2:                                   # two points, mostly the top
        band = [high if rng.random() < 0.8 else low for _ in range(n)]
    elif kind == 3:                                   # the positive part
        band = [high * rng.random() for _ in range(n)]
    elif kind == 4:                                   # a small positive mean
        band = [0.3 * high + 0.25 * span * (rng.random() - 0.5) for _ in range(n)]
    else:                                             # may leave the support: refused as invalid
        band = [low + 1.02 * span * rng.random() for _ in range(n)]
    budget = SIZES[int(rng.random() * len(SIZES))]
    return (low, high), alpha, band, budget


def hexed(value):
    return None if value is None else float(value).hex()


def evaluate(strict, sequential):
    rng = random.Random(SEED)
    rows = []
    for _ in range(CASES):
        support, alpha, band, budget = draw(rng)
        fixed = strict.strict_mean_gate(band, support=support, support_basis=BASIS, alpha=alpha,
                                        n_expected=len(band))
        seq = sequential.sequential_mean_gate(iter(band), support=support, support_basis=BASIS, alpha=alpha,
                                              budget=budget)
        rows.append([fixed["status"], hexed(fixed["e_value"]), hexed(fixed["e_max"]),
                     seq["status"], seq["n_read"], hexed(seq["e_value"])])
    return rows


def close(a, b) -> bool:
    if a is None or b is None:
        return a is b
    x, y = float.fromhex(a), float.fromhex(b)
    return x == y or abs(x - y) <= TOLERANCE * max(abs(x), abs(y))


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main() -> None:
    if len(sys.argv) == 5 and sys.argv[1] == "--record":
        strict_path, sequential_path, out = sys.argv[2:5]
        rows = evaluate(load("evaluated_strict", strict_path), load("evaluated_sequential", sequential_path))
        record = dict(what="what the gate files evaluated for the paper return on the seeded bands of evaluated_values.py",
                      strict_sha256=sha256(strict_path), sequential_sha256=sha256(sequential_path),
                      seed=SEED, cases=CASES, python=sys.version.split()[0], platform=platform.platform(),
                      columns=["strict status", "strict e_value", "strict e_max", "sequential status",
                               "sequential n_read", "sequential e_value"],
                      rows=rows)
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(record, fh, separators=(",", ":"))
            fh.write("\n")
        print(f"recorded {len(rows)} cases -> {out}")
        return
    sys.path.insert(0, HERE)
    import sequential_mean_gate  # noqa: E402
    import strict_mean_gate  # noqa: E402
    reference = json.load(open(REFERENCE, encoding="utf-8"))
    if (reference["seed"], reference["cases"]) != (SEED, CASES):
        print("the reference file was made with another seed or case count")
        print("FAILED")
        sys.exit(1)
    rows = evaluate(strict_mean_gate, sequential_mean_gate)
    bad = []
    evalues = exact = 0
    for i, (mine, ref) in enumerate(zip(rows, reference["rows"])):
        if (mine[0], mine[3], mine[4]) != (ref[0], ref[3], ref[4]):
            bad.append((i, "status or count", mine[0], mine[3], mine[4], ref[0], ref[3], ref[4]))
            continue
        for j in (1, 2, 5):
            if mine[j] is not None or ref[j] is not None:
                evalues += 1
                exact += mine[j] == ref[j]
            if not close(mine[j], ref[j]):
                bad.append((i, reference["columns"][j], mine[j], ref[j]))
    statuses = {}
    for r in rows:
        statuses[r[0]] = statuses.get(r[0], 0) + 1
    print(f"compared {len(rows)} seeded bands under both gates with the values recorded from the evaluated files "
          f"(strict {reference['strict_sha256'][:12]}, sequential {reference['sequential_sha256'][:12]}; "
          f"{reference['platform']}, Python {reference['python']})")
    print("strict statuses: " + ", ".join(f"{k} {v}" for k, v in sorted(statuses.items())))
    print(f"e-values and capacities compared: {evalues}; identical to the last bit: {exact}")
    for b in bad[:20]:
        print("  MISMATCH", b)
    ok = not bad and len(rows) == len(reference["rows"]) == CASES
    print("PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
