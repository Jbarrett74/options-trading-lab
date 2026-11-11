"""Summaries: per rule/ticker/variant, IS (first 70% of dates) vs OOS (last 30%), bankroll sim ($80 bets from $273)."""
import numpy as np, pandas as pd
tr = pd.read_csv('trades_all.csv', parse_dates=['date', 'exit_date'])
EXITS = ['hold', 'tp100', 'tp100_sl50_dm1']; START, BET = 273.0, 80.0; NPATH = 1000
rng = np.random.default_rng(7)
dates = np.sort(tr.date.unique()); cut = dates[int(0.7 * len(dates))]
tr['period'] = np.where(tr.date < cut, 'IS', 'OOS')

# 1) cap feasibility (use 'random' rule rows: every day, mixed call/put)
r = tr[(tr.rule == 'random') & tr.delta.isin(['0.3', '0.5'])]
feas = r.groupby(['symbol', 'exp_days', 'delta', 'factor']).under_cap.mean().unstack('factor').round(3)
feas.to_csv('cap_feasibility.csv'); print('cap feasibility (fraction of days buy<=0.80):\n', feas)
c = tr[(tr.rule == 'random') & (tr.delta == 'cap') & tr.feasible]
capinfo = c.groupby(['symbol', 'exp_days', 'factor']).apply(lambda x: pd.Series({'median_otm_pct': (abs(x.K / x.S - 1) * 100).median(), 'median_buy': x.buy.median()})).round(3)
capinfo.to_csv('cap_strike_info.csv'); print(capinfo)

# 2) build "modes"
rows = []
for D in ['0.3', '0.5']:
    rows.append(tr[(tr.delta == D) & tr.feasible].assign(mode='uncapped'))
    rows.append(tr[(tr.delta == D) & tr.feasible & tr.under_cap].assign(mode='capped'))
rows.append(tr[(tr.delta == 'cap') & tr.feasible].assign(mode='capped'))
T = pd.concat(rows)
# portfolio: one trade per day across tickers (seeded random pick among tickers with a signal)
key = ['rule', 'exp_days', 'factor', 'delta', 'mode', 'date']
T['_u'] = rng.random(len(T))
port = T.sort_values('_u').groupby(key, as_index=False).head(1).assign(symbol='PORTFOLIO_1perday')
T = pd.concat([T, port]).sort_values('date')

def bank(rets):
    rets = np.asarray(rets)
    if len(rets) == 0: return np.nan, np.nan, np.nan, np.nan
    eq = START + np.concatenate([[0], np.cumsum(BET * rets)])
    dead = np.where(eq < BET)[0]
    if len(dead): eq = eq[:dead[0] + 1]
    peak = np.maximum.accumulate(eq); mdd = (peak - eq).max(); mddp = ((peak - eq) / peak).max()
    sims = START + np.cumsum(BET * rng.choice(rets, size=(NPATH, len(rets))), axis=1)
    ruin = (sims.min(axis=1) < BET).mean()
    return mdd, mddp, ruin, eq[-1]

out = []
for (rule, sym, E, f, D, mode, per), g in list(T.groupby(['rule', 'symbol', 'exp_days', 'factor', 'delta', 'mode', 'period'])) + \
        [((a[0], a[1], a[2], a[3], a[4], a[5], 'ALL'), g) for a, g in T.groupby(['rule', 'symbol', 'exp_days', 'factor', 'delta', 'mode'])]:
    for x in EXITS:
        rr = g['ret_' + x].values; mdd, mddp, ruin, end = bank(rr)
        out.append(dict(rule=rule, symbol=sym, exp_days=E, factor=f, delta=D, mode=mode, period=per, exit=x, n=len(rr),
                        win_rate=(rr > 0).mean(), mean_ret=rr.mean(), median_ret=np.median(rr), maxdd_usd=mdd, maxdd_pct=mddp,
                        pct_paths_ruined=ruin, end_equity_actual_order=end))
res = pd.DataFrame(out).round(4); res.to_csv('results_by_variant.csv', index=False)
print('cutoff date', pd.Timestamp(cut).date(), 'rows', len(res))
