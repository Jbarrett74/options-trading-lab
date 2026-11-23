# VRP study "Strategy B" put spread: independent test (2026-11-23)

Read-only research. No orders were placed, changed or cancelled. Option prices are modeled (Black-Scholes), not real fills.
The rules and pass test were pre-registered in PLAN.md, with one amendment written after the first run (A36 and a tight-cost sensitivity).

## Verdict
- (A) Study structure, -0.30/-0.10 delta wing: PASS on the letter of the rule. All 4 IV settings had a positive OOS mean on 120 trades.
  But it is weak evidence. t-stats run 0.3 to 2.9; mean return on max loss is negative at f1.0 (-0.8%).
  A random-direction spread did about as well (f1.2: +$83.76 vs +$83.15). That points to the IV assumption, not the strategy.
- (A36) Fixed 3.6% gap, the study's reported width: FAIL. f1.0 OOS mean -$8.23 (3 of 4 settings positive).
- (B) Account-sized, max loss <= $45: FAIL. 1 of 4 settings positive. Only 32-47 of 120 OOS months could be traded.
  At today's SPY level the 1%-of-leg cost is larger than a $0.50-wide spread's credit. A post-hoc tight-cost run ($0.01 per leg, not scored) still had 2 of 4 settings negative, with means between -$1.38 and +$1.04.

## Data and split
SPY and ^VIX daily from FMP, 1993-01-29 to 2026-11-20. SPY matched the repo file on all 2,376 overlapping days.
403 monthly trades (1993-04 to 2026-10). IS = 283 (to 2016-10). OOS = 120 (2016-11 to 2026-10). 2025+ = 22 (also inside OOS).
Monthly entries reach 30 OOS trades. 2025+ (22) is insufficient data on its own.

## OOS results, base cost (dollars per 1 spread)
| Sizing | IV | Trades | Win % | Mean | Median | Worst | Mean RoR | Max DD | Ruin $440 @ $45 |
|---|---|---|---|---|---|---|---|---|---|
| A | vix | 120 | 85.8 | +92.06 | +271.69 | -2,504.80 | +3.6% | -5,137.79 | 0.0% |
| A | f1.0 | 120 | 82.5 | +16.70 | +193.81 | -2,259.46 | -0.8% | -5,968.79 | 3.0% |
| A | f1.2 | 120 | 83.3 | +83.15 | +241.99 | -2,410.22 | +2.0% | -4,231.11 | 0.5% |
| A | f1.4 | 120 | 85.8 | +157.53 | +287.91 | -2,168.27 | +4.5% | -3,633.73 | 0.1% |
| A36 | vix | 120 | 85.8 | +49.65 | +212.91 | -1,725.26 | +3.5% | -4,725.47 | 0.6% |
| A36 | f1.0 | 120 | 82.5 | -8.23 | +178.94 | -1,817.73 | -1.0% | -6,899.43 | 5.6% |
| A36 | f1.2 | 120 | 83.3 | +27.79 | +193.09 | -1,789.32 | +1.7% | -4,846.40 | 1.9% |
| A36 | f1.4 | 120 | 85.0 | +57.16 | +214.67 | -1,778.70 | +4.0% | -3,506.61 | 0.4% |
| B | vix | 33 | 90.9 | +2.06 | +6.57 | -44.13 | +4.9% | -82.39 | 0.0% |
| B | f1.0 | 47 | 78.7 | -3.42 | +6.56 | -43.88 | -7.8% | -262.19 | 8.0% |
| B | f1.2 | 39 | 76.9 | -4.47 | +7.01 | -44.51 | -10.3% | -247.47 | 9.4% |
| B | f1.4 | 32 | 81.2 | -2.23 | +6.73 | -43.96 | -5.2% | -143.88 | 0.3% |

Max loss per spread, OOS. (A): average $1,715-2,308, up to $8,882. The skewed 10-delta wing averages 4.8-6.4% below the short strike, not 3.6%. (A36): average about $1,290, up to $2,455. (B): $43 average.
Ruin for A and A36 scales each trade to $45 risk. That is fractional and cannot be traded at this account's size.
In-sample (B) ruin was 69-99%, and (A36) at f1.0 was 24%. IS, 2025+, the study's 2013-18 / 2019-24 windows, harsh costs, the Strategy C gate and the random baselines are all in summary.csv.

2025+ (22 trades, insufficient): (A) mean +$200 to +$401, win rate 90.9%, worst about -$1,580 to -$2,190. (B) at base cost: 2 trades only.

## Checks
- Replication: VIX, no skew, the study's 5% cost. 2019-2024 mean +$46, train +$55, gap 3.0-3.8%. This agrees in sign with the study.
- Calibration, one month (2026-10-01 open, real SPY 747/706 puts, trade prints not quotes): real credit $4.16. Model: VIX+skew $5.27, VIX no skew $5.73, f1.0 $2.98, f1.2 $3.91, f1.4 $4.79. VIX pricing overstated the credit by 27-38%. Real fell between f1.2 and f1.4. That is n = 1.
- Gate: Strategy B has no gate, so it is the every-month baseline. Strategy C (+1 vol point gate, for information) raised the OOS mean for (A) under VIX pricing (+$138 vs +$92) but lowered it under all three realized-vol settings.

## Caveats
- Prices are modeled. The result moves with the IV assumption: f1.0 is about zero or negative, f1.4 is positive. The random-direction baseline earns similar money, so most of the "edge" is the assumed IV-over-RV premium.
- Fat left tail. Return skew is -2.0 to -2.7. 10-17 OOS trades lost more than half the max loss. One loss erases about 8-10 wins.
- OOS is 120 monthly trades, about 2-4 independent stress episodes (2018, 2020, 2022, 2025). Dollar means are dominated by recent, higher-priced SPY years.
- Costs: a calm-day calibration. Harsh costs turn A's f1.0 negative (-$3.16). Expiry is assumed to settle at intrinsic with no cost, and SPY is American-style (assignment risk ignored). No dividends in pricing.
- SPY options before 2005 and end-of-month expiries before about 2016 did not exist (SPX proxy). $0.50 SPY strikes are not always listed.
- Multiple testing: 3 sizings x 4 IV settings, plus a post-hoc amendment. The study itself tested many variants.
- Survivorship: SPY/SPX is the market that went up. The OOS decade was a strong bull run, which helps put sellers.
