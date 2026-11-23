# Open-source SPY / VIX / NVDA options strategies on GitHub: evidence review

Date: 2026-11-23. Read-only research. No code was cloned or run, nothing was logged into, and no orders were placed.

## Bottom line (read first)

1. **Popularity and evidence quality point in opposite directions.** The well-starred repos (ThetaGang, optopsy, lambdaclass options_portfolio_backtester, alpacahq/options-wheel) are execution tools or backtest libraries. None of them publishes a strategy result with an out-of-sample test. The repos with the best-documented evidence have 0 to 8 stars.
2. **No published repo has an out-of-sample edge in a structure that fits a $45 max loss.** The only small-account study (floor-insurance-bot) found that $1-wide SPY 0DTE put spreads pay about 7% to 9% of width, and almost every variant lost money after costs. That matches this lab's own finding in STATUS.md: SPY/QQQ credit spreads had no out-of-sample edge.
3. **Best candidate for an independent out-of-sample backtest: sam-bateman/vrp-harvesting-study, "Strategy B put spread"** (monthly SPX short -0.30 delta put / long -0.10 delta put). It is the only repo here that shows a train/test split (2013-2018 / 2019-2024), a documented look-ahead audit and costs. Its spread result held out of sample (test Sharpe +0.54).
   - **It cannot be traded at $45 as stated.** The strikes are about 3.6% of spot apart. On SPY that is a spread roughly $25 wide, with a max loss in the thousands of dollars.
   - **Its prices are synthetic.** They are Black-Scholes values with VIX used as the volatility for every strike, not real option quotes.
   - **What can be tested:** repeat it on real SPY quotes for 2025-01 to 2026-11, a period the study never saw. That tests the idea. A $45-risk version would be a different, narrow-width trade that this lab has already tested without finding an edge.
4. **Rules are mostly reproducible, with gaps.** The delta targets, monthly cadence, cost model and gate timing are stated. The README does not state the exact entry day and time, the expiry choice, strike rounding or whether the trade is held to expiry. You would need to read the code to fill those in. **The repo has no license, so the code may be read but not copied.** Reimplement it from the description.
5. **NVDA: nothing credible found.** The NVDA-specific repos found have 0 to 1 stars and claim no measured results. The only NVDA result found is one NVDA put inside Alpaca's two-week paper test.

Tags: [Certain] = read directly from the cited page. [Likely] = reasoned from it. Star counts and dates come from the GitHub search API on 2026-11-23. "Last push" is GitHub's `pushed_at` field, used as a stand-in for the last commit date. The per-repo commit endpoint was blocked by this session's network proxy, so exact last-commit dates are "not found".

---

## Candidates

### 1. sam-bateman/vrp-harvesting-study
- URL: https://github.com/sam-bateman/vrp-harvesting-study
- Stars 1, forks 0, last push 2026-07-11, created 2026-04-22 [Certain, GitHub search API]
- Instruments: (A) VIX futures calendar: short front month, long second month, rolled 5 trading days before expiry. (B) Monthly SPX put writing at -0.30 delta, cash-secured; the spread variant buys a -0.10 delta wing. (C) Strategy B, but only entered when the prior month-end VIX minus 20-day realized vol is at or above a threshold. [Certain, README]
- Exit: not stated explicitly. The study benchmarks against the CBOE PUT index, which holds to expiry, so this probably holds to expiry too [Likely]. The README mentions "calendar-month cycles misalign expiry timing around COVID", so expiries are approximate.
- Claimed performance, as stated in the README:
  - B put spread: train Sharpe +1.22 / test Sharpe +0.54. Annual return 4.0% / 2.6%. Max drawdown -4.1% / -9.2%.
  - A, VIX calendar: train Sharpe +0.07 / test Sharpe +0.88.
  - C, VRP gate: the threshold chosen on training data did worse than no gate out of sample (+0.49 vs +0.54).
  - All three tail overlays (VIX>30 regime filter, vol scaling, tail hedge) failed out of sample.
