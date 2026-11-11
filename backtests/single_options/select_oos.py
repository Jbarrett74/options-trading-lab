"""Honest selection: for each rule, pick the single best IS config (portfolio level, by IS mean return,
requiring n>=30), then report its OOS and the random baseline with the same config. Also factor sensitivity."""
import pandas as pd; pd.set_option('display.width', 250)
r = pd.read_csv('results_by_variant.csv')
p = r[(r.symbol == 'PORTFOLIO_1perday') & ~((r['mode'] == 'capped') & (r.delta != 'cap'))]
cfg = ['exp_days', 'factor', 'delta', 'mode', 'exit']
W = p.pivot_table(index=['rule'] + cfg, columns='period', values=['n', 'mean_ret', 'median_ret', 'win_rate', 'pct_paths_ruined', 'maxdd_usd']).reset_index()
W.columns = ['_'.join([c for c in col if c]) for col in W.columns]
W.to_csv('portfolio_IS_vs_OOS.csv', index=False)
out = []
for fam, sub in [('uncapped_0.3/0.5', W[W['mode'] == 'uncapped']), ('capped_$0.80', W[W['mode'] == 'capped'])]:
    for rule in ['trend', 'meanrev', 'breakout']:
        s = sub[(sub.rule == rule) & (sub.n_IS >= 30)].sort_values('mean_ret_IS', ascending=False).iloc[0]
        base = sub[(sub.rule == 'random') & (sub[cfg[:-1]] == s[cfg[:-1]]).all(axis=1) & (sub.exit == s.exit)].iloc[0]
        out.append(dict(family=fam, rule=rule, **{c: s[c] for c in cfg}, n_IS=s.n_IS, mean_IS=s.mean_ret_IS, n_OOS=s.n_OOS, mean_OOS=s.mean_ret_OOS,
                        median_OOS=s.median_ret_OOS, win_OOS=s.win_rate_OOS, ruin_OOS=s.pct_paths_ruined_OOS, maxdd_OOS=s.maxdd_usd_OOS,
                        random_same_cfg_mean_OOS=base.mean_ret_OOS))
o = pd.DataFrame(out).round(3); o.to_csv('best_IS_config_OOS_check.csv', index=False); print(o.to_string())
# share of configs with positive mean, by mode/factor/period
print(p[p.period != 'ALL'].assign(pos=lambda d: d.mean_ret > 0).groupby(['mode', 'factor', 'period']).pos.mean().unstack().round(3))
print(p[(p.period == 'ALL')].groupby(['rule', 'mode', 'factor']).mean_ret.median().unstack().round(3))
print(p[(p.period == 'ALL')].groupby(['rule', 'mode', 'factor']).pct_paths_ruined.median().unstack().round(3))
