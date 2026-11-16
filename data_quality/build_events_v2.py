"""Build data_quality/events_v2.csv from backtests/credit_spreads/events.csv. The old file is left untouched.

Adds for each event: release_time_et, known_in_advance, verification and note. Adds rows the old file lacked.
Verification values:
  robinhood_2026-11-16        report date returned by Robinhood get_earnings_results (verified flag true)
  web_search_2026-11-16       found in a web search today (secondary pages quoting the Fed calendar, or bls.gov archive pages)
  web_search_2026-11-12       2026 CPI dates confirmed by a web search of the BLS schedule on 2026-11-12 (see prep_data.py)
  third_party_2026-11-16      listed by a third-party calendar only
  user_brief                  date given by the user in the 2026-11-12 brief
  memory_unverified           typed from memory, not checked against any source
federalreserve.gov, bls.gov and alfred.stlouisfed.org are blocked from this session, so no primary source was read.
Release times: CPI 08:30 ET (before the open), FOMC statement 14:00 ET, NVDA after the close (reaction = next session).
"""
import os, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
FOMC_WEB = set("""2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-03-18 2020-04-29 2020-06-10 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-09-16""".split())
CPI_WEB = set("2024-09-11 2024-11-13 2024-12-11 2025-01-15 2025-02-12 2025-10-24 2025-12-18 2026-01-13".split())
CPI_WEB_1112 = set("2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14".split())
CPI_THIRD = set("2026-10-14 2026-11-10".split())
NVDA_RH = set("2025-05-28 2025-08-27 2025-11-19 2026-02-25 2026-05-20 2026-08-26 2026-11-17".split())   # report dates
USER = {('FOMC', '2026-12-09'), ('CPI', '2026-12-10')}
ADD = [('2017-06-14', 'FOMC', 'SPY,QQQ', 'scheduled meeting missing from events.csv; before the first backtest trade'),
       ('2020-03-18', 'FOMC', 'SPY,QQQ', 'scheduled meeting missing from events.csv. It was on the calendar until the 2020-03-15 unscheduled action replaced it, '
                                         'so a filter using dates known at the time must include it'),
       ('2020-03-03', 'FOMC_unscheduled', 'SPY,QQQ', 'unscheduled rate cut; not knowable in advance, for analysis only, never for an entry filter'),
       ('2020-03-15', 'FOMC_unscheduled', 'SPY,QQQ', 'unscheduled rate cut on a Sunday; not knowable in advance, for analysis only')]


def main():
    e = pd.read_csv(os.path.join(HERE, '..', 'backtests', 'credit_spreads', 'events.csv'))[['date', 'event', 'applies_to']]
    e['note'] = ''
    e = pd.concat([e, pd.DataFrame(ADD, columns=['date', 'event', 'applies_to', 'note'])], ignore_index=True).sort_values(['date', 'event']).reset_index(drop=True)
    ver, tm, known = [], [], []
    for r in e.itertuples():
        if r.event == 'FOMC':
            v = 'user_brief' if (r.event, r.date) in USER else 'web_search_2026-11-16' if r.date in FOMC_WEB else 'memory_unverified'; t = '14:00'; k = 'yes'
        elif r.event == 'FOMC_unscheduled':
            v = 'memory_unverified'; t = ''; k = 'no'
        elif r.event == 'CPI':
            v = ('user_brief' if (r.event, r.date) in USER else 'web_search_2026-11-16' if r.date in CPI_WEB else 'web_search_2026-11-12' if r.date in CPI_WEB_1112
                 else 'third_party_2026-11-16' if r.date in CPI_THIRD else 'memory_unverified'); t = '08:30'
            k = 'rescheduled' if r.date in ('2025-10-24', '2025-12-18') else 'yes'
        else:   # NVDA_earnings_reaction: the row date is the session after the report
            rep = (pd.Timestamp(r.date) - pd.tseries.offsets.BDay(1)).strftime('%Y-%m-%d')
            v = 'robinhood_2026-11-16' if rep in NVDA_RH else 'memory_unverified'; t = 'report after the close of the prior session'; k = 'unknown'
        ver.append(v); tm.append(t); known.append(k)
    e['release_time_et'] = tm; e['known_in_advance'] = known; e['verification'] = ver
    e.loc[(e.event == 'CPI') & e.date.isin(['2025-10-24', '2025-12-18']), 'note'] = 'moved by the 2025 government shutdown; the October 2025 CPI release was cancelled'
    e.loc[(e.event == 'CPI') & (e.date == '2020-04-10'), 'note'] = 'released on Good Friday, market closed; first reaction session 2020-04-13'
    e.loc[e.event == 'NVDA_earnings_reaction', 'note'] = 'date the company announced each report date is not available, so known-at-the-time status cannot be checked'
    e[['date', 'event', 'applies_to', 'release_time_et', 'known_in_advance', 'verification', 'note']].to_csv(os.path.join(HERE, 'events_v2.csv'), index=False)
    print(e.groupby(['event', 'verification']).size().to_string())


if __name__ == '__main__':
    main()
