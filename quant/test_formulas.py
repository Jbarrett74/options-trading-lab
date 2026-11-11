import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import formulas as f  # noqa: E402


def close(a, b, tol):
    assert abs(a - b) <= tol, (a, b)


def test_bs_textbook():
    # Hull example: S=42, K=40, r=10%, sigma=20%, T=0.5 -> call 4.76, put 0.81
    close(f.bs_price(42, 40, 0.5, 0.10, 0.20, "call"), 4.76, 0.01)
    close(f.bs_price(42, 40, 0.5, 0.10, 0.20, "put"), 0.81, 0.01)


def test_parity_and_iv_roundtrip():
    c = f.bs_price(100, 100, 0.25, 0.04, 0.3, "call")
    p = f.bs_price(100, 100, 0.25, 0.04, 0.3, "put")
    close(f.put_call_parity_gap(c, p, 100, 100, 0.25, 0.04), 0.0, 1e-9)
    close(f.implied_vol(c, 100, 100, 0.25, 0.04, "call"), 0.3, 1e-5)


def test_greeks_vs_finite_difference():
    S, h = 100.0, 0.01
    g = f.bs_greeks(S, 105, 0.2, 0.04, 0.25, "call")
    up = f.bs_price(S + h, 105, 0.2, 0.04, 0.25)
    dn = f.bs_price(S - h, 105, 0.2, 0.04, 0.25)
    mid = f.bs_price(S, 105, 0.2, 0.04, 0.25)
    close(g["delta"], (up - dn) / (2 * h), 1e-4)
    close(g["gamma"], (up - 2 * mid + dn) / (h * h), 1e-3)


def test_vertical_and_probabilities():
    v = f.debit_vertical(285, 286, 0.33, "call", fees=0.0008)
    close(v["max_loss"], 0.3308, 1e-9)
    close(v["breakeven"], 285.3308, 1e-9)
    pr = f.vertical_probabilities(283.5, 285, 286, v["breakeven"], 2 / 365, 0.04, 0.17)
    assert 0 < pr["p_max_profit"] < pr["p_profit"] < 1 - pr["p_max_loss"] + 1e-12


def test_gex_and_flip():
    rows = [
        {"strike": 100, "type": "put", "gamma": 0.05, "open_interest": 1000},
        {"strike": 101, "type": "call", "gamma": 0.05, "open_interest": 300},
        {"strike": 102, "type": "call", "gamma": 0.05, "open_interest": 2000},
    ]
    g = f.gex_per_strike(rows, 101.0)
    assert g[100] < 0 < g[102]
    flip = f.zero_gamma_flip(g)
    assert flip is not None and 101 <= flip <= 102


def test_vol_estimators_constant_prices():
    closes = [100 * math.exp(0.01 * (-1) ** i) for i in range(30)]
    assert f.realized_vol_close(closes) > 0
    o = h = l = c = [100.0] * 10
    assert f.parkinson_vol(h, l) == 0.0
    assert f.garman_klass_vol(o, h, l, c) == 0.0


def test_sizing():
    assert f.kelly_fraction(0.6, 1.0) == 0.6 - 0.4
    assert f.max_contracts(422.79, 0.10, 33.08) == 1
    close(f.losing_streak_prob(0.5, 1, 1), 0.5, 1e-12)
    close(f.losing_streak_prob(0.5, 2, 2), 0.25, 1e-12)
    close(f.losing_streak_prob(0.5, 2, 3), 0.375, 1e-12)


if __name__ == "__main__":
    for name in sorted(k for k in dir() if k.startswith("test_")):
        globals()[name]()
        print("ok", name)
