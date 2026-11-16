"""Data quality checks (Phase 2). Pure functions: each returns a list of problem dicts and changes nothing.

A problem dict has PROBLEM_FIELDS. Severity: HIGH = can change a backtest or trade decision, MED = biases results
by a small or bounded amount, LOW = cosmetic or conservative, INFO = checked and found clean, or a fact to record.
The runner is data_quality/run_checks.py, which writes data_quality/problem_log.csv.
"""
import datetime as dt
import numpy as np, pandas as pd

PROBLEM_FIELDS = ['dataset', 'symbol', 'check', 'severity', 'count', 'first', 'last', 'detail']
ET = 'America/New_York'


def problem(dataset, symbol, check, severity, count, first='', last='', detail=''):
    assert severity in ('HIGH', 'MED', 'LOW', 'INFO'), severity
    return dict(dataset=dataset, symbol=symbol, check=check, severity=severity, count=int(count),
                first=str(first)[:10] if first != '' else '', last=str(last)[:10] if last != '' else '', detail=detail)


def nyse_sessions(start, end):
    """NYSE trading days (dates, no time), from pandas_market_calendars. Includes special closures."""
    import pandas_market_calendars as mcal
    s = mcal.get_calendar('NYSE').schedule(start_date=str(start)[:10], end_date=str(end)[:10])
    return pd.DatetimeIndex(s.index).normalize()


def early_closes(start, end):
    import pandas_market_calendars as mcal
    c = mcal.get_calendar('NYSE'); s = c.schedule(start_date=str(start)[:10], end_date=str(end)[:10])
    return pd.DatetimeIndex(c.early_closes(s).index).normalize()


def calendar_problems(dates, dataset, symbol, sessions=None):
    """Missing sessions, rows on non-sessions, duplicate dates, unsorted dates."""
    d = pd.DatetimeIndex(pd.to_datetime(dates)); out = []
    if sessions is None: sessions = nyse_sessions(d.min(), d.max())
    sessions = sessions[(sessions >= d.min()) & (sessions <= d.max())]
    miss = sessions.difference(d); extra = d.difference(sessions); dup = d[d.duplicated()]
    if len(miss): out.append(problem(dataset, symbol, 'missing_session', 'HIGH', len(miss), miss.min(), miss.max(), 'NYSE sessions with no row'))
    if len(extra): out.append(problem(dataset, symbol, 'row_on_non_session', 'HIGH', len(extra), extra.min(), extra.max(), 'row dated on a weekend, holiday or closure'))
    if len(dup): out.append(problem(dataset, symbol, 'duplicate_date', 'HIGH', len(dup), dup.min(), dup.max(), ''))
    if not d.is_monotonic_increasing: out.append(problem(dataset, symbol, 'unsorted_dates', 'MED', 1, '', '', 'dates not ascending'))
    return out


def ohlc_problems(df, dataset, symbol):
    """Non-positive prices, high below low, open or close outside the high-low range, missing values."""
    out = []; c = [k for k in ('open', 'high', 'low', 'close') if k in df]
    def add(mask, check, sev, detail):
        if mask.any():
            b = df[mask]; out.append(problem(dataset, symbol, check, sev, len(b), b.date.min(), b.date.max(), detail))
    add(df[c].isna().any(axis=1), 'missing_value', 'HIGH', 'NaN in a price field')
    add((df[c] <= 0).any(axis=1), 'non_positive_price', 'HIGH', '')
    if {'high', 'low'} <= set(c):
        add(df.high < df.low - 1e-9, 'high_below_low', 'HIGH', '')
        for k in ('open', 'close'):
            if k in df: add((df[k] > df.high + 1e-9) | (df[k] < df.low - 1e-9), f'{k}_outside_range', 'MED', f'{k} above high or below low')
    return out


def stale_runs(df, dataset, symbol, run=2):
    """Bars identical to the previous bar in every price field (a sign of forward fill), and zero volume bars."""
    out = []; c = [k for k in ('open', 'high', 'low', 'close') if k in df]
    same = (df[c] == df[c].shift(1)).all(axis=1)
    if same.sum() >= run - 1 and same.any():
        b = df[same]; out.append(problem(dataset, symbol, 'repeated_bar', 'MED', len(b), b.date.min(), b.date.max(), 'bar equals the previous bar in every price field'))
    if 'volume' in df and (df.volume == 0).any():
        b = df[df.volume == 0]; out.append(problem(dataset, symbol, 'zero_volume', 'MED', len(b), b.date.min(), b.date.max(), ''))
    return out


