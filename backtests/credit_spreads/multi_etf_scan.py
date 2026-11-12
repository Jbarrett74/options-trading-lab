"""Credit spread scan across 20 liquid ETFs, limited to spreads whose max loss is at or below $100.

Usage: python3 multi_etf_scan.py prep RH_FILE_1.json RH_FILE_2.json   (builds prices_multi.csv from Robinhood day bars)
       python3 multi_etf_scan.py                                      (runs the scan)
Same engine as credit_backtest.py (signal at close, entry next open, BS on 20d realized vol x 1.0 / 1.2 / 1.4,
skew A=0.25 B=-0.10, exits, rules, CPI and FOMC event filter). Differences:
- Strike increment $0.50 when the entry price is under $50, else $1 (assumed, not checked against each chain's history).
- Widths $0.50 and $1 only, so one contract never risks more than $100.
- Costs: half-spread max($0.02, 2% of leg mid) + $0.04 fees per leg, each way. These ETFs trade wider than SPY.
  Not calibrated per ticker.
- No VIX-style cross-check exists for these tickers, and the skew is the SPY skew. Both are assumptions.
- Single stocks are left out because the model has no earnings dates or earnings IV.

Pass rule, written before the run. 60 ticker x strategy picks are tested, so the bar is higher than the SPY/QQQ run:
  1. config chosen in-sample (best mean return on max loss at factor 1.2, at least 60 IS trades);
  2. out of sample at factor 1.2: at least 30 trades, mean P&L > 0, and the 1% lower bound of the mean > 0
     (month-block bootstrap). With 60 picks and no real edge, about 0.6 false passes are expected;
  3. out of sample mean P&L > 0 at factor 1.0 too, so the result is not created by the assumed IV premium alone;
  4. timing rules must reach the 95th percentile against random entry.
A backtest pass is only a candidate. Before any trade the live IV / 20d realized vol ratio and the live bid/ask
must be checked on the actual chain.
Output: multi_etf_best_IS_config_OOS_check.csv, multi_etf_always_baseline.csv
"""
import os, sys, json
os.environ.setdefault('HS_FLOOR', '0.02'); os.environ.setdefault('HS_PCT', '0.02')
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import credit_backtest as cb
import credit_analyze as ca
from credit_backtest import indicators, pick_expiry, vertical, exits, rule_masks, EXITS, RULES, DELTAS, EXPS, MIN_CREDIT
import formulas as F

MODES = {'f1.0': 1.0, 'f1.2': 1.2, 'f1.4': 1.4}; WIDTHS = [0.5, 1.0]

def prep(files):
    rows = []
    for f in files:
        for r in json.load(open(f))['data']['results']:
            b = pd.DataFrame(r['bars'])
            rows.append(pd.DataFrame({'symbol': r['symbol'], 'date': b.begins_at.str[:10], 'open': b.open_price.astype(float),
                        'high': b.high_price.astype(float), 'low': b.low_price.astype(float), 'close': b.close_price.astype(float)}))
    p = pd.concat(rows); p.to_csv(os.path.join(HERE, 'prices_multi.csv'), index=False)
    print(p.groupby('symbol').agg(n=('date', 'size'), first=('date', 'min'), last=('date', 'max'), px=('close', 'last')))

def trades(sym, g, evd):
    g = indicators(g.sort_values('date').reset_index(drop=True)); dates = pd.DatetimeIndex(g.date)
    rm = rule_masks(g); ok0 = (g.sma50.notna() & g.rv20.notna()).values; out = []
    for E in EXPS:
        rec = [(t, t + 1) + pick_expiry(dates, t + 1, E) for t in range(len(g) - 1) if ok0[t]]
        rec = [r for r in rec if r[2] is not None]
        t = np.array([r[0] for r in rec]); ie = np.array([r[1] for r in rec]); jx = np.array([r[3] for r in rec])
        exp = pd.DatetimeIndex([r[2] for r in rec]); L = jx - ie + 1
        idx = np.minimum(ie[:, None] + np.arange(L.max())[None, :], jx[:, None]); pre = np.arange(L.max())[None, :] <= (L - 2)[:, None]
        S0 = g.open.values[ie]; T0 = ((exp - dates[ie]).days.values + 0.3) / 365; inc = np.where(S0 < 50, 0.5, 1.0)
        Sp = g.close.values[idx]; Tp = (exp.values[:, None] - dates.values[idx]).astype('timedelta64[D]').astype(float) / 365
        ev_ok = np.searchsorted(evd, dates.values[ie], 'left') == np.searchsorted(evd, exp.values, 'right')
        for mode, f in MODES.items():
            b0 = f * g.rv20.values[t]; bp = f * g.rv20.values[idx]
            for D in DELTAS:
                for W in WIDTHS:
                    wok = W >= inc - 1e-9          # a $0.50 spread needs $0.50 strikes
                    legs = {s: vertical(S0, T0, b0, Sp, Tp, bp, s == 'call', D, W, inc) for s in ('put', 'call')}
                    for strat in ('put', 'call', 'condor'):
                        if strat == 'condor':
                            (kp, Cp, Dp, sp), (kc, Cc, Dc, sc) = legs['put'], legs['call']
                            Ks, C, Dk, settle = kp, Cp + Cc, Dp + Dc, sp + sc; feas = (Cp >= MIN_CREDIT) & (Cc >= MIN_CREDIT)
                        else:
                            Ks, C, Dk, settle = legs[strat]; feas = C >= MIN_CREDIT
                        df = pd.DataFrame({'symbol': sym, 'strat': strat, 'delta': D, 'width': W, 'dte': E, 'ivmode': mode, 'date': dates[ie],
                                           'expiry': exp, 'ie': ie, 'feasible': feas & wok, 'ev_ok': ev_ok, 'S': S0, 'short_k': Ks, 'credit': C, 'max_loss': W - C})
                        for r in RULES: df['r_' + r] = True if r == 'always' else rm[(r, strat)].values[t]
                        for x, (pnl, k) in exits(C, Dk, settle, pre, L).items(): df['pnl_' + x] = pnl; df['kx_' + x] = k.astype(np.int16)
                        out.append(df)
    return pd.concat(out, ignore_index=True), dates

