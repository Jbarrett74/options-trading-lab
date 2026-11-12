"""Summaries for the credit spread backtest. Reads credit_trades_all.pkl from credit_backtest.py.

Split: first 70% of entry dates in-sample (IS), last 30% out-of-sample (OOS), chronological.
A config = symbol, strategy, delta, width, dte, exit, entry rule, event filter on/off.

Pass rule, written before looking at OOS results. A config "holds up" only if ALL are true out of sample:
  1. at IV factor 1.2: at least 30 trades, mean P&L > 0, and the 5% lower bound of the mean (month-block bootstrap) > 0;
  2. mean P&L > 0 under the 'vix' IV mode as well (so the result does not rest on the realized-vol factor alone);
  3. for a timing rule (trend, meanrev, highvol): mean P&L at or above the 95th percentile of random entry, where
     random entry = the same structure entered on the rule's day pattern shifted by a random number of days.
     The 'always' rule IS random entry, so it has no timing claim and is judged on 1 and 2 only.
Configs are chosen in IS (best mean return on max loss at factor 1.2, at least 60 IS trades) and then checked OOS once.

Outputs: grid_IS_vs_OOS.csv, share_positive.csv, always_baseline.csv, best_IS_config_OOS_check.csv
Dollar figures are per one contract. Return = P&L / max loss (width minus credit).
"""
import os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'quant'))
import formulas as F
from credit_backtest import EXITS, RULES, IVMODES

SRC = os.environ.get('TRADES_OUT', os.path.join(HERE, 'credit_trades_all.pkl')); TAG = os.environ.get('TAG', '')
KEYS = ['symbol', 'strat', 'delta', 'width', 'dte']; CFG = KEYS + ['exit', 'rule', 'evfilter']
ACCOUNT, CAP, FLOOR = 380.0, 100.0, 100.0
rng = np.random.default_rng(20261112)


def grid(tr):
    parts = []
    for rule in RULES:
        for evf in (False, True):
            sub = tr[tr.feasible & tr['r_' + rule] & (tr.ev_ok | (not evf))]
            for x in EXITS:
                d = pd.DataFrame({'pnl': 100 * sub['pnl_' + x].values, 'ret': (sub['pnl_' + x] / sub.max_loss).values,
                                  'ml': 100 * sub.max_loss.values})
                for k in KEYS + ['ivmode', 'seg']: d[k] = sub[k].values
                a = d.groupby(KEYS + ['ivmode', 'seg'], observed=True).agg(
                    n=('pnl', 'size'), win=('pnl', lambda v: (v > 0).mean()), mean_pnl=('pnl', 'mean'), med_pnl=('pnl', 'median'),
                    mean_ret=('ret', 'mean'), med_ret=('ret', 'median'), worst=('pnl', 'min'), max_ml=('ml', 'max')).reset_index()
                a['exit'], a['rule'], a['evfilter'] = x, rule, evf; parts.append(a)
    g = pd.concat(parts, ignore_index=True)
    w = g.pivot_table(index=CFG + ['ivmode'], columns='seg', values=['n', 'win', 'mean_pnl', 'med_pnl', 'mean_ret', 'med_ret', 'worst', 'max_ml'], observed=True)
    w.columns = [f'{a}_{b}' for a, b in w.columns]; return w.reset_index()

def boot_lo(pnl, dates, B=2000):
    m = pd.Series(pnl).groupby(pd.DatetimeIndex(dates).to_period('M')).agg(['sum', 'count']).values
    i = rng.integers(0, len(m), (B, len(m))); return float(np.percentile(m[i, 0].sum(1) / m[i, 1].sum(1), 5))

def select(tr, c, mode, seg=None):
    s = tr[(tr.symbol == c.symbol) & (tr.strat == c.strat) & (tr.delta == c.delta) & (tr.width == c.width) & (tr.dte == c.dte) & (tr.ivmode == mode)]
    return s if seg is None else s[s.seg == seg]

