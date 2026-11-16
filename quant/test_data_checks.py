"""Tests for data_checks.py. Run: python3 quant/test_data_checks.py"""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_checks as C


def bars(dates, closes):
    return pd.DataFrame({'date': pd.to_datetime(dates), 'open': closes, 'high': [c + 1 for c in closes], 'low': [c - 1 for c in closes], 'close': closes})


def checks(ps): return sorted(p['check'] for p in ps)


def test_calendar():
    s = C.nyse_sessions('2024-03-25', '2024-04-05')
    assert pd.Timestamp('2024-03-29') not in s and len(s) == 9                      # Good Friday closed
    d = [x for x in s if x != pd.Timestamp('2024-04-02')] + [pd.Timestamp('2024-03-30'), pd.Timestamp('2024-04-01')]
    assert checks(C.calendar_problems(d, 'x', 'X', s)) == ['duplicate_date', 'missing_session', 'row_on_non_session', 'unsorted_dates']
    assert C.calendar_problems(s, 'x', 'X', s) == []
    assert pd.Timestamp('2024-11-29') in C.early_closes('2024-11-01', '2024-12-31')   # day after Thanksgiving, 1pm close


def test_ohlc_and_stale():
    b = bars(['2024-04-01', '2024-04-02', '2024-04-03', '2024-04-04'], [10.0, 10.0, 11.0, -1.0])
    b.loc[2, 'high'] = 9.0
    got = checks(C.ohlc_problems(b, 'x', 'X') + C.stale_runs(b, 'x', 'X'))
    assert got == ['close_outside_range', 'high_below_low', 'non_positive_price', 'open_outside_range', 'repeated_bar'], got
    assert C.ohlc_problems(bars(['2024-04-01', '2024-04-02'], [10.0, 11.0]), 'x', 'X') == []


def test_splits_and_compare():
    d = pd.bdate_range('2024-06-03', periods=8)
    adj = pd.DataFrame({'date': d, 'close': [10, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7]})
    raw = adj.copy(); raw.loc[:3, 'close'] = raw.loc[:3, 'close'] * 4            # 4-for-1 effective on the 5th bar
    assert C.split_events(raw, adj) == [(d[4].strftime('%Y-%m-%d'), 4.0)]
    rev = adj.copy(); rev.loc[:3, 'close'] = rev.loc[:3, 'close'] / 8           # 1-for-8 reverse split
    assert C.split_events(rev, adj) == [(d[4].strftime('%Y-%m-%d'), 0.125)]
    assert C.split_events(adj, adj) == []
    other = adj.copy(); other.loc[2, 'close'] += 0.5
    c = C.compare_close(adj, other); assert c['n_diff'] == 1 and c['best_lag'] == 0 and abs(c['max_abs_diff'] - 0.5) < 1e-9
    shifted = adj.copy(); shifted['close'] = shifted.close.shift(-1)
    assert C.compare_close(adj, shifted.dropna())['best_lag'] == 1                # a one-day date shift is detected
    assert len(C.jumps(raw, 0.15)) == 1


def test_quotes():
    base = dict(snapshot_ts_utc='2026-11-16T18:53:56Z', ticker='T', expiry='2026-12-18', iv='0.2', delta='0.3', gamma='0.01', open_interest='5', volume='1',
                quote_age_min='0.1', stale='0', crossed='0', zero_bid='0', missing='0', id_mismatch='0')
    rows = [dict(base, type='call', strike='10', bid='2.00', ask='2.02', mark='2.01'),
            dict(base, type='call', strike='11', bid='2.50', ask='2.52', mark='2.51'),               # call price rises with strike
            dict(base, type='put', strike='10', bid='0.10', ask='0.20', mark='0.30', iv=''),          # wide, mark outside, no iv
            dict(base, type='put', strike='11', bid='0', ask='0.05', mark='0.03', zero_bid='1', crossed='1', volume='0')]
    ps, st = C.quote_problems(rows, 'snap')
    got = checks(ps)
    for want in ('price_not_monotonic_in_strike', 'wide_quote', 'mark_outside_quote', 'iv_missing', 'zero_bid', 'crossed_quote', 'zero_volume_today'):
        assert want in got, (want, got)
    ps, st = C.quote_problems(rows[:1], 'snap'); assert ps == [] and st['n'] == 1


def test_timestamps_and_tz():
    ps = C.timestamp_problems(['2026-11-13 10:11', '2026-11-13', '2026-11-14 10:00', '2026-11-13 16:30'], 'x')
    assert checks(ps) == ['timestamp_on_non_session', 'timestamp_outside_regular_hours', 'timestamp_unparseable']
    assert C.timestamp_problems(['2026-11-13 09:30', '2026-11-13 16:00'], 'x') == []
    assert C.et_from_utc('2026-11-16T18:53:52.052124022Z').strftime('%Y-%m-%d %H:%M') == '2026-11-16 13:53'    # EST, UTC-5
    assert C.et_from_utc('2026-07-01T18:53:52Z').strftime('%H:%M') == '14:53'                                  # EDT, UTC-4


def test_events():
    s = C.nyse_sessions('2019-01-01', '2020-12-31')
    ev = pd.DataFrame({'date': ['2019-06-19'] + [f'2020-{m:02d}-15' for m in (1, 4, 6, 7, 8, 9, 12)], 'event': 'FOMC'})   # 2020-08-15 is a Saturday
    got = C.event_problems(ev, 'x', s)
    assert any(p['check'] == 'event_count_per_year' and '2020:7' in p['detail'] for p in got)
    assert any(p['check'] == 'event_on_non_session' for p in got)                


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_'): f(); print('ok', n)
