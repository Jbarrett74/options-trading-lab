# Findings digest

Each line was checked against the committed files named. Model results are simulations, not real fills.

## 1. Long calls and puts (2026-11-11) - `backtests/single_options/`
- No entry rule beat a random-direction baseline out of sample at realistic option prices (IV 1.2-1.4x realized).
- Median trade -50% to -100%. 87-100% of simulated $273 accounts went broke at $80 per trade.
- At $0.80 or less, contracts sit far out of the money (7-day: SPY ~3%, AAPL ~5%, NVDA ~7.5%, TSLA ~14%).

## 2. Debit spreads costing $50 or less (2026-11-11) - `backtests/debit_spreads/`
- 0% of configurations positive out of sample. Worse than single options, because the short leg caps the right tail and four bid/ask crossings add cost.

## 3. Credit spreads on SPY and QQQ (Fable, 2026-11-12) - `backtests/credit_spreads/`
Data: daily bars 2017-06 to 2026-11, last 30% (entries from 2024-01-25) held out. Costs calibrated to live SPY quotes: max($0.01, 1% of leg) per side plus $0.04 per contract. Skew added (puts dearer).
- No setup passed the pre-written out-of-sample rule (`best_IS_config_OOS_check.csv`, all 48 rows "fail").
- Selling every day and holding (`always_baseline.csv`), out-of-sample mean return on risk:
  - IV factor 1.0: -3% to -12% (negative everywhere).
  - IV factor 1.2: about -3% to +1%.
  - IV factor 1.4: 0% to +8%.
  - VIX-based IV: SPY slightly positive, QQQ slightly negative.
  - So the answer depends on the IV assumption. The test cannot show an edge of its own.
- Win rates 69% to 94% across all IV modes (77% to 94% at IV 1.2 and VIX); worst losses near full width (about -$265 to -$290 on 3-wide).
- Exits made things worse. Stops at 2x credit and closing a day early lowered returns.
- Event filter (skip if CPI, FOMC, or NVDA earnings for QQQ falls before expiry) raised averages but left too few trades to pass.
- Closest miss, SPY put spread 0.15 delta, $1 wide, 21 days, hold, event filter, IV 1.2 (`grid_IS_vs_OOS.csv`): 63 out-of-sample trades, 96.8% wins, mean +$1.95, median +$5.14, worst -$94.90. Two losses wiped out most of 61 wins.

## 4. 20-ETF credit spread scan (Fable, 2026-11-12) - `multi_etf_*.csv`
- 60 picks (best in-sample per ticker and structure), each checked under IV 1.0, 1.2 and 1.4.
- 3 picks passed under all three: EEM put 0.20 delta, XLU put 0.20 delta (both: $1 wide, 21 days, hold, high-vol rule, event filter), XLE call 0.10 delta ($1 wide, 21 days, take profit at 50%, event filter).
- EEM and XLU had zero out-of-sample losses on 10-12 non-overlapping trades, so the loss tail was never tested. About 0.6 false passes were expected by chance across 60 picks.
- Live check on 2026-11-12: all three fail at real bid/ask (see section 5).

## 5. Live reality check (2026-11-12, about 11:23am ET) - `paper_trading/credit_arm/`
| Setup | Conservative credit | Max loss | Result |
|---|---|---|---|
| SPY 732/731 put, Dec 4 | $0.049 | $95.08 | Paper entry |
| XLU 42.5/41.5 put, Dec 4 | -$0.031 | - | Skip: quotes too wide |
| EEM 58/57 put, Dec 4 | -$0.001 | - | Skip: quotes too wide |
| XLE 70/71 call, Dec 4 | $0.029 | - | Skip: below $0.03 floor |

The one entry risks $95 to make $4.92 with a risk-neutral 83% chance of full profit. Using those odds the expected value is negative. A positive result needs implied volatility to overstate the real move, which is the premium the backtest could not confirm.

## What this means
- Three strategy families tested; none has shown an edge that survives real costs.
- The $50-$100 risk cap is the binding problem. It forces $1-wide spreads, where the bid/ask eats most of the credit (credit spreads) or forces far out-of-the-money bets (debit spreads, long options).
- The paper test is the only remaining evidence source. It must not be over-read: 2 weeks is a tiny sample.

## Unverified inputs (from Fable's notes)
- Aug, Sep and Oct 2026 CPI dates in `events.csv` were typed from memory and are marked unverified.
- Option prices are modelled, not historical.
- Costs come from one calm-morning snapshot.
