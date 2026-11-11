import os
"""Sensitivity (NOT the spec cost model): leg half-spread = max($0.01, 1.5% of leg mid) instead of max($0.02, 5%).
Only IV factor 1.0, 'cap' long leg (the only construction that fits <= $0.50), both skew settings. Same portfolio/IS-OOS logic."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spreads_backtest as sb
sb.hs = lambda m: np.maximum(0.01, 0.015 * m); sb.FACTORS = [1.0]; sb.LEGS = ['cap']
tr = sb.run(); tr.to_csv('spread_trades_lowcost.csv', index=False)
EXITS = ['hold', 'tp100', 'tp50maxprofit', 'tp100_sl50_dm1']; rng = np.random.default_rng(7)
tr['period'] = np.where(tr.date < pd.Timestamp('2026-03-24'), 'IS', 'OOS')
F = tr[tr.feasible].copy(); F['_u'] = rng.random(len(F))
port = F.sort_values('_u').groupby(['rule', 'exp_days', 'skew', 'date'], as_index=False).head(1)
rows = []
for (rule, E, sk, per), g in port.groupby(['rule', 'exp_days', 'skew', 'period']):
    for x in EXITS:
        rr = g['ret_' + x].values
        sims = 273 + np.cumsum(50 * rng.choice(rr, size=(1000, len(rr))), axis=1)
        rows.append(dict(rule=rule, exp_days=E, skew=sk, period=per, exit=x, n=len(rr), win=(rr > 0).mean(), mean=rr.mean(),
                         median=np.median(rr), pct_paths_below50=(sims.min(axis=1) < 50).mean(), mean_debit=g.debit.mean()))
R = pd.DataFrame(rows).round(3); R.to_csv('spread_lowcost_portfolio_results.csv', index=False)
Wd = R.pivot_table(index=['rule', 'exp_days', 'skew', 'exit'], columns='period', values=['n', 'mean', 'win', 'pct_paths_below50']).reset_index()
Wd.columns = ['_'.join([c for c in col if c]) for col in Wd.columns]
print(R.assign(pos=R['mean'] > 0).groupby(['skew', 'rule', 'period']).agg(share_pos=('pos', 'mean'), med_mean=('mean', 'median')).unstack().round(3))
for sk in ['none', 'skew']:
    for rule in ['trend', 'meanrev', 'breakout', 'random', 'always_bull']:
        s = Wd[(Wd.rule == rule) & (Wd['skew'] == sk)].sort_values('mean_IS', ascending=False).iloc[0]
        print(sk, rule, s.exp_days, s.exit, 'IS', s.n_IS, s.mean_IS, 'OOS', s.n_OOS, s.mean_OOS, 'win', s.win_OOS, 'ruin', s.pct_paths_below50_OOS)