def random_pct(tr, c, mode, B=2000):
    """Share of random day-shifts of the rule pattern whose mean P&L is below the rule's own (OOS)."""
    s = select(tr, c, mode, 'OOS').sort_values('date')
    ok = (s.feasible & (s.ev_ok | (not c.evfilter))).values; r = s['r_' + c.rule].values; p = s['pnl_' + c.exit].values
    act = p[ok & r].mean(); n = len(s); sims = []
    for sh in rng.integers(1, n, B):
        m = np.roll(r, sh) & ok
        if m.sum() >= 10: sims.append(p[m].mean())
    return float((np.array(sims) < act).mean()), 100 * float(np.mean(sims))

def sequential(tr, c, mode, dates_by_sym, seg=None):
    """One contract at a time: take the next eligible entry after the previous trade has exited."""
    s = select(tr, c, mode, seg)
    s = s[s.feasible & s['r_' + c.rule] & (s.ev_ok | (not c.evfilter))].sort_values('date')
    d = dates_by_sym[c.symbol]; last = pd.Timestamp('1900-01-01'); pnl = []; ml = []
    for dt, ie, k, p, m in zip(s.date, s.ie, s['kx_' + c.exit], s['pnl_' + c.exit], s.max_loss):
        if dt <= last: continue
        pnl.append(100 * p); ml.append(100 * m); last = d[ie + k]
    return np.array(pnl), np.array(ml)

def max_dd(pnl):
    eq = np.concatenate([[0], np.cumsum(pnl)]); return float((np.maximum.accumulate(eq) - eq).max()) if len(pnl) else np.nan

def ruin(pnl, ml, n_trades=100, paths=5000):
    """P(equity < $100 at any point in the next n_trades), $380 start, one contract, trade P&Ls resampled with replacement."""
    if len(pnl) < 15: return np.nan
    if ml.max() > CAP + 1e-9: return np.nan   # max loss above the $100 cap: not tradable under the user's rule
    eq = ACCOUNT + np.cumsum(pnl[rng.integers(0, len(pnl), (paths, n_trades))], 1)
    return float((eq.min(1) < FLOOR).mean())

