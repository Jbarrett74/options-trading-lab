"""Long call/put backtest on daily bars (BS pricing with trailing 20d RV x premium factor).
Signal at close of day t -> enter at OPEN of day t+1 (no same-bar look-ahead). Marks/exits at daily closes.
Spread: buy at mid+hs, sell at mid-hs, hs=max(0.02, 5% of mid). Expiry: intrinsic minus hs if ITM, else 0."""
import numpy as np, pandas as pd
from scipy.stats import norm
R = 0.04; FACTORS = [1.0, 1.2, 1.4]; DELTAS = [0.30, 0.50, 'cap']; EXPS = [7, 30]
EXITS = ['hold', 'tp100', 'tp100_sl50_dm1']; CAP = 0.80
INC = {'SPY': 1.0, 'NVDA': 1.0, 'AAPL': 2.5, 'TSLA': 2.5, 'MSFT': 2.5}
RULES = ['trend', 'meanrev', 'breakout', 'random', 'always_call']

def bs(S, K, T, v, call):
    S, K, T, v = map(np.asarray, (S, K, T, v)); T = np.maximum(T, 1e-9)
    d1 = (np.log(S / K) + (R + v * v / 2) * T) / (v * np.sqrt(T)); d2 = d1 - v * np.sqrt(T)
    return np.where(call, S * norm.cdf(d1) - K * np.exp(-R * T) * norm.cdf(d2), K * np.exp(-R * T) * norm.cdf(-d2) - S * norm.cdf(-d1))
def hs(m): return np.maximum(0.02, 0.05 * m)

def indicators(g):
    g = g.copy(); c = g.close
    g['sma20'] = c.rolling(20).mean(); g['sma50'] = c.rolling(50).mean()
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean(); g['rsi'] = 100 - 100 / (1 + up / dn)
    g['hi20'] = c.shift(1).rolling(20).max(); g['lo20'] = c.shift(1).rolling(20).min()
    g['rv20'] = np.log(c).diff().rolling(20).std() * np.sqrt(252)
    return g

def signals(g, rule, rng):
    s = pd.Series(0, index=g.index)
    if rule == 'trend':
        s[(g.close > g.sma20) & (g.sma20 > g.sma50)] = 1; s[(g.close < g.sma20) & (g.sma20 < g.sma50)] = -1
    elif rule == 'meanrev':
        s[g.rsi < 30] = 1; s[g.rsi > 70] = -1
    elif rule == 'breakout':
        s[g.close > g.hi20] = 1; s[g.close < g.lo20] = -1
    elif rule == 'random':
        s[:] = rng.choice([-1, 1], size=len(g))
    elif rule == 'always_call':
        s[:] = 1
    s[g.sma50.isna() | g.rv20.isna()] = 0
    return s

def pick_expiry(dates, i_entry, target):
    d0 = dates[i_entry]; tgt = d0 + pd.Timedelta(days=target)
    fri = tgt + pd.Timedelta(days=(4 - tgt.weekday()) % 7)
    if (fri - tgt).days > 3: fri -= pd.Timedelta(days=7)
    if fri <= d0: fri += pd.Timedelta(days=7)
    j = dates.searchsorted(fri, side='right') - 1   # last trading day <= Friday
    if fri > dates[-1] or j <= i_entry: return None, None
    return fri, j

def choose_strike(S, T, v, call, delta, inc):
    if delta == 'cap':   # most expensive (closest to ATM) strike whose buy price <= CAP, OTM side
        ks = np.arange((np.ceil(S / inc) if call else np.floor(S / inc)) * inc, S * (1.6 if call else 0.4), inc if call else -inc)
        m = bs(S, ks, T, v, call); buy = m + hs(m); ok = np.where(buy <= CAP)[0]
        return (ks[ok[0]] if len(ok) else None)
    sd = v * np.sqrt(T); d1t = norm.ppf(delta) if call else -norm.ppf(delta)
    K = S * np.exp(-(d1t * sd) + (R + v * v / 2) * T)
    return round(K / inc) * inc

def run():
    px = pd.read_csv('raw_prices_daily.csv', parse_dates=['date'])
    trades = []
    for sym, g in px.groupby('symbol'):
        g = indicators(g.sort_values('date').reset_index(drop=True)); dates = pd.DatetimeIndex(g.date)
        for rule in RULES:
            rng = np.random.default_rng(12345 + sum(map(ord, sym)))  # seeded, deterministic
            sig = signals(g, rule, rng).values
            for t in range(len(g) - 1):
                if sig[t] == 0: continue
                call = sig[t] == 1; ie = t + 1; S0 = g.open[ie]; rv = g.rv20[t]
                for E in EXPS:
                    exp, jx = pick_expiry(dates, ie, E)
                    if exp is None: continue
                    T0 = ((exp - dates[ie]).days + 0.3) / 365
                    path_idx = np.arange(ie, jx + 1); Sp = g.close.values[path_idx]
                    Tp = np.array([(exp - dates[k]).days for k in path_idx]) / 365.0
                    rvp = g.rv20.values[path_idx]
                    for f in FACTORS:
                        v0 = rv * f
                        for D in DELTAS:
                            K = choose_strike(S0, T0, v0, call, D, INC[sym])
                            if K is None:
                                trades.append(dict(symbol=sym, rule=rule, exp_days=E, factor=f, delta=str(D), date=dates[ie], call=call, feasible=False)); continue
                            m0 = float(bs(S0, K, T0, v0, call)); buy = m0 + hs(m0)
                            mids = bs(Sp, K, Tp, rvp * f, call); intr = np.maximum(Sp - K, 0) if call else np.maximum(K - Sp, 0)
                            mids[-1] = intr[-1]; sell = np.maximum(mids - hs(mids), 0); sell[-1] = max(intr[-1] - hs(intr[-1]), 0) if intr[-1] > 0 else 0.0
                            res = {}
                            res['hold'] = sell[-1]
                            hit = np.where(sell[:-1] >= 2 * buy)[0]; res['tp100'] = sell[hit[0]] if len(hit) else sell[-1]
                            if len(sell) >= 2:
                                c = np.where((sell[:-1] >= 2 * buy) | (sell[:-1] <= 0.5 * buy))[0]
                                k = c[0] if len(c) and c[0] <= len(sell) - 2 else len(sell) - 2
                                res['tp100_sl50_dm1'] = sell[k]
                            else: res['tp100_sl50_dm1'] = sell[-1]
                            row = dict(symbol=sym, rule=rule, exp_days=E, factor=f, delta=str(D), date=dates[ie], call=call, feasible=True,
                                       S=S0, K=K, mid=m0, buy=buy, under_cap=buy <= CAP, exit_date=dates[jx])
                            for x in EXITS: row['ret_' + x] = res[x] / buy - 1
                            trades.append(row)
    return pd.DataFrame(trades)

if __name__ == '__main__':
    tr = run(); tr.to_csv('trades_all.csv', index=False); print(len(tr))
