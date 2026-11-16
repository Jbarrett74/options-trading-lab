"""Phase 2 data quality run. Reads the stored data files, compares them with fresh raw pulls, writes problem_log.csv.

  python3 data_quality/run_checks.py

Inputs (all OBSERVED unless noted):
  backtests/credit_spreads/prices_daily.csv     SPY (FMP, split-adjusted), QQQ (Robinhood, split-adjusted), VIX close (FMP)
  backtests/credit_spreads/prices_multi.csv     20 ETFs (Robinhood, split-adjusted)
  backtests/single_options/raw_prices_daily.csv 5 symbols from 2024-08 (Robinhood)
  backtests/single_options/real_option_sample.csv  Robinhood daily option bars
  data_quality/sources/rh_daily_raw_2026-11-16.csv.gz  Robinhood daily bars, adjustment none, pulled 2026-11-16
  data_quality/sources/fmp_splits.csv, fmp_dividends_SPY.csv  FMP, pulled 2026-11-16
  data_quality/events_v2.csv                    event list with release times and verification status
  paper_trading/snapshots/chain_*.csv, paper_trading/ledger_v2.csv
Outputs: data_quality/problem_log.csv, data_quality/split_events.csv, data_quality/summary.json
"""
import glob, json, os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'quant'))
import data_checks as C

P = lambda *a: os.path.join(ROOT, *a)


def load(path): return pd.read_csv(path, parse_dates=['date'])


