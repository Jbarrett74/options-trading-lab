# Phase 0 audit, 2026-11-15 (Sunday, about 4:35pm to 5:00pm ET)

Labels: OBSERVED = read from the broker, a data API, git or a file today. ESTIMATED = derived with a stated assumption. Nothing here is MODELED.
Markets were closed. Broker quotes are from the Friday 2026-11-13 close.

## 1. Limit check (real account ending 8530)

| Position | Max loss | Limit | Status |
|---|---|---|---|
| NVDA 170/172 call debit spread, Dec 18, 1 contract, debit 0.80 | $80.00 OBSERVED debit, $80.08 with ESTIMATED $0.08 fees | $45 per trade | BREACH by about $35 |
| SPY 760/759 put debit spread, Nov 20, 1 contract, debit 0.37 | $37.08 OBSERVED (ledger includes fees) | $45 per trade | within |
| Working option orders (confirmed or queued) | none OBSERVED 4:35pm ET | | no closing orders working |
| Combined open risk | $117.16 ESTIMATED ($117.08 without the NVDA fee) | $125 | within, headroom $7.84 |

Account value $458.45, cash $318.45 (OBSERVED, option marks from Friday). $45 is 9.8% of the account, $125 is 27.3%, the NVDA spread is 17.5%.

## 2. Scheduled tasks (list_triggers, OBSERVED)

Trading tasks. All but the first fire into the paper desk session; the first fires into the research session.

| Task | Schedule (ET) | Next run | Order instructions in prompt | Notes |
|---|---|---|---|---|
| Re-price TLT and XLF (read-only) | once, Mon 11/16 9:47am | 11/16 | none after today's edit | Was "place TLT if in cap". Changed to read-only on 2026-11-15 under the execution protocol. |
| Paper test premarket briefing | 7:53am daily 11/12 to 11/24 | 11/16 | none ("never place") | Cron includes weekends; prints a skip line. |
| SPY paper spread morning | 10:07am weekdays, Nov and Dec | 11/16 | none | Self-skips after 12/04. Ran twice on 11/13 (partial then full). |
| SPY 760/759 put spread stop check | 10:47am, 12:47pm, 3:47pm, 11/12 to 11/20 | 11/16 | none ("READ ONLY") | Cron includes weekends: six skip lines per weekend. |
| SPY paper spread close mark | 3:37pm weekdays, Nov and Dec | 11/16 | none | Self-skips after 12/04. |
| Paper test directional arm review | once, 11/24 4:23pm | 11/24 | none | |
| Paper test final review | once, 12/04 4:31pm | 12/04 | none | Deletes the three paper tasks. |
| Close NVDA Dec 170/172 call spread | once, 12/17 11:47am | 12/17 | YES: review then place a closing order after a yes | Conflicts with the execution protocol. Not changed yet. |
| Daily options trade proposal | 12:41pm weekdays, DISABLED | none | YES: place after a yes; cap $50 | Disabled since 11/11. Conflicts with the protocol and the $45 cap. Not changed yet. |

Non-trading tasks (no Robinhood connector listed, so no order capability): Daily morning briefing 8:00am, Daily market build 7:40am weekdays, Week-ahead academics Sun 5:46pm, Recruiting pipeline digest Sun and Wed 7:48pm. "Daily market build" overlaps the premarket briefing in content (overnight market scan) but is a separate personal product.

Session cron jobs (CronList): none.

Findings
- Order permission cannot be confirmed as absent. Tasks bound to a session inherit that session's tools, and the Robinhood connector exposes order tools there. The only barrier is the prompt text. The broker-side control is the trade approval setting, which was OFF when read today (updated 2026-11-12). Turning it ON in the Robinhood app makes every agent order wait for approval in the app.
- Duplicates and overlaps: on a weekday seven trading runs fire (7:53, 9:47 once, 10:07, 10:47, 12:47, 3:37, 3:47). The 3:37 close mark and the 3:47 SPY check are ten minutes apart in the same session.
- Weekend runs produced no commits on 11/14 or 11/15 (git log), so the skips are chat lines only.
- Holidays: Thanksgiving 11/26 (closed) and the 11/27 1:00pm early close rely on the prompt's "skip on US market holidays". The 3:37pm close mark on 11/27 runs after the market has closed.
- automation/scheduled_tasks.md is stale: dated 11/12, quotes a $50 cap, lists the credit arm under the close mark, and omits the SPY real-position check.
- The paper tasks commit to main. STATUS.md is edited on both main and claude/nifty-bohr-bj24xh. Main was merged into the branch today.

## 3. Ledger (paper_trading/log.csv, 41 rows, OBSERVED)