def jumps(df, thresh=0.15):
    """Rows whose close-to-close log return exceeds thresh in absolute value."""
    r = np.log(df.close / df.close.shift(1)); m = r.abs() > thresh
    return pd.DataFrame({'date': df.date[m], 'ret': r[m]})


def split_events(raw, adj, tol=0.03):
    """Splits implied by raw close / adjusted close. Returns [(effective_date, factor)], factor 2.0 = 2-for-1.

    raw and adj: DataFrames with date and close for the same symbol. The ratio is constant between splits and
    equals 1 after the last split, so a change in the ratio marks the first session traded at the new share count.
    """
    m = raw[['date', 'close']].merge(adj[['date', 'close']], on='date', suffixes=('_raw', '_adj')).sort_values('date')
    k = (m.close_raw / m.close_adj).values; out = []
    for i in range(1, len(k)):
        f = k[i - 1] / k[i]
        if abs(f - 1) > tol: out.append((pd.Timestamp(m.date.values[i]).strftime('%Y-%m-%d'), round(float(f), 4)))
    return out


def compare_close(a, b, tol=0.011):
    """Compare two close series on common dates. Also reports which date shift (-1, 0, +1) agrees best."""
    a = a.set_index('date').close; b = b.set_index('date').close; idx = a.index.intersection(b.index)
    d = (a[idx] - b[idx]).abs(); bad = d[d > tol]
    lag = {}
    for s in (-1, 0, 1):
        bs = b.shift(s); j = a.index.intersection(bs.dropna().index); lag[s] = float(((a[j] - bs[j]).abs() <= tol).mean()) if len(j) else np.nan
    return dict(n_common=len(idx), n_diff=len(bad), max_abs_diff=float(d.max()) if len(d) else np.nan,
                first_diff=str(bad.index.min())[:10] if len(bad) else '', last_diff=str(bad.index.max())[:10] if len(bad) else '',
                match_by_lag=lag, best_lag=max(lag, key=lambda s: -1 if np.isnan(lag[s]) else lag[s]))


def quote_problems(rows, dataset, wide=0.10):
    """Checks on one option chain snapshot (rows from paper_trading/snapshot.py)."""
    q = pd.DataFrame(rows); out = []
    for c in ('bid', 'ask', 'mark', 'iv', 'delta', 'gamma', 'strike', 'open_interest', 'volume', 'quote_age_min'):
        q[c] = pd.to_numeric(q[c], errors='coerce')
    for c in ('stale', 'crossed', 'zero_bid', 'missing', 'id_mismatch'):
        q[c] = pd.to_numeric(q[c], errors='coerce').fillna(0).astype(int)
    day = str(q.snapshot_ts_utc.iloc[0])[:10]
    def add(mask, check, sev, detail):
        n = int(mask.sum())
        if n: out.append(problem(dataset, ','.join(sorted(q.ticker[mask].unique())), check, sev, n, day, day, detail))
    add(q.missing == 1, 'quote_missing', 'HIGH', 'instrument id returned no quote')
    add(q.id_mismatch == 1, 'id_mismatch', 'HIGH', 'break-even disagrees with strike +/- mark')
    add(q.crossed == 1, 'crossed_quote', 'HIGH', 'bid above ask')
    add(q.stale == 1, 'stale_quote', 'MED', 'quote older than 20 minutes at ingest')
    add(q.zero_bid == 1, 'zero_bid', 'MED', 'bid is zero, so a sale has no observed price')
    live = q[q.missing == 0]
    rel = (live.ask - live.bid) / ((live.ask + live.bid) / 2)
    add((q.missing == 0) & (((q.ask - q.bid) / ((q.ask + q.bid) / 2)) > wide), 'wide_quote', 'MED', f'bid-ask wider than {wide:.0%} of the mid')
    add((q.missing == 0) & ((q.mark < q.bid - 1e-9) | (q.mark > q.ask + 1e-9)), 'mark_outside_quote', 'MED', 'mark not between bid and ask')
    add((q.missing == 0) & q.iv.isna(), 'iv_missing', 'MED', 'no implied volatility returned')
    add((q.missing == 0) & q.gamma.isna(), 'gamma_missing', 'MED', 'no gamma returned')
    add((q.missing == 0) & (q.open_interest == 0), 'zero_open_interest', 'LOW', '')
    add((q.missing == 0) & (q.volume == 0), 'zero_volume_today', 'LOW', 'no trades yet in this session')
    mono = 0
    for (_, _, typ), g in live.groupby(['ticker', 'expiry', 'type']):
        m = g.sort_values('strike').mark.values; d = np.diff(m)
        mono += int(((d > 0.011) if typ == 'call' else (d < -0.011)).sum())
    if mono: out.append(problem(dataset, 'ALL', 'price_not_monotonic_in_strike', 'HIGH', mono, day, day, 'call marks rise or put marks fall with strike'))
    stats = dict(n=len(q), median_rel_spread=float(rel.median()), p90_rel_spread=float(rel.quantile(0.9)),
                 max_age_min=float(live.quote_age_min.max()), rel_by_ticker=rel.groupby(live.ticker).median().round(4).to_dict())
    return out, stats


