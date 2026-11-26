"""Build the dashboard's data files from the repo ledgers. Run: python3 dashboard/build_data.py"""
import csv, re, json, os
from collections import defaultdict, OrderedDict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dashboard", "data")
os.makedirs(OUT, exist_ok=True)
rows = list(csv.DictReader(open(os.path.join(ROOT, "paper_trading/log.csv"))))

def arm(r):
    s = r["structure"]
    if "SANDBOX" in s: return "sandbox"
    if "WIDTH" in s: return "width_test"
    if "CREDIT" in s or "credit" in s.lower() and "debit" not in s.lower(): return "credit"
    return "directional"

def num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", s or "")
    return float(m.group()) if m else None

# ---- closed trades
opens = [r for r in rows if r["action"] == "open"]
trades = []
for c in [r for r in rows if r["action"] == "close"]:
    a = arm(c)
    if a == "sandbox": continue
    cands = [o for o in opens if o["ticker"] == c["ticker"] and arm(o) == a and o["date"] <= c["date"]
             and o["structure"].split(" exp ")[-1] == c["structure"].split(" exp ")[-1]]
    o = cands[-1] if cands else None
    entry = num(o["price"]) if o else None
    if o and a == "directional": entry = round(entry + 0.0008, 4)
    trades.append(OrderedDict(
        trade_id=f"{a[0].upper()}-{c['ticker']}-{(o or c)['date'].replace('-','')}",
        arm=a, ticker=c["ticker"], side=("bearish" if "put" in c["structure"] and a == "directional" else "bullish" if a == "directional" else "short premium"),
        structure=c["structure"].replace("CREDIT ARM: ", ""), opened=(o or {}).get("date", ""), closed=c["date"],
        entry=entry, exit=num(c["price"]), max_loss=float(c["max_loss"]), pnl=float(c["pnl"]),
        return_on_risk=round(float(c["pnl"]) / float(c["max_loss"]), 4),
        exit_reason=c["reason"].split(":")[0].split(".")[0][:40]))
trades.sort(key=lambda t: t["closed"])
with open(os.path.join(OUT, "trades.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(trades[0].keys())); w.writeheader(); w.writerows(trades)

# ---- daily equity at the conservative (bid/ask) exit
dates = sorted({r["date"] for r in rows})
cons = re.compile(r"([+-]?\d+(?:\.\d+)?) conservative")
eq = []
for d in dates:
    last = {}
    for r in rows:
        if r["date"] == d and r["action"] == "mark" and arm(r) in ("directional", "credit"):
            m = cons.search(r["pnl"])
            if m: last[(r["ticker"], r["structure"])] = (arm(r), float(m.group(1)))
    closed_today = {(t["ticker"], t["arm"]) for t in trades if t["closed"] == d}
    open_dir = sum(v for (k, (a, v)) in last.items() if a == "directional")
    open_cr = sum(v for (k, (a, v)) in last.items() if a == "credit" and (k[0], "credit") not in closed_today)
    real_dir = sum(t["pnl"] for t in trades if t["arm"] == "directional" and t["closed"] <= d)
    real_cr = sum(t["pnl"] for t in trades if t["arm"] == "credit" and t["closed"] <= d)
    if not last and not any(t["closed"] == d for t in trades): continue
    eq.append(OrderedDict(date=d, directional_realized=round(real_dir, 2), directional_open=round(open_dir, 2),
                          credit_realized=round(real_cr, 2), credit_open=round(open_cr, 2),
                          total=round(real_dir + open_dir + real_cr + open_cr, 2)))
with open(os.path.join(OUT, "equity.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(eq[0].keys())); w.writeheader(); w.writerows(eq)

# ---- width test, P&L per $100 of max loss at mid, last mark of each day
per100 = re.compile(r"([+-]?\d+(?:\.\d+)?) per \$100 risk at mid")
wt = OrderedDict()
for r in rows:
    if r["action"] != "mark": continue
    a = arm(r); s = r["structure"]
    if a not in ("width_test", "credit") or r["ticker"] != "SPY": continue
    m = per100.search(r["reason"])
    if not m: continue
    if a == "credit": label = "1-wide 732/731"
    elif "3 wide" in s: label = "3-wide 732/729"
    elif "732/727" in s: label = "5-wide 732/727"
    elif "11/13" in s: label = "5-wide 710/705 (11/13)"
    elif "11/16" in s: label = "5-wide 710/705 (11/16)"
    else: continue
    wt[(r["date"], label)] = float(m.group(1))
with open(os.path.join(OUT, "width_test.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "spread", "pnl_per_100_risk_mid"])
    for (d, l), v in wt.items(): w.writerow([d, l, v])

# ---- gamma map (latest ALT run)
spots = {"SPY": 706.32, "QQQ": 628.00, "IWM": 262.39}  # premarket spot used by the 2026-11-23 run
with open(os.path.join(OUT, "gamma.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["ticker", "spot", "expiry", "type", "strike", "open_interest", "gex_alt", "gex_rh"])
    for t in spots:
        for r in csv.DictReader(open(os.path.join(ROOT, f"paper_trading/gex/gex_{t}_2026-11-23.csv"))):
            g = r.get("gex_alt") or ""
            if g == "": continue
            w.writerow([t, spots[t], r["expiry"], r["type"], r["strike"], r["open_interest"], g, r.get("gex_rh") or ""])
# ---- real account: closed trades from STATUS.md / real_trades.csv, open NVDA mark from the latest real_check
real_closed = [
    ["KKR", "105 call", "2026-11 (date not found)", "2026-11 (date not found)", "closed", "65.00", "not found", "STATUS.md"],
    ["RGTI", "10.5 put", "2026-11 (date not found)", "2026-11 (date not found)", "closed", "35.00", "not found", "STATUS.md"],
    ["NU", "12.5 call x2", "2026-11 (date not found)", "2026-11 (date not found)", "closed", "-14.00", "not found", "STATUS.md (sold by the agent without the user's approval)"],
    ["SPY", "760/759 put debit spread", "2026-11-12", "2026-11-16", "closed", "43.84", "37.08", "paper_trading/real_trades.csv"],
]
nv = [r for r in rows if r["action"] == "real_check" and r["ticker"] == "NVDA"]
with open(os.path.join(OUT, "real_trades.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["symbol", "structure", "opened", "closed", "status", "pnl", "max_loss", "source"])
    w.writerows(real_closed)
    if nv:
        last = nv[-1]; m = cons.search(last["pnl"])
        status = "closed" if "closed" in last["reason"].lower() and "still open" not in last["reason"].lower() else "open"
        w.writerow(["NVDA", "170/172 call debit spread exp 2026-12-18", "2026-11-12", "", status,
                    f"{float(m.group(1)):.2f}" if m else "not found", last["max_loss"],
                    f"paper_trading/log.csv real_check {last['date']} ({last['price']})"])
print(len(trades), "trades;", len(eq), "equity days;", len(wt), "width points")