- How it was measured:
  - Backtest only. Train 2013-2018, test 2019-2024, with no tuning on the test window.
  - Costs: options at 5% of gross premium round trip on both legs; VIX futures at 1 bp per leg per roll, with a sweep from 1 to 30 bp.
  - Option prices are synthetic Black-Scholes values using VIX as the volatility, not real quotes.
  - Includes a bootstrap, the probabilistic Sharpe ratio and an Oct-1987 stress test.
- License: no LICENSE file found on main or master [Certain, raw URL returned 404]. All rights reserved by default: read and learn from it, but **do not copy the code**.
- Red flags:
  - Prices are synthetic. Using VIX for both strikes ignores skew, so the spread's net credit is probably overstated, because the 10-delta wing usually trades at a higher implied vol than VIX [Likely].
  - Feb 2018 falls in the training window. The author says so.
  - Many variants were tested (multiple testing). The author says so.
  - 1 star, single author. Not independently verified.
  - The study's strengths are its own disclosures: five bugs found (including two look-ahead leaks) and the original results retracted.

### 2. kapilcdave/floor-insurance-bot
- URL: https://github.com/kapilcdave/floor-insurance-bot
- Stars 0, forks 0, last push 2026-10-25, created 2026-08-18 [Certain]
- Instrument: 0DTE SPY / QQQ / IWM put credit spreads on Alpaca, plus paper-only XSP. [Certain, README]
- Entry and exit:
  - Entry at 09:45 ET. A trend filter compares the prior close with its 20-day SMA. The bot sells the nearest put at or below spot and buys the put exactly `SPREAD_WIDTH` lower. In the buffered variant, the short strike is a fixed dollar buffer below spot.
  - Exit when the spread debit reaches `STOP_DEBIT_MULTIPLE` times the credit, at an optional take-profit fraction, or by flattening at 15:00 ET. [Certain, README]
- Claimed performance: **negative.** Across 36 structures declared in advance and 615 sessions (2024-02-01 to 2026-07-17):
  - The credit was 7% to 9% of the width.
  - The default $15 buffer met its $0.05 minimum credit on only 7 of 615 sessions.
  - The best structure made "about 3.9% per year while risking 5.4% of the account on a single session".
  - The ATM/SMA20 grid, the implied-move spreads and the $2 SPY iron fly (-$16.63 / -$13.98 per trade, train / validation) all failed.
  - Sources: README and https://github.com/kapilcdave/floor-insurance-bot/blob/main/docs/CREDIT_STRUCTURE.md
- How it was measured:
  - Backtest on one-minute option *trade* bars, not bid/ask. The author calls these "research marks".
  - Train / validation split, with a final holdout (2026-07-20 to 2026-08-18) kept sealed.
  - Costs: $0.02 per side of slippage plus $0.10 in fees per spread.
  - Paper and shadow forward tests only. No live account results.
- License: MIT (LICENSE file present) [Certain]. You may copy it with the copyright notice kept.
- Red flags:
  - 0 stars. Not independently verified.
  - Trade prints are not executable quotes.
  - **Internal inconsistency:** in CREDIT_STRUCTURE.md, row `buf10_w3_stop1_tp0.5` shows gross average $9.12 and net average $11.18. Net cannot be above gross after costs, so that row is wrong somewhere. The other rows I checked had net below gross.
  - The one positive candidate (a relative-value butterfly) turns negative at 3 cents of slippage.

