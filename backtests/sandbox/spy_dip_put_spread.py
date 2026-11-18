"""Sandbox retest of the 2026-11-18 proposal: SPY 1-wide put debit spread, ~0.2% OTM long leg,
4 trading days to expiry, entered after a sharp pullback below the 20/50-day averages.

Pricing: Black-Scholes on daily closes, IV = VIX/100 (live check 11/18: 727P IV 22.9% with VIX ~24.5).
Costs: 0.06 per spread to cross the bid/ask on entry and again on exit (live 727/726: ask-bid debit 0.44
vs mid 0.38), plus 0.0016 fees, all scaled by S/728.5. Strikes are scaled from the live trade:
long = S*727/728.49, short = S*726/728.49, so width = S*1/728.49.
Exit rules as proposed: take profit at value >= 0.80 width-units, stop <= 0.20, else close at the
close of day 3 (the day before expiry), repriced with 1 trading day left.
Signal: close < SMA20 and < SMA50 and 4-day return <= -3%. Baselines: every day; and the same signal
with a mirrored call spread (bet on a bounce). Split: first 70% of dates in-sample, last 30% out.
"""
import csv, math, os, sys, statistics as st
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'quant'))
from formulas import bs_price

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in csv.DictReader(open(os.path.join(HERE, '..', 'credit_spreads', 'prices_daily.csv'))) if r['symbol'] == 'SPY']
rows = [r for r in rows if r['vix']]
d = [r['date'] for r in rows]; c = [float(r['close']) for r in rows]; v = [float(r['vix']) / 100 for r in rows]
R, H = 0.04, 4

def spread_val(S, kl, ks, T, iv, kind):
    if T <= 0:
        return max(kl - S, 0) - max(ks - S, 0) if kind == 'put' else max(S - kl, 0) - max(S - ks, 0)
    return bs_price(S, kl, T, R, iv, kind) - bs_price(S, ks, T, R, iv, kind)

def trade(i, kind):
    S = c[i]; w = S / 728.49
    if kind == 'put':
        kl, ks = S * 727 / 728.49, S * 726 / 728.49
    else:
        kl, ks = S * 730 / 728.49, S * 731 / 728.49
    cost = 0.06 * S / 728.5; fee = 0.0016 * S / 728.5
    entry = spread_val(S, kl, ks, H / 252, v[i], kind) + cost + fee / 2
    for k in range(1, H):
        val = spread_val(c[i + k], kl, ks, (H - k) / 252, v[i + k], kind)
        if val >= 0.80 * w or val <= 0.20 * w or k == H - 1:
            exitv = val - cost - fee / 2
            return (exitv - entry) / w * 100, entry / w * 100   # $ per spread at SPY~728 scale, max loss $
    raise RuntimeError

def sig(i):
    if i < 50: return False
    sma20 = st.mean(c[i - 19:i + 1]); sma50 = st.mean(c[i - 49:i + 1])
    return c[i] < sma20 and c[i] < sma50 and c[i] / c[i - 4] - 1 <= -0.03

def summary(name, idx, kind):
    res = [trade(i, kind) for i in idx]
    if not res: return [name, 0] + [''] * 6
    p = [x[0] for x in res]; risk = st.mean(x[1] for x in res)
    nonover, last = 0, -99
    for i in idx:
        if i - last >= H: nonover += 1; last = i
    se = st.stdev(p) / math.sqrt(len(p)) if len(p) > 1 else float('nan')
    return [name, len(p), nonover, round(sum(x > 0 for x in p) / len(p) * 100, 1), round(st.mean(p), 2),
            round(st.mean(p) - 1.96 * se, 2), round(risk, 2), round(st.mean(p) / risk * 100, 1)]

N = len(c) - H; cut = int(N * 0.7)
allidx = list(range(50, N)); sigidx = [i for i in allidx if sig(i)]
out = [['test', 'trades', 'non_overlapping', 'win_pct', 'mean_pnl_usd', 'mean_minus_1.96se', 'avg_debit_usd', 'mean_pnl_pct_of_debit']]
for lab, sub in (('IS', lambda i: i < cut), ('OOS', lambda i: i >= cut), ('ALL', lambda i: True)):
    out.append([f'put_spread_signal_{lab}'] + summary('', [i for i in sigidx if sub(i)], 'put')[1:])
    out.append([f'put_spread_every_day_{lab}'] + summary('', [i for i in allidx if sub(i)], 'put')[1:])
    out.append([f'call_spread_signal_{lab}'] + summary('', [i for i in sigidx if sub(i)], 'call')[1:])
with open(os.path.join(HERE, 'spy_dip_put_spread_results.csv'), 'w', newline='') as f:
    csv.writer(f).writerows(out)
print('data', d[0], 'to', d[-1], '| OOS starts', d[cut], '| signal days', len(sigidx))
for r in out: print(*r, sep=' | ')
print('last signal dates:', [d[i] for i in sigidx[-6:]])