- Actions: 11 open, 3 close, 17 mark, 7 skip, 3 no_trade. No exact duplicate rows.
- 2026-11-11 has two SPY no_trade rows (two runs). 2026-11-13 has two sets of credit-arm marks (morning run and close run), and the morning ran twice.
- Closed trades: 3, all directional (IWM -$78.08, SPY +$49.84, QQQ +$45.84). Credit arm closed trades: 0.
- No run id, timestamp column, trade id or arm column. Price and P&L are free text ("mid 0.63; conservative exit 0.5992"), so totals cannot be computed without parsing prose.
- Paper limits differ from the real limits: $150 per spread and $450 open (directional), $95 (credit arm), $274 to $466 (width test).
- Open directional paper spreads: SPY, QQQ and IWM bear put spreads expiring 11/17, entered the same minute. One market bet, $263.24 at risk.
- paper_trading/real_trades.csv: 1 row (the SPY spread). The NVDA spread is not in it.

## 4. Data sources (tested today)

| Source | What works | History | What does not | Cost and licence |
|---|---|---|---|---|
| Robinhood MCP, equities | Daily OHLCV, quotes with timestamps, technical indicators | Daily: SPY bars returned for 2005, 2013 and 2017 onward. 5-minute: real bars on 2026-08-17 and 2026-11-02. | Hourly and 5-minute requests for 2025-11 and earlier return bars flagged interpolated, filled with the CURRENT price and zero volume. Yearly interval returned nothing. Exact intraday retention not measured (between 3 and 12 months). | No extra cost OBSERVED. Licence terms not read. |
| Robinhood MCP, options live | Chain, bid, ask, sizes, IV, greeks, open interest, volume, per-quote timestamp | Live only | Deep in-the-money puts often lack gamma (known issue in STATUS.md) | as above |
| Robinhood MCP, options history | Daily OHLC price bars per contract, including expired contracts | Expired SPY contracts found for Jan 2019, Jan 2022, Jan 2025, Oct 2026 expiries; real bars from 2018-06 for the Jan 2019 put | NO bid, ask, volume, open interest or IV in history. 35% to 86% of bars interpolated on the old SPY contracts. Bars continue after expiry on one contract (to 2020-08 for a Jan 2019 expiry). An expired contract's quote returns zeros and null greeks. | as above |
| FMP (proxy key) | Daily OHLCV for SPY, NVDA, AAPL, ^VIX, ^GSPC; quote; earnings (limit 5); earnings calendar; dividends; treasury rates; dividend-adjusted prices | SPY capped at 5,000 rows, from 2006-12-29 | QQQ, IWM, TLT, XLF, XLE, XLU, EEM blocked. Intraday, economic calendar, splits for blocked symbols, v3/v4 legacy option endpoints blocked. Option chain endpoint returns an empty list. | Plan restrictions OBSERVED; plan name, cost and redistribution terms not read. |
| Web search | News, calendars | n/a | Not a data feed. Several searches returned other years' pages. | n/a |
| Other hosts | none | | cdn.cboe.com, cboe.com, polygon.io, tradier (live and sandbox), alphavantage, Yahoo, stooq, Nasdaq Data Link, marketdata.app, eodhd, ORATS, optionsdx, FRED, sec.gov all refused by the session network policy (403) | Would need the host allowed in the environment and, for most, a paid key. Not priced. |

Historical option chains with bid, ask, volume, open interest and implied volatility: NOT AVAILABLE for any of SPY, QQQ, IWM, TLT, XLF, NVDA, XLE, XLU, EEM from any source this session can reach. Per-contract daily OHLC exists on Robinhood for all nine (tested on the 2026-10-16 expiry: real bars for 44 to 197 of 199 days depending on the contract).

Forward snapshots already in the repo: paper_trading/gex/ (SPY, QQQ, IWM; strikes within 2% of spot; nearest two expiries; gamma, open interest, bid, ask, IV, quote time; 11/11 to 11/13; no volume) and paper_trading/credit_arm/ (one file, 11/12).

Local price files: backtests/credit_spreads/prices_daily.csv (SPY from FMP, QQQ from Robinhood, 2017-06 to 2026-11-11) and prices_multi.csv (20 ETFs from Robinhood, same span). Not yet checked for splits or dividends. FMP's SPY close for 11/13 is 754.37; Robinhood's last regular trade is 754.25.

## 5. Consequences

- Option strategy backtests filled at historical bid and ask cannot be run with the data available. Options work is limited to forward daily chain snapshots and analysis labeled MODELED.
- Robinhood per-contract daily OHLC is real traded-price history but has no bid/ask and legs close at different times, so a $1-wide spread priced from two leg closes carries error larger than the spread's own value. It can support single-leg sanity checks, not spread fills.
- Underlying-price hypotheses (reversal after a 1% to 2% drop, momentum, mean reversion, realized-volatility regimes, earnings-day moves) can be tested on daily bars now. Gamma exposure cannot: it needs historical open interest and gamma by strike, and only three days of snapshots exist.