def main():
    P = pd.read_csv(os.path.join(HERE, 'prices_multi.csv'), parse_dates=['date'])
    EV = pd.read_csv(os.path.join(HERE, 'events.csv'), parse_dates=['date']); evd = np.sort(EV[EV.applies_to.str.contains('SPY')].date.values)
    rows, base = [], []
    for sym, g in P.groupby('symbol'):
        tr, dates = trades(sym, g, evd); ud = np.sort(tr.date.unique()); cut = ud[int(0.7 * len(ud))]
        tr['seg'] = np.where(tr.date < cut, 'IS', 'OOS'); G = ca.grid(tr); dbs = {sym: dates}
        b = G[(G.rule == 'always') & (G.exit == 'hold') & (~G.evfilter)]
        base.append(b.groupby(['symbol', 'strat', 'ivmode'], observed=True).agg(configs=('n_IS', 'size'), mean_ret_IS=('mean_ret_IS', 'mean'),
                    mean_ret_OOS=('mean_ret_OOS', 'mean'), win_OOS=('win_OOS', 'mean'), mean_pnl_OOS=('mean_pnl_OOS', 'mean'), worst_OOS=('worst_OOS', 'min')).reset_index())
        pool = G[(G.ivmode == 'f1.2') & (G.n_IS >= 60)]
        for strat, q in pool.groupby('strat', observed=True):
            c = q.sort_values('mean_ret_IS', ascending=False).iloc[0]; res = {}
            for mode in MODES:
                r = G[(G[ca.CFG] == c[ca.CFG]).all(axis=1) & (G.ivmode == mode)]
                if r.empty: continue
                r = r.iloc[0]; s = ca.select(tr, c, mode, 'OOS'); s = s[s.feasible & s['r_' + c.rule] & (s.ev_ok | (not c.evfilter))]
                row = {**{k: c[k] for k in ca.CFG}, 'ivmode': mode, 'price': g.close.iloc[-1]}
                for k in ('n', 'win', 'mean_pnl', 'med_pnl', 'mean_ret', 'worst'): row[k + '_IS'] = r[k + '_IS']; row[k + '_OOS'] = r[k + '_OOS']
                row['avg_credit_OOS'] = 100 * s.credit.mean() if len(s) else np.nan
                if len(s) >= 30:
                    row['oos_mean_lo1'] = 100 * ca.boot_lo(s['pnl_' + c.exit].values, s.date.values, q=1)
                    if c.rule != 'always': row['random_pctile'], _ = ca.random_pct(tr, c, mode)
                    po, mo = ca.sequential(tr, c, mode, dbs, 'OOS'); pf, mf = ca.sequential(tr, c, mode, dbs)
                    row.update(seq_trades_OOS=len(po), seq_total_OOS=po.sum(), seq_maxdd_OOS=ca.max_dd(po), ruin_OOS=ca.ruin(po, mo), ruin_full=ca.ruin(pf, mf))
                res[mode] = row
            f2, f0 = res.get('f1.2'), res.get('f1.0'); why = []
            if f2 is None or not f2['n_OOS'] >= 30: why.append('too few OOS trades')
            else:
                if not f2['mean_pnl_OOS'] > 0: why.append('f1.2 mean <= 0')
                if not f2.get('oos_mean_lo1', -1) > 0: why.append('f1.2 1% lower bound <= 0')
                if f0 is None or not f0['mean_pnl_OOS'] > 0: why.append('f1.0 mean <= 0')
                if c.rule != 'always' and not f2.get('random_pctile', 0) >= 0.95: why.append('does not beat random entry')
            for row in res.values(): row['verdict'] = 'PASS' if not why else 'fail: ' + '; '.join(why); rows.append(row)
        print(sym, 'done', flush=True)
    b = pd.DataFrame(rows); b.round(4).to_csv(os.path.join(HERE, 'multi_etf_best_IS_config_OOS_check.csv'), index=False)
    pd.concat(base).round(4).to_csv(os.path.join(HERE, 'multi_etf_always_baseline.csv'), index=False)
    pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 300)
    show = ['symbol', 'strat', 'delta', 'width', 'dte', 'exit', 'rule', 'evfilter', 'n_IS', 'mean_pnl_IS', 'n_OOS', 'win_OOS', 'mean_pnl_OOS', 'worst_OOS',
            'avg_credit_OOS', 'oos_mean_lo1', 'random_pctile', 'seq_trades_OOS', 'seq_maxdd_OOS', 'ruin_OOS', 'ruin_full', 'verdict']
    print(b[b.ivmode == 'f1.2'][show].round(2).to_string(index=False))
    print(b[b.verdict == 'PASS'].round(3).to_string(index=False))

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'prep': prep(sys.argv[2:])
    else: main()
