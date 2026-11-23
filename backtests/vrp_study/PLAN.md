# Pre-registration: independent test of sam-bateman/vrp-harvesting-study "Strategy B" put spread

Written 2026-11-23, before any result was computed. Nothing below is changed after results are seen.
If something has to change (a bug), the change and its reason are added at the bottom under "Amendments".

## Source of the rules
- Study README read on 2026-11-23 from raw.githubusercontent.com (main branch). The repo has no license.
  Code was NOT read or copied; this implementation is written from the README only.
- Rules stated in the README:
  - Monthly SPX puts, short -0.30 delta; the spread variant buys a -0.10 delta wing.
  - Black-Scholes prices with VIX as the 30-day ATM IV proxy (same IV for every strike).
  - Costs: 5% of gross premium round trip on both legs, half at open, half at close.
  - Train 2013-2018, test 2019-2024. No gate on Strategy B. Strategy C adds a gate:
    trade month N+1 only if month N's closing VIX - RV20 >= threshold (train-chosen +1 vol point).
  - The 1987 stress example puts -0.30 delta at K~96.9 and -0.10 delta at K~93.3 for S=100, IV 20%,
    which matches about 30 calendar days (20 trading days) to expiry.

## Data
- SPY daily OHLC (unadjusted) and ^VIX daily close from FMP `/stable/historical-price-eod/full`,
  1993-01-29 to 2026-11-20. The 2026-11-23 bar is dropped (fetched intraday, incomplete).
  FMP SPY matched `backtests/credit_spreads/prices_daily.csv` exactly on all 2,376 overlapping days.
- SPY stands in for SPX/10. SPY options only listed in 2005; earlier SPY trades are an SPX proxy.
- No historical option quotes. All option prices are modeled.

## Assumptions filling gaps in the README (fixed now, not tuned later)
1. Entry: open of the first trading day of each calendar month. Inputs (VIX, RV20) come from the
   prior trading day's close (signal at day t close, entry at t+1 open). Strike chosen from the entry open.
2. Expiry: last trading day of the same calendar month (about 28-30 calendar days, matching the
   README's stress example and its "calendar-month cycles" remark). T = (calendar days + 0.3) / 365.
3. Exit: hold to expiry, settle at intrinsic from the expiry-day close, capped at the width.
   No exit cost at expiry (same convention as backtests/credit_spreads/).
4. Strikes: $1 SPY strikes. Short = strike nearest -0.30 delta. r = 4%, no dividend yield.
5. Skew (all scored settings): the credit_spreads model, iv(K) = base x (1 + 0.25 z) for K < S,
   z = |ln(K/S)| / (base sqrt(T)) clipped at 3. Delta targeting uses the skewed IV.
6. Costs (scored): every leg, entry only (hold to expiry): half-spread max($0.01, 1% of leg mid)
   plus $0.04 per contract. Trades with net credit under $0.03 are skipped (repo convention).

## Structures
- (A) Study structure: long put = $1 strike nearest -0.10 delta (must sit below the short).
  Report the strike gap as % of spot and max loss per spread.
- (B) Account-sized: same short strike. Width $1.00 if max loss (width - net credit) x 100 <= $45,
  else $0.50 if that fits, else no trade. Net credit already includes entry fees.
  Caveat: $0.50 SPY strikes are not listed for every expiry; this is a modeled best case.
- Random-direction baseline (same structure, each sizing): each month a seeded coin flip chooses
  the put spread or the mirror call credit spread (short +0.30 delta call, long +0.10 delta call or
  same width rule). Call skew slope -0.10 (credit_spreads model).
- Gate: Strategy B has no gate, so B itself is the "sell every month" baseline.
  For information only: Strategy C with the study's own +1 vol point gate on prior month-end VIX - RV20.

## IV settings (all reported)
- vix: base IV = VIX/100 (prior close).
- f1.0, f1.2, f1.4: base IV = trailing 20-day close-to-close realized vol x 1.0 / 1.2 / 1.4.
- Not scored, for comparison with the study: vix, no skew, study cost (2.5% of each leg's premium at
  entry and 2.5% of each leg's settlement value at exit), structure (A).
- Sensitivity (not scored): harsh cost max($0.02, 5% of leg) per side.

## Split
- Trades ordered by entry date. First 70% = in-sample (IS), last 30% = out-of-sample (OOS).
- 2025-01 onward reported separately as data the study never saw (it is also part of OOS).
- Only completed trades count (November 2026 expires 2026-11-30, after the data end).
- There is no parameter grid to select: the rule is fixed. "Best IS setting" is reported only to
  show how it did OOS.

## Metrics (per sizing x IV setting x period)
Trades, win rate (P&L > 0), mean, median, worst trade (dollars per 1 spread), mean return on max loss,
max drawdown of cumulative P&L (1 spread), and a bankroll test: 1,000 bootstrap paths (seed 7) of the
period's trades, path length = number of trades, start $440, $45 risk per trade. (A) is scaled to
$45 risk (P&L / max loss x $45, fractional, not tradable at that size). (B) uses 1 spread's actual P&L.
Ruin = equity below $45 (cannot fund the next trade). Report ruin % and median ending equity.

## Pass criteria (per sizing, decided now)
PASS only if OOS mean P&L per trade after costs is > 0 under every one of vix, f1.0, f1.2, f1.4,
AND OOS has at least 30 trades. Otherwise FAIL (or "insufficient data" if under 30 trades).
2025+ is reported but is not a pass condition; under 30 trades it is labeled insufficient data.

## Amendments
(none)

### Amendment 1 (2026-11-23, after the first run; does not change the scored A or B rules)
- Added (A36): long put = short strike minus 3.6% of spot rounded to $1. Reason: the caller's brief defines
  (A) as "strike gap as reported, about 3.6% of spot". Under the skew model, delta-targeting the -0.10 wing
  gives a gap near 6%, not 3.6% (the study's no-skew construction gives 3.6-3.8%, which the replication row
  reproduces). A36 is scored with the same pass rule and reported next to A; neither replaces the other.
- Added a post-hoc, NOT scored, cost sensitivity 'tight': half-spread flat $0.01 per leg plus $0.04 fees.
  Reason: under the scored 1%-of-leg rule, the -0.30 delta put costs about $6 at today's SPY level, so the
  half-spread (about $0.06 per leg) exceeds a $0.50-wide spread's mid credit and (B) skips most recent months.
  Live SPY legs priced $1-$4 were $0.02-$0.04 wide on 2026-11-12; $6 legs were not measured.
- Added stats.csv (t-statistics in dollars and in return on max loss, skew of returns).
