"""Independent test of the vrp-harvesting-study "Strategy B" put spread (rules from its README only; see PLAN.md).

Monthly: decide at the prior month's last close, enter at the open of the month's first trading day, hold to the
month's last trading day and settle at intrinsic. Short put ~-0.30 delta ($1 strike).
(A) long put ~-0.10 delta. (B) $1 wide if max loss <= $45, else $0.50, else skip.
Pricing reuses bs() (../single_options/backtest.py, checked against quant/formulas.py) and the put/call skew of
../credit_spreads/credit_backtest.py. Costs: max($0.01, 1% of leg) per side + $0.04 per contract (scored).
Outputs: trades.csv, summary.csv (incl. ruin bootstrap), verdict.csv in this folder.
"""
import os, sys
import numpy as np, pandas as pd
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'single_options')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'quant'))
from backtest import bs, indicators, R
import formulas as F

SKEW_A, SKEW_B = 0.25, -0.10; FEE = 0.04 / 100; MIN_CREDIT = 0.03; CAP = 45.0
SCORED = ['vix', 'f1.0', 'f1.2', 'f1.4']
ACCT, RISK, NPATH = 440.0, 45.0, 1000


def skew_iv(base, K, S, T, on=True):
    if not on: return base
    z = min(abs(np.log(K / S)) / (base * np.sqrt(max(T, 1e-9))), 3)
    return base * max(1 + (SKEW_A if K < S else SKEW_B) * z, 0.5)

def px(S, K, T, base, call, skew=True): return float(bs(S, K, T, skew_iv(base, K, S, T, skew), call))

def strike_at(S, T, base, D, call, skew=True):
    q = norm.ppf(D); v = base
    for _ in range(6):
        K = S * np.exp((-q if call else q) * v * np.sqrt(T) + (R + v * v / 2) * T); v = skew_iv(base, K, S, T, skew)
    return float(np.round(K))

def trade(S0, T0, base, ST, call, sizing, cost, skew=True):
    """One vertical credit spread. Returns dict or None (skipped). P&L in dollars per 1 spread."""
    sgn = 1 if call else -1
    Ks = strike_at(S0, T0, base, 0.30, call, skew)
    ms = px(S0, Ks, T0, base, call, skew)
    def entry(Kl):
        ml = px(S0, Kl, T0, base, call, skew)
        if cost == 'study':
            return ms - ml - 0.025 * (ms + ml), ml
        hf, hp = {'harsh': (0.02, 0.05), 'tight': (0.01, 0.0)}.get(cost, (0.01, 0.01))
        return (ms - max(hf, hp * ms)) - (ml + max(hf, hp * ml)) - 2 * FEE, ml
    if sizing in ('A', 'A36'):
        Kl = strike_at(S0, T0, base, 0.10, call, skew) if sizing == 'A' else Ks + sgn * max(1.0, float(np.round(0.036 * S0)))
        if sgn * (Kl - Ks) <= 0: Kl = Ks + sgn
        C, ml = entry(Kl); W = abs(Kl - Ks)
    else:
        C = None
        for W in (1.0, 0.5):
            Kl = Ks + sgn * W; c, ml = entry(Kl)
            if (W - c) * 100 <= CAP: C = c; break
        if C is None: return None
    if C < MIN_CREDIT: return None
    settle = min(max(sgn * (ST - Ks), 0), W)
    exitc = 0.025 * (settle + max(sgn * (ST - Kl), 0)) if cost == 'study' else 0.0
    pnl = (C - settle - exitc) * 100
    return dict(short_k=Ks, long_k=Kl, width=W, gap_pct=100 * W / S0, credit=C * 100, max_loss=(W - C) * 100,
                settle=settle * 100, pnl=pnl, ror=pnl / ((W - C) * 100))

