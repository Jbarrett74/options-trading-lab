# Status and handoff (2026-11-12, about 11:00am ET)

Read this first when picking up the work.

## Account (Robinhood, MCP account ending 8530, options Level 3)
- Account about $422 before this week's last trades; cash about $380 after NU sold.
- Trade approvals: OFF (changed 2026-11-12 9:50am ET). Agent single-leg orders go through. Agent MULTI-LEG orders are still rejected with "requires the customer to approve agent-placed trades" despite the setting. The user places spreads in the app.

## Open real position
- NVDA 170/172 call debit spread, exp 2026-12-18, bought 2026-11-12 for $0.80 (long 170C at 8.52, short 172C at 7.72). Max loss ~$80, max gain ~$120, breakeven ~$170.80.
- Take-profit: user needs to place it in the app (close spread, $1.60 credit, GTC). Agent attempts were rejected.
- Reminder scheduled 2026-12-17 11:47am ET to close before 1:15pm on 12/18 (assignment risk on the short 172C).

## Closed this week (realized, before fees)
| Trade | Result |
|---|---|
| KKR 105C | +$65 |
| RGTI 10.5P | +$35 |
| NU 12.5C x2 | -$14 (sold by the agent without asking; the user did not want it sold) |

## Standing rules from the user
- Every real position gets a take-profit at 2x the fill price.
- Real trades: max loss $50 per trade normally ($100 was approved for the NVDA spread). Kill switch: stop after 3 losses in a row or a weekly realized loss over $60.
- Never close, cancel or change a real position without the user's explicit yes on that specific action.
- The user does not want coin-flip trades.

## Research findings
- Long single options (calls/puts <= $0.80) on AAPL/NVDA/SPY/MSFT/TSLA: no rule beat random out of sample. `backtests/single_options/`
- Debit verticals <= $50: worse. `backtests/debit_spreads/`
- Not yet tested: credit spreads / volatility risk premium on SPY and QQQ. This is the next test the user agreed to consider.

## Paper test (SPY, QQQ, IWM), 2026-11-11 to 2026-11-24
- Ledger: `paper_trading/log.csv`. Briefings: `paper_trading/briefings/`. Gamma maps: `paper_trading/gex/`.
- Open: SPY 758/756 put spread and QQQ 686/684 put spread, both exp 11/16, close by 1:15pm 11/13.
- Closed: IWM 284/287 call spread, -$78.08 (stop).
- Scheduled: premarket briefing 7:53am, morning run 10:07am, close mark 3:37pm, final review 11/24 4:23pm ET.
- Known data issue: Robinhood returns no gamma for many deep in-the-money puts; GEX understates put gamma. Fix: fill missing gamma with Black-Scholes using a neighbouring strike's IV.

## Paused
- Daily real-money proposal task (12:41pm ET).