def timestamp_problems(ts_et, dataset, sessions=None):
    """ts_et: strings 'YYYY-MM-DD HH:MM' in US Eastern wall time. Flags unparseable, non-session and off-hours stamps."""
    out = []; t = pd.to_datetime(pd.Series(list(ts_et), dtype='object'), format='%Y-%m-%d %H:%M', errors='coerce')
    bad = t.isna()
    if bad.any(): out.append(problem(dataset, '', 'timestamp_unparseable', 'MED', bad.sum(), '', '', 'not YYYY-MM-DD HH:MM'))
    t = t.dropna()
    if not len(t): return out
    if sessions is None: sessions = nyse_sessions(t.min(), t.max())
    off = ~t.dt.normalize().isin(sessions)
    if off.any(): out.append(problem(dataset, '', 'timestamp_on_non_session', 'HIGH', off.sum(), t[off].min(), t[off].max(), ''))
    mins = t.dt.hour * 60 + t.dt.minute; hrs = (mins < 570) | (mins > 960)
    if hrs.any(): out.append(problem(dataset, '', 'timestamp_outside_regular_hours', 'MED', hrs.sum(), t[hrs].min(), t[hrs].max(), 'before 9:30 or after 16:00 ET'))
    return out


def et_from_utc(ts_utc):
    """UTC ISO string -> timezone-aware US Eastern datetime, daylight saving handled by the tz database."""
    from zoneinfo import ZoneInfo
    s = ts_utc.replace('Z', '+00:00')
    if '.' in s:                                  # trim nanoseconds, which fromisoformat rejects
        head, rest = s.split('.', 1); digits = ''
        for ch in rest:
            if ch.isdigit(): digits += ch
            else: break
        s = head + '.' + digits[:6] + rest[len(digits):]
    return dt.datetime.fromisoformat(s).astimezone(ZoneInfo(ET))


def event_problems(ev, dataset, sessions):
    """ev: DataFrame with date, event. Flags events on non-sessions and years with an unexpected count."""
    out = []; ev = ev.copy(); ev['date'] = pd.to_datetime(ev.date)
    off = ev[~ev.date.isin(sessions)]
    for e, g in off.groupby('event'):
        out.append(problem(dataset, e, 'event_on_non_session', 'LOW', len(g), g.date.min(), g.date.max(),
                           'dates: ' + ' '.join(g.date.dt.strftime('%Y-%m-%d'))))
    want = {'FOMC': 8, 'CPI': 12, 'NVDA_earnings_reaction': 4}
    yrs = sorted(ev.date.dt.year.unique())[1:]          # the first year is partial by construction
    for e, n in want.items():
        cnt = ev[ev.event == e].groupby(ev.date.dt.year).size()
        odd = [f'{y}:{int(cnt.get(y, 0))}' for y in yrs if int(cnt.get(y, 0)) != n]
        if odd: out.append(problem(dataset, e, 'event_count_per_year', 'MED', len(odd), '', '', f'expected {n} per year, got ' + ' '.join(odd)))
    return out
