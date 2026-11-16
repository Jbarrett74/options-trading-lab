"""Daily option chain snapshot for forward data collection (no historical bid/ask source exists).

Contracts are fixed in snapshots/contracts.csv (ticker, expiry, type, strike, instrument_id): two monthly
expiries, five strikes per ticker, puts and calls. The run makes ONE get_option_quotes call with every id
(the output is large, so the harness saves it to a file) and passes that file here. Nothing is retyped.

  python3 paper_trading/snapshot.py ids                       # JSON list of live instrument ids to quote
  python3 paper_trading/snapshot.py ingest QUOTES.json --spots SPY=754.25,QQQ=679.9 --run-id 2026-11-16_1537_close
  python3 paper_trading/snapshot.py verify QUOTES.json        # check ids against strikes without writing

Output: snapshots/chain_<YYYY-MM-DD>_<HHMM>.csv, one row per contract, every value OBSERVED from the quote.
Flags: stale (quote older than 20 minutes at ingest), crossed (bid > ask), zero_bid, missing (id not returned),
id_mismatch (break-even price disagrees with strike +/- mark, so the id may not be the contract listed).
"""
import argparse, csv, datetime as dt, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get('SNAPSHOT_DIR', os.path.join(HERE, 'snapshots'))
CONTRACTS = os.path.join(DIR, 'contracts.csv')
OUT_FIELDS = ['snapshot_ts_utc', 'run_id', 'ticker', 'expiry', 'type', 'strike', 'spot', 'bid', 'ask', 'bid_size', 'ask_size', 'mark',
              'iv', 'delta', 'gamma', 'theta', 'vega', 'open_interest', 'volume', 'quote_updated_at', 'quote_age_min',
              'stale', 'crossed', 'zero_bid', 'missing', 'id_mismatch', 'instrument_id']
STALE_MIN = 20.0


def contracts(today=None):
    today = today or dt.date.today().isoformat()
    with open(CONTRACTS, newline='') as f:
        return [r for r in csv.DictReader(f) if r['expiry'] >= today]

def load_quotes(path):
    d = json.load(open(path)); res = d.get('data', d).get('results', [])
    return {r['quote']['instrument_id']: r['quote'] for r in res if r.get('quote')}

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def parse_ts(s):
    if not s or s.startswith('0001'): return None
    s = s.replace('Z', '+00:00')
    if '.' in s:                                   # trim nanoseconds to microseconds
        head, rest = s.split('.', 1); n = 0
        while n < len(rest) and rest[n].isdigit(): n += 1
        frac, tz = rest[:n], rest[n:]
        s = f'{head}.{frac[:6]}{tz}'
    return dt.datetime.fromisoformat(s)

def build_rows(quotes, spots, run_id='', now=None, today=None):
    now = now or dt.datetime.now(dt.timezone.utc); rows = []
    for c in contracts(today):
        q = quotes.get(c['instrument_id']); k = float(c['strike'])
        row = {f: '' for f in OUT_FIELDS}
        row.update(snapshot_ts_utc=now.strftime('%Y-%m-%dT%H:%M:%SZ'), run_id=run_id, ticker=c['ticker'], expiry=c['expiry'], type=c['type'],
                   strike=c['strike'], spot=spots.get(c['ticker'], ''), instrument_id=c['instrument_id'], missing=int(q is None))
        if q is not None:
            bid, ask, mark = num(q.get('bid_price')), num(q.get('ask_price')), num(q.get('mark_price'))
            ts = parse_ts(q.get('updated_at')); age = (now - ts).total_seconds() / 60 if ts else None
            be = num(q.get('break_even_price')); exp_be = None if mark is None else (k + mark if c['type'] == 'call' else k - mark)
            row.update(bid=q.get('bid_price'), ask=q.get('ask_price'), bid_size=q.get('bid_size'), ask_size=q.get('ask_size'), mark=q.get('mark_price'),
                       iv=q.get('implied_volatility') or '', delta=q.get('delta') or '', gamma=q.get('gamma') or '', theta=q.get('theta') or '',
                       vega=q.get('vega') or '', open_interest=q.get('open_interest'), volume=q.get('volume'), quote_updated_at=q.get('updated_at'),
                       quote_age_min='' if age is None else round(age, 1), stale=int(age is None or age > STALE_MIN),
                       crossed=int(bid is not None and ask is not None and bid > ask), zero_bid=int(not bid),
                       id_mismatch=int(be is not None and exp_be is not None and abs(be - exp_be) > 0.06))
        rows.append(row)
    return rows

def report(rows):
    n = len(rows); tot = lambda k: sum(int(r[k] or 0) for r in rows)
    by = {}
    for r in rows: by.setdefault(r['ticker'], []).append(r)
    print(f"contracts {n} missing {tot('missing')} stale {tot('stale')} crossed {tot('crossed')} zero_bid {tot('zero_bid')} id_mismatch {tot('id_mismatch')}")
    for t, rs in sorted(by.items()):
        print(f"  {t}: {len(rs)} rows, missing {sum(int(r['missing']) for r in rs)}, stale {sum(int(r['stale'] or 0) for r in rs)}, id_mismatch {sum(int(r['id_mismatch'] or 0) for r in rs)}, spot {rs[0]['spot'] or 'not given'}")

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('ids')
    for name in ('ingest', 'verify'):
        p = sub.add_parser(name); p.add_argument('quotes'); p.add_argument('--spots', default=''); p.add_argument('--run-id', default='')
    a = ap.parse_args()
    if a.cmd == 'ids':
        print(json.dumps([c['instrument_id'] for c in contracts()])); return
    spots = dict(kv.split('=') for kv in a.spots.split(',') if '=' in kv)
    now = dt.datetime.now(dt.timezone.utc); rows = build_rows(load_quotes(a.quotes), spots, a.run_id, now); report(rows)
    if a.cmd == 'ingest':
        et = now.astimezone(dt.timezone(dt.timedelta(hours=-5)))        # EST; the file name is a label, timestamps inside are UTC
        out = os.path.join(DIR, f"chain_{et.strftime('%Y-%m-%d_%H%M')}.csv")
        with open(out, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=OUT_FIELDS); w.writeheader(); w.writerows(rows)
        print('wrote', out)

if __name__ == '__main__':
    main()
