"""Regression tests for the kit (standard library unittest; under a second).

usage (from the kit directory): python -I -S -m unittest discover -s tests -v
"""
from __future__ import annotations

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import frozen_rule as fr  # noqa: E402
import strict_mean_gate as sg  # noqa: E402
import sequential_mean_gate as sq  # noqa: E402

INF, NAN = float("inf"), float("nan")
SUP = (-1.0, 1.0)
BASIS = "metric in [0,1] by definition -> difference in [-1,1]"


def strict(d, **kw):
    kw.setdefault("support", SUP)
    kw.setdefault("support_basis", BASIS)
    return sg.strict_mean_gate(d, **kw)


class TheAuditedRuleReproducesThePaper(unittest.TestCase):
    """The behaviors the paper reports for the audited gate (Section 5.4, Appendices D and E)."""

    def test_every_all_positive_band_is_confirmed(self):
        rng = random.Random(1)
        for n in (2, 3, 4, 5, 8, 12):
            for _ in range(200):
                d = [rng.uniform(1e-6, 1.0) * rng.choice((1e-3, 1.0)) for _ in range(n)]
                self.assertTrue(fr.frozen_gate(d)["confirmed"], (n, d))

    def test_unsupported_routes_confirm(self):
        self.assertTrue(fr.frozen_gate([0.3])["confirmed"])                              # single value
        self.assertTrue(fr.frozen_gate([0.1] * 5)["confirmed"])                          # constant band
        self.assertTrue(fr.frozen_gate([2.0], declared_support=SUP)["confirmed"])         # outside support
        self.assertTrue(fr.frozen_gate([0.5, 2.0, 0.7], declared_support=SUP)["confirmed"])
        self.assertTrue(fr.frozen_gate([0.2] * 3, declared_support=(0.0, 1.0))["confirmed"])  # malformed
        self.assertTrue(fr.frozen_gate([INF])["confirmed"])
        self.assertTrue(fr.frozen_gate([INF, INF])["confirmed"])
        self.assertFalse(fr.frozen_gate([NAN])["confirmed"])
        self.assertFalse(fr.frozen_gate([])["confirmed"])

    def test_zero_variance_bypasses_the_opt_in_minimum(self):
        self.assertTrue(fr.frozen_gate([1 / 9] * 3, min_n="auto")["confirmed"])
        self.assertFalse(fr.frozen_gate([0.1, 0.2, 0.3], min_n="auto")["confirmed"])

    def test_declared_support_branch_cannot_confirm_at_n_le_7(self):
        for n in range(1, 8):
            self.assertLess(fr.declared_support_evalue([1.0] * n, support=SUP), 20.0)
        self.assertGreaterEqual(fr.declared_support_evalue([1.0] * 8, support=SUP), 20.0)


class TheStrictGateKeepsItsContract(unittest.TestCase):
    def test_statuses(self):
        cases = [
            ([0.01, 0.02, 0.015, 0.03, 0.012], dict(support=None), sg.NO_JUSTIFIED_SUPPORT),
            ([0.01, 0.02], dict(support_basis=""), sg.NO_JUSTIFIED_SUPPORT),
            ([0.2] * 3, dict(support=(0.0, 1.0)), sg.INVALID_SUPPORT),
            ([2.0], {}, sg.INVALID_INPUT),
            ([0.5, 2.0, 0.7], {}, sg.INVALID_INPUT),
            ([INF], {}, sg.INVALID_INPUT),
            ([NAN], {}, sg.INVALID_INPUT),
            ([True, 0.3], {}, sg.INVALID_INPUT),
            ([0.2, None, 0.3], {}, sg.INCOMPLETE),
            ([0.2, 0.3, 0.25, 0.4], dict(n_expected=5), sg.INCOMPLETE),
            ([], {}, sg.EMPTY),
            ([0.3], {}, sg.UNATTAINABLE),
            ([0.1] * 5, {}, sg.UNATTAINABLE),
            ([1.0] * 8, {}, sg.CONFIRMED),
            ([1.0, 1.0], dict(support=(-0.1, 1.0)), sg.CONFIRMED),
            ([0.1, -0.1] * 25, {}, sg.NOT_CONFIRMED),
        ]
        for d, kw, want in cases:
            r = strict(d, **kw)
            self.assertEqual(r["status"], want, (d, kw, r["reason"]))
            self.assertEqual(r["confirmed"], want == sg.CONFIRMED)

    def test_capacity_on_a_symmetric_support(self):
        for n in range(1, 8):
            self.assertEqual(strict([1.0] * n)["status"], sg.UNATTAINABLE)
        self.assertAlmostEqual(strict([1.0] * 8)["e_value"], 1.5 ** 8, places=9)

    def test_same_evalue_as_the_audited_declared_support_branch(self):
        rng = random.Random(2)
        for _ in range(300):
            a, b = -rng.choice((0.5, 1.0, 4.0)), rng.choice((0.5, 1.0, 4.0))
            d = [rng.uniform(a, b) for _ in range(rng.randint(1, 30))]
            e_old, e_new = fr.declared_support_evalue(d, support=(a, b)), sg.evalue(d, (a, b), 0.05)
            self.assertTrue(e_old == e_new or (e_old >= 1e6 and e_new >= 1e6), (e_old, e_new))

    def test_null_spot_check(self):
        rng = random.Random(3)
        k = sum(strict([1.0 if rng.random() < 0.5 else -1.0 for _ in range(20)])["confirmed"]
                for _ in range(1000))
        self.assertLessEqual(k / 1000, 0.05)

    def test_bad_alpha_raises(self):
        for bad in (0, 1, -0.1, True, "0.05", NAN):
            with self.assertRaises(ValueError):
                strict([0.1], alpha=bad)


