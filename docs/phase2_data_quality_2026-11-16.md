# Phase 2: data quality results (2026-11-16)

Run: `python3 data_quality/run_checks.py`. Checks: `quant/data_checks.py`. Tests: `quant/test_data_checks.py`.
Every problem is a row in `data_quality/problem_log.csv` (72 rows: 4 HIGH, 34 MED, 7 LOW, 27 INFO, where INFO means checked and clean or a fact recorded).
All figures are OBSERVED from the files and sources named unless marked otherwise.

## Sources read today
| Source | What | Pulled |
|---|---|---|
| Robinhood | daily bars, adjustment none, 26 symbols, 2017-06-01 to 2026-11-13, 61,828 rows | `data_quality/sources/rh_daily_raw_2026-11-16.csv.gz` |
| FMP | SPY dividends (136 rows), splits for SPY, NVDA, AAPL, MSFT, TSLA, index closes ^GSPC, ^RUT, ^DJI | `data_quality/sources/` |
| Robinhood | live quotes for the 174 snapshot contracts at 1:53pm ET | `paper_trading/snapshots/chain_2026-11-16_1353.csv` |
| Robinhood | NVDA report dates, last 8 quarters | in `events_v2.csv` |
| Web search | FOMC and CPI dates (secondary pages and bls.gov archive titles) | in `events_v2.csv` |

Blocked from this session: www.federalreserve.gov, alfred.stlouisfed.org, www.bls.gov, fred.stlouisfed.org. FMP refuses splits, dividends and prices for QQQ and every ETF except SPY, the economic calendar, and more than 5 earnings rows.

## Results by check
| Check | Result | Confidence |
|---|---|---|
| Time zones | Robinhood daily bars are stamped 00:00 UTC of the session date. FMP and Robinhood SPY closes agree on the same date for 98.2% of days and on a shifted date for 0.5%, so dates are aligned. Option quote times are UTC. `snapshot.py` named files with a fixed UTC-5 offset, wrong during daylight saving; fixed to America/New_York. | [Certain] |
| Missing observations | No missing NYSE session, no row on a closed day, no duplicate date in any of the 53 stored or fresh price series. FMP ^RUT has one row dated Saturday 2025-04-26 and one repeated bar. | [Certain] |
| OHLC sanity | No non-positive price, no high below low, no open or close outside the range. | [Certain] |
| Splits | 6 splits fall inside the ETF sample: SMH 2-for-1 2023-05-05, USO 1-for-8 2020-04-29, XLE, XLK, XLU 2-for-1 2025-12-05. Stocks: AAPL 4-for-1 2020-08-31, NVDA 4-for-1 2021-07-20 and 10-for-1 2024-06-10, TSLA 5-for-1 2020-08-31 and 3-for-1 2022-08-25. Stored prices are split-adjusted correctly. Consequence: before a split, the modeled $1 strike grid and dollar costs are not what traded (USO history is multiplied by 8, the others divided by 2). | [Certain] |
| Bad adjustment | SMH stored closes on 2019-12-11, 12 and 13 are 1.5% too low (ratio 2.030 instead of 2.000). | [Certain] on the mismatch, [Uncertain] on the cause |
| Dividends | Prices are not dividend-adjusted. SPY: 38 ex-dates, mean 0.39% of price each, about 1.57% a year. The option models use no dividend yield. No dividend data exists here for QQQ or the 20 ETFs, so ex-date drops and early assignment cannot be modeled for them. | [Certain] |
| Cross-source closes | SPY, FMP vs Robinhood: 43 of 2,376 closes differ by more than 1 cent. 41 are under $0.45. Two are large: 2022-09-22 (Robinhood 378.30, FMP 374.22) and 2024-02-13 (Robinhood 497.09, FMP 494.08). On both days the Robinhood close equals the day high and FMP agrees with the S&P 500 index. Robinhood is wrong on those two days. | [Certain] |
| Single-source risk | QQQ and 18 ETFs have Robinhood as the only source. At the SPY error rate (2 bad closes in 2,376) each series may hold a few bad closes that nothing here can detect. IWM vs ^RUT disagrees by 1% to 3% on 2020-03-17 to 03-20; which side is wrong is not known. DIA vs ^DJI is clean. | [Likely] |
| Stale and crossed quotes, zero bids | Live snapshot, 174 contracts: 0 missing, 0 stale (oldest quote 2.1 minutes), 0 crossed, 0 zero bids, 0 id mismatches, 0 marks outside the quote. 2 TLT deep in-the-money calls returned no IV or gamma. 18 contracts had no trade yet today. One snapshot only. | [Certain] for this snapshot |
| Quote width | Median bid-ask as a share of mid: QQQ 0.8%, SPY 1.0%, NVDA 1.5%, IWM 2.1%, TLT 3.1%, XLE 5.1%, XLU 9.2%, XLF 11.2%, EEM 18.0%. | [Certain] for this snapshot |
| Cost model vs quotes | For 0.05 to 0.35 delta contracts the backtest half-spread is at or above the observed one for SPY, QQQ, IWM, NVDA, TLT, XLE, XLU (ratio 0.38 to 0.75) and close for XLF (1.25). EEM is 4.1 times wider than modeled ($0.083 vs $0.020 per leg). That is about $12.60 more per two-leg entry than the scan charged, against a modeled EEM edge of $8.13 per trade. | [Likely] the EEM scan result does not survive observed quotes |
| Option history | `real_option_sample.csv`: 1,180 of 1,802 daily bars are interpolated (no trade). 666 bars are dated after expiry, all interpolated, all dropped before use. No bid, ask, volume, open interest or IV history exists from any reachable source. | [Certain] |
| Survivorship | The 20 ETFs and 5 stocks were picked in November 2026 from names alive and liquid today. Every ETF has the full 2,376 rows. Single-ticker results are not affected. Any statement across the universe, and the long-call test on AAPL, NVDA, MSFT and TSLA, carries hindsight in the choice of names. | [Certain] |
| Ledger timestamps | `ledger_v2.csv`: 1 of 18 rows has a date with no time (C-XLE-20261113-1 open). All 18 rows lack a quote timestamp because they were backfilled from `log.csv`, which stores dates only. | [Certain] |
| Event dates | See next section. | |

