# Options Trading Lab

Personal research notebook for a small Robinhood options account. It holds the backtests, the paper-trading log, the gamma-map data and the trading skills used in a Claude Code session in November 2026.

This is research, not advice and not a signal service. Nothing here has shown a trading edge.

## Results so far

| Test | Data | Result |
|---|---|---|
| Single long calls/puts, AAPL NVDA SPY MSFT TSLA | Daily bars 2024-08 to 2026-11, 136,170 simulated trades, last 30% held out | No rule beat a random-direction baseline out of sample. Median trade -50% to -100%. 87-100% of simulated $273 accounts went broke at $80 per trade. |
| Debit vertical spreads costing $50 or less, same tickers | Same data and split | Worse than single options. 0% of configurations positive out of sample. 85-100% of simulated accounts fell below $50. |
| Credit spreads (put, call, iron condor) on SPY and QQQ, 0.10-0.20 delta, 1-3 strikes wide, 7-21 days | Daily bars 2017-06 to 2026-11, 1.48M simulated trades, last 30% (from 2024-01-25) held out | No setup passed. Selling on every day averaged about zero return on risk out of sample at IV factor 1.2 and under a VIX-based IV, negative at 1.0, positive only at 1.4. No timing rule beat random entry. Stops and early exits made results worse. |
| Paper test, SPY / QQQ / IWM spreads up to $150 max loss | Live Robinhood quotes, 2026-11-11 to 2026-11-24 | In progress. See `paper_trading/log.csv`. |

Both backtests price options with Black-Scholes on trailing realized volatility times a premium factor (1.0, 1.2, 1.4) calibrated against a small sample of real Robinhood option prices. They have no volatility skew in the base case, use rule-of-thumb bid/ask costs, and cover a mostly rising market. Treat any positive cell as an upper bound.

## Layout

- `backtests/single_options/` - scripts and summary CSVs for the long call/put backtest. `raw_prices_daily.csv` is the input price history.
- `backtests/debit_spreads/` - scripts and summary CSVs for the debit spread backtest. Reuses the pricing code in `single_options/backtest.py`.
- `backtests/credit_spreads/` - credit spread backtest. `prep_data.py` builds `prices_daily.csv` and `events.csv`, `credit_backtest.py` simulates, `credit_analyze.py` writes the summaries and states the pass rule. Files tagged `_harshcost` use the older cost convention.
- `paper_trading/log.csv` - every paper entry, exit and no-trade day, with the reason.
- `paper_trading/gex/` - daily gamma-exposure snapshots built from Robinhood option quotes.
- `skills/` - seven Claude skills from [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills), MIT licensed (see `skills/LICENSE-tradermonty`). Tests removed.
- `.claude/agents/` - the research subagents as reusable Claude Code agents: `ticker-researcher`, `source-cross-checker`, `options-backtester`, `gamma-mapper`, `paper-trader`. All are read-only toward the broker.
- `quant/formulas.py` - Black-Scholes, Greeks, implied vol, expected move, four realized-vol estimators, spread math and probabilities, GEX and zero-gamma flip, Kelly and losing-streak odds. `quant/test_formulas.py` checks them (`python3 quant/test_formulas.py` or pytest).
- `docs/equations.md` - the math behind each function, with sources.
- `automation/scheduled_tasks.md` - the scheduled tasks that run the paper test and manage open positions, with the account number removed.

The large per-trade CSVs (about 80 MB) are not committed. Rerun the backtest scripts to regenerate them.

## Rerunning the backtests

```bash
pip install numpy pandas scipy
```

```bash
python3 backtests/single_options/backtest.py
```

```bash
python3 backtests/debit_spreads/spreads_backtest.py
```

The scripts were written inside a Claude session against data already saved in the repo. They have not been rerun from this folder layout, so expect to fix an input or output path on the first run.

## Gamma map method

GEX per strike = gamma x open interest x 100 x spot^2 x 0.01. Calls count positive and puts negative, which assumes dealers are long calls and short puts. That assumption cannot be checked from public data. Open interest is from the prior session.
