# Scheduled tasks (as of 2026-11-11)

These run inside a Claude Code cloud session. The Robinhood account number is replaced with `<ACCOUNT>`.

## Paper test, 2026-11-11 to 2026-11-24

1. **Morning run, 10:07am ET.** Reads the Nikkei, Hang Seng and FTSE (FMP), builds gamma maps for SPY, QQQ and IWM, tests candidate spreads, and enters up to 3 paper spreads a day (1 per ticker).
   - Max loss $150 per spread, $450 total open.
   - Fills assume paying the ask on bought legs and receiving the bid on sold legs.
   - A candidate must pass four checks: (a) at least two of gamma regime, trend and overseas direction agree; (b) gain-to-risk at least 1.0; (c) each leg's bid/ask spread at most 10% of mid; (d) no major event before expiry unless the trade is built for it.
2. **Close mark, 3:37pm ET.** London close, whether the gamma walls held, paper exits.
   - Exit at +100% of debit or 80% of max value, stop at -50% of debit, close by 1:15pm ET the day before expiry.
3. **Final review, 2026-11-24 4:23pm ET.** Summary and a plain verdict on real-money trading, then deletes the two paper tasks.

## Real positions

- Hourly stop checks, Nov 16-20, 9:47am-3:47pm ET, for the NU calls (stop at mark $0.29) and the RGTI put (stop at mark $0.15).
- Final-day sale, Nov 20 1:17pm ET, closes anything still open before Robinhood's 3:30pm sellout.
- Every real position carries a GTC take-profit at 2x the fill price.

## Paused

- Daily real-money proposal, 12:41pm ET. Paused on 2026-11-11 until the paper test ends. Max loss $50, proposes only, needs an explicit yes.

## Standing rules

- Real trades: max loss $50 per trade, stop proposing after 3 losses in a row or a weekly realized loss over $60.
- No naked short options. Spreads are closed before expiry to avoid assignment.
