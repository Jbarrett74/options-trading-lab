"""Sample-size and power arithmetic for the forward test. All inputs are per-trade P&L per $100 of risk.
One-sided test of mean > 0 with a normal approximation, and an exact binomial test for win-rate strategies."""
import math
from statistics import NormalDist
N = NormalDist()

def power(n, edge, sd, alpha=0.05):
    """P(reject mean <= 0) when the true mean is `edge` and the per-trade sd is `sd`."""
    return 1 - N.cdf(N.inv_cdf(1 - alpha) - edge * math.sqrt(n) / sd)

def n_required(edge, sd, alpha=0.05, target=0.80):
    return math.ceil(((N.inv_cdf(1 - alpha) + N.inv_cdf(target)) * sd / edge) ** 2)

def min_detectable_edge(n, sd, alpha=0.05, target=0.80):
    return (N.inv_cdf(1 - alpha) + N.inv_cdf(target)) * sd / math.sqrt(n)

def breakeven_win_rate(credit, max_loss):
    """Hold-to-expiry credit spread that wins `credit` or loses `max_loss`."""
    return max_loss / (max_loss + credit)

def binom_sf(k, n, p):
    """P(X >= k), X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))

def binom_power(n, p0, p1, alpha=0.05):
    """Exact one-sided test of win rate > p0: critical count and power at true win rate p1."""
    k = next((k for k in range(n + 2) if binom_sf(k, n, p0) <= alpha), n + 1)
    return k, (binom_sf(k, n, p1) if k <= n else 0.0)

def binom_n_required(p0, p1, alpha=0.05, target=0.80, n_max=5000):
    for n in range(10, n_max, 10):
        if binom_power(n, p0, p1, alpha)[1] >= target: return n
    return None

def cluster_stats(values, clusters):
    """Mean, standard error and t using one average per cluster (trades entered together are one bet)."""
    groups = {}
    for v, c in zip(values, clusters): groups.setdefault(c, []).append(v)
    m = [sum(g) / len(g) for g in groups.values()]; k = len(m); mean = sum(m) / k
    sd = math.sqrt(sum((x - mean) ** 2 for x in m) / (k - 1)) if k > 1 else float('nan')
    se = sd / math.sqrt(k) if k > 1 else float('nan')
    return {'clusters': k, 'mean': mean, 'sd': sd, 'se': se, 't': mean / se if k > 1 and se > 0 else float('nan')}
