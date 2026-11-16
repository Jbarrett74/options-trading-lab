# Paper desk prompt changes approved by the user on 2026-11-15

A routine's prompt can only be edited from the conversation it posts into, so these must be applied from the
paper desk conversation. Append each block verbatim to the END of the named routine's existing prompt. Change
nothing else in the prompts.

## A. Append to "SPY paper spread - morning"

ADDED 2026-11-15 (approved by the user in the research session):
- Never call any order placement, cancel, exercise or modification tool.
- Tools: after git pull, run `git merge --no-edit origin/claude/nifty-bohr-bj24xh` to bring in paper_trading/ledger.py and paper_trading/snapshot.py. If the merge conflicts, run `git merge --abort`, continue without them and report it.
- Calendar: the market is closed on 2026-11-26 and closes at 1:00pm ET on 2026-11-27.
- Log once per run. run_id = <YYYY-MM-DD>_1007_morning. For every open, close, settle, skip and no_trade, also add a row to paper_trading/ledger_v2.csv with `python3 paper_trading/ledger.py add --json '{...}'` (fields are listed at the top of ledger.py). Record price_worst (worst side of the spread) AND price_mid for every entry and exit, pnl_worst_usd and pnl_mid_usd on exits, arm = directional, credit or width_test, a stable trade_id (D-, C- or W- then TICKER-YYYYMMDD-n; existing ids are in ledger_v2.csv), underlying_px and quote_ts_utc. The tool refuses a second row for the same run_id, trade_id and action, so a re-run cannot log twice. Keep writing log.csv as before; marks stay in log.csv only.
- Report totals from `python3 paper_trading/ledger.py summary`. The width test never enters totals. State the number of closed trades per arm and that no conclusion is drawn below 100 closed trades per strategy.

## B. Append to "SPY paper spread - close mark"

ADDED 2026-11-15 (approved by the user in the research session):
- Never call any order placement, cancel, exercise or modification tool.
- Tools: after git pull, run `git merge --no-edit origin/claude/nifty-bohr-bj24xh`. If the merge conflicts, run `git merge --abort`, continue without the tools and report it.
- Calendar: the market is closed on 2026-11-26. On 2026-11-27 it closed at 1:00pm ET, so mark with the last quotes and label them post-close.
- Log once per run. run_id = <YYYY-MM-DD>_1537_close. For every close and settle, also add a row to paper_trading/ledger_v2.csv with `python3 paper_trading/ledger.py add --json '{...}'`, with price_worst and price_mid, pnl_worst_usd and pnl_mid_usd. Report totals from `python3 paper_trading/ledger.py summary`; the width test never enters totals.
- REAL POSITION CHECK, read-only, through 2026-11-20 (this replaces the separate 3:47pm check). Position: SPY 760/759 put debit spread, exp 2026-11-20, 1 contract, filled 2026-11-12 at 0.37, account ending 8530, max loss $37.08. If get_option_positions shows it closed, say so in one line and update STATUS.md and paper_trading/real_trades.csv. Otherwise quote both legs (760P id 59e98c6c-3913-4ec1-832f-1e225a30636b, 759P id 4bbb12d2-0213-44f9-86c5-e63d8f130747) and SPY, and report the spread as one unit: mid, conservative exit (sell 760P at bid, buy 759P at ask), P&L in dollars. Check get_option_orders for a working GTC closing order at 0.75 and say if there is none. Alert prominently if the conservative exit is at or below 0.18 or at or above 0.75. Recommend, never act.
- CHAIN SNAPSHOT, every market day: (1) run `python3 paper_trading/snapshot.py ids`; (2) pass that exact list to ONE get_option_quotes call. The result is too large to return inline and is saved to a file; do not read it into context; (3) get_equity_quotes for SPY, QQQ, IWM, NVDA, TLT, XLF, XLE, XLU, EEM; (4) run `python3 paper_trading/snapshot.py ingest <saved file> --spots SPY=<last>,QQQ=<last>,... --run-id <run_id>`; (5) report its summary line (missing, stale, crossed, zero_bid, id_mismatch). Never retype quotes by hand. If the call returns inline instead of a saved file, or the tool reports missing ids or id_mismatch, report that and skip the snapshot. Include paper_trading/snapshots in the commit.

## C. After B is applied

Change the "SPY 760/759 put spread stop check" schedule to `CRON_TZ=America/New_York 47 10,12 16-20 11 *`
(drops the 3:47pm run, which the close mark now covers).

## D. Optional

"RETIRED" stub for the disabled "Daily options trade proposal" prompt:
RETIRED on 2026-11-15 at the user's request. Do nothing except reply in one line that this task is retired. Never call any order tool.

## Already done from the research session on 2026-11-15
- SPY real-position check: weekdays only, `47 10,12,15 16-20 11 *`.
- Premarket briefing: weekdays only, `53 7 16-20,23,24 11 *`.
- "Close NVDA Dec 170/172 call spread" (which carried an order step): paused. A read-only replacement fires in the research session on 2026-12-17 11:47am ET.
- "Re-price TLT and XLF": deleted.