def run():
    assert abs(float(bs(100, 95, 0.05, 0.2, False)) - F.bs_price(100, 95, 0.05, R, 0.2, 'put')) < 1e-9
    g = indicators(pd.read_csv(os.path.join(HERE, 'prices_spy_vix.csv'), parse_dates=['date']))
    dates = pd.DatetimeIndex(g.date); ym = dates.to_period('M')
    first = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]]); last = np.r_[first[1:] - 1, len(g) - 1]
    rng = np.random.default_rng(7); rows = []
    for ie, jx in zip(first, last):
        t = ie - 1
        if t < 0 or np.isnan(g.rv20[t]) or jx == len(g) - 1 and dates[jx] < pd.Timestamp('2026-11-30'):
            continue  # need prior close with RV20; skip the open November 2026 trade
        if jx <= ie: continue
        S0 = g.open[ie]; ST = g.close[jx]; T0 = ((dates[jx] - dates[ie]).days + 0.3) / 365
        iv = {'vix': g.vix[t] / 100, 'f1.0': g.rv20[t], 'f1.2': 1.2 * g.rv20[t], 'f1.4': 1.4 * g.rv20[t]}
        flip_call = bool(rng.integers(2))
        gate_ok = g.vix[t] - 100 * g.rv20[t] >= 1.0
        base = dict(entry=dates[ie].date(), expiry=dates[jx].date(), S0=S0, ST=ST, vix=g.vix[t], rv20=g.rv20[t], gate_ok=gate_ok)
        SZ = ['A', 'A36', 'B']
        runs = [(m, s, 'put', 'base', m, True) for m in SCORED for s in SZ]
        runs += [(m, s, 'random', 'base', m, True) for m in SCORED for s in SZ]
        runs += [(m, s, 'put', c, m, True) for c in ('harsh', 'tight') for m in SCORED for s in SZ]
        runs += [('vix', 'A', 'put', 'study', 'vix_noskew_studycost', False)]
        for m, s, strat, cost, label, skew in runs:
            call = flip_call if strat == 'random' else False
            r = trade(S0, T0, iv[m], ST, call, s, cost, skew)
            rows.append({**base, 'ivmode': label, 'sizing': s, 'strat': strat, 'cost': cost, 'side': 'call' if call else 'put',
                         'traded': r is not None, **(r or {})})
    tr = pd.DataFrame(rows)
    ent = np.sort(tr.entry.unique()); cut = ent[int(np.ceil(0.7 * len(ent)))]
    tr['period'] = np.where(tr.entry < cut, 'IS', 'OOS')
    return tr, cut

def maxdd(x):
    c = np.cumsum(x); return float((c - np.maximum.accumulate(np.r_[0, c])[1:]).min()) if len(x) else np.nan

def ruin(pnl45, rng):
    if len(pnl45) == 0: return np.nan, np.nan
    n = len(pnl45); dead = 0; ends = []
    for _ in range(NPATH):
        eq = ACCT; seq = rng.choice(pnl45, n)
        for p in seq:
            if eq < RISK: break
            eq += p
        dead += eq < RISK; ends.append(eq)
    return 100 * dead / NPATH, float(np.median(ends))

def period_mask(d, pname):
    e = pd.to_datetime(d.entry)
    if pname in ('IS', 'OOS'): return (d.period == pname).values
    if pname == '2025+': return (e >= '2025-01-01').values
    if pname == 'study_train_2013_2018': return ((e >= '2013-01-01') & (e <= '2018-12-31')).values
    return ((e >= '2019-01-01') & (e <= '2024-12-31')).values

PERIODS = ['IS', 'OOS', '2025+', 'study_train_2013_2018', 'study_test_2019_2024']

