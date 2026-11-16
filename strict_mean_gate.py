"""Strict holdout confirmation gate: a level-alpha test that the mean paired difference is positive.

Contract paper236-strict-gate-1.0 (the paper's Appendix H). Standard library only and
self-contained, so it can be audited, tested and copied as one file. Not wired into any live path.

H0: E[d_i | d_1..d_{i-1}] <= 0, every d_i in a declared support [a, b] with a < 0 < b, the
support justified independently of the data (normally the metric's definition) and fixed before
the holdout is evaluated, the order and the band size fixed in advance. The e-value is the
one-sided betting capital of Waudby-Smith & Ramdas with the predictable plug-in fractions of the
paper's Appendix E (priors 1/2 and 1/4, truncated at c/m0 with c = 1/2); the gate confirms iff
E_n >= 1/alpha, evaluated once at the complete band. Under H0, E_t is a nonnegative
supermartingale with E_0 = 1, so the level is alpha by Ville's inequality.

Only status CONFIRMED sets confirmed=True. Every other status says why there is no confirmation.
The decision is E_n >= 1/alpha, and the capacity decides UNATTAINABLE; the mean, and an e-value
reported with any other status, are descriptive.

THIS IS THE KIT'S EDITION. The file evaluated for the paper computed the betting fractions with a
function of the audited system, which is not released. Here the constants, `PlugInBets`,
`betting_fractions`, `_on_unit_scale`, `max_evalue` and `evalue` are written anew, with the same
arithmetic in the same order (a floor under the fraction's denominator that could not bind is
left out). The validation helpers and the decision function `strict_mean_gate` are the evaluated
file's, unchanged. PROVENANCE.md gives the evidence that the two editions return identical
results, and says where the two helper functions differ on invalid arguments.
"""
from __future__ import annotations

import math
import numbers

CONTRACT_VERSION = "paper236-strict-gate-1.0"
BET_CAP_C = 0.5          # c: no bet exceeds c / m0
PRIOR_MEAN = 0.5         # the running mean starts as if one value of 1/2 had been seen
PRIOR_VARIANCE = 0.25    # and the running variance as if one squared deviation of 1/4 had

CONFIRMED = "CONFIRMED"
NOT_CONFIRMED = "NOT_CONFIRMED"
UNATTAINABLE = "UNATTAINABLE"
NO_JUSTIFIED_SUPPORT = "NO_JUSTIFIED_SUPPORT"
INVALID_SUPPORT = "INVALID_SUPPORT"
INVALID_INPUT = "INVALID_INPUT"
INCOMPLETE = "INCOMPLETE"
EMPTY = "EMPTY"
STATUSES = (CONFIRMED, NOT_CONFIRMED, UNATTAINABLE, NO_JUSTIFIED_SUPPORT, INVALID_SUPPORT,
            INVALID_INPUT, INCOMPLETE, EMPTY)
ABSTENTIONS = frozenset({UNATTAINABLE, NO_JUSTIFIED_SUPPORT, INCOMPLETE, EMPTY})
INVALID = frozenset({INVALID_SUPPORT, INVALID_INPUT})


def _is_real(v) -> bool:
    return isinstance(v, numbers.Real) and not isinstance(v, bool)


def _as_float(v):
    """float(v) for a real number, or None if it cannot be represented (e.g. a huge int)."""
    try:
        return float(v)
    except (OverflowError, TypeError, ValueError):
        return None


class PlugInBets:
    """The predictable betting fractions of the paper's Appendix E, for data on [0, 1].

    lambda_t = sqrt(2 ln(2/alpha) / (s2_(t-1) t ln(1 + t))), with m_(t-1) = (1/2 + sum_(i<t) x_i) / t
    and s2_(t-1) = (1/4 + sum_(i<t) (x_i - m_(i-1))^2) / t: each value is centered at the running
    mean before it. `fraction()` is the bet on the next value, computed from the values observed
    so far, so no value enters its own bet.
    """

    def __init__(self, alpha: float) -> None:
        self._log_term = math.log(2.0 / alpha)
        self._seen = 0
        self._sum = 0.0
        self._squares = 0.0      # sum of squared deviations, each from the mean before its value

    def fraction(self) -> float:
        t = self._seen + 1
        variance = (PRIOR_VARIANCE + self._squares) / t
        return math.sqrt(2.0 * self._log_term / (variance * t * math.log(t + 1)))

    def observe(self, x: float) -> None:
        t = self._seen + 1
        mean_before = (PRIOR_MEAN + self._sum) / t
        self._sum += x
        self._squares += (x - mean_before) ** 2
        self._seen = t


def betting_fractions(unit_values, alpha: float) -> list:
    """lambda_1..lambda_n for values already on [0, 1]; lambda_t uses only the values before t."""
    bets = PlugInBets(alpha)
    fractions = []
    for x in unit_values:
        fractions.append(bets.fraction())
        bets.observe(x)
    return fractions


def _on_unit_scale(value: float, low: float, span: float) -> float:
    """(value - low) / span held inside [0, 1]: a guard against float rounding at the ends of the
    support, not a clip of the data, which the gate has validated before."""
    x = (value - low) / span
    if not x > 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def max_evalue(n: int, support, c: float = BET_CAP_C) -> float:
    """Largest e-value any band of n values can reach on this support: (1 + (c/m0)(1-m0))^n."""
    low = float(support[0])
    null = -low / (float(support[1]) - low)              # zero on the unit scale: m0 = -a/(b-a)
    best_factor = 1.0 + (c / null) * (1.0 - null)
    try:
        return best_factor ** n
    except OverflowError:
        return math.inf


