"""Convert the real Robinhood option-historicals JSON dumps (get_option_historicals) into a CSV
and compare real close prices with Black-Scholes using trailing 20d realized vol (implied/realized ratio)."""
import json, sys, numpy as np, pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
files = sys.argv[1:]
rows = []
for f in files:
    d = json.load(open(f))
    for x in d['data']['results']:
        occ = x['occ_symbol']; und = occ[:6].strip(); exp = '20'+occ[6:8]+'-'+occ[8:10]+'-'+occ[10:12]
        typ = 'call' if occ[12]=='C' else 'put'; K = int(occ[13:])/1000
        for b in x['bars']:
            rows.append(dict(occ=occ, underlying=und, expiration=exp, type=typ, strike=K, date=b['begins_at'][:10],
                             open=float(b['open_price']), high=float(b['high_price']), low=float(b['low_price']),
                             close=float(b['close_price']), interpolated=b.get('interpolated', False)))
opt = pd.DataFrame(rows); opt.to_csv('real_option_sample.csv', index=False)
px = pd.read_csv('raw_prices_daily.csv')
px['ret'] = px.groupby('symbol').close.transform(lambda s: np.log(s).diff())
px['rv20'] = px.groupby('symbol').ret.transform(lambda s: s.rolling(20).std()*np.sqrt(252))
m = opt[~opt.interpolated].merge(px[['symbol','date','close','rv20']].rename(columns={'symbol':'underlying','close':'S'}), on=['underlying','date'])
def bs(S,K,T,r,v,typ):
    if T<=0 or v<=0: return max(S-K,0) if typ=='call' else max(K-S,0)
    d1=(np.log(S/K)+(r+v*v/2)*T)/(v*np.sqrt(T)); d2=d1-v*np.sqrt(T)
    return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2) if typ=='call' else K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)
out=[]
for _,r in m.iterrows():
    T=(pd.Timestamp(r.expiration)-pd.Timestamp(r.date)).days/365
    if T<2/365: continue
    intr = max(r.S-r.strike,0) if r.type=='call' else max(r.strike-r.S,0)
    iv=np.nan
    if r.close>intr+0.01:
        try: iv=brentq(lambda v: bs(r.S,r.strike,T,0.04,v,r.type)-r.close,1e-3,5)
        except ValueError: pass
    out.append(dict(**r, T_days=round(T*365), bs_rv=bs(r.S,r.strike,T,0.04,r.rv20,r.type), iv=iv))
o=pd.DataFrame(out); o['iv_over_rv']=o.iv/o.rv20
o.to_csv('real_vs_bs_comparison.csv',index=False)
print('contracts:',opt.occ.nunique(),'real bars:',(~opt.interpolated).sum(),'interp bars:',opt.interpolated.sum())
print(o.groupby('underlying').iv_over_rv.describe()[['count','25%','50%','75%']])
print('overall median IV/RV:',o.iv_over_rv.median())
w=o[(o.T_days<=10)&(o.close<=2)]
print('short-dated cheap rows median IV/RV:',w.iv_over_rv.median(),len(w))