### 3. Javier-Garzo/ern-wo-options-backtester
- URL: https://github.com/Javier-Garzo/ern-wo-options-backtester
- Stars 8, forks 0, last push 2026-08-16, created 2026-07-26 [Certain]
- Instruments: SPXW, SPY and XSP short puts and calls, replicating WealthyOption (WO) and Early Retirement Now (ERN).
- WO entry and exit, fully specified [Certain, https://github.com/Javier-Garzo/ern-wo-options-backtester/blob/main/docs/research/strategies-theory/wealthy-option.md]:
  - Three independent short-put sleeves:

    | Target delta | Profit target | Allocation |
    |---|---|---|
    | 0.055 | 74% | 25% |
    | 0.065 | 72% | 30% |
    | 0.075 | 69% | 25% |

  - Entry from 09:34 ET, 1 to 4 calendar days to expiry, nearest expiry first.
  - A quote is rejected if its delta is more than 0.02 from target or if (ask-bid)/mid is above 0.50.
  - Entry fill is modeled at ask - 60% of the spread.
  - Exit is a GTC profit-target limit. Losers are held to expiry with no stop and no roll.
  - Position size assumes risk of strike x 20% x 100.
- ERN: 0DTE and 1DTE SPXW short puts. There is also a "defined-risk" 1DTE put spread with the long leg 50 SPX points below the short.
- Claimed performance [Certain, README and https://github.com/Javier-Garzo/ern-wo-options-backtester/blob/main/docs/research/README.md]:
  - WO puts on SPXW: CAGR 13.97%, max drawdown 22.90%, 8,367 trades (2017-01-03 to 2026-07-31). WO's own site claims 19.0% CAGR.
  - WO puts on SPY at $50k: 12.21% CAGR, 21.10% max drawdown.
  - ERN 0DTE+1DTE: 1.55% a year against ERN's live 7.06%.
  - ERN 50-point put spread: 0.17% a year, 188 trades, 3 losses.
- How it was measured:
  - Backtest on ThetaData 5-minute NBBO with Greeks. Fills are conservative: no profit-target fill on missing or zero asks, and inferred inside-spread fills are counted (27.2% of WO profit targets).
  - Commissions are modeled.
  - Postmortems compare each result with the published source.
  - **No in-sample / out-of-sample split.** The parameters are copied from WO's published configuration, which WO presumably chose on overlapping history, so the result is effectively in-sample for WO's rules [Likely].
- License: Apache-2.0 [Certain, LICENSE file]. You may copy it with attribution and must keep the license and NOTICE.
- Red flags:
  - Naked short options: not defined risk and not allowed for this account.
  - Requires a paid ThetaData subscription.
  - The 97% win rate hides large expiry losses. The author says so.
  - 8 stars, new repo.
  - Its strength is honesty: it reports results worse than the published claims and explains why.

### 4. lambdaclass/options_portfolio_backtester
- URL: https://github.com/lambdaclass/options_portfolio_backtester
- Stars 287, forks 53, last push 2026-11-03, created 2019-05-08 [Certain]
- What it is: a backtest engine, not a strategy. Built-in presets include a Spitznagel-style deep-OTM SPY put leg (delta -0.10 to -0.02, 90 to 180 days to expiry), near-ATM put protection and a strangle.
- Fill models are bid/ask, mid, a spread fraction or volume-aware. Commissions are modeled.
- The SPY options data is pinned by SHA-256 so results can be reproduced. [Certain, README]
- Claimed performance: only an example output in the README: `{'annual_return': 10.42, 'max_drawdown': -51.9, 'volatility': 19.53, 'sharpe': 0.61, 'trades': 147}` for 100% SPY plus a 0.5% put budget. The period and the in-sample / out-of-sample status are not stated in the README ("not found"). The companion research is at https://github.com/unbalancedparentheses/finance_research (not reviewed).
- License: MIT [Certain]. You may copy it with the notice kept.
- Red flags: it is a tool with no strategy claim to verify. The README points readers to docs/METHODOLOGY.md about "entry-calendar luck", which is a good sign.

### 5. goldspanlabs/optopsy
- URL: https://github.com/goldspanlabs/optopsy
- Stars 1,522, forks 233, last push 2026-11-22, created 2017-09-17 [Certain]
- What it is: a Python backtest library with 38 strategies, including iron condors, vertical spreads and calendars.
  - Strikes are chosen by per-leg delta.
  - Exits can use stop-loss, take-profit or a maximum holding period.
  - Slippage can be mid, spread-based, liquidity-based or per leg. Commissions are modeled.
  - Data comes through EODHD and needs an API key. [Certain, README]
- Claimed performance: none. The README shows example statistics tables only.
- License: AGPL-3.0 [Certain]. Copyleft: any copy or derivative, including one offered over a network, must be released under AGPL.
- Red flags: no strategy evidence. The data source is a paid third party. Useful only as an engine.

### 6. brndnmtthws/thetagang
- URL: https://github.com/brndnmtthws/thetagang
- Stars 2,773, last push 2026-11-16, created 2020-12-03 [Certain]
- Instrument: an IBKR bot that runs the "wheel" (sell puts, then covered calls) on a portfolio. Default symbols include SPY, QQQ and TLT. Optional VIX call hedge and long-put tail hedge. [Certain, README]
- Rules [Certain, https://github.com/brndnmtthws/thetagang/blob/main/thetagang.toml]:
  - Default target 45 days to expiry at delta 0.3, with a minimum open interest of 10.
  - Roll when profit reaches 90% (`roll_when.pnl = 0.9`) or at 15 days to expiry.
  - By default, in-the-money puts are assigned rather than rolled.
  - The VIX call hedge follows the Cboe VXTH tiers and closes when VIX is above 50.
- Claimed performance: none found in the README. It warns of "losses exceeding your initial investment" and points to Portfolio Visualizer for backtests.
- License: AGPL-3.0 [Certain]. Copyleft.
- Red flags:
  - No published evidence of any edge.
  - Needs IBKR, margin and enough capital to hold 100 shares per symbol.
  - Cash-secured or naked puts, not defined risk. Not usable here.

### 7. alpacahq/options-wheel
- URL: https://github.com/alpacahq/options-wheel
- Stars 138, forks 44, last push 2025-06-05, created 2025-06-02 [Certain]
- Rules:
  - Sell puts filtered by delta, open interest and yield, chosen by `score = (1 - |delta|) x (250/(DTE+5)) x (bid/strike)`.
  - After assignment, sell calls above cost basis.
  - One contract per symbol. [Certain, README]
- Claimed performance: +$951.89 on a $100,000 paper account, May 14 to May 28, 2025. Premiums collected $1,240, including one NVDA 127 put for $332. [Certain, README]
- How it was measured: two weeks of Alpaca paper trading. The README itself says it "do[es] not represent actual live trading performance".
- License: Apache-2.0 [Certain]. Copy with attribution.
- Red flags:
  - Two weeks is not evidence of anything.
  - Paper fills.
  - Repo abandoned since June 2025 (last push).
  - A vendor demo: the repo is published by Alpaca, the broker it runs on.

### 8. peterchettiar/trading-volatility (and eigenquant53/VRP)
- URLs: https://github.com/peterchettiar/trading-volatility (12 stars, last push 2026-10-18) and https://github.com/eigenquant53/VRP (34 stars, last push 2022-12-20; the README is one line) [Certain]
- Instrument: VIXY / SVXY / SPY, replicating the thesis "Trading strategies based on the VIX term structure".
- Long-Short VIX (LSV) rule:
  - Each day, basis = VIX futures open / VIX spot open - 1.
  - If basis < 0 (backwardation): hold VIXY, bought at the open, closing any SVXY first.
  - If basis > 0 (contango): hold SVXY, closing any VIXY first.
  - Assumed costs: brokerage 0.15%, slippage 0.04%, management fee 0.85% a year.
  - The thesis sample is 2011-10-11 to 2020-03-31. [Certain, README]
- Claimed performance: none in the README ("not found").
- License: no LICENSE file in either repo [Certain, raw URL 404]. No copying permitted.
- Red flags:
  - Trades at the open using that same open's basis. This is look-ahead unless the futures and spot opens are both known before your fill [Likely].
  - SVXY changed from -1x to -0.5x after Feb 2018 (noted in a QuantConnect thread, https://quantconnect.com/forum/discussion/2657/a-simple-vix-strategy/p1/comment-9053), so returns before and after 2018 are not comparable.
  - No out-of-sample test.
  - eigenquant53 looks abandoned.

### 9. mcf-long-short/ibkr-options-volatility-trading
- URL: https://github.com/mcf-long-short/ibkr-options-volatility-trading
- Stars 378, last push 2025-01-23 [Certain]
- Rules:
  - Weighted volatility = 0.5 x 1-week + 0.3 x 2-week + 0.2 x 1-month realized vol, ranked across the Russell 3000.
  - Alert for a long straddle when the absolute daily move is above 5%; alert for a short straddle when it is below 0.5%.
  - **A person then hand-picked the trades.** [Certain, README]
- Claimed performance: none ("not found"). It was a master's course project on an IBKR paper account.
- License: MIT [Certain].
- Red flags: discretionary selection, no results, short straddles (undefined risk), abandoned.

### Also seen, not ranked
- **NutellaPazza/vix-futures-strategy** (0 stars, https://github.com/NutellaPazza/vix-futures-strategy). Long VX2 accumulation, claimed 16.7% CAGR 2013-2026 with walk-forward. "The strategy source code is private", so it cannot be checked. The author also says the parameters came from the same 2013-2026 history.
- **YichengYang-Ethan/0dte-strategy** (14 stars, https://github.com/YichengYang-Ethan/0dte-strategy). An honest log of failed SPX 0DTE tests ("falsified"); no positive claim. The README says MIT, but no LICENSE file was found [Certain].
- **quantgalore/spx-vol-engine** (14 stars, https://github.com/quantgalore/spx-vol-engine). Two .py files and no README. Tied to a Substack newsletter. Its filename says NDX while its description says SPX.
- **danielkim009-cmd/options-backtester** (1 star, MIT, https://github.com/danielkim009-cmd/options-backtester). SPY bull put spreads priced with Black-Scholes and VIX as the volatility. No out-of-sample test.

---

## Ranking by trustworthiness of evidence (not by claimed return)

| Rank | Repo | Why |
|---|---|---|
| 1 | sam-bateman/vrp-harvesting-study | Only one with train/test results, a published look-ahead audit, cost sensitivity and stated limitations. Weakness: synthetic prices. |
| 2 | kapilcdave/floor-insurance-bot | Grids declared in advance, sealed holdout, small-account focus, real option prints. Weaknesses: one table is internally inconsistent; trade prints are not quotes. |
| 3 | Javier-Garzo/ern-wo-options-backtester | Real 5-minute NBBO, conservative fills, honest comparison with published claims. Weakness: no out-of-sample split; naked options. |
| 4 | lambdaclass/options_portfolio_backtester | Solid engine with pinned data. No strategy claim to rate. |
| 5 | goldspanlabs/optopsy | Solid engine. No strategy claim. |
| 6 | brndnmtthws/thetagang | Mature live tool. No performance evidence. |
| 7 | alpacahq/options-wheel | Two weeks of paper trading. |
| 8 | peterchettiar/trading-volatility | Clear rules, no results, likely look-ahead at the open. |
| 9 | mcf-long-short/ibkr-options-volatility-trading | Discretionary, no results. |

## Best candidate for an independent out-of-sample backtest

**sam-bateman/vrp-harvesting-study, Strategy B put spread.**

- **Why this one:**
  - It is the only claim that has already survived the author's own out-of-sample test.
  - Its main weakness (Black-Scholes prices with VIX as the volatility) is exactly what a real-quote backtest checks.
  - The study never saw 2025-01 to 2026-11, so that period is a true out-of-sample window.
- **Is it specified precisely enough to reproduce?** Partly.
  - Stated: short -0.30 delta and long -0.10 delta, monthly; costs of 5% of gross premium round trip on both legs; any gate uses the prior month-end value.
  - Not stated in the README: the exact entry day and time, how the expiry is chosen (calendar month vs third Friday), strike rounding, and whether the trade is held to expiry.
  - The code holds those details but has no license. Read it, do not copy it.
- **Fit with this account:**
  - Robinhood Level 3 allows the trade itself (a defined-risk vertical).
  - It does not fit the $45 max loss. At S=100 and 20% IV the study puts the strikes about 3.6 points apart. On SPY near 730 that is a spread about $25 wide [Likely], so the max loss is far above $45.
  - Shrinking it to a $1-wide spread changes the strategy into the narrow-spread trade that this lab (STATUS.md, backtests/credit_spreads/) and floor-insurance-bot both found has no edge after costs.
  - **Recommendation:** treat the test as research on whether the premium is real on real quotes, not as a source of trades for this account.
- **NVDA:** no credible repo found.

## What was not possible
- The GitHub per-repo API (`api.github.com/repos/...`) was blocked by this session's proxy, so exact last-commit dates are "not found". `pushed_at` from the search API is given instead.
- alpaca.markets could not be reached (the host is not allowed in this session's network settings), so Alpaca's 0DTE bull put spread tutorial and its code were not reviewed.
- The full content of the PDFs and JSON result files was not read. Numbers above come only from the README and docs pages cited.