def evalue(values, support, alpha: float, c: float = BET_CAP_C) -> float:
    """One-sided betting e-value for mean > 0 on a declared support. Inputs must already be
    validated (finite, inside the support); nothing is clipped here except float rounding."""
    low = float(support[0])
    span = float(support[1]) - low
    null = -low / span                                    # zero on the unit scale: m0 = -a/(b-a)
    ceiling = c / null
    bets = PlugInBets(alpha)
    capital = 1.0
    for value in values:
        x = _on_unit_scale(value, low, span)
        bet = bets.fraction()
        if not bet < ceiling:
            bet = ceiling
        payoff = bet * (x - null)
        capital *= 1.0 + payoff
        bets.observe(x)
    return capital


def strict_mean_gate(diffs, *, support=None, support_basis=None, alpha: float = 0.05,
                     n_expected: int | None = None) -> dict:
    """Decide whether the paired holdout differences give level-alpha evidence of a positive mean.

    diffs: the band in its pre-registered order; a failed observation is passed as None (never
      dropped). support: the declared (a, b), a < 0 < b, fixed before evaluation.
      support_basis: a non-empty record of where the support comes from (e.g. the metric's
      definition). n_expected: the pre-registered band size, if the caller knows it.
    """
    if not (_is_real(alpha) and 0.0 < float(alpha) < 1.0):
        raise ValueError(f"alpha must be a number in (0, 1), got {alpha!r}")
    if n_expected is not None and not (isinstance(n_expected, int)
                                       and not isinstance(n_expected, bool) and n_expected >= 0):
        raise ValueError(f"n_expected must be a non-negative int or None, got {n_expected!r}")
    alpha = float(alpha)
    vals = [] if diffs is None else list(diffs)
    finite = [f for f in (_as_float(v) for v in vals if _is_real(v))
              if f is not None and math.isfinite(f)]
    out = {"status": None, "confirmed": False, "contract": CONTRACT_VERSION, "alpha": alpha,
           "threshold": 1.0 / alpha, "support": None, "support_basis": support_basis,
           "n_values": len(vals), "n_valid": None, "n_failed": sum(v is None for v in vals),
           "n_expected": n_expected, "e_value": None, "e_max": None,
           "mean": (math.fsum(finite) / len(finite)) if finite else None, "reason": ""}

    def done(status: str, reason: str) -> dict:
        out["status"], out["confirmed"], out["reason"] = status, status == CONFIRMED, reason
        return out

    if support is None:
        return done(NO_JUSTIFIED_SUPPORT, "no support declared; the data cannot supply one")
    if not (isinstance(support_basis, str) and support_basis.strip()):
        return done(NO_JUSTIFIED_SUPPORT, "support declared without a recorded basis")
    try:
        a, b = support
    except (TypeError, ValueError):
        return done(INVALID_SUPPORT, "support is not a pair (a, b)")
    a = _as_float(a) if _is_real(a) else None
    b = _as_float(b) if _is_real(b) else None
    if a is None or b is None or not (math.isfinite(a) and math.isfinite(b)):
        return done(INVALID_SUPPORT, "support bounds must be finite numbers")
    if not (a < 0.0 < b):
        return done(INVALID_SUPPORT, "support must satisfy a < 0 < b")
    out["support"] = (a, b)

    xs = []
    for v in vals:
        if v is None:
            continue
        if not _is_real(v):
            return done(INVALID_INPUT, f"non-numeric value {v!r}")
        f = _as_float(v)
        if f is None or not math.isfinite(f):
            return done(INVALID_INPUT, f"nonfinite or unrepresentable value {v!r}")
        if not (a <= f <= b):
            return done(INVALID_INPUT, f"value {f!r} outside the declared support [{a}, {b}]")
        xs.append(f)
    if n_expected is not None and len(vals) > n_expected:
        return done(INVALID_INPUT, f"{len(vals)} values for a band of {n_expected}")
    out["n_valid"] = n = len(xs)
    out["e_max"] = max_evalue(n, (a, b))
    if n:
        out["e_value"] = evalue(xs, (a, b), alpha)

    if out["n_failed"] or (n_expected is not None and len(vals) < n_expected):
        return done(INCOMPLETE, f"{n} usable of {n_expected if n_expected is not None else len(vals)}"
                                f" expected ({out['n_failed']} failed); no decision on a partial band")
    if n == 0:
        return done(EMPTY, "no observations")
    if out["e_max"] < out["threshold"]:
        return done(UNATTAINABLE, f"a band of {n} can reach at most E={out['e_max']:.4g} "
                                  f"< 1/alpha={out['threshold']:.4g}; no data could confirm")
    if out["e_value"] >= out["threshold"]:
        return done(CONFIRMED, f"E={out['e_value']:.4g} >= 1/alpha={out['threshold']:.4g}")
    return done(NOT_CONFIRMED, f"E={out['e_value']:.4g} < 1/alpha={out['threshold']:.4g}")


__all__ = ["strict_mean_gate", "evalue", "max_evalue", "betting_fractions", "PlugInBets", "STATUSES",
           "ABSTENTIONS", "INVALID", "CONTRACT_VERSION", "CONFIRMED", "NOT_CONFIRMED",
           "UNATTAINABLE", "NO_JUSTIFIED_SUPPORT", "INVALID_SUPPORT", "INVALID_INPUT",
           "INCOMPLETE", "EMPTY"]
