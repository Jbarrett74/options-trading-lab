import os
"""Summaries for spread backtest: feasibility, per-variant IS/OOS (cut 2026-03-24 by entry date), portfolio 1/day,
bootstrap bankroll ($50 stake x return, start $273, 1000 paths, ruin = equity < $50), best-IS-per-rule OOS check,
comparison with the prior single-long-option backtest."""
import numpy as np, pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
PRIOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'single_options') + '/'
tr = pd.read_csv('spread_trades_all.csv', parse_dates=['date', 'exit_date'])
EXITS = ['hold', 'tp100', 'tp50maxprofit', 'tp100_sl50_dm1']; START, BET, NPATH = 273.0, 50.0, 1000
CUT = pd.Timestamp('2026-03-24'); rng = np.random.default_rng(7)
tr['period'] = np.where(tr.date < CUT, 'IS', 'OOS')

# 1) feasibility (random rule = every day, mixed direction)
r = tr[tr.rule == 'random']
feas = r.groupby(['symbol', 'exp_days', 'leg', 'skew', 'factor']).agg(frac_feasible=('feasible', 'mean'),
        frac_1wide_too_expensive=('reason', lambda s: (s == '1wide>0.50').mean()),
        median_debit=('debit', 'median'), median_width=('width', 'median'), median_nstrikes=('nstrikes', 'median'),
        median_KL_otm_pct=('KL', lambda s: np.nan)).reset_index()
rf = r[r.feasible]
otm = (np.where(rf.call, rf.KL / rf.S - 1, 1 - rf.KL / rf.S) * 100)
feas = feas.drop(columns='median_KL_otm_pct').merge(rf.assign(otm=otm).groupby(['symbol', 'exp_days', 'leg', 'skew', 'factor']).otm.median()
        .rename('median_longleg_otm_pct').reset_index(), how='left')
feas.round(3).to_csv('spread_feasibility.csv', index=False)

# 2) portfolio: one trade/day, seeded random pick among tickers with a feasible spread
F = tr[tr.feasible].copy()
key = ['rule', 'exp_days', 'factor', 'skew', 'leg', 'date']
F['_u'] = rng.random(len(F))
port = F.sort_values('_u').groupby(key, as_index=False).head(1).assign(symbol='PORTFOLIO_1perday')
T = pd.concat([F, port]).sort_values('date')

def bank(rets, stake=BET):
    rets = np.asarray(rets)
    if len(rets) == 0: return np.nan, np.nan
    return _absorb(START + np.cumsum(stake * rng.choice(rets, size=(NPATH, len(rets))), axis=1))

def _absorb(sims):
    # stop trading once equity < $50 (cannot fund next spread); ending equity frozen at that point
    below = sims < BET; hit = below.any(axis=1); first = np.where(hit, below.argmax(axis=1), sims.shape[1] - 1)
    end = sims[np.arange(len(sims)), first]
    return hit.mean(), np.median(end)

def bank_dollars(pnl):
    pnl = np.asarray(pnl)
    if len(pnl) == 0: return np.nan, np.nan
    return _absorb(START + np.cumsum(rng.choice(pnl, size=(NPATH, len(pnl))), axis=1))

out = []
cfgcols = ['rule', 'symbol', 'exp_days', 'factor', 'skew', 'leg']
groups = [(k + (p,), g) for (k), gg in T.groupby(cfgcols) for p, g in list(gg.groupby('period')) + [('ALL', gg)]]
for k, g in groups:
    is_port = k[1] == 'PORTFOLIO_1perday'
    for x in EXITS:
        rr = g['ret_' + x].values
        row = dict(zip(cfgcols + ['period'], k), exit=x, n=len(rr), win_rate=(rr > 0).mean(), mean_ret=rr.mean(),
                   median_ret=np.median(rr), mean_debit=g.debit.mean())
        if is_port and k[-1] != 'ALL':
            row['pct_paths_below50'], row['median_end_equity'] = bank(rr)
            row['pct_paths_below50_1spread'], row['median_end_equity_1spread'] = bank_dollars(g['pnl1_' + x].values)
            bs_means = rng.choice(rr, size=(1000, len(rr))).mean(axis=1)
            row['mean_ret_ci_lo'], row['mean_ret_ci_hi'] = np.percentile(bs_means, [2.5, 97.5])
        out.append(row)
res = pd.DataFrame(out).round(4); res.to_csv('spread_results_by_variant.csv', index=False)

# 3) portfolio IS vs OOS wide
p = res[(res.symbol == 'PORTFOLIO_1perday') & (res.period != 'ALL')]
cfg = ['exp_days', 'factor', 'skew', 'leg', 'exit']
W = p.pivot_table(index=['rule'] + cfg, columns='period', values=['n', 'mean_ret', 'median_ret', 'win_rate', 'pct_paths_below50',
      'median_end_equity', 'pct_paths_below50_1spread', 'median_end_equity_1spread', 'mean_ret_ci_lo', 'mean_ret_ci_hi']).reset_index()
