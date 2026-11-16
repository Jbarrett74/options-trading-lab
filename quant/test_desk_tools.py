"""Tests for paper_trading/ledger.py and snapshot.py. Run: python3 quant/test_desk_tools.py (or pytest)."""
import csv, datetime as dt, json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'paper_trading'))
import ledger, snapshot

def _open(tid='D-SPY-1', ml=88.08, arm='directional', run='r1'):
    return dict(run_id=run, ts_et='2026-11-16 10:07', trade_id=tid, arm=arm, ticker='SPY', action='open', structure='bear put debit spread 750/748',
                side='debit', expiry='2026-11-20', legs='buy 750P / sell 748P', qty=1, price_worst=0.88, price_mid=0.85, fees_usd=0.08, max_loss_usd=ml, max_gain_usd=111.92)

def test_ledger_add_dedupe_and_limit_flag():
    p = os.path.join(tempfile.mkdtemp(), 'l.csv')
    assert ledger.add(_open(), p) is True
    assert ledger.add(_open(), p) is False                      # same run, trade and action: logged once
    assert ledger.add(_open(tid='C-SPY-1', ml=44.0, arm='credit'), p) is True
    rows = ledger.read(p); assert len(rows) == 2
    assert rows[0]['over_real_limit'] == '1' and rows[1]['over_real_limit'] == '0'

def test_ledger_rejects_bad_rows():
    p = os.path.join(tempfile.mkdtemp(), 'l.csv')
    for bad in (dict(_open(), arm='misc'), dict(_open(), price_worst='about 0.9'), {k: v for k, v in _open().items() if k != 'max_loss_usd'}, dict(_open(), extra=1)):
        try: ledger.add(bad, p); raise AssertionError('accepted a bad row')
        except ValueError: pass

def test_ledger_summary_excludes_width_test():
    p = os.path.join(tempfile.mkdtemp(), 'l.csv')
    ledger.add(_open(), p); ledger.add(_open(tid='W-1', ml=456.08, arm='width_test'), p)
    for tid, arm, pnl in (('D-SPY-1', 'directional', 49.84), ('W-1', 'width_test', -300.0)):
        ledger.add(dict(run_id='r2', ts_et='2026-11-17 10:07', trade_id=tid, arm=arm, ticker='SPY', action='close', price_worst=1.38, pnl_worst_usd=pnl), p)
    s = ledger.summary(p)
    assert s['directional']['pnl_worst_usd'] == 49.84 and s['width_test']['pnl_worst_usd'] == -300.0
    assert s['TOTAL_excluding_width_test_and_real'] == {'closed': 1, 'pnl_worst_usd': 49.84}
    assert s['directional']['pnl_worst_per_100_risk'] == round(100 * 49.84 / 88.08, 2)

def test_snapshot_flags():
    d = tempfile.mkdtemp(); snapshot.DIR = d; snapshot.CONTRACTS = os.path.join(d, 'contracts.csv')
    with open(snapshot.CONTRACTS, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['ticker', 'expiry', 'type', 'strike', 'instrument_id'])
        w.writerows([['SPY', '2026-12-18', 'put', '725', 'a'], ['SPY', '2026-12-18', 'call', '785', 'b'], ['SPY', '2026-12-18', 'put', '700', 'c'],
                     ['SPY', '2026-12-18', 'call', '810', 'd'], ['SPY', '2026-11-13', 'put', '700', 'old']])
    now = dt.datetime(2026, 11, 16, 20, 40, tzinfo=dt.timezone.utc)
    q = lambda bid, ask, mark, be, ts: dict(bid_price=bid, ask_price=ask, mark_price=mark, break_even_price=be, updated_at=ts, implied_volatility='0.17',
                                            open_interest=10, volume=3, bid_size=1, ask_size=1)
    quotes = {'a': q('5.00', '5.10', '5.05', '719.95', '2026-11-16T20:39:10.123456789Z'),      # clean put
              'b': q('2.10', '2.00', '2.05', '787.05', '2026-11-16T19:00:00Z'),                # crossed and stale
              'c': q('0.00', '0.05', '0.03', '650.00', '2026-11-16T20:39:00Z')}                # zero bid, break-even says another strike
    rows = {r['instrument_id']: r for r in snapshot.build_rows(quotes, {'SPY': '754.25'}, 'run', now, today='2026-11-16')}
    assert set(rows) == {'a', 'b', 'c', 'd'}                                                     # expired contract dropped
    a, b, c, dd = rows['a'], rows['b'], rows['c'], rows['d']
    assert (a['stale'], a['crossed'], a['zero_bid'], a['id_mismatch'], a['missing']) == (0, 0, 0, 0, 0) and a['spot'] == '754.25'
    assert b['crossed'] == 1 and b['stale'] == 1 and b['id_mismatch'] == 0
    assert c['zero_bid'] == 1 and c['id_mismatch'] == 1
    assert dd['missing'] == 1 and dd['bid'] == ''

if __name__ == '__main__':
    for n, f in sorted(globals().items()):
        if n.startswith('test_'): f(); print('ok', n)
