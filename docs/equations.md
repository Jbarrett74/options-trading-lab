# Equations

Every formula here is implemented in `quant/formulas.py` and checked by `quant/test_formulas.py`. Notation: S spot, K strike, T years to expiry, r risk-free rate, q dividend yield, sigma volatility (annual decimals), N() standard normal CDF, n() its density.

## 1. Black-Scholes price

d1 = [ln(S/K) + (r - q + sigma^2/2) T] / (sigma sqrt(T)),  d2 = d1 - sigma sqrt(T)

Call = S e^(-qT) N(d1) - K e^(-rT) N(d2)
Put = K e^(-rT) N(-d2) - S e^(-qT) N(-d1)

Checked against Hull's textbook example (S 42, K 40, r 10%, sigma 20%, T 0.5 gives call 4.76, put 0.81). Black-Scholes prices European options with constant volatility. US equity options are American, and real IV varies by strike (skew).

## 2. Greeks

- Delta: call e^(-qT) N(d1), put e^(-qT) (N(d1) - 1)
- Gamma: e^(-qT) n(d1) / (S sigma sqrt(T))
- Vega per 1 vol point: S e^(-qT) n(d1) sqrt(T) / 100
- Theta per calendar day: call [-S e^(-qT) n(d1) sigma / (2 sqrt(T)) - r K e^(-rT) N(d2) + q S e^(-qT) N(d1)] / 365

Delta and gamma are checked against finite differences in the tests.

## 3. Put-call parity

C - P = S e^(-qT) - K e^(-rT) for European options. A large gap in real quotes points to stale data, dividends, or early-exercise value.

## 4. Implied volatility

The sigma that makes the Black-Scholes price equal the market mid. Solved by bisection.

## 5. Probability of finishing in the money

P(S_T > K) = N(d2) under risk-neutral pricing. This is not the real-world probability: it ignores the equity risk premium and skew. N(d1) is the delta, not the in-the-money probability. ([Moontower](https://moontowermeta.com/a-deeper-understanding-of-vertical-spreads/), [Option Alpha](https://docs.optionalpha.com/calculations/probability))

## 6. Expected move

Expected move (1 sd) = S x IV x sqrt(days / 365)

Rule of thumb: ATM straddle x 0.85 is about the same. The straddle prices the average absolute move, which is about 0.8 of a standard deviation for a normal distribution. ([FlashAlpha](https://flashalpha.com/concepts/expected-move), [LuxAlgo](https://www.luxalgo.com/library/concept/expected-move.md))

## 7. Realized volatility

- Close-to-close: sample stdev of ln(C_t / C_(t-1)) x sqrt(252)
- Parkinson (high/low only): var = sum[ln(H/L)^2] / (4 n ln 2)
- Garman-Klass: var = mean[0.5 ln(H/L)^2 - (2 ln 2 - 1) ln(C/O)^2]
- Yang-Zhang: var = var(overnight) + k var(open-to-close) + (1 - k) mean(Rogers-Satchell), k = 0.34 / (1.34 + (n+1)/(n-1)). Handles overnight gaps and drift.

Range-based estimators are more efficient than close-to-close but assume no gaps (Parkinson, Garman-Klass). Yang-Zhang is noisy on short windows. ([TTR docs](https://www.rdocumentation.org/packages/TTR/versions/0.24.2/topics/volatility), [LuxAlgo](https://www.luxalgo.com/library/concept/volatility-estimators/), [FlashAlpha](https://flashalpha.com/articles/yang-zhang-vs-close-to-close-realized-volatility))

## 8. Debit vertical spread

For a call debit spread, long K1 and short K2 > K1, debit D per share including fees:
- Max loss = D
- Max gain = (K2 - K1) - D
- Breakeven = K1 + D (put spread: K1 - D, with K1 the higher strike)
- Reward/risk = max gain / max loss

Risk-neutral probabilities (Black-Scholes): P(max profit) = N(d2 at K2), P(profit) = N(d2 at breakeven), P(max loss) = 1 - N(d2 at K1). Put spreads use the mirror. These follow directly from section 5. One search result noted the price of a 1-wide spread divided by its width approximates the probability of finishing past the midpoint. ([Moontower](https://moontowermeta.com/a-deeper-understanding-of-vertical-spreads/))

Conservative fill used in the paper test: debit = long leg ask - short leg bid.

## 9. Expected value per trade

EV = p_win x average win - (1 - p_win) x average loss. A positive EV estimate from a small sample is weak evidence.

## 10. Gamma exposure (GEX)

GEX per contract = sign x gamma x open interest x 100 x S^2 x 0.01, in dollars per 1% move. Calls count +1 and puts -1 under the standard assumption that dealers are long calls and short puts. Open interest does not show who owns each side, so the sign is a model assumption. ([SpotGamma](https://spotgamma.com/gamma-exposure-gex/), [FlashAlpha worked example](https://flashalpha.com/articles/how-to-calculate-gamma-exposure-gex-formula-worked-example))

Zero-gamma flip, two methods that give different numbers:
- Strike-cumulative: the level where cumulative net GEX across strikes changes sign. This is what `zero_gamma_flip` uses.
- Spot sweep: recompute every contract's gamma with Black-Scholes at hypothetical spot prices and find where total GEX crosses zero (SpotGamma style).

Some free sources write GEX with S instead of S^2. The S^2 x 0.01 form is the one that gives dollars per 1% move.

## 11. Position sizing and ruin

- Fixed fractional: contracts = floor(account x risk % / max loss per contract)
- Kelly for a bet that loses the stake or wins b times it: f* = p - (1 - p) / b. With an estimated edge, use half Kelly or less, because over-estimating p makes full Kelly over-bet. ([Kelly criterion overview](https://cavac.at/cavacopedia/Kelly_criterion), [LuxAlgo](https://www.luxalgo.com/library/concept/kelly-criterion.md))
- Losing streak: probability of at least one run of L losses in n trades, computed exactly by dynamic programming in `losing_streak_prob`. With p_loss = 0.7, the chance of at least one run of 3 losses in 20 trades is 98.6%.

## What is not here

Skew-aware pricing (local or stochastic volatility), American early exercise (binomial trees), and transaction-cost models from real fill data. Those would be the next additions if the paper test finds something worth refining.