def fractions_by_formula(xs, alpha):
    """The fractions of the paper's Appendix E, evaluated term by term from the printed formula."""
    mean_before = [(0.5 + sum(xs[:i])) / (i + 1) for i in range(len(xs))]        # the running mean before x_(i+1)
    out = []
    for t in range(1, len(xs) + 1):
        variance = (0.25 + sum((xs[i] - mean_before[i]) ** 2 for i in range(t - 1))) / t
        out.append(math.sqrt(2.0 * math.log(2.0 / alpha) / (variance * t * math.log(1 + t))))
    return out


class TheBettingFractionsFollowAppendixE(unittest.TestCase):
    def test_against_the_printed_formula(self):
        rng = random.Random(6)
        for _ in range(200):
            xs = [rng.random() for _ in range(rng.randint(0, 40))]
            alpha = rng.choice((0.05, 0.01, 0.2))
            want = fractions_by_formula(xs, alpha)
            for got in (sg.betting_fractions(xs, alpha), fr.plug_in_fractions(xs, alpha)):
                self.assertEqual(len(got), len(want))
                for g, w in zip(got, want):
                    self.assertTrue(math.isclose(g, w, rel_tol=1e-12), (g, w))

    def test_the_three_files_compute_the_same_fractions(self):
        rng = random.Random(7)
        for _ in range(200):
            xs = [rng.choice((0.0, 1.0, rng.random())) for _ in range(rng.randint(0, 60))]
            alpha = rng.choice((0.05, 0.01, 0.2))
            a, b = sg.betting_fractions(xs, alpha), fr.plug_in_fractions(xs, alpha)
            bets, c = sq.PlugInBets(alpha), []
            for x in xs:
                c.append(bets.fraction())
                bets.observe(x)
            self.assertEqual(a, b)
            self.assertEqual(a, c)


def seq(stream, **kw):
    kw.setdefault("support", SUP)
    kw.setdefault("support_basis", BASIS)
    kw.setdefault("budget", 50)
    return sq.sequential_mean_gate(stream, **kw)


class StopsWhereItShould:
    """Yields `values`; reading one more value fails the test."""

    def __init__(self, values):
        self.values, self.i = list(values), 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= len(self.values):
            raise AssertionError("the gate read past the value that should have stopped it")
        v = self.values[self.i]
        self.i += 1
        return v


class TheSequentialGateKeepsItsContract(unittest.TestCase):
    def test_short_budgets_abstain_before_reading(self):
        for budget in range(1, 8):
            r = seq(StopsWhereItShould([]), budget=budget)
            self.assertEqual((r["status"], r["n_read"]), (sq.UNATTAINABLE, 0))

    def test_stops_at_the_first_confirmation(self):
        r = seq(StopsWhereItShould([1.0] * 8), budget=200)
        self.assertEqual((r["status"], r["n_read"]), (sq.CONFIRMED, 8))
        self.assertAlmostEqual(r["e_value"], 1.5 ** 8, places=9)

    def test_failed_and_invalid_values_stop_the_read(self):
        for stream, want, n in (([0.1, None], sq.INCOMPLETE, 2), ([0.1, -0.1, NAN], sq.INVALID_INPUT, 3),
                                ([0.1, 2.0], sq.INVALID_INPUT, 2), ([0.1, True], sq.INVALID_INPUT, 2),
                                ([0.1, INF], sq.INVALID_INPUT, 2)):
            r = seq(StopsWhereItShould(stream))
            self.assertEqual((r["status"], r["n_read"]), (want, n), (stream, r["reason"]))
        r = seq([0.1, -0.1] * 3)                                   # the stream ends before the budget
        self.assertEqual((r["status"], r["n_read"]), (sq.INCOMPLETE, 6))
        self.assertEqual(seq([0.1, -0.1] * 25)["status"], sq.NOT_CONFIRMED)

    def test_same_evalue_as_the_strict_gate_at_every_stop(self):
        rng = random.Random(4)
        checked = 0
        for _ in range(400):
            a, b = -rng.choice((0.5, 1.0)), rng.choice((0.5, 1.0, 4.0))
            stream = [rng.uniform(a, b) + rng.choice((0.0, 0.3)) * b for _ in range(40)]
            stream = [min(v, b) for v in stream]
            budget = rng.randint(8, 40)
            r = seq(stream, support=(a, b), budget=budget)
            if r["status"] not in (sq.CONFIRMED, sq.NOT_CONFIRMED):
                continue
            t = r["n_read"]
            x = strict(stream[:t], support=(a, b), n_expected=t)
            self.assertEqual(r["e_value"], x["e_value"])
            self.assertEqual(r["status"] == sq.CONFIRMED, x["status"] == sg.CONFIRMED)
            checked += 1
        self.assertGreater(checked, 100)

    def test_null_spot_check(self):
        rng = random.Random(5)
        k = sum(seq([1.0 if rng.random() < 0.5 else -1.0 for _ in range(100)], budget=100)["confirmed"]
                for _ in range(1000))
        self.assertLessEqual(k / 1000, 0.05)

    def test_bad_arguments_raise(self):
        for bad in (dict(budget=0), dict(budget=True), dict(budget=8.0), dict(alpha=0.0), dict(alpha=1.0)):
            with self.assertRaises(ValueError, msg=repr(bad)):
                sq.sequential_mean_gate([1.0], support=SUP, support_basis=BASIS, **{"budget": 8, "alpha": 0.05, **bad})


if __name__ == "__main__":
    unittest.main()
