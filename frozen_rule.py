"""The audited confirmation rule, written for this kit.

Given a band of paired holdout differences, `frozen_gate` returns the audited gate's decision and
the branch that made it. The file implements the specification in Appendix E of the paper: the
plug-in betting fractions, the declared-support branch, the default branch on the observed range,
and the refusal and degenerate branches. It was written with an AI coding assistant under the
paper author's direction, in a session that had read the audited code. Where Appendix E is silent
the file does what that code does, in its own words; PROVENANCE.md lists those points, compares
the file with the audited code, and states the inputs on which the two were found to agree. The
check anyone can rerun is `compare_to_reference.py`: the same decision and the same branch label
on every band of the protocol. The branch labels are the ones the reference results are keyed by.

THIS IS THE FLAWED RULE UNDER AUDIT. It is here so that its behavior can be reproduced. Do not
use it to certify anything. Standard library only.
"""
from __future__ import annotations

import math
import statistics

GRID_STEPS = 240        # Appendix E: "a 241-point grid of [0, 1]"
BET_CAP = 0.5           # c in Appendix E
EDGE = 1e-9             # a grid mean at either end of [0, 1] is moved in by this much for its bet ceilings
REPORT_CAP = 1e6        # no e-value above this is reported (Appendix H, criterion C4)
DECLARED_LEVEL = 0.05   # Appendix E: the declared-support branch bets at 0.05 whatever the gate's level
SMALLEST_LEVEL = 1e-9   # a smaller level counts as this one when a band size is derived from it
UP, DOWN = 1.0, -1.0    # the two one-sided bets: that the mean is larger, that it is smaller

# Branch labels, as the reference results are keyed.
BY_DECLARED_SUPPORT = "apriori_betting"
BY_OBSERVED_RANGE = "eprocess"
SHORT_BAND_SUFFIX = "_underpowered_n{n}"
REFUSED = "underpowered_holdout_n{n}_min{minimum}"
BY_SIGN = "sign_only"
BY_SIGN_SUPPORT_UNUSED = "sign_only_support_violation"


def required_n(alpha: float) -> int:
    """ceil(log2(1/alpha)), and at least 2: below this band size the default branch is labelled
    underpowered, and this is the minimum that "auto" stands for."""
    level = max(alpha, SMALLEST_LEVEL)
    halvings = math.log2(1.0 / level)
    return max(2, math.ceil(halvings))


def minimum_band(alpha: float, min_n) -> int:
    """The opt-in minimum band size as a number. None gives 0 (no minimum); "auto" gives
    required_n(alpha), and so does 1, which the audited setting reads as "auto"."""
    if min_n == "auto" or min_n == 1:
        return required_n(alpha)
    return max(0, int(min_n or 0))


def on_unit_scale(value: float, low, span) -> float:
    """(value - low) / span, held inside [0, 1]; a value that is not a number lands on 0."""
    x = (value - low) / span
    if not x > 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def zero_on_unit_scale(low, span):
    """m_0 of Appendix E: where zero falls when the support is mapped onto [0, 1].

    A support that does not straddle zero still gets an answer: None when zero is at or above its
    top (no bet is placed and the e-value is 1), and 1e-6 when zero is at or below its bottom.
    """
    position = -low / span
    if position >= 1.0:
        return None
    return position if position > 0.0 else 1e-6


def plug_in_fractions(x, alpha: float) -> list:
    """The predictable fractions of Appendix E for data x on [0, 1].

    The fraction for step t uses only x_1 .. x_(t-1): a running mean started at 1/2 and a running
    variance started at 1/4, in which each value is centered at the running mean before it.
    """
    log_term = math.log(2.0 / alpha)
    fractions = []
    total = 0.0
    spread = 0.0
    for t, value in enumerate(x, start=1):
        variance = (0.25 + spread) / t
        fractions.append(math.sqrt(2.0 * log_term / (variance * t * math.log(t + 1))))
        spread += (value - (0.5 + total) / t) ** 2
        total += value
    return fractions


def capital_path(pairs, mean: float, ceiling: float, side: float):
    """Yield K_1 .. K_n: the capital, after each value, of the one-sided bet `side` against `mean`.

    `pairs` holds (value, fraction) for values on [0, 1]; no bet exceeds `ceiling`.
    """
    capital = 1.0
    for value, fraction in pairs:
        bet = fraction
        if not bet < ceiling:
            bet = ceiling
        capital *= 1.0 + side * bet * (value - mean)
        yield capital


def bet_ceiling(mean: float, side: float) -> float:
    """The largest bet against `mean`: c/m for the bet that the mean is larger, c/(1 - m) for the
    bet that it is smaller. A mean at either end of [0, 1] is moved in by EDGE first, which keeps
    both ceilings finite."""
    if mean < EDGE:
        inside = EDGE
    elif mean > 1.0 - EDGE:
        inside = 1.0 - EDGE
    else:
        inside = mean
    return BET_CAP / (inside if side > 0 else 1.0 - inside)


