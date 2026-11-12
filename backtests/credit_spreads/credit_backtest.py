"""Credit spread backtest on SPY and QQQ: put credit spreads, call credit spreads, iron condors.

Method (same conventions as ../single_options/backtest.py, whose bs / indicators / pick_expiry are reused):
- Signal at the close of day t, entry at the OPEN of day t+1, marks and exits at daily closes.
- Option prices: Black-Scholes, r = 4%. At-the-money IV = trailing 20d realized vol x factor (1.0, 1.2, 1.4).
  A fourth IV mode, 'vix', is a cross-check that does not use realized vol: ATM IV = 0.90 x VIX close
  (SPY), and for QQQ that value x the trailing 252d ratio of QQQ to SPY realized vol (clipped 1.0-1.6).
  The 0.90 and the QQQ scaling are assumptions, not calibrated.
- Skew: iv(K) = ATM x (1 + A x z) for K < S and ATM x (1 + B x z) for K > S, z = |ln(K/S)| / (ATM x sqrt(T)),
  clipped at 3, A = +0.25 (puts cost more), B = -0.10 (calls cost less), floor 0.5 x ATM. Recomputed at every mark.
- Short strike: $1 strike closest to the target delta (0.10, 0.15, 0.20) under the skewed IV. Long strike
  1, 2 or 3 strikes further out. Expiry: the Friday nearest 7, 14 or 21 calendar days out.
- Costs on every leg, in and out: half-spread max($0.01, 1% of the leg mid) plus $0.04 per contract fees.
  Calibrated on live SPY quotes for the 2026-11-27 expiry on 2026-11-12 (legs priced $1.06 to $4.14 were $0.02 to
  $0.04 wide). One calm snapshot: spreads are wider in a selloff, which is when stops fill. The older convention
  max($0.02, 5%) is kept as a sensitivity run (HS_FLOOR=0.02 HS_PCT=0.05, outputs tagged _harshcost).
  The same quotes gave put skew A of 0.23 to 0.24 (15 and 7.5 delta) and a call slope near -0.22 at 35 delta.
  Expiry settles at intrinsic capped at the width with no cost. Trades with net credit under $0.03 are skipped.
- Exits: hold (to expiry), tp50 (close when the cost to close <= 50% of the credit), sl2x (close when the cost
  to close >= 2x the credit), dm1 (close one trading day before expiry), managed (tp50 or sl2x, else dm1).
  Stops fill at the daily close, so a gap can make the stop loss larger than 1x the credit.
- Entry rules at the signal close: always, trend, meanrev, highvol (see rule_masks). Event filter: skip when a
  CPI, FOMC or (QQQ only) NVDA earnings reaction day falls between entry and expiry, inclusive.
Output: credit_trades_all.pkl (one row per symbol / date / structure / IV mode; not committed).
"""
import os, sys
import numpy as np, pandas as pd
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'single_options')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'quant'))
from backtest import bs, indicators, pick_expiry, R
import formulas as F

IVMODES = ['f1.0', 'f1.2', 'f1.4', 'vix']; DELTAS = [0.10, 0.15, 0.20]; WIDTHS = [1.0, 2.0, 3.0]; EXPS = [7, 14, 21]
EXITS = ['hold', 'tp50', 'sl2x', 'dm1', 'managed']; RULES = ['always', 'trend', 'meanrev', 'highvol']
SKEW_A, SKEW_B = 0.25, -0.10; FEE = 0.0004; MIN_CREDIT = 0.03
HS_FLOOR, HS_PCT = float(os.environ.get('HS_FLOOR', 0.01)), float(os.environ.get('HS_PCT', 0.01))
OUT = os.environ.get('TRADES_OUT', os.path.join(HERE, 'credit_trades_all.pkl'))


def hs(m): return np.maximum(HS_FLOOR, HS_PCT * m)

