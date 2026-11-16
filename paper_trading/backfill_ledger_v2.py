"""One-off backfill of ledger_v2.csv from the open and close rows of log.csv (11 opens, 3 closes, 2026-11-11 to 11-13).
Values are copied by hand from log.csv; the log.csv line number is in `source`. Marks, skips and no_trade rows
are not backfilled: they stay in log.csv. price_mid is blank where the run did not record a mid."""
import ledger
R = 'backfill_2026-11-15'
def o(line, ts, tid, arm, tk, struct, side, exp, legs, pw, pm, fees, ml, mg, px, notes=''):
    return dict(run_id=R, ts_et=ts, trade_id=tid, arm=arm, ticker=tk, action='open', structure=struct, side=side, expiry=exp, legs=legs, qty=1,
                price_worst=pw, price_mid=pm, fees_usd=fees, max_loss_usd=ml, max_gain_usd=mg, underlying_px=px, rule_set='pre-registry', notes=notes, source=f'log.csv:{line}')
def c(line, ts, tid, arm, tk, legs, pw, pnl, px, notes):
    return dict(run_id=R, ts_et=ts, trade_id=tid, arm=arm, ticker=tk, action='close', legs=legs, qty=1, price_worst=pw, fees_usd=0.08, pnl_worst_usd=pnl,
                underlying_px=px, rule_set='pre-registry', notes=notes, source=f'log.csv:{line}')
ROWS = [
 o(5, '2026-11-11 12:43', 'D-IWM-20261111-1', 'directional', 'IWM', 'bull call debit spread 284/287', 'debit', '2026-11-20', 'buy 284C @3.03 ask / sell 287C @1.64 bid', 1.39, '', 8.00, 147.00, 153.00, 283.51, 'fees logged as $0.08 per share on this row only; later rows use $0.08 per spread'),
 c(7, '2026-11-12 10:11', 'D-IWM-20261111-1', 'directional', 'IWM', 'sell 284C @1.29 bid / buy 287C @0.60 ask', 0.69, -78.08, 279.60, 'stop at -50% of debit'),
 o(8, '2026-11-12 10:11', 'D-SPY-20261112-1', 'directional', 'SPY', 'bear put debit spread 758/756', 'debit', '2026-11-16', 'buy 758P @4.86 ask / sell 756P @3.98 bid', 0.88, '', 0.08, 88.08, 111.92, 756.17),
 o(9, '2026-11-12 10:11', 'D-QQQ-20261112-1', 'directional', 'QQQ', 'bear put debit spread 686/684', 'debit', '2026-11-16', 'buy 686P @7.50 ask / sell 684P @6.55 bid', 0.95, '', 0.08, 95.08, 104.92, 684.07),
 o(10, '2026-11-12 11:23', 'C-SPY-20261112-1', 'credit', 'SPY', 'put credit spread 732/731', 'credit', '2026-12-04', 'sell 732P @2.67 bid / buy 731P @2.62 ask', 0.05, 0.09, 0.08, 95.08, 4.92, 762.54, 'mid from credit_arm/credit_entries_2026-11-12.csv'),
 o(14, '2026-11-12 11:47', 'W-SPY-20261112-3w', 'width_test', 'SPY', 'put credit spread 732/729', 'credit', '2026-12-04', 'sell 732P @2.98 bid / buy 729P @2.72 ask', 0.26, 0.295, 0.08, 274.08, 25.92, 760.59),
 o(15, '2026-11-12 11:47', 'W-SPY-20261112-5w', 'width_test', 'SPY', 'put credit spread 732/727', 'credit', '2026-12-04', 'sell 732P @2.98 bid / buy 727P @2.54 ask', 0.44, 0.475, 0.08, 456.08, 43.92, 760.59),
 c(21, '2026-11-13 10:35', 'D-SPY-20261112-1', 'directional', 'SPY', 'sell 758P @8.40 bid / buy 756P @7.02 ask', 1.38, 49.84, 750.85, 'time exit: close by 1:15pm the day before expiry'),
 c(22, '2026-11-13 10:35', 'D-QQQ-20261112-1', 'directional', 'QQQ', 'sell 686P @13.19 bid / buy 684P @11.78 ask', 1.41, 45.84, 674.60, 'time exit: close by 1:15pm the day before expiry'),
 o(28, '2026-11-13 10:36', 'W-SPY-20261113-5w', 'width_test', 'SPY', 'put credit spread 710/705', 'credit', '2026-12-04', 'sell 710P @2.91 bid / buy 705P @2.57 ask', 0.34, 0.38, 0.08, 466.08, 33.92, 749.9),
 o(31, '2026-11-13', 'C-XLE-20261113-1', 'credit', 'XLE', 'call credit spread 70/71', 'credit', '2026-12-04', 'sell 70C @0.18 bid / buy 71C @0.13 ask', 0.05, 0.07, 0.08, 95.08, 4.92, '', 'entry time not logged; exit rule: close when cost to close <= 50% of credit'),
 o(32, '2026-11-13 10:44', 'D-SPY-20261113-1', 'directional', 'SPY', 'bear put debit spread 750/748', 'debit', '2026-11-17', 'buy 750P @5.38 ask / sell 748P @4.51 bid', 0.87, '', 0.08, 87.08, 112.92, 749.55),
 o(33, '2026-11-13 10:44', 'D-QQQ-20261113-1', 'directional', 'QQQ', 'bear put debit spread 674/672', 'debit', '2026-11-17', 'buy 674P @8.42 ask / sell 672P @7.45 bid', 0.97, '', 0.08, 97.08, 102.92, 673.27),
 o(34, '2026-11-13 10:44', 'D-IWM-20261113-1', 'directional', 'IWM', 'bear put debit spread 276/274', 'debit', '2026-11-17', 'buy 276P @2.18 ask / sell 274P @1.39 bid', 0.79, '', 0.08, 79.08, 120.92, 275.82),
]
if __name__ == '__main__':
    for r in ROWS: print('added' if ledger.add(r) else 'duplicate', r['trade_id'], r['action'])
