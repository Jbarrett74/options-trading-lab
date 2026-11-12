"""Build prices_daily.csv and events.csv for the credit spread backtest.

Usage: python3 prep_data.py SPY.json VIX.json QQQ.json
  SPY.json, VIX.json: FMP /stable/historical-price-eod/full output (symbol SPY and ^VIX).
  QQQ.json: Robinhood get_equity_historicals output (day bars, unadjusted). FMP refused QQQ on this plan.
Event dates: FOMC decision days (scheduled meetings only) and CPI release days are typed in from memory because
the FMP economic calendar and bls.gov / federalreserve.gov were not reachable from the session. 2026 CPI dates
for Jan-Jul, Nov, Dec were confirmed by a web search of the BLS schedule; Aug, Sep, Oct 2026 are unverified guesses.
NVDA earnings: 2025-05 onward from Robinhood, earlier from memory. All NVDA reports are after the close, so the
event day used by the filter is the next weekday.
"""
import json, sys, pandas as pd

FOMC = """2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09""".split()
CPI = """2017-07-14 2017-08-11 2017-09-14 2017-10-13 2017-11-15 2017-12-13
2018-01-12 2018-02-14 2018-03-13 2018-04-11 2018-05-10 2018-06-12 2018-07-12 2018-08-10 2018-09-13 2018-10-11 2018-11-14 2018-12-12
2019-01-11 2019-02-13 2019-03-12 2019-04-10 2019-05-10 2019-06-12 2019-07-11 2019-08-13 2019-09-12 2019-10-10 2019-11-13 2019-12-11
2020-01-14 2020-02-13 2020-03-11 2020-04-10 2020-05-12 2020-06-10 2020-07-14 2020-08-12 2020-09-11 2020-10-13 2020-11-12 2020-12-10
2021-01-13 2021-02-10 2021-03-10 2021-04-13 2021-05-12 2021-06-10 2021-07-13 2021-08-11 2021-09-14 2021-10-13 2021-11-10 2021-12-10
2022-01-12 2022-02-10 2022-03-10 2022-04-12 2022-05-11 2022-06-10 2022-07-13 2022-08-10 2022-09-13 2022-10-13 2022-11-10 2022-12-13
2023-01-12 2023-02-14 2023-03-14 2023-04-12 2023-05-10 2023-06-13 2023-07-12 2023-08-10 2023-09-13 2023-10-12 2023-11-14 2023-12-12
2024-01-11 2024-02-13 2024-03-12 2024-04-10 2024-05-15 2024-06-12 2024-07-11 2024-08-14 2024-09-11 2024-10-10 2024-11-13 2024-12-11
2025-01-15 2025-02-12 2025-03-12 2025-04-10 2025-05-13 2025-06-11 2025-07-15 2025-08-12 2025-09-11 2025-10-24 2025-12-18
2026-01-13 2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14 2026-08-12 2026-09-11 2026-10-14 2026-11-10 2026-12-10""".split()
NVDA = """2017-08-10 2017-11-09 2018-02-08 2018-05-10 2018-08-16 2018-11-15 2019-02-14 2019-05-16 2019-08-15 2019-11-14
2020-02-13 2020-05-21 2020-08-19 2020-11-18 2021-02-24 2021-05-26 2021-08-18 2021-11-17 2022-02-16 2022-05-25 2022-08-24 2022-11-16
2023-02-22 2023-05-24 2023-08-23 2023-11-21 2024-02-21 2024-05-22 2024-08-28 2024-11-20 2025-02-26
2025-05-28 2025-08-27 2025-11-19 2026-02-25 2026-05-20 2026-08-26 2026-11-17""".split()
UNVERIFIED = {'2026-08-12', '2026-09-11', '2026-10-14'}

def main(spy, vix, qqq):
    s = pd.DataFrame(json.load(open(spy)))[['date', 'open', 'high', 'low', 'close']]; s['symbol'] = 'SPY'
    q = pd.DataFrame(json.load(open(qqq))['data']['results'][0]['bars'])
    q = pd.DataFrame({'date': q.begins_at.str[:10], 'open': q.open_price.astype(float), 'high': q.high_price.astype(float),
                      'low': q.low_price.astype(float), 'close': q.close_price.astype(float), 'symbol': 'QQQ'})
    v = pd.DataFrame(json.load(open(vix)))[['date', 'close']].rename(columns={'close': 'vix'})
    p = pd.concat([s, q]).merge(v, on='date', how='left').sort_values(['symbol', 'date'])
    p['vix'] = p.groupby('symbol').vix.ffill()
    p[['symbol', 'date', 'open', 'high', 'low', 'close', 'vix']].to_csv('prices_daily.csv', index=False)
    ev = [(d, 'FOMC', 'SPY,QQQ') for d in FOMC] + [(d, 'CPI', 'SPY,QQQ') for d in CPI]
    for d in NVDA:
        nd = pd.Timestamp(d) + pd.tseries.offsets.BDay(1)
        ev.append((nd.strftime('%Y-%m-%d'), 'NVDA_earnings_reaction', 'QQQ'))
    e = pd.DataFrame(ev, columns=['date', 'event', 'applies_to']).sort_values('date')
    e['verified'] = ~e.date.isin(UNVERIFIED)
    e.to_csv('events.csv', index=False); print(p.groupby('symbol').date.agg(['min', 'max', 'count'])); print(len(e))

if __name__ == '__main__':
    main(*sys.argv[1:4])