def main():
    tr = pd.read_pickle(SRC)
    ud = np.sort(tr.date.unique()); cut = ud[int(0.7 * len(ud))]
    tr['seg'] = np.where(tr.date < cut, 'IS', 'OOS'); print('split date', pd.Timestamp(cut).date(), 'first', pd.Timestamp(ud[0]).date(), 'last', pd.Timestamp(ud[-1]).date())
    P = pd.read_csv(os.path.join(HERE, 'prices_daily.csv'), parse_dates=['date'])
    dbs = {s: pd.DatetimeIndex(g.sort_values('date').date) for s, g in P.groupby('symbol')}
    g = grid(tr); g.round(4).to_csv(os.path.join(HERE, f'grid_IS_vs_OOS{TAG}.csv'), index=False)

    ok = g[(g.n_IS >= 60) & (g.n_OOS >= 30)]
    sp = ok.groupby(['strat', 'ivmode'], observed=True).agg(configs=('n_IS', 'size'), pos_IS=('mean_pnl_IS', lambda v: (v > 0).mean()),
            pos_OOS=('mean_pnl_OOS', lambda v: (v > 0).mean()), med_mean_ret_IS=('mean_ret_IS', 'median'), med_mean_ret_OOS=('mean_ret_OOS', 'median')).reset_index()
    sp.round(4).to_csv(os.path.join(HERE, f'share_positive{TAG}.csv'), index=False); print(sp.round(3).to_string(index=False))

    base = g[(g.rule == 'always') & (g.exit == 'hold') & (~g.evfilter)]
    ab = base.groupby(['symbol', 'strat', 'ivmode'], observed=True).agg(configs=('n_IS', 'size'), mean_ret_IS=('mean_ret_IS', 'mean'), mean_ret_OOS=('mean_ret_OOS', 'mean'),
            win_OOS=('win_OOS', 'mean'), mean_pnl_OOS=('mean_pnl_OOS', 'mean'), worst_OOS=('worst_OOS', 'min')).reset_index()
    ab.round(4).to_csv(os.path.join(HERE, f'always_baseline{TAG}.csv'), index=False); print(ab.round(3).to_string(index=False))

    rows = []
    for scope in ('any_width', 'max_loss_le_100'):
        pool = g[(g.ivmode == 'f1.2') & (g.n_IS >= 60)]
        if scope == 'max_loss_le_100': pool = pool[pool.width == 1.0]
        for (sym, strat), q in pool.groupby(['symbol', 'strat'], observed=True):
            c = q.sort_values('mean_ret_IS', ascending=False).iloc[0]
            for mode in IVMODES:
                r = g[(g[CFG] == c[CFG]).all(axis=1) & (g.ivmode == mode)]
                if r.empty: continue
                r = r.iloc[0]; s = select(tr, c, mode, 'OOS'); s = s[s.feasible & s['r_' + c.rule] & (s.ev_ok | (not c.evfilter))]
                row = {'scope': scope, **{k: c[k] for k in CFG}, 'ivmode': mode}
                for k in ('n', 'win', 'mean_pnl', 'med_pnl', 'mean_ret', 'med_ret', 'worst'):
                    row[k + '_IS'] = r[k + '_IS']; row[k + '_OOS'] = r[k + '_OOS']
                row['max_loss_usd'] = r.max_ml_OOS
                if len(s) >= 30:
                    row['oos_mean_lo5'] = 100 * boot_lo(s['pnl_' + c.exit].values, s.date.values)
                    if c.rule != 'always': row['random_pctile'], row['random_mean_pnl'] = random_pct(tr, c, mode)
                    po, mo = sequential(tr, c, mode, dbs, 'OOS'); pf, mf = sequential(tr, c, mode, dbs)
                    row.update(seq_trades_OOS=len(po), seq_total_OOS=po.sum(), seq_maxdd_OOS=max_dd(po), seq_maxdd_full=max_dd(pf),
                               ruin_OOS=ruin(po, mo), ruin_full=ruin(pf, mf),
                               p_3_losses_in_50=F.losing_streak_prob(float((po <= 0).mean()), 3, 50) if len(po) else np.nan)
                rows.append(row)
    b = pd.DataFrame(rows)
    def verdict(q):
        a = q.set_index('ivmode'); f = a.loc['f1.2'] if 'f1.2' in a.index else None; v = a.loc['vix'] if 'vix' in a.index else None
        if f is None or v is None or not (f.n_OOS >= 30): return 'fail: too few OOS trades'
        why = []
        if not f.mean_pnl_OOS > 0: why.append('f1.2 mean <= 0')
        if not f.get('oos_mean_lo5', -1) > 0: why.append('f1.2 lower bound <= 0')
        if not v.mean_pnl_OOS > 0: why.append('vix mean <= 0')
        if f.rule != 'always' and not f.get('random_pctile', 0) >= 0.95: why.append('does not beat random entry')
        return 'PASS' if not why else 'fail: ' + '; '.join(why)
    vd = {k: verdict(q) for k, q in b.groupby(['scope', 'symbol', 'strat'], observed=True)}
    b['verdict'] = [vd[(r.scope, r.symbol, r.strat)] for r in b.itertuples()]
    b.round(4).to_csv(os.path.join(HERE, f'best_IS_config_OOS_check{TAG}.csv'), index=False)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
    show = ['scope', 'symbol', 'strat', 'delta', 'width', 'dte', 'exit', 'rule', 'evfilter', 'ivmode', 'n_IS', 'mean_pnl_IS', 'n_OOS', 'win_OOS', 'mean_pnl_OOS',
            'med_pnl_OOS', 'mean_ret_OOS', 'worst_OOS', 'oos_mean_lo5', 'random_pctile', 'seq_maxdd_OOS', 'ruin_OOS', 'ruin_full', 'verdict']
    print(b[[c for c in show if c in b.columns]].round(3).to_string(index=False))

if __name__ == '__main__':
    main()