def skew_iv(base, K, S, T):
    z = np.clip(np.abs(np.log(K / S)) / (base * np.sqrt(np.maximum(T, 1e-9))), 0, 3)
    return base * np.maximum(1 + np.where(K < S, SKEW_A, SKEW_B) * z, 0.5)

def price(S, K, T, base, call): return bs(S, K, T, skew_iv(base, K, S, T), call)

def vertical(S0, T0, b0, Sp, Tp, bp, call, D, W):
    """Short strike at |delta| ~ D, long strike W further out. Returns short K, net credit, cost-to-close path, settlement."""
    q = norm.ppf(D); v = b0.copy()
    for _ in range(4):
        K = S0 * np.exp((-q if call else q) * v * np.sqrt(T0) + (R + v * v / 2) * T0); v = skew_iv(b0, K, S0, T0)
    Ks = np.round(K); Kl = Ks + W if call else Ks - W
    ms0, ml0 = price(S0, Ks, T0, b0, call), price(S0, Kl, T0, b0, call)
    C = (ms0 - hs(ms0)) - (ml0 + hs(ml0)) - 2 * FEE
    msp, mlp = price(Sp, Ks[:, None], Tp, bp, call), price(Sp, Kl[:, None], Tp, bp, call)
    Dk = np.clip(msp - mlp, 0, W) + hs(msp) + hs(mlp) + 2 * FEE
    ST = Sp[:, -1]; settle = np.clip((ST - Ks) if call else (Ks - ST), 0, W)
    return Ks, C, Dk, settle

def exits(C, Dk, settle, pre, L):
    """P&L per share and exit offset (trading days after entry) for each exit rule."""
    n = len(C); rows = np.arange(n); hold = C - settle; kl = L - 1; out = {'hold': (hold, kl)}
    def first(cond):
        c = cond & pre; return c.any(1), c.argmax(1)
    tp, sl = Dk <= 0.5 * C[:, None], Dk >= 2 * C[:, None]
    h, k = first(tp); out['tp50'] = (np.where(h, C - Dk[rows, k], hold), np.where(h, k, kl))
    h, k = first(sl); out['sl2x'] = (np.where(h, C - Dk[rows, k], hold), np.where(h, k, kl))
    kd = L - 2; ok = kd >= 0; dm = np.where(ok, C - Dk[rows, np.maximum(kd, 0)], hold); kdm = np.where(ok, kd, kl)
    out['dm1'] = (dm, kdm)
    h, k = first(tp | sl); out['managed'] = (np.where(h, C - Dk[rows, k], dm), np.where(h, k, kdm))
    return out

def rule_masks(g):
    up = (g.close > g.sma20) & (g.sma20 > g.sma50); dn = (g.close < g.sma20) & (g.sma20 < g.sma50)
    hv = g.rv20 > g.rv20.rolling(252, min_periods=120).median().shift(1)
    return {('trend', 'put'): up, ('trend', 'call'): dn, ('trend', 'condor'): ~up & ~dn,
            ('meanrev', 'put'): g.rsi < 35, ('meanrev', 'call'): g.rsi > 65, ('meanrev', 'condor'): (g.rsi >= 40) & (g.rsi <= 60),
            ('highvol', 'put'): hv, ('highvol', 'call'): hv, ('highvol', 'condor'): hv}

