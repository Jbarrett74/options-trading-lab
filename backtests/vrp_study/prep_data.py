"""Build prices_spy_vix.csv for the VRP study test.

Usage: python3 prep_data.py SPY_recent.json SPY_old.json VIX_recent.json VIX_old.json
Inputs: FMP /stable/historical-price-eod/full output (symbols SPY and ^VIX), fetched 2026-11-23 in two
chunks because FMP returns at most 5,000 rows per call. Unadjusted prices.
The 2026-11-23 bar is dropped: it was fetched during the session and is incomplete.
"""
import json, sys, pandas as pd

LAST = '2026-11-20'

def load(*fs):
    d = pd.concat([pd.DataFrame(json.load(open(f))) for f in fs]).drop_duplicates('date')
    return d[d.date <= LAST].sort_values('date')

def main(s1, s2, v1, v2):
    s = load(s1, s2)[['date', 'open', 'high', 'low', 'close']]
    v = load(v1, v2)[['date', 'close']].rename(columns={'close': 'vix'})
    p = s.merge(v, on='date', how='left'); p['vix'] = p.vix.ffill()
    p.to_csv('prices_spy_vix.csv', index=False)
    print(p.date.min(), p.date.max(), len(p), 'missing vix:', int(p.vix.isna().sum()))

if __name__ == '__main__':
    main(*sys.argv[1:5])
