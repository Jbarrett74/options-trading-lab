"""Option and risk formulas used by the research and paper-trading routines.

Every function documents its units. See docs/equations.md for the math and sources.
Prices are per share; multiply by 100 for one contract.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

SQRT_2PI = math.sqrt(2.0 * math.pi)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


# ---------------------------------------------------------------- Black-Scholes
def d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0):
    """T in years, r/sigma/q as annual decimals."""
    if T <= 0 or sigma <= 0:
        raise ValueError("T and sigma must be positive")
    vt = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / vt
    return d1, d1 - vt


def bs_price(S, K, T, r, sigma, kind="call", q=0.0):
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    if kind == "call":
        return S * math.exp(-q * T) * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * math.exp(-q * T) * norm_cdf(-d1)


def bs_greeks(S, K, T, r, sigma, kind="call", q=0.0):
    """Delta, gamma, theta per calendar day, vega per 1 vol point."""
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    disc_q, disc_r = math.exp(-q * T), math.exp(-r * T)
    gamma = disc_q * norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * disc_q * norm_pdf(d1) * math.sqrt(T) / 100.0
    common = -S * disc_q * norm_pdf(d1) * sigma / (2 * math.sqrt(T))
    if kind == "call":
        delta = disc_q * norm_cdf(d1)
        theta = common - r * K * disc_r * norm_cdf(d2) + q * S * disc_q * norm_cdf(d1)
    else:
        delta = disc_q * (norm_cdf(d1) - 1.0)
        theta = common + r * K * disc_r * norm_cdf(-d2) - q * S * disc_q * norm_cdf(-d1)
    return {"delta": delta, "gamma": gamma, "theta": theta / 365.0, "vega": vega}


def implied_vol(price, S, K, T, r, kind="call", q=0.0, lo=1e-4, hi=5.0, tol=1e-6):
    """Bisection. Returns None if the price is outside the model's range."""
    f = lambda s: bs_price(S, K, T, r, s, kind, q) - price
    if f(lo) > 0 or f(hi) < 0:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def prob_above(S, K, T, r, sigma, q=0.0):
    """Risk-neutral probability the stock finishes above K: N(d2)."""
    return norm_cdf(d1_d2(S, K, T, r, sigma, q)[1])


def put_call_parity_gap(call, put, S, K, T, r, q=0.0):
    """C - P - (S e^{-qT} - K e^{-rT}). Near zero for European options."""
    return call - put - (S * math.exp(-q * T) - K * math.exp(-r * T))


# ---------------------------------------------------------------- moves and vol
def expected_move(S, iv, days):
    """One-standard-deviation move by expiry: S x IV x sqrt(days/365)."""
    return S * iv * math.sqrt(days / 365.0)


def straddle_expected_move(call_mid, put_mid, factor=0.85):
    """Rule of thumb: ATM straddle x ~0.85 approximates the 1-sd move."""
    return (call_mid + put_mid) * factor


def realized_vol_close(closes: Sequence[float], periods=252):
    """Close-to-close: stdev of log returns (sample) x sqrt(periods)."""
    rets = [math.log(b / a) for a, b in zip(closes[:-1], closes[1:])]
    n = len(rets)
    if n < 2:
        raise ValueError("need at least 3 closes")
    m = sum(rets) / n
    var = sum((x - m) ** 2 for x in rets) / (n - 1)
    return math.sqrt(var * periods)


def parkinson_vol(highs, lows, periods=252):
    n = len(highs)
    s = sum(math.log(h / l) ** 2 for h, l in zip(highs, lows))
    return math.sqrt(s / (4.0 * n * math.log(2.0)) * periods)


def garman_klass_vol(opens, highs, lows, closes, periods=252):
    n = len(opens)
    s = sum(0.5 * math.log(h / l) ** 2 - (2 * math.log(2) - 1) * math.log(c / o) ** 2
            for o, h, l, c in zip(opens, highs, lows, closes))
    return math.sqrt(max(s / n, 0.0) * periods)


def yang_zhang_vol(opens, highs, lows, closes, periods=252):
    """Needs n+1 bars: the first close is only used for the first overnight gap."""
    n = len(opens) - 1
    if n < 2:
        raise ValueError("need at least 3 bars")
    o = [math.log(opens[i] / closes[i - 1]) for i in range(1, n + 1)]
    c = [math.log(closes[i] / opens[i]) for i in range(1, n + 1)]
    rs = [math.log(highs[i] / closes[i]) * math.log(highs[i] / opens[i])
          + math.log(lows[i] / closes[i]) * math.log(lows[i] / opens[i]) for i in range(1, n + 1)]

    def svar(x):
        m = sum(x) / len(x)
        return sum((v - m) ** 2 for v in x) / (len(x) - 1)

    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    var = svar(o) + k * svar(c) + (1 - k) * (sum(rs) / n)
    return math.sqrt(var * periods)


