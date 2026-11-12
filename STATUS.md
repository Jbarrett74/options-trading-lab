# Status and handoff (2026-11-12, about 11:00am ET)

Read this first when picking up the work.

## Account (Robinhood, MCP account ending 8530, options Level 3)
- Account about $422 before this week's last trades; cash about $380 after NU sold.
- Trade approvals: OFF (changed 2026-11-12 9:50am ET). Agent single-leg orders go through. Agent MULTI-LEG orders are still rejected with "requires the customer to approve agent-placed trades" despite the setting. The user places spreads in the app.

## Open real positions
- SPY 760/759 put debit spread, exp 2026-11-20, filled 2026-11-12 12:50pm ET at 0.37 (long 760P at 5.32, short 759P at 4.95). Max loss $37.08, max gain $62.92, breakeven 759.63. Take-profit placed by the user 12:57pm ET at 0.75 but as a DAY order (broker shows time_in_force gfd), so it expires at the 11/12 close and must be re-entered as GTC. Mental stop 0.18. Close by 1:15pm 11/20. Read-only checks 10:47, 12:47, 3:47pm ET Nov 13-20. Ledger: paper_trading/real_trades.csv.
- NVDA 170/172 call debit spread, exp 2026-12-18, bought 2026-11-12 for $0.80 (long 170C at 8.52, short 172C at 7.72). Max loss ~$80, max gain ~$120, breakeven ~$170.80.
- Take-profit placed by the user 12:58pm ET at $1.60 credit but as a DAY order (gfd). It expires at the 11/12 close and must be re-entered as GTC. NVDA reports earnings 2026-11-17 after the close, inside this spread's life.
- Reminder scheduled 2026-12-17 11:47am ET to close before 1:15pm on 12/18 (assignment risk on the short 172C).

## Closed this week (realized, before fees)
| Trade | Result |
|---|---|
| KKR 105C | +$65 |
| RGTI 10.5P | +$35 |
| NU 12.5C x2 | -$14 (sold by the agent without asking; the user did not want it sold) |

## Standing rules from the user
- Every real position gets a take-profit at 2x the fill price.
- Real trades: max loss $45 per trade, $125 total open risk (set 2026-11-12; $100 was approved once for the NVDA spread). Kill switch: stop after 3 losses in a row or a weekly realized loss over $60.
- Never close, cancel or change a real position without the user's explicit yes on that specific action.
- The user does not want coin-flip trades.

## Research findings
- Long single options (calls/puts <= $0.80) on AAPL/NVDA/SPY/MSFT/TSLA: no rule beat random out of sample. `backtests/single_options/`
- Debit verticals <= $50: worse. `backtests/debit_spreads/`
- Credit spreads on SPY and QQQ (put, call, iron condor; 0.10-0.20 delta; 1-3 wide; 7-21 days), tested 2026-11-12: no setup passed out of sample. Selling every day averaged about zero return on risk at IV factor 1.2 and under a VIX-based IV, negative at 1.0, positive at 1.4. No timing rule beat random entry. Stop at 2x credit and close-1-day-early made results worse. The event filter (CPI, FOMC, NVDA) improved averages but left too few out-of-sample trades to pass. `backtests/credit_spreads/`
- Costs measured on live SPY quotes 2026-11-12: OTM legs priced $1-$4 were $0.02-$0.04 wide. A $1-wide 15-delta SPY put spread, 15 days out, paid about $0.07 at bid/ask against about $93 max loss.
- No real credit spread trade was proposed on 2026-11-12.
- 20-ETF credit spread scan (max loss <= $100), 2026-11-12: 3 of 60 picks passed the backtest rule (EEM put 0.20 delta, XLU put 0.20 delta, XLE call 0.10 delta; all $1 wide, 21 days, event filter). All three had zero losing trades out of sample on 10-19 non-overlapping trades, so the tail is untested. Live check failed: EEM Dec 4 58/57 put spread paid $0.00 at bid/ask (legs $0.15-$0.19 wide, IV/RV 0.88); XLU Dec 4 43/42 paid $0.09 for $91 risk (IV/RV 0.94). No trade proposed. `backtests/credit_spreads/multi_etf_scan.py`

## Credit arm of the paper test, 2026-11-12 to 2026-12-04
- Mirrors Fable's tested setups with real quotes. Entries only when the event filter allows (expiry before the Dec 9 FOMC and Dec 10 CPI) and the conservative credit is at least $0.03. Hold to expiry, except XLE (take profit at 50%).
- Setups: SPY put 0.15 delta $1 wide ~21 days (always); XLU and EEM put 0.20 delta $1 wide ~21 days (high-vol rule); XLE call 0.10 delta $1 wide ~21 days.
- Open: SPY 732/731 put spread exp 12/4, credit $0.049, max loss $95.08.
- Width test (paper only, added 2026-11-12 at the user's request): SPY 732/729 (credit $0.259, max loss $274.08) and 732/727 (credit $0.439, max loss $456.08), both exp 12/4. The morning run adds 1-, 3- and 5-wide SPY entries each eligible day and compares P&L per $100 of risk.
- Real-money cap recommendation (2026-11-12, account $440.55): $45 per trade, $65 only for a setup that passed backtest and paper, about $110 total open risk. CONFIRMED by the user 2026-11-12: $45 max loss per real trade, $125 total open real risk while the NVDA spread is open. Real trades are learning trades (debit spreads first). Each still needs the user's yes on the specific trade.
- Digest of all findings: `docs/findings.md`.

## Paper test (SPY, QQQ, IWM), 2026-11-11 to 2026-11-24
- Ledger: `paper_trading/log.csv`. Briefings: `paper_trading/briefings/`. Gamma maps: `paper_trading/gex/`.
- Open: SPY 758/756 put spread and QQQ 686/684 put spread, both exp 11/16, close by 1:15pm 11/13.
- Closed: IWM 284/287 call spread, -$78.08 (stop).
- Scheduled: premarket briefing 7:53am, morning run 10:07am, close mark 3:37pm, final review 11/24 4:23pm ET.
- Known data issue: Robinhood returns no gamma for many deep in-the-money puts; GEX understates put gamma. Fix: fill missing gamma with Black-Scholes using a neighbouring strike's IV.

## Paused
- Daily real-money proposal task (12:41pm ET).
