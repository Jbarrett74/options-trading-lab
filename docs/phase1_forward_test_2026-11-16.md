# Phase 1: the paper desk as a forward test (2026-11-16, 12:45pm ET)

Labels: OBSERVED = paper fills at real quotes, git history or routine timestamps. ESTIMATED = arithmetic on stated assumptions. Nothing here is MODELED.

## 1. Rule registry

`paper_trading/rule_registry.csv` holds 34 rules with the first time each was recorded and the evidence.

| Timing | Count | Meaning |
|---|---|---|
| PRE | 7 | Recorded before the first trade it governs. |
| UNVERIFIED_PRE | 10 | Directional and gamma rules. The morning routine existed at 16:09Z on 11/11, before the first entry at 17:43Z, but its text at that moment cannot be recovered. The first written copy in git is 20:18Z the same day. Unverified for the one 11/11 trade, PRE for every later trade. |
| AT_ENTRY | 9 | Recorded within minutes of the entry and before any mark (credit arm rules, the real SPY stop 0.18, target 0.75 and time exit, the NVDA time exit). |
| POST | 6 | Set after results were visible: premarket briefing feeding the plan (11/11 evening), Black-Scholes gamma fill (11/12-13), the width test (11/12), the $45/$125 limits relative to the NVDA trade, and the two ledger reporting rules (11/15). |
| OPEN | 1 | C08: the delta rule can pick a SPY strike with no $1 neighbour. Unfixed. |
| DEVIATION | 1 | W02: 5-wide spreads entered at 710/705 with no 1-wide or 3-wide control. |

Ambiguities that leave room for judgement on the day
- G02: two gamma flip methods exist and no rule says which decides check (a).
- D04: the events that count as "major" are not listed. NVDA earnings was treated as market-wide for IWM on 11/16.
- D08: the stop is only checked at the two daily runs, so a stop can fill well past -50%.
- Rejected candidates are logged in prose on some days and not at all on others.

## 2. Results so far (OBSERVED paper fills, worst side of the spread)

| Arm | Closed | Wins | P&L | Per $100 of risk | Open | Open max loss |
|---|---|---|---|---|---|---|
| Directional | 6 | 5 | +$95.12 | +16.03 | 0 | $0 |
| Credit | 0 | 0 | $0 | n/a | 2 | $190.16 |
| Width test (never in totals) | 0 | 0 | $0 | n/a | 4 | $1,654.32 |
| Total (directional + credit) | 6 | 5 | +$95.12 | | | |

- Mid-to-mid P&L cannot be computed for any closed trade: entry mids were not recorded before 2026-11-16. Exit mids for the three 11/16 closes were 1.225, 1.315 and 1.01 against worst-side exits of 1.19, 1.23 and 0.99.
- Every paper position opened so far exceeded the $45 real limit (smallest $79.08). Results are therefore reported per $100 of risk.
- The five wins are all bear put spreads entered on two days (11/12 and 11/13) while SPY fell from about 757 to 745. The one loss is the only bullish trade. This is one market view expressed five times, not five tests.

## 3. Statistical power (ESTIMATED)

Directional arm, per-trade P&L per $100 of risk: -53.1, +56.6, +48.2, +36.6, +26.6, +25.1.
- Treating the six as independent: mean +23.3, standard error 16.1, t = 1.45. Not significant.
- Treating each entry day as one bet (3 bets): mean +9.6, standard error 32.0, t = 0.30.
- Assumed per-trade standard deviation 40 (observed) to 60 (stop and target design).

| Question | sd 40 | sd 60 |
|---|---|---|
| Power to detect a true edge of +10 with 6 trades | 15% | 11% |
| Power with 100 trades | 80% | 51% |
| Trades for 80% power, true edge +10 | 99 | 223 |
| Trades for 80% power, true edge +5 | 396 | 891 |
| Smallest edge detectable with 100 trades | +9.9 | +14.9 |

The 100-trade floor is a minimum. It detects only an edge of roughly +10 to +15 per $100 of risk per trade, and only if the trades are independent.

Credit arm (win $4.92 or lose $95.08, OBSERVED on the SPY entry): breakeven win rate 95.1%.
- Independent trades needed for 80% power: 660 if the true win rate is 97%, 270 if 98%, 130 if 99%.
- With 100 trades the test needs 99 wins to reject breakeven, and has 40% power at a true 98%.
- Both open credit spreads expire 2026-12-04, and the event filter blocks later expiries until after the Dec 9 FOMC and Dec 10 CPI. The arm will end with about two closed trades.

Pace: 6 directional trades closed in 4 sessions on 3 entry days. At that rate 100 closed trades takes about 67 sessions (three months) and 100 independent entry days about 133 sessions (six months). The directional arm is scheduled to stop on 2026-11-24.

## 4. Configurations tried (count)

| Work | Configurations | Label |
|---|---|---|
| Long calls and puts backtest | 1,728 | MODELED |
| Debit spread backtest | 2,380 | MODELED |
| SPY/QQQ credit spread backtest | 6,480, each under 4 IV modes | MODELED |
| 20-ETF credit scan | 43,200 nominal, each under 3 IV modes; 60 picks checked out of sample | MODELED |
| Paper directional | 6 entered; 10 rejected candidates logged (11/11 and 11/16); rejects on 11/12 and 11/13 not logged | OBSERVED |
| Paper credit arm | 4 setups; 12 candidate entries, 2 entered, 8 blocked by the credit floor or wide quotes, 2 by a missing strike | OBSERVED |
| Width test | 2 widths; 4 entered, 2 skipped | OBSERVED |

About 53,800 modeled configurations have been examined. Any later claim of an edge has to be corrected for that count.

## 5. What is missing
- Entry mids for trades opened before 2026-11-16.
- The morning routine's text as it stood before the first trade.
- A complete log of rejected candidates.
- The desk prompt changes are not applied, so the desk does not yet write `ledger_v2.csv`. It is being kept up to date from `log.csv` by the research session.