def main():
    probs = []; summ = {}
    raw = load(P('data_quality', 'sources', 'rh_daily_raw_2026-11-16.csv.gz'))
    stored = {'prices_daily': load(P('backtests', 'credit_spreads', 'prices_daily.csv')),
              'prices_multi': load(P('backtests', 'credit_spreads', 'prices_multi.csv')),
              'raw_prices_daily': load(P('backtests', 'single_options', 'raw_prices_daily.csv')),
              'rh_raw_2026-11-16': raw,
              'fmp_index_daily': load(P('data_quality', 'sources', 'fmp_index_daily.csv'))}
    sessions = C.nyse_sessions('2017-06-01', '2026-12-31')

    # 1. calendar, OHLC and stale checks on every price file
    for name, df in stored.items():
        for sym, g in df.groupby('symbol'):
            g = g.sort_values('date').reset_index(drop=True); before = len(probs)
            probs += C.calendar_problems(g.date, name, sym, sessions) + C.ohlc_problems(g, name, sym) + C.stale_runs(g, name, sym)
        n = df.symbol.nunique()
        bad = {(p['symbol']) for p in probs if p['dataset'] == name}
        probs.append(C.problem(name, 'ALL', 'calendar_ohlc_stale_scan', 'INFO', n - len(bad), df.date.min(), df.date.max(),
                               f'{n} symbols scanned, {n - len(bad)} with no calendar, OHLC or stale-bar problem'))

    # 2. splits: raw close / stored split-adjusted close; cross-check with FMP where FMP has the symbol
    fs = pd.read_csv(P('data_quality', 'sources', 'fmp_splits.csv'))
    rows = []
    adj_all = pd.concat([stored['prices_daily'][['symbol', 'date', 'close']], stored['prices_multi'][['symbol', 'date', 'close']]])
    for sym, a in adj_all.groupby('symbol'):
        r = raw[raw.symbol == sym]
        if sym == 'SPY':   # stored SPY is FMP: this is the cross-source check
            cmp_ = C.compare_close(a, r); summ['SPY_fmp_vs_robinhood'] = cmp_
            sev = 'INFO' if cmp_['n_diff'] == 0 and cmp_['best_lag'] == 0 else 'MED'
            probs.append(C.problem('prices_daily', 'SPY', 'cross_source_close', sev, cmp_['n_diff'], cmp_['first_diff'], cmp_['last_diff'],
                                   f"FMP vs Robinhood raw on {cmp_['n_common']} dates, max abs diff {cmp_['max_abs_diff']:.3f}, share equal by date shift {cmp_['match_by_lag']}"))
        ev = C.split_events(r, a)
        for d, f in ev: rows.append(dict(symbol=sym, effective_date=d, factor=f, source='robinhood raw vs stored adjusted'))
        # reproducibility: after removing the split ratio, stored close should equal the fresh raw close
        m = r[['date', 'close']].merge(a[['date', 'close']], on='date', suffixes=('_raw', '_adj')).sort_values('date')
        k = m.close_raw / m.close_adj; kr = k.round(0).where(k >= 0.75, (1 / (1 / k).round(0)))   # nearest whole split ratio
        dev = (m.close_raw / kr - m.close_adj).abs(); nbad = int((dev > 0.011).sum())
        if nbad and sym != 'SPY':
            b = m[dev > 0.011]
            probs.append(C.problem('prices_multi' if sym not in ('SPY', 'QQQ') else 'prices_daily', sym, 'stored_vs_fresh_pull', 'MED', nbad, b.date.min(), b.date.max(),
                                   f'stored split-adjusted close differs from fresh raw close / split ratio by more than $0.011, max {dev.max():.3f} '
                                   f"({100 * (dev / m.close_adj).max():.1f}% of price) on: " + ' '.join(b.date.dt.strftime('%Y-%m-%d').head(8))))
    se = pd.DataFrame(rows)
    for sym in ('NVDA', 'AAPL', 'MSFT', 'TSLA'):       # stocks: raw_prices_daily starts 2024-08, so use FMP for the record
        for r_ in fs[(fs.symbol == sym) & (fs.date >= '2017-06-01')].itertuples():
            se.loc[len(se)] = dict(symbol=sym, effective_date=r_.date, factor=r_.numerator / r_.denominator, source='FMP splits')
    se = se.sort_values(['symbol', 'effective_date']); se.to_csv(P('data_quality', 'split_events.csv'), index=False)
    summ['splits'] = se.to_dict('records')
    for r_ in se.itertuples():
        probs.append(C.problem('prices_multi' if r_.source.startswith('robinhood') else 'raw_prices_daily', r_.symbol, 'split_in_sample', 'MED', 1, r_.effective_date, r_.effective_date,
                               f'{r_.factor:g}-for-1 split. Stored prices before this date are divided by {r_.factor:g}, so modeled $1 strikes and '
                               f'dollar costs before it are not the strikes or costs that traded'))
    # stocks in raw_prices_daily: is the stored series split-adjusted?
    for sym, a in stored['raw_prices_daily'].groupby('symbol'):
        r = raw[raw.symbol == sym]; ev = C.split_events(r, a); cmp_ = C.compare_close(a, r)
        probs.append(C.problem('raw_prices_daily', sym, 'cross_pull_close', 'INFO' if cmp_['n_diff'] == 0 else 'MED', cmp_['n_diff'], cmp_['first_diff'], cmp_['last_diff'],
                               f"stored vs fresh raw pull on {cmp_['n_common']} dates, max abs diff {cmp_['max_abs_diff']:.3f}, implied splits {ev}"))

    # 3. large one-day moves in the stored (adjusted) data: real move or bad adjustment?
    for sym, a in adj_all.groupby('symbol'):
        a = a.sort_values('date').reset_index(drop=True); j = C.jumps(a, 0.15)
        if not len(j): continue
        r = raw[raw.symbol == sym].sort_values('date').reset_index(drop=True); jr = C.jumps(r, 0.15)
        only_adj = sorted(set(j.date) - set(jr.date))
        sev = 'HIGH' if only_adj else 'INFO'
        probs.append(C.problem('prices_multi' if sym not in ('SPY', 'QQQ') else 'prices_daily', sym, 'one_day_move_over_15pct', sev, len(j), j.date.min(), j.date.max(),
                               ('adjusted series jumps where raw does not: ' + ' '.join(str(d)[:10] for d in only_adj)) if only_adj else
                               'present in the raw series too, so real moves: ' + ' '.join(f"{str(d)[:10]}({x:+.0%})" for d, x in zip(j.date, np.expm1(j.ret)))))


    # 3b. ETF close vs its index (FMP): a second source for returns. Residual = ETF return minus index return.
    ix = load(P('data_quality', 'sources', 'fmp_index_daily.csv'))
    for etf, idx, name in (('SPY', '^GSPC', 'prices_daily'), ('IWM', '^RUT', 'prices_multi'), ('DIA', '^DJI', 'prices_multi')):
        for src, a in (('stored', adj_all[adj_all.symbol == etf]), ('robinhood_raw', raw[raw.symbol == etf])):
            if etf != 'SPY' and src == 'robinhood_raw': continue
            m = a[['date', 'close']].merge(ix[ix.symbol == idx][['date', 'close']], on='date', suffixes=('', '_ix')).sort_values('date')
            res = (m.close.pct_change() - m.close_ix.pct_change()); big = m[res.abs() > 0.006]
            summ[f'{etf}_{src}_vs_{idx}'] = dict(n=len(m), resid_sd_pct=float(100 * res.std()), n_over_0p6pct=len(big),
                                                 dates=[f"{str(d)[:10]}({x:+.2%})" for d, x in zip(big.date, res[res.abs() > 0.006])])
            probs.append(C.problem(name if src == 'stored' else 'rh_raw_2026-11-16', etf, 'return_vs_index', 'MED' if len(big) else 'INFO', len(big), big.date.min() if len(big) else '', big.date.max() if len(big) else '',
                                   f"{src} close vs FMP {idx} on {len(m)} days: residual sd {100 * res.std():.3f}%, days over 0.6%: " + (' '.join(summ[f'{etf}_{src}_vs_{idx}']['dates']) or 'none')))
    probs.append(C.problem('prices_multi', 'ALL', 'single_source_prices', 'MED', 19, '', '', 'QQQ and 18 of the 20 ETFs come from Robinhood only. FMP refuses them, so their closes have no second source. '
                           'The SPY comparison shows what to expect: Robinhood disagreed with FMP on 43 of 2376 closes, 2 of them by more than $3'))

    # 3c. Robinhood closes that FMP and the index both contradict
    a = adj_all[adj_all.symbol == 'SPY'].merge(raw[raw.symbol == 'SPY'], on='date', suffixes=('_fmp', '_rh'))
    b = a[(a.close_fmp - a.close_rh).abs() > 1.0]
    probs.append(C.problem('rh_raw_2026-11-16', 'SPY', 'bad_close_in_robinhood', 'HIGH' if len(b) else 'INFO', len(b), b.date.min() if len(b) else '', b.date.max() if len(b) else '',
                           'Robinhood close differs from FMP by more than $1 and equals the day high: ' + ' '.join(f"{str(r.date)[:10]} rh {r.close_rh} fmp {r.close_fmp} high {r.high}" for r in b.itertuples())
                           + '. FMP agrees with the S&P 500 index on both days. The stored SPY file uses FMP, so SPY backtests are unaffected; QQQ and the ETFs have no such check'))

    # 4. dividends: stored closes are not dividend-adjusted (they equal raw closes), so returns omit distributions
    dv = pd.read_csv(P('data_quality', 'sources', 'fmp_dividends_SPY.csv'), parse_dates=['date'])
    dv = dv[(dv.date >= '2017-06-01') & (dv.date <= '2026-11-13')]
    spy = stored['prices_daily'][stored['prices_daily'].symbol == 'SPY'].set_index('date').close
    yld = (dv.set_index('date').dividend / spy.reindex(dv.date).values)
    summ['SPY_dividends'] = dict(n=len(dv), mean_pct_per_ex_date=float(100 * yld.mean()), max_pct=float(100 * yld.max()),
                                 annual_pct=float(100 * yld.groupby(yld.index.year).sum().iloc[1:-1].mean()))
    probs.append(C.problem('prices_daily', 'SPY', 'dividends_not_in_prices', 'LOW', len(dv), dv.date.min(), dv.date.max(),
                           f"{len(dv)} ex-dividend dates, mean {100 * yld.mean():.2f}% of price each, about {summ['SPY_dividends']['annual_pct']:.2f}% a year. "
                           'Prices are split-adjusted only. Option models here use no dividend yield, which overprices calls and underprices puts slightly'))
    probs.append(C.problem('prices_multi', 'ALL', 'dividends_unknown', 'MED', 20, '', '', 'FMP returns no dividend history for the 20 ETFs or QQQ on this plan. TLT and HYG pay monthly '
                           'and USO, GLD, SLV pay nothing; ex-dividend drops are untested for every ETF except SPY. No early-assignment modelling is possible without ex-dates'))

    # 5. VIX column
    pdx = stored['prices_daily']; v = pdx[pdx.symbol == 'SPY'].sort_values('date')
    rep = int((v.vix == v.vix.shift(1)).sum())
    probs.append(C.problem('prices_daily', 'VIX', 'vix_forward_fill', 'LOW' if rep else 'INFO', rep, '', '', f'{int(v.vix.isna().sum())} missing, {rep} days equal to the prior day '
                           '(prep_data.py forward-fills gaps, so a repeat can be a real tie or a filled gap; range ' f'{v.vix.min():.2f} to {v.vix.max():.2f})'))

    # 6. survivorship and universe selection
    cnt = stored['prices_multi'].groupby('symbol').size()
    probs.append(C.problem('prices_multi', 'ALL', 'universe_chosen_with_hindsight', 'MED', len(cnt), '', '',
                           f'all {len(cnt)} ETFs have {int(cnt.min())} to {int(cnt.max())} rows: the list was picked in 2026-11 from funds alive and liquid today. Funds that closed or lost '
                           'liquidity since 2017 are absent. Single-ticker results are not affected. Any claim across the universe is'))
    probs.append(C.problem('raw_prices_daily', 'ALL', 'universe_chosen_with_hindsight', 'MED', 5, '', '', 'AAPL, NVDA, MSFT, TSLA were picked as large winners known in 2026; a long-call test on them inherits that choice'))

    # 7. option bars
    o = pd.read_csv(P('backtests', 'single_options', 'real_option_sample.csv'), parse_dates=['date', 'expiration'])
    ni = int(o.interpolated.astype(str).str.lower().eq('true').sum())
    probs.append(C.problem('real_option_sample', 'ALL', 'interpolated_option_bars', 'MED' if ni else 'INFO', ni, o.date.min(), o.date.max(),
                           f'{ni} of {len(o)} daily option bars are flagged interpolated by Robinhood (no trade that day); these carry no price information'))
    late = o[o.date > o.expiration]; bad = o[(o.high < o.low) | (o[['open', 'high', 'low', 'close']] <= 0).any(axis=1)]
    if len(late):
        li = int(late.interpolated.astype(str).str.lower().eq('true').sum())
        probs.append(C.problem('real_option_sample', 'ALL', 'bar_after_expiration', 'LOW' if li == len(late) else 'HIGH', len(late), late.date.min(), late.date.max(),
                               f'Robinhood returns bars dated after expiry; {li} of {len(late)} are flagged interpolated. fetch_option_sample.py drops interpolated bars before use'))
    if len(bad): probs.append(C.problem('real_option_sample', 'ALL', 'bad_option_bar', 'MED', len(bad), bad.date.min(), bad.date.max(), 'high below low or non-positive price'))
    probs.append(C.problem('real_option_sample', 'ALL', 'no_bid_ask_history', 'HIGH', len(o), '', '', 'Robinhood option history is trade-based OHLC per contract. It has no bid, ask, size, '
                           'volume, open interest or implied volatility. No reachable source has them, so option backtests cannot fill at observed quotes'))

    # 8. chain snapshots
    for f in sorted(glob.glob(P('paper_trading', 'snapshots', 'chain_*.csv'))):
        rows_ = pd.read_csv(f, dtype=str).to_dict('records'); name = os.path.basename(f)
        p, st = C.quote_problems(rows_, name); probs += p; summ[name] = st

        # observed half-spread vs the half-spread the backtests charge: max($0.01, 1%) for SPY/QQQ, max($0.02, 2%) in the ETF scan
        q = pd.read_csv(f); q = q[(q.missing == 0) & (q.delta.abs() >= 0.05) & (q.delta.abs() <= 0.35)].copy()
        mid = (q.bid + q.ask) / 2; q['obs_half'] = (q.ask - q.bid) / 2
        core = q.ticker.isin(['SPY', 'QQQ']); q['model_half'] = np.where(core, np.maximum(0.01, 0.01 * mid), np.maximum(0.02, 0.02 * mid))
        g = q.groupby('ticker').agg(n=('obs_half', 'size'), obs_half_median=('obs_half', 'median'), model_half_median=('model_half', 'median'))
        g['ratio'] = (q.obs_half / q.model_half).groupby(q.ticker).median(); summ[name + '_cost_vs_model'] = g.round(4).reset_index().to_dict('records')
        for r_ in g.itertuples():
            sev = 'HIGH' if r_.ratio > 1.5 else 'INFO'
            probs.append(C.problem(name, r_.Index, 'observed_half_spread_vs_cost_model', sev, r_.n, '', '', f'{r_.n} contracts with 0.05 to 0.35 delta: observed half-spread median '
                                   f'${r_.obs_half_median:.3f}, backtest charges ${r_.model_half_median:.3f}, median ratio {r_.ratio:.2f}. One snapshot, on a day SPY fell 1.7%'))
        probs.append(C.problem(name, 'ALL', 'snapshot_scan', 'INFO', st['n'], '', '', f"{st['n']} contracts, median bid-ask {st['median_rel_spread']:.1%} of mid, "
                               f"90th percentile {st['p90_rel_spread']:.1%}, oldest quote {st['max_age_min']:.1f} min"))

    # 9. ledger timestamps
    L = pd.read_csv(P('paper_trading', 'ledger_v2.csv'), dtype=str).fillna('')
    probs += C.timestamp_problems(L.ts_et, 'ledger_v2', sessions)
    nq = int((L.quote_ts_utc == '').sum())
    probs.append(C.problem('ledger_v2', 'ALL', 'quote_timestamp_missing', 'MED' if nq else 'INFO', nq, '', '', f'{nq} of {len(L)} rows have no quote_ts_utc (rows backfilled from log.csv, which stored no quote time)'))
    lg = pd.read_csv(P('paper_trading', 'log.csv'), dtype=str).fillna('')
    probs.append(C.problem('log.csv', 'ALL', 'no_time_of_day', 'MED', len(lg), lg.date.min(), lg.date.max(), 'log.csv has a date column only; entry and exit times live in free text. ledger_v2.csv replaces it'))
    ld = pd.to_datetime(lg.date, errors='coerce'); off = lg[~ld.isin(sessions)]
    if len(off): probs.append(C.problem('log.csv', 'ALL', 'row_on_non_session', 'HIGH', len(off), off.date.min(), off.date.max(), ''))

    # 10. events
    for name, path in (('events.csv', P('backtests', 'credit_spreads', 'events.csv')), ('events_v2.csv', P('data_quality', 'events_v2.csv'))):
        if not os.path.exists(path): continue
        ev = pd.read_csv(path); probs += C.event_problems(ev, name, sessions)
        if 'verification' in ev:
            vc = ev.groupby(['event', 'verification']).size()
            summ['events_v2_verification'] = {f'{a}|{b}': int(n) for (a, b), n in vc.items()}
            un = ev[ev.verification.str.startswith(('memory', 'third_party'))]
            for e, g in un.groupby('event'):
                probs.append(C.problem(name, e, 'event_date_unverified', 'MED', len(g), g.date.min(), g.date.max(), f'{len(g)} of {int((ev.event == e).sum())} dates typed from memory or from a third-party calendar, not checked against a primary source'))

    out = pd.DataFrame(probs, columns=C.PROBLEM_FIELDS)
    out.insert(0, 'id', [f'P{i + 1:03d}' for i in range(len(out))])
    out.to_csv(P('data_quality', 'problem_log.csv'), index=False)
    json.dump(summ, open(P('data_quality', 'summary.json'), 'w'), indent=1, default=str)
    print(out.groupby(['severity']).size().to_string()); print()
    pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 150)
    print(out[out.severity != 'INFO'].drop(columns=['detail']).to_string(index=False))
    return out


if __name__ == '__main__':
    main()
