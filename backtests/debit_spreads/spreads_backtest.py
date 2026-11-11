import os
"""Debit vertical spread backtest (bull call / bear put), net debit <= $0.50 incl. costs.
Same conventions as ../backtest/backtest.py: BS on trailing 20d RV x IV factor, r=4%, signal at close t,
entry at open t+1, marks/exits at daily closes, half-spread per leg = max(0.02, 5% of leg mid) on entry and exit.
Expiry settles at intrinsic capped at width (no costs at expiry).
Skew (optional, assumed not calibrated): iv(K) = base*(1 + A*zput + B*zcall), z = |ln(K/S)|/(base*sqrt(T)) clipped at 3,
A=0.08 for K<S, B=0.02 for K>S (sticky-moneyness, recomputed at every mark)."""
import sys, numpy as np, pandas as pd
from scipy.stats import norm
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'single_options'))
from backtest import bs, hs, indicators, signals, pick_expiry, R
PX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'single_options', 'raw_prices_daily.csv')
FACTORS = [1.0, 1.2, 1.4]; LEGS = [0.50, 0.40, 'cap']; EXPS = [7, 14, 30]; SKEWS = {'none': (0., 0.), 'skew': (0.08, 0.02)}
INC = {'SPY': 1.0, 'AAPL': 2.5, 'MSFT': 2.5, 'NVDA': 2.5, 'TSLA': 5.0}
RULES = ['trend', 'meanrev', 'breakout', 'random', 'always_bull']; BUDGET = 0.50; MIN_DEBIT = 0.05; NMAX = 8

def iv(base, K, S, T, sk):
    A, B = SKEWS[sk]
    if A == 0 and B == 0: return base * np.ones(np.broadcast(K, S, T).shape)
    z = np.clip(np.abs(np.log(K / S)) / (base * np.sqrt(np.maximum(T, 1e-9))), 0, 3)
    return base * (1 + np.where(K < S, A, B) * z)

def px(S, K, T, base, call, sk): return bs(S, K, T, iv(base, K, S, T, sk), call)

def debit(S, KL, KS, T, base, call, sk):
    mL = float(px(S, KL, T, base, call, sk)); mS = float(px(S, KS, T, base, call, sk))
    return (mL + hs(mL)) - (mS - hs(mS))

def build(S, T, base, call, leg, inc, sk):
    """returns (KL, KS, debit, n_strikes) or reason string"""
    sgn = 1 if call else -1
    if leg == 'cap':
        K0 = np.round(S / inc) * inc
        for i in range(0, 200):
            KL = K0 + sgn * i * inc; KS = KL + sgn * inc
            if KS <= 0: break
            d = debit(S, KL, KS, T, base, call, sk)
            if d <= BUDGET: return (KL, KS, d, 1) if d >= MIN_DEBIT else 'debit<0.05'
        return 'no_strike'
    sd = base * np.sqrt(T); d1t = norm.ppf(leg) if call else -norm.ppf(leg)
    KL = round(S * np.exp(-(d1t * sd) + (R + base * base / 2) * T) / inc) * inc
    best = None
    for n in range(1, NMAX + 1):
        KS = KL + sgn * n * inc
        if KS <= 0: break
        d = debit(S, KL, KS, T, base, call, sk)
        if d <= BUDGET: best = (KL, KS, d, n)
        else: break
    if best is None: return '1wide>0.50'
    return best if best[2] >= MIN_DEBIT else 'debit<0.05'

def run():
    P = pd.read_csv(PX, parse_dates=['date']); out = []
    for sym, g in P.groupby('symbol'):
        g = indicators(g.sort_values('date').reset_index(drop=True)); dates = pd.DatetimeIndex(g.date)
        for rule in RULES:
            rng = np.random.default_rng(12345 + sum(map(ord, sym)))
            sig = signals(g, 'always_call' if rule == 'always_bull' else rule, rng).values
            for t in range(len(g) - 1):
                if sig[t] == 0: continue
                call = sig[t] == 1; ie = t + 1; S0 = g.open[ie]; rv = g.rv20[t]
                for E in EXPS:
                    exp, jx = pick_expiry(dates, ie, E)
                    if exp is None: continue
                    T0 = ((exp - dates[ie]).days + 0.3) / 365
                    idx = np.arange(ie, jx + 1); Sp = g.close.values[idx]
                    Tp = np.array([(exp - dates[k]).days for k in idx]) / 365.0; rvp = g.rv20.values[idx]
                    for f in FACTORS:
                        for sk in SKEWS:
                            for leg in LEGS:
                                base = dict(symbol=sym, rule=rule, exp_days=E, factor=f, skew=sk, leg=str(leg), date=dates[ie], call=call)
                                b = build(S0, T0, rv * f, call, leg, INC[sym], sk)
                                if isinstance(b, str): out.append({**base, 'feasible': False, 'reason': b}); continue
                                KL, KS, d, n = b; W = abs(KS - KL)
                                vL = px(Sp, KL, Tp, rvp * f, call, sk); vS = px(Sp, KS, Tp, rvp * f, call, sk)
                                proc = np.clip((vL - hs(vL)) - (vS + hs(vS)), 0, W)
                                intr = np.maximum(Sp[-1] - KL, 0) if call else np.maximum(KL - Sp[-1], 0)
                                proc[-1] = min(intr, W)
                                res = {'hold': proc[-1]}
                                pre = proc[:-1]
                                h = np.where(pre >= 2 * d)[0]; res['tp100'] = pre[h[0]] if len(h) else proc[-1]
                                h = np.where(pre >= d + 0.5 * (W - d))[0]; res['tp50maxprofit'] = pre[h[0]] if len(h) else proc[-1]
                                if len(proc) >= 2:
                                    c = np.where((pre >= 2 * d) | (pre <= 0.5 * d))[0]
                                    k = c[0] if len(c) and c[0] <= len(proc) - 2 else len(proc) - 2
                                    res['tp100_sl50_dm1'] = proc[k]
                                else: res['tp100_sl50_dm1'] = proc[-1]
                                row = {**base, 'feasible': True, 'reason': '', 'S': S0, 'KL': KL, 'KS': KS, 'width': W, 'nstrikes': n,
                                       'debit': d, 'exit_date': dates[jx]}
                                for x, v in res.items(): row['ret_' + x] = v / d - 1; row['pnl1_' + x] = 100 * (v - d)
                                out.append(row)
        print(sym, len(out), flush=True)
    return pd.DataFrame(out)

if __name__ == '__main__':
    tr = run(); tr.to_csv('spread_trades_all.csv', index=False); print(len(tr))