def summarize(tr):
    rng = np.random.default_rng(7); out = []
    for (mode, sz, cost, strat), g0 in tr.groupby(['ivmode', 'sizing', 'cost', 'strat'], sort=True):
        variants = [('random_direction', g0)] if strat == 'random' else [('B_every_month', g0)]
        if strat == 'put' and cost == 'base': variants.append(('C_gate_info', g0[g0.gate_ok]))
        for vname, gv in variants:
            for pname in PERIODS:
                gm = gv[period_mask(gv, pname)]; g = gm[gm.traded]
                if not len(g): continue
                p = g.pnl.values; p45 = p if sz == 'B' else g.ror.values * RISK
                rp, med_end = ruin(p45, rng)
                out.append(dict(ivmode=mode, sizing=sz, cost=cost, variant=vname, period=pname, months=len(gm), trades=len(g),
                                win_rate=round(100 * (p > 0).mean(), 1), mean=round(p.mean(), 2), median=round(np.median(p), 2),
                                worst=round(p.min(), 2), best=round(p.max(), 2), mean_ror_pct=round(100 * g.ror.mean(), 2),
                                avg_credit=round(g.credit.mean(), 2), avg_max_loss=round(g.max_loss.mean(), 2),
                                max_max_loss=round(g.max_loss.max(), 2), avg_gap_pct=round(g.gap_pct.mean(), 2),
                                share_half_wide=round(100 * (g.width == 0.5).mean(), 1), max_dd=round(maxdd(p), 2),
                                ruin_pct_440_at_45=rp, median_end_equity=round(med_end, 0)))
    return pd.DataFrame(out)

if __name__ == '__main__':
    tr, cut = run()
    tr.to_csv(os.path.join(HERE, 'trades.csv'), index=False)
    s = summarize(tr); s.to_csv(os.path.join(HERE, 'summary.csv'), index=False)
    ent = tr.entry.unique()
    print('months', len(ent), 'first', min(ent), 'last', max(ent), 'OOS starts', cut)
    v = []
    for sz in ('A', 'A36', 'B'):
        o = s[(s.sizing == sz) & (s.cost == 'base') & (s.variant == 'B_every_month') & (s.period == 'OOS') & s.ivmode.isin(SCORED)]
        n = int(o.trades.min()); pos = int((o['mean'] > 0).sum())
        verdict = 'INSUFFICIENT DATA' if n < 30 else ('PASS' if pos == len(SCORED) else 'FAIL')
        isb = s[(s.sizing == sz) & (s.cost == 'base') & (s.variant == 'B_every_month') & (s.period == 'IS') & s.ivmode.isin(SCORED)]
        best = isb.sort_values('mean').ivmode.iloc[-1]
        v.append(dict(sizing=sz, oos_min_trades=n, oos_settings_positive=f'{pos}/{len(SCORED)}', best_IS_setting=best,
                      best_IS_setting_OOS_mean=float(o[o.ivmode == best]['mean'].iloc[0]), verdict=verdict))
    pd.DataFrame(v).to_csv(os.path.join(HERE, 'verdict.csv'), index=False); print(pd.DataFrame(v).to_string())
    st = []
    for (mode, sz, cost, strat, per), g in tr[tr.traded].groupby(['ivmode', 'sizing', 'cost', 'strat', 'period']):
        n = len(g)
        st.append(dict(ivmode=mode, sizing=sz, cost=cost, strat=strat, period=per, trades=n,
                       mean=round(g.pnl.mean(), 2), t_stat_dollars=round(g.pnl.mean() / (g.pnl.std(ddof=1) / np.sqrt(n)), 2) if n > 2 else np.nan,
                       mean_ror_pct=round(100 * g.ror.mean(), 2),
                       t_stat_ror=round(g.ror.mean() / (g.ror.std(ddof=1) / np.sqrt(n)), 2) if n > 2 else np.nan,
                       skew_ror=round(g.ror.skew(), 2), worst_ror_pct=round(100 * g.ror.min(), 1),
                       losses_over_half_max=int((g.ror < -0.5).sum())))
    pd.DataFrame(st).to_csv(os.path.join(HERE, 'stats.csv'), index=False)
