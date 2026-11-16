"""Sequential strict holdout gate: read paired differences one fresh instance at a time and stop
at the first level-alpha confirmation, or after a budget fixed in advance.

Contract paper236-sequential-gate-1.0 (the paper's Appendix H). It extends the strict gate
(strict_mean_gate.py, paper236-strict-gate-1.0) without changing it: the same predictable betting
e-process, computed one value at a time in the same arithmetic order, so on any prefix of valid
values the e-value equals the strict gate's. Under H0 (E[d_i | past] <= 0) it is a nonnegative
supermartingale with E_0 = 1, so P(exists t <= N: E_t >= 1/alpha) <= alpha (Ville's inequality):
stopping early keeps the level. Standard library only and self-contained. Not wired into any live
path.

THIS IS THE KIT'S EDITION. The file evaluated for the paper carried the betting-fraction
arithmetic of the audited system, which is not released. Here the constants, `PlugInBets`,
`_on_unit_scale`, `max_evalue` and the arithmetic inside the reading loop are written anew, with
the same arithmetic in the same order (a floor under the fraction's denominator that could not
bind is left out). The validation, the statuses and the messages are the evaluated file's.
PROVENANCE.md gives the evidence that the two editions return identical results.
"""
from __future__ import annotations

import math
import numbers

CONTRACT_VERSION = "paper236-sequential-gate-1.0"
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
STATUSES = (CONFIRMED, NOT_CONFIRMED, UNATTAINABLE, NO_JUSTIFIED_SUPPORT, INVALID_SUPPORT,
            INVALID_INPUT, INCOMPLETE)


def _is_real(v) -> bool:
    return isinstance(v, numbers.Real) and not isinstance(v, bool)


def _as_float(v):
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


def _on_unit_scale(value: float, low: float, span: float) -> float:
    """(value - low) / span held inside [0, 1]: a guard against float rounding at the ends of the
    support, as in the strict gate; the value has been validated before."""
    x = (value - low) / span
    if not x > 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def max_evalue(n: int, support, c: float = BET_CAP_C) -> float:
    """Largest e-value any n values can reach on this support: (1 + (c/m0)(1-m0))^n."""
    low = float(support[0])
    null = -low / (float(support[1]) - low)              # zero on the unit scale: m0 = -a/(b-a)
    best_factor = 1.0 + (c / null) * (1.0 - null)
    try:
        return best_factor ** n
    except OverflowError:
        return math.inf


def sequential_mean_gate(stream, *, support=None, support_basis=None, alpha: float = 0.05,
                         budget: int) -> dict:
    """Decide, reading at most `budget` values of `stream` in order, whether the paired holdout
    differences give level-alpha evidence of a positive mean.

    stream: an iterable of differences in the pre-registered instance order; a failed
      observation is yielded as None. It is read lazily and never past the stopping value.
    support: the declared (a, b), a < 0 < b, fixed before evaluation; support_basis: a
      non-empty record of where it comes from. budget: the largest number of instances the gate
      may read, fixed before evaluation.
    """
    if not (_is_real(alpha) and 0.0 < float(alpha) < 1.0):
        raise ValueError(f"alpha must be a number in (0, 1), got {alpha!r}")
    if not (isinstance(budget, int) and not isinstance(budget, bool) and budget >= 1):
        raise ValueError(f"budget must be an int >= 1, got {budget!r}")
    alpha = float(alpha)
    thr = 1.0 / alpha
    out = {"status": None, "confirmed": False, "contract": CONTRACT_VERSION, "alpha": alpha,
           "threshold": thr, "budget": budget, "support": None, "support_basis": support_basis,
           "n_read": 0, "stop_index": None, "e_value": None, "e_max": None, "reason": ""}

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
    out["e_max"] = max_evalue(budget, (a, b))
    if out["e_max"] < thr:
        return done(UNATTAINABLE, f"a budget of {budget} can reach at most E={out['e_max']:.4g} "
                                  f"< 1/alpha={thr:.4g}; no instance read")

    span = b - a
    null = -a / span                                # zero on the unit scale: m0 = -a/(b-a)
    ceiling = BET_CAP_C / null
    bets = PlugInBets(alpha)
    capital = 1.0
    source = iter(stream)
    for t in range(budget):                    # t is 0-based; the value read is the (t+1)-th
        try:
            v = next(source)
        except StopIteration:
            out["stop_index"] = t
            return done(INCOMPLETE, f"the stream ended after {t} of {budget} values; no decision")
        out["n_read"] = t + 1
        out["stop_index"] = t + 1
        if v is None:
            return done(INCOMPLETE, f"observation {t + 1} failed; no decision on a partial stream")
        if not _is_real(v):
            return done(INVALID_INPUT, f"non-numeric value {v!r} at {t + 1}")
        f = _as_float(v)
        if f is None or not math.isfinite(f):
            return done(INVALID_INPUT, f"nonfinite or unrepresentable value {v!r} at {t + 1}")
        if not (a <= f <= b):
            return done(INVALID_INPUT, f"value {f!r} at {t + 1} outside the declared support [{a}, {b}]")
        x = _on_unit_scale(f, a, span)
        bet = bets.fraction()
        if not bet < ceiling:
            bet = ceiling
        payoff = bet * (x - null)
        capital *= 1.0 + payoff
        bets.observe(x)
        out["e_value"] = capital
        if capital >= thr:
            return done(CONFIRMED, f"E={capital:.4g} >= 1/alpha={thr:.4g} after {t + 1} instances")
    return done(NOT_CONFIRMED, f"E={capital:.4g} < 1/alpha={thr:.4g} after the budget of {budget}")


__all__ = ["sequential_mean_gate", "max_evalue", "PlugInBets", "STATUSES", "CONTRACT_VERSION", "CONFIRMED",
           "NOT_CONFIRMED", "UNATTAINABLE", "NO_JUSTIFIED_SUPPORT", "INVALID_SUPPORT",
           "INVALID_INPUT", "INCOMPLETE"]