## Event list: release times and what is verified
`data_quality/events_v2.csv` (built by `build_events_v2.py`; the old `events.csv` is unchanged) adds release time, whether the date was known in advance, and where each date was checked.

| Event | Rows | Checked against a source | From memory or third party |
|---|---|---|---|
| FOMC scheduled | 77 | 68 (67 web search today, 1 from your brief) | 9 |
| FOMC unscheduled (2020-03-03, 2020-03-15) | 2 | 0 | 2 |
| CPI | 113 | 15 (8 web search today, 6 web search 11/12, 1 from your brief) | 98 |
| NVDA earnings | 38 | 7 (Robinhood) | 31 |

Findings:
1. The old list had no FOMC date in March 2020. The scheduled 2020-03-18 meeting was on the calendar until an unscheduled action replaced it, so a filter using dates known at the time must include it. Effect on the credit backtest, measured: 5 entry days (2020-03-12 to 03-18), all in-sample, 3 trades per configuration. For the SPY 0.15 delta put spread the in-sample mean moves from $2.98 to $2.96. Out-of-sample verdicts are unaffected.
2. The old list also lacked 2017-06-14, which is before the first backtest trade.
3. No date found by search contradicted the list. One secondary page gave 2017 dates one day later than the Fed's tentative calendar quoted by another.
4. Timing convention: CPI comes out at 8:30am ET and NVDA reports after the close, so a trade entered at the open of the CPI day or the NVDA reaction day is entered after the news. The filter still blocks those entries. That is conservative, not look-ahead.
5. Known at the time: FOMC and CPI dates are published well ahead (the two shutdown-moved CPI dates in late 2025 are marked rescheduled). The date NVDA announced each report date is not available, so that part of the requirement cannot be met.
6. 139 of 230 dates still rest on memory or a third-party calendar. One fetch each of the Fed calendar pages and the ALFRED CPI release-date file would settle FOMC and CPI. Both hosts are blocked.

## Unresolved
- SPY on 2026-06-26 closed 0.68% below the S&P 500 index move in both sources and recovered the next day. Cause not known.
- IWM vs ^RUT in March 2020 (above).
- SMH adjusted-close anomaly cause.
- Quote quality rests on one snapshot. The daily snapshot is not running because the paper desk prompt changes (sections A, B, C) are not applied.

## What changes because of this
- SPY results stand on FMP data that agree with the index. QQQ and ETF results rest on a single source with a measured error rate in its sibling series.
- The ETF scan's three modeled passes: XLE and XLU costs look adequate on today's quotes, EEM's do not.
- Phase 4 must price strikes on unadjusted prices around splits, add dividends for any multi-week holding test, and use `events_v2.csv`.