def excluded(pairs, mean: float, threshold: float) -> bool:
    """Is `mean` ruled out: does the capital of either one-sided bet reach the threshold at some step?"""
    for side in (UP, DOWN):
        path = capital_path(pairs, mean, bet_ceiling(mean, side), side)
        if any(capital >= threshold for capital in path):
            return True
    return False


def observed_range_lower_end(values, alpha: float) -> float:
    """L_n of the default branch: the smallest grid mean that the bets do not rule out.

    The support is the observed range of the same values. If every grid mean is ruled out, the
    sample mean is returned.
    """
    low = min(values)
    span = max(values) - low
    if span <= 0:
        return -math.inf
    x = [on_unit_scale(v, low, span) for v in values]
    pairs = list(zip(x, plug_in_fractions(x, alpha)))
    threshold = 2.0 / alpha                          # a union bound over the two sides
    grid = (step / GRID_STEPS for step in range(GRID_STEPS + 1))
    kept = next((m for m in grid if not excluded(pairs, m, threshold)), None)
    if kept is None:
        return sum(values) / len(values)
    return low + kept * span


def declared_support_evalue(values, support) -> float:
    """E_n of the declared-support branch: the capital from betting that the mean exceeds zero.

    `support` is a pair (a, b). Values outside it are moved to its nearer end, and a support of
    no width gives 1.
    """
    low, high = support
    span = high - low
    if not values or span <= 0:
        return 1.0
    x = [on_unit_scale(float(v), low, span) for v in values]
    null = zero_on_unit_scale(low, span)
    if null is None:
        return 1.0
    pairs = list(zip(x, plug_in_fractions(x, DECLARED_LEVEL)))
    capital = list(capital_path(pairs, null, BET_CAP / null, UP))[-1]
    if not math.isfinite(capital):
        return REPORT_CAP
    return min(capital, REPORT_CAP)


def support_holds(band, low: float, high: float) -> bool:
    """Can the declared support be used: a < 0 < b, and every value inside [a, b]?"""
    if not low < 0.0 < high:
        return False
    return all(low <= value <= high for value in band)


def frozen_gate(differences, *, alpha: float = 0.05, declared_support=None, min_n=None) -> dict:
    """The audited decision for one band.

    `alpha` is a level between 1e-9 and 1. `declared_support` is None or a pair of numbers.
    `min_n` is the opt-in minimum band size: None for none, "auto" (or 1) for required_n(alpha),
    or a whole number from 2 up. PROVENANCE.md says what was compared with the audited gate
    inside these limits and how the two differ outside them.

    Returns the decision (`confirmed`), the branch label (`branch`), the declared-support
    e-value (`e_declared`: whenever a support was given, except where the sign decides), the
    default branch's lower end when it ran and is finite (`lower_end`), the mean and the band size.
    """
    band = list(map(float, differences))
    report = {"confirmed": False, "branch": None, "e_declared": None, "lower_end": None, "mean": None,
              "n": len(band)}
    if not band:
        return report
    report["mean"] = statistics.fmean(band)
    usable = False
    if declared_support is not None:
        low = float(declared_support[0])
        high = float(declared_support[1])
        report["e_declared"] = declared_support_evalue(band, tuple(declared_support))
        usable = support_holds(band, low, high)
    minimum = minimum_band(alpha, min_n)

    if usable:
        # Declared-support branch: the e-value alone decides, at any band size.
        report["branch"] = BY_DECLARED_SUPPORT
        report["confirmed"] = report["e_declared"] >= 1.0 / alpha
    elif len(set(band)) < 2:
        # One value, or all values equal: the sign of the mean decides. A declared support that
        # could not be used is dropped from the report.
        report["confirmed"] = report["mean"] > 0
        if declared_support is None:
            report["branch"] = BY_SIGN
        else:
            report["branch"] = BY_SIGN_SUPPORT_UNUSED
            report["e_declared"] = None
    elif minimum and len(band) < minimum:
        # Refusal: a minimum is set and the band is shorter.
        report["branch"] = REFUSED.format(n=len(band), minimum=minimum)
    else:
        # Default branch: the support is the observed range of the values under test.
        level = 1.0 - (1.0 - alpha)                  # the level as the audited call forms it, from 1 - alpha
        lower = observed_range_lower_end(band, level)
        if math.isfinite(lower):
            report.update(lower_end=lower, confirmed=lower > 0)
        report["branch"] = BY_OBSERVED_RANGE
        if len(band) < required_n(alpha):
            report["branch"] += SHORT_BAND_SUFFIX.format(n=len(band))
    return report