W.columns = ['_'.join([c for c in col if c]) for col in W.columns]
W.to_csv('spread_portfolio_IS_vs_OOS.csv', index=False)

# 4) best IS config per rule (n_IS>=30), by skew family; OOS check + random baseline same cfg
o = []
for sk in ['none', 'skew']:
    sub = W[W['skew'] == sk]
    for rule in ['trend', 'meanrev', 'breakout', 'random', 'always_bull']:
        c = sub[(sub.rule == rule) & (sub.n_IS >= 30)].sort_values('mean_ret_IS', ascending=False)
        if not len(c): continue
        s = c.iloc[0]
        b = sub[(sub.rule == 'random') & (sub[cfg] == s[cfg]).all(axis=1)]
        o.append(dict(skew=sk, rule=rule, **{q: s[q] for q in cfg if q != 'skew'}, n_IS=s.n_IS, mean_IS=s.mean_ret_IS, n_OOS=s.n_OOS,
                      mean_OOS=s.mean_ret_OOS, ci95_OOS=f"[{s.mean_ret_ci_lo_OOS:.2f},{s.mean_ret_ci_hi_OOS:.2f}]", median_OOS=s.median_ret_OOS,
                      win_OOS=s.win_rate_OOS, pct_below50_OOS=s.pct_paths_below50_OOS, med_end_eq_OOS=s.median_end_equity_OOS,
                      random_same_cfg_mean_OOS=b.mean_ret_OOS.iloc[0] if len(b) else np.nan))
o = pd.DataFrame(o).round(3); o.to_csv('spread_best_IS_config_OOS_check.csv', index=False)
print(o.to_string())

# 5) share of configs with positive mean (portfolio), by rule x skew x period
sh = p.assign(pos=p.mean_ret > 0).groupby(['skew', 'rule', 'period']).pos.mean().unstack().round(3)
sh2 = p.assign(pos=p.mean_ret > 0).groupby(['skew', 'factor', 'period']).pos.mean().unstack().round(3)
med = p.groupby(['skew', 'rule', 'period']).agg(median_cfg_mean=('mean_ret', 'median'), median_cfg_win=('win_rate', 'median'),
        median_pct_below50=('pct_paths_below50', 'median'), median_end_eq=('median_end_equity', 'median'), n_median=('n', 'median')).round(3)
mu = med.unstack('period'); mu.columns = ['_'.join(c) for c in mu.columns]; sh.columns = ['share_pos_' + c for c in sh.columns]; summ = sh.join(mu); summ.to_csv('spread_summary_by_rule.csv')
print(sh); print(sh2); print(med.to_string())
print('by exit, OOS:'); print(p[p.period == 'OOS'].groupby(['skew', 'exit']).agg(pos=('mean_ret', lambda s: (s > 0).mean()), med=('mean_ret', 'median')).round(3))
print('by leg/exp, OOS:'); print(p[p.period == 'OOS'].groupby(['skew', 'leg', 'exp_days']).agg(pos=('mean_ret', lambda s: (s > 0).mean()), med=('mean_ret', 'median'), n=('n', 'median')).round(3))

# 6) comparison with prior single long options (portfolio level)
pr = pd.read_csv(PRIOR + 'portfolio_IS_vs_OOS.csv')
pr = pr[~((pr['mode'] == 'capped') & (pr.delta != 'cap'))]
pr['family'] = np.where(pr['mode'] == 'capped', 'single_capped_0.80', 'single_uncapped_0.3/0.5')
cmp1 = pr.groupby(['family', 'rule']).agg(n_cfg=('mean_ret_OOS', 'size'), share_pos_IS=('mean_ret_IS', lambda s: (s > 0).mean()),
        share_pos_OOS=('mean_ret_OOS', lambda s: (s > 0).mean()), median_cfg_mean_OOS=('mean_ret_OOS', 'median'),
        median_cfg_win_OOS=('win_rate_OOS', 'median'), median_cfg_median_OOS=('median_ret_OOS', 'median')).reset_index()
Wc = W.assign(family='spread_' + W['skew'])
cmp2 = Wc.groupby(['family', 'rule']).agg(n_cfg=('mean_ret_OOS', 'size'), share_pos_IS=('mean_ret_IS', lambda s: (s > 0).mean()),
        share_pos_OOS=('mean_ret_OOS', lambda s: (s > 0).mean()), median_cfg_mean_OOS=('mean_ret_OOS', 'median'),
        median_cfg_win_OOS=('win_rate_OOS', 'median'), median_cfg_median_OOS=('median_ret_OOS', 'median')).reset_index()
cmp = pd.concat([cmp1, cmp2]).round(3); cmp.to_csv('spread_vs_single_comparison.csv', index=False); print(cmp.to_string())
print('IS/OOS trade counts (portfolio, median over cfgs):', p.groupby('period').n.median().to_dict())
