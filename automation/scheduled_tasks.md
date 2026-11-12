# Scheduled tasks (as of 2026-11-12)

These run inside a Claude Code cloud session. The Robinhood account number is replaced with `<ACCOUNT>`.

## Paper test

Directional arm (SPY/QQQ/IWM debit spreads) 2026-11-11 to 2026-11-24. Credit arm (Fable's credit spread setups on SPY, XLU, EEM, XLE, real quotes, conservative fills) 2026-11-12 to 2026-12-04. Morning and close runs now run weekdays through 2026-12-04; interim review 2026-11-24, final review 2026-12-04 4:31pm ET deletes the paper tasks.

0. **Premarket briefing, 7:53am ET (from 2026-11-12).** Overnight Asia and London, VIX, premarket ETF prices, today's economic calendar and news, gamma maps on the day's fresh open interest, and a game plan per ticker. No paper entries, because option quotes before the 9:30am open are stale. Saved to `paper_trading/briefings/<date>.md`.
1. **Morning run, 10:07am ET.** Starts from the briefing and checks whether its plan survived the open. Reads the Nikkei, Hang Seng and FTSE (FMP), builds gamma maps for SPY, QQQ and IWM, tests candidate spreads, and enters up to 3 paper spreads a day (1 per ticker).
   - Max loss $150 per spread, $450 total open.
   - Fills assume paying the ask on bought legs and receiving the bid on sold legs.
   - A candidate must pass four checks: (a) at least two of gamma regime, trend and overseas direction agree; (b) gain-to-risk at least 1.0; (c) each leg's bid/ask spread at most 10% of mid; (d) no major event before expiry unless the trade is built for it.
2. **Close mark, 3:37pm ET.** London close, whether the gamma walls held, paper exits.
   - Exit at +100% of debit or 80% of max value, stop at -50% of debit, close by 1:15pm ET the day before expiry.
   - Part B, credit arm: prices the SPY, XLU, EEM and XLE setups on live quotes, enters only if the event filter allows and the conservative credit is at least $0.03.
3. **Directional arm review, 2026-11-24 4:23pm ET.** Summary of the SPY/QQQ/IWM arm. Deletes nothing.
4. **Final review, 2026-12-04 4:31pm ET.** Both arms, a plain verdict on real-money trading, then deletes the premarket, morning and close tasks.

## Real positions

- NVDA 170/172 call spread, exp 2026-12-18. Reminder 2026-12-17 11:47am ET to close before 1:15pm on 12/18. The take-profit ($1.60 credit, GTC) must be placed by the user in the app.
- The KKR, NU and RGTI stop tasks and the Nov 20 final-sale task were deleted after those positions closed.

## Paused

- Daily real-money proposal, 12:41pm ET. Paused on 2026-11-11 until the paper test ends. Max loss $50, proposes only, needs an explicit yes.

## Standing rules

- Real trades: max loss $50 per trade, stop proposing after 3 losses in a row or a weekly realized loss over $60.
- No naked short options. Spreads are closed before expiry to avoid assignment.
