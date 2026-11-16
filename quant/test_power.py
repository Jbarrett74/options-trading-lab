import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import power as P

def test_power_and_n_agree():
    n = P.n_required(10, 60); assert 0.80 <= P.power(n, 10, 60) < 0.81
    assert P.power(1, 0.0001, 60) < 0.051                       # no edge: power equals alpha
    assert abs(P.min_detectable_edge(n, 60) - 10) < 0.05

def test_breakeven_and_binomial():
    assert abs(P.breakeven_win_rate(4.92, 95.08) - 0.9508) < 1e-4
    assert abs(P.binom_sf(0, 20, 0.3) - 1) < 1e-12 and abs(P.binom_sf(20, 20, 0.5) - 0.5 ** 20) < 1e-15
    k, pw = P.binom_power(20, 0.5, 0.5); assert pw <= 0.05      # size is controlled
    assert P.binom_power(10, 0.95, 0.97)[0] == 11               # 10 wins in 10 cannot reject a 95% breakeven

def test_cluster_stats():
    s = P.cluster_stats([1, 3, 10, 10, 10], ['a', 'a', 'b', 'b', 'b']); assert s['clusters'] == 2 and s['mean'] == 6
    assert abs(s['se'] - math.sqrt(32) / math.sqrt(2)) < 1e-9

if __name__ == '__main__':
    for n, f in sorted(globals().items()):
        if n.startswith('test_'): f(); print('ok', n)