# ---------------------------------------------------------------- spreads
def debit_vertical(long_strike, short_strike, debit, kind="call", fees=0.0):
    """Per-share values. debit and fees per share (fees per contract / 100)."""
    width = abs(short_strike - long_strike)
    cost = debit + fees
    max_loss, max_gain = cost, width - cost
    be = long_strike + cost if kind == "call" else long_strike - cost
    return {"max_loss": max_loss, "max_gain": max_gain, "breakeven": be,
            "reward_risk": max_gain / max_loss if max_loss > 0 else float("inf")}


def conservative_debit(long_ask, short_bid):
    """Fill assumption used in the paper test: pay the ask, receive the bid."""
    return long_ask - short_bid


def vertical_probabilities(S, k_long, k_short, breakeven, T, r, sigma, kind="call", q=0.0):
    """Risk-neutral P(max profit), P(profit), P(max loss) for a debit vertical."""
    if kind == "call":
        p_max = prob_above(S, k_short, T, r, sigma, q)
        p_profit = prob_above(S, breakeven, T, r, sigma, q)
        p_loss = 1 - prob_above(S, k_long, T, r, sigma, q)
    else:
        p_max = 1 - prob_above(S, k_short, T, r, sigma, q)
        p_profit = 1 - prob_above(S, breakeven, T, r, sigma, q)
        p_loss = prob_above(S, k_long, T, r, sigma, q)
    return {"p_max_profit": p_max, "p_profit": p_profit, "p_max_loss": p_loss}


def expected_value(p_win, avg_win, avg_loss):
    """avg_loss as a positive number."""
    return p_win * avg_win - (1 - p_win) * avg_loss


# ---------------------------------------------------------------- gamma exposure
def gex_per_strike(rows: Iterable[dict], spot: float):
    """rows: dicts with strike, type ('call'/'put'), gamma, open_interest.

    GEX = gamma x OI x 100 x spot^2 x 0.01, calls +, puts - (dealer long calls /
    short puts assumption, which public data cannot confirm). Dollars per 1% move.
    """
    out = {}
    for r in rows:
        g, oi = r.get("gamma"), r.get("open_interest")
        if g in (None, "") or oi in (None, ""):
            continue
        sign = 1.0 if str(r["type"]).lower().startswith("c") else -1.0
        val = sign * float(g) * float(oi) * 100 * spot * spot * 0.01
        k = float(r["strike"])
        out[k] = out.get(k, 0.0) + val
    return dict(sorted(out.items()))


def zero_gamma_flip(gex_by_strike: dict):
    """Strike-cumulative method: first strike where cumulative net GEX turns from
    negative to positive, interpolated. Returns None if no sign change."""
    strikes = sorted(gex_by_strike)
    cum, prev_k, prev_c = 0.0, None, None
    for k in strikes:
        cum += gex_by_strike[k]
        if prev_c is not None and prev_c < 0 <= cum:
            return prev_k + (k - prev_k) * (-prev_c) / (cum - prev_c)
        prev_k, prev_c = k, cum
    return None


# ---------------------------------------------------------------- sizing and ruin
def kelly_fraction(p_win, b):
    """Binary bet: lose the stake or win b times it. f* = p - (1-p)/b."""
    return p_win - (1 - p_win) / b


def max_contracts(account, risk_pct, max_loss_per_contract):
    """Fixed-fractional sizing: floor(account x risk% / max loss per contract)."""
    return int(math.floor(account * risk_pct / max_loss_per_contract))


def losing_streak_prob(p_loss, streak, n_trades):
    """Probability of at least one run of `streak` consecutive losses in n trades."""
    # dp[j] = prob current run length is j with no qualifying run yet
    dp = [1.0] + [0.0] * (streak - 1)
    hit = 0.0
    for _ in range(n_trades):
        new = [0.0] * streak
        new[0] = sum(dp) * (1 - p_loss)
        for j in range(streak - 1):
            new[j + 1] = dp[j] * p_loss
        hit += dp[streak - 1] * p_loss
        dp = new
    return hit
