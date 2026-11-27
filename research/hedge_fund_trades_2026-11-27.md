# Two trade candidates for 2026-11-27 (half day, closes 1pm ET)

Prepared 2026-11-27 about 1am ET. Real orders are placed only by the account owner in the app.

## Hedge fund buying (Q3 2026 13F, positions as of 2026-09-30, filed by 2026-11-16)
- Equibles: most new hedge fund positions META (65), SpaceX (60), MSFT (54); largest net buying META ($9.1B), INTC ($8.2B), NVDA ($5.9B).
- Seeking Alpha on Goldman's Hedge Fund VIP list (739 funds): AMZN, MSFT, META top; basket -3% YTD vs S&P +6% (date of edition not confirmed).
- Retailvest: NVDA, META, AMZN largest dollars added. Sources disagree on method; 13F data is 8-14 weeks old, not "just bought".

## Prices (overnight, about 12:50am ET 11/27) and trend (11/25 closes)
| | Overnight | 11/25 close | SMA20 | SMA50 |
|---|---|---|---|---|
| QQQ | 652.29 | 633.93 | 666.73 | 707.05 |
| META | 626.33 | 609.89 | 615.27 | 672.42 |
| MSFT | 500.19 | 489.93 | 517.14 | 519.55 |
| AMZN | 251.27 | 244.43 | 257.19 | 255.12 |
| SPY | 729.69 | 716.70 | 740.33 | 757.89 |

## Why META/MSFT directly do not fit
Near-the-money spreads on $500-600 stocks with $5 strikes cost well over $45. XLC (META proxy) 12/4 options quoted 0.05 x 5.00 with open interest 11-19: untradable.

## Most-backtested strategy
SPY $1-wide put credit spread (0.15 delta, 21 days): max loss about $95 per spread, above the $45 cap; its own event filter blocks every expiry until after CPI 12/10. Not tradable today.

## Candidates (both bullish, both fail the trend check)
1. QQQ 12/4 bull call 1-wide, about 1% out of the money at the open; limit 0.40. 11/25 close quotes for 662/663: 3.93/4.22 and 3.69/3.97 (mid 0.245, worst 0.53).
2. AMZN 12/4 bull call 2.5-wide, strikes so the worst fill is at or under 0.45. 11/25 close quotes for 260/262.5: 1.35/1.44 and 0.97/1.07 (mid 0.375, worst 0.47) with AMZN at 244.

Exit rules (paper arm): take profit at 80% of width, stop at 50% of debit, close by 1:15pm ET 12/3 (before the 12/4 jobs report).
Risk cap: NVDA 170/172 open with $80 max loss; total cap $125 leaves $45, so only one candidate fits unless NVDA is closed.

Sources:
- https://equibles.com/research/q3-2026-13f-roundup-spacexs-early-holders-cut-as-1-110-filers-bought-in
- https://seekingalpha.com/news/4676203-the-50-stocks-that-matter-most-to-hedge-funds-goldman
- https://www.retailvest.com/stocks/13f-report
- https://stockslash.com/13f/q3-2026
