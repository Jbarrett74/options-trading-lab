"""Structured paper ledger (ledger_v2.csv). log.csv is left untouched and stays the prose record.

One row per event. Fill prices are paper fills at OBSERVED quotes: price_worst is the worst side of the
spread (pay the ask on bought legs, receive the bid on sold legs), price_mid is the mid. Both are per share
and positive; `side` says whether the spread was a debit or a credit. Dollar fields are per position.

  python3 paper_trading/ledger.py add --json '{"run_id": "2026-11-16_1007_morning", ...}'
  python3 paper_trading/ledger.py summary
  python3 paper_trading/ledger.py check

A row is rejected if the same (run_id, trade_id, action) is already in the file, so a run that fires twice
logs once. Limits: max_loss_usd above REAL_MAX_LOSS sets over_real_limit=1. The width_test arm is reported
separately and never enters totals.
"""
import argparse, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.environ.get('LEDGER_V2', os.path.join(HERE, 'ledger_v2.csv'))
REAL_MAX_LOSS, REAL_MAX_OPEN = 45.0, 125.0
FIELDS = ['run_id', 'ts_et', 'trade_id', 'arm', 'ticker', 'action', 'structure', 'side', 'expiry', 'legs', 'qty',
          'price_worst', 'price_mid', 'fees_usd', 'max_loss_usd', 'max_gain_usd', 'pnl_worst_usd', 'pnl_mid_usd',
          'underlying_px', 'quote_ts_utc', 'rule_set', 'over_real_limit', 'notes', 'source']
ARMS = {'directional', 'credit', 'width_test', 'real'}
ACTIONS = {'open', 'mark', 'close', 'settle', 'skip', 'no_trade'}
REQUIRED = {'open': ['trade_id', 'structure', 'side', 'expiry', 'legs', 'price_worst', 'max_loss_usd'],
            'close': ['trade_id', 'price_worst', 'pnl_worst_usd'], 'settle': ['trade_id', 'pnl_worst_usd'],
            'mark': ['trade_id', 'price_worst'], 'skip': ['notes'], 'no_trade': ['notes']}


def read(path=None):
    path = path or PATH
    if not os.path.exists(path): return []
    with open(path, newline='') as f: return list(csv.DictReader(f))

def validate(row):
    errs = []
    for k in ('run_id', 'ts_et', 'arm', 'ticker', 'action'):
        if not str(row.get(k, '')).strip(): errs.append(f'missing {k}')
    if row.get('arm') not in ARMS: errs.append(f"arm must be one of {sorted(ARMS)}")
    if row.get('action') not in ACTIONS: errs.append(f"action must be one of {sorted(ACTIONS)}")
    for k in REQUIRED.get(row.get('action'), []):
        if str(row.get(k, '')).strip() == '': errs.append(f"{row.get('action')} needs {k}")
    if row.get('side') not in ('', None, 'debit', 'credit'): errs.append('side must be debit or credit')
    for k in ('price_worst', 'price_mid', 'fees_usd', 'max_loss_usd', 'max_gain_usd', 'pnl_worst_usd', 'pnl_mid_usd', 'underlying_px'):
        v = row.get(k, '')
        if v not in ('', None):
            try: float(v)
            except ValueError: errs.append(f'{k} is not a number: {v!r}')
    unknown = set(row) - set(FIELDS)
    if unknown: errs.append(f'unknown fields {sorted(unknown)}')
    return errs

def add(row, path=None):
    path = path or PATH
    row = {k: ('' if v is None else v) for k, v in row.items()}
    errs = validate(row)
    if errs: raise ValueError('; '.join(errs))
    rows = read(path)
    key = (row['run_id'], row.get('trade_id', ''), row['action'])
    if row['action'] in ('skip', 'no_trade'): key += (row.get('structure', ''), row['ticker'])
    for r in rows:
        k2 = (r['run_id'], r['trade_id'], r['action'])
        if r['action'] in ('skip', 'no_trade'): k2 += (r['structure'], r['ticker'])
        if k2 == key: return False                      # already logged by this run
    ml = row.get('max_loss_usd', '')
    row['over_real_limit'] = '' if ml == '' else int(float(ml) > REAL_MAX_LOSS + 1e-9)
    new = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow({k: row.get(k, '') for k in FIELDS})
    return True

def summary(path=None):
    rows = read(path); out = {}
    opens = {r['trade_id']: r for r in rows if r['action'] == 'open'}
    for arm in sorted(ARMS):
        closed = [r for r in rows if r['arm'] == arm and r['action'] in ('close', 'settle')]
        closed_ids = {r['trade_id'] for r in closed}
        open_now = [o for t, o in opens.items() if o['arm'] == arm and t not in closed_ids]
        pw = [float(r['pnl_worst_usd']) for r in closed]
        pm = [float(r['pnl_mid_usd']) for r in closed if r['pnl_mid_usd'] != '']
        risk = [float(opens[r['trade_id']]['max_loss_usd']) for r in closed if r['trade_id'] in opens]
        out[arm] = {'closed': len(closed), 'open': len(open_now), 'wins_worst': sum(p > 0 for p in pw),
                    'pnl_worst_usd': round(sum(pw), 2), 'pnl_mid_usd': round(sum(pm), 2) if len(pm) == len(pw) and pw else None,
                    'pnl_worst_per_100_risk': round(100 * sum(pw) / sum(risk), 2) if risk and len(risk) == len(pw) else None,
                    'open_max_loss_usd': round(sum(float(o['max_loss_usd']) for o in open_now), 2),
                    'open_over_real_limit': sum(o['over_real_limit'] == '1' for o in open_now)}
    core = [a for a in ('directional', 'credit') if a in out]
    out['TOTAL_excluding_width_test_and_real'] = {'closed': sum(out[a]['closed'] for a in core),
                                                  'pnl_worst_usd': round(sum(out[a]['pnl_worst_usd'] for a in core), 2)}
    out['note'] = 'No conclusion below 100 closed trades per strategy. width_test and real are never in the total.'
    return out

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add'); a.add_argument('--json', required=True)
    sub.add_parser('summary'); sub.add_parser('check')
    args = ap.parse_args()
    if args.cmd == 'add':
        rows = json.loads(args.json); rows = rows if isinstance(rows, list) else [rows]
        for r in rows:
            try: print('added' if add(r) else 'duplicate, skipped', r.get('trade_id', ''), r.get('action'))
            except ValueError as e: print('REJECTED', r.get('trade_id', ''), r.get('action'), '-', e); sys.exit(1)
    elif args.cmd == 'summary': print(json.dumps(summary(), indent=1))
    else:
        bad = [(i + 2, validate({k: v for k, v in r.items() if k != 'over_real_limit' or True})) for i, r in enumerate(read())]
        bad = [b for b in bad if b[1]]; print('rows', len(read()), 'invalid', len(bad)); [print(b) for b in bad]; sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
