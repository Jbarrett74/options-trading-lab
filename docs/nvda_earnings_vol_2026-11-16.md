# NVDA earnings: implied move recorded before the event (2026-11-16, 2:45pm ET)

Written before the report (2026-11-17 after the close, date verified by Robinhood). Nothing here is a trade proposal.
No validated strategy covers earnings, so no real order is eligible.

## OBSERVED (Robinhood quotes, 2026-11-16 19:45 UTC, NVDA last 155.47, down 4.5% on the day, VIX 24.31)
| Expiry | 155 call bid/ask | 155 put bid/ask | Straddle mid | Share of spot | IV (call, put) |
|---|---|---|---|---|---|
| 2026-11-20 | 8.15 / 8.20 | 7.55 / 7.60 | 15.75 | 10.1% | 121.2%, 120.4% |
| 2026-11-27 | 9.45 / 9.50 | 8.70 / 8.80 | 18.23 | 11.7% | 85.4%, 84.8% |
| 2026-12-18 | 12.20 / 12.30 | 11.30 / 11.40 | 23.60 | 15.2% | 64.1%, 64.8% |

Other 11/20 quotes: 140 put 2.24 / 2.26 (IV 123.1%), 170 call 2.82 / 2.83 (IV 118.3%).
Trailing 20-day realized volatility: 54.0% annualized (Robinhood daily closes through 11/13).

## OBSERVED: close-to-close move on the session after each of the last 9 reports
-6.4%, +0.5%, -8.5%, +3.2%, -0.8%, -3.2%, -5.5%, -1.8%, +8.7% (2024-08 to 2026-08).
Mean absolute move 4.3%, median 3.2%, largest 8.7%. The first three report dates are from memory, the last six are verified by Robinhood.

## MODELED: move the options price for the event itself
Two-expiry variance split (11/20 and 11/27, calendar time, one event): baseline volatility 54.7%, event standard deviation 11.3%,
expected absolute move about 9.1%. The 12/18 expiry is roughly consistent (observed variance 0.0364, model 0.0392).
Assumptions: constant baseline volatility across the two expiries, normal move, at-the-money IV only.

## To record after the event
Close-to-close move on 2026-11-18, the 11/20 and 11/27 straddle mids at the 11/17 and 11/18 snapshots, and the IV drop.
Eight NVDA contracts were added to `paper_trading/snapshots/contracts.csv` for this.
