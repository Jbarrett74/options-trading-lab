# Scheduled tasks (as of 2026-11-15, evening)

These run inside Claude Code cloud sessions. The account number is not written here.
No scheduled task may place, cancel or change a real order (user's execution protocol, 2026-11-15). That rule lives
in the prompt text; the session still has the broker's order tools. The broker-side lock is the trade approval
setting in the Robinhood app.

## Paper desk session

| Task | Schedule (ET) | What it does |
|---|---|---|
| Paper test premarket briefing | 7:53am, Nov 16-20, 23, 24 | Overnight markets, calendar, gamma maps, game plan. No entries. |
| SPY paper spread morning | 10:07am weekdays, self-skips after Dec 4 | Directional arm entries (through Nov 24), credit arm and width test entries, marks. |
| SPY 760/759 put spread stop check | 10:47am, 12:47pm, 3:47pm, Nov 16-20 | Read-only check of the real SPY spread. The 3:47pm run moves into the close mark once `docs/desk_prompt_changes_2026-11-15.md` is applied. |
| SPY paper spread close mark | 3:37pm weekdays, self-skips after Dec 4 | Marks, exits, settlements. After the prompt change: real SPY check and the daily chain snapshot. |
| Paper test directional arm review | Nov 24, 4:23pm | Summary of the directional arm. |
| Paper test final review | Dec 4, 4:31pm | Both arms; deletes the premarket, morning and close tasks. |
| Close NVDA Dec 170/172 call spread | PAUSED 2026-11-15 | Carried an order step. Replaced by the research session alert below. |
| Daily options trade proposal | DISABLED since 2026-11-11 | Retired. Prompt still holds an old order step and a $50 cap; it does not run. |

Paper limits: directional $150 per spread and $450 open; credit arm $1 wide; width test up to $466. These exceed the
real limits ($45 per trade, $125 open), so results are also reported per $100 of risk and flagged in ledger_v2.csv.

## Research session

| Task | Schedule (ET) | What it does |
|---|---|---|
| NVDA 170/172 expiry alert (read-only) | Dec 17, 11:47am | Quotes the spread as one unit and reminds the user to close it before 1:15pm on Dec 18. No order step. |

## Market calendar the prompts rely on
- Closed Thursday 2026-11-26. Early close 1:00pm ET Friday 2026-11-27.

## Files
- `paper_trading/log.csv`: prose ledger, unchanged format.
- `paper_trading/ledger_v2.csv` and `ledger.py`: structured ledger with worst-side and mid fills, one row per run, trade and action.
- `paper_trading/snapshots/contracts.csv` and `snapshot.py`: 174 fixed contracts (nine tickers, Dec 18 and Jan 15 expiries, five strikes, puts and calls) quoted once a day. New expiries must be added before Dec 18.