def run():
    assert abs(float(bs(100, 95, 0.05, 0.2, False)) - F.bs_price(100, 95, 0.05, R, 0.2, 'put')) < 1e-9
    P = pd.read_csv(os.path.join(HERE, 'prices_daily.csv'), parse_dates=['date'])
    EV = pd.read_csv(os.path.join(HERE, 'events.csv'), parse_dates=['date'])
    W_ = P.pivot(index='date', columns='symbol', values='close'); lr = np.log(W_).diff()
    ratio = (lr.QQQ.rolling(252, min_periods=120).std() / lr.SPY.rolling(252, min_periods=120).std()).clip(1.0, 1.6)
    out = []
    for sym, g in P.groupby('symbol'):
        g = indicators(g.sort_values('date').reset_index(drop=True)); dates = pd.DatetimeIndex(g.date)
        vixiv = 0.90 * g.vix.values / 100 * (ratio.reindex(dates).values if sym == 'QQQ' else 1.0)
        iv = {'f1.0': g.rv20.values, 'f1.2': 1.2 * g.rv20.values, 'f1.4': 1.4 * g.rv20.values, 'vix': vixiv}
        evd = np.sort(EV[EV.applies_to.str.contains(sym)].date.values)
        rm = rule_masks(g); ok0 = (g.sma50.notna() & g.rv20.notna() & ~np.isnan(vixiv)).values
        for E in EXPS:
            rec = [(t, t + 1) + pick_expiry(dates, t + 1, E) for t in range(len(g) - 1) if ok0[t]]
            rec = [r for r in rec if r[2] is not None]
            t = np.array([r[0] for r in rec]); ie = np.array([r[1] for r in rec]); jx = np.array([r[3] for r in rec])
            exp = pd.DatetimeIndex([r[2] for r in rec]); L = jx - ie + 1
            idx = np.minimum(ie[:, None] + np.arange(L.max())[None, :], jx[:, None])
            pre = np.arange(L.max())[None, :] <= (L - 2)[:, None]
            S0 = g.open.values[ie]; T0 = ((exp - dates[ie]).days.values + 0.3) / 365
            Sp = g.close.values[idx]; Tp = (exp.values[:, None] - dates.values[idx]).astype('timedelta64[D]').astype(float) / 365
            a = np.searchsorted(evd, dates.values[ie], 'left'); b = np.searchsorted(evd, exp.values, 'right'); ev_ok = a == b
            for mode in IVMODES:
                b0 = iv[mode][t]; bp = iv[mode][idx]
                for D in DELTAS:
                    for W in WIDTHS:
                        legs = {s: vertical(S0, T0, b0, Sp, Tp, bp, s == 'call', D, W) for s in ('put', 'call')}
                        for strat in ('put', 'call', 'condor'):
                            if strat == 'condor':
                                (kp, Cp, Dp, sp), (kc, Cc, Dc, sc) = legs['put'], legs['call']
                                Ks, C, Dk, settle = kp, Cp + Cc, Dp + Dc, sp + sc
                                feas = (Cp >= MIN_CREDIT) & (Cc >= MIN_CREDIT); dist = np.minimum(S0 - kp, kc - S0) / S0
                            else:
                                Ks, C, Dk, settle = legs[strat]; feas = C >= MIN_CREDIT; dist = np.abs(Ks - S0) / S0
                            df = pd.DataFrame({'symbol': sym, 'strat': strat, 'delta': D, 'width': W, 'dte': E, 'ivmode': mode,
                                               'date': dates[ie], 'expiry': exp, 'ie': ie, 'feasible': feas, 'ev_ok': ev_ok,
                                               'S': S0, 'short_k': Ks, 'dist': dist, 'credit': C, 'max_loss': W - C})
                            for r in RULES:
                                df['r_' + r] = True if r == 'always' else rm[(r, strat)].values[t]
                            for x, (pnl, k) in exits(C, Dk, settle, pre, L).items():
                                df['pnl_' + x] = pnl; df['kx_' + x] = k.astype(np.int16)
                            out.append(df)
        print(sym, sum(map(len, out)), flush=True)
    tr = pd.concat(out, ignore_index=True)
    for c in ('symbol', 'strat', 'ivmode'): tr[c] = tr[c].astype('category')
    return tr

if __name__ == '__main__':
    tr = run(); tr.to_pickle(OUT); print(len(tr), 'rows ->', OUT)
    f = tr[tr.feasible]
    print(f.groupby(['strat', 'ivmode'], observed=True)[['credit', 'dist']].median().round(3))
    print(tr.groupby(['width', 'delta']).feasible.mean().round(2).unstack())
