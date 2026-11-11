import csv,sys
import numpy as np
from math import log,sqrt,exp,pi
S=282.915
rows=list(csv.DictReader(open(sys.argv[1])))
def g(r): return float(r['gamma']) if r['gamma'] else None
tot=0; by={}; byexp={}; missing=[]
for r in rows:
    gm=g(r)
    if gm is None: missing.append((r['expiry'],r['type'],r['strike'],r['open_interest'])); continue
    v=gm*int(r['open_interest'])*100*S*S*0.01*(1 if r['type']=='call' else -1)
    tot+=v; by.setdefault((r['type'],float(r['strike'])),0); by[(r['type'],float(r['strike']))]+=v
    byexp[r['expiry']]=byexp.get(r['expiry'],0)+v
print("net GEX",round(tot))
print("by expiry",{k:round(v) for k,v in byexp.items()})
gross={}
for r in rows:
    gm=g(r)
    if gm is None: continue
    gross[r['expiry']]=gross.get(r['expiry'],0)+abs(gm*int(r['open_interest'])*100*S*S*0.01)
print("gross by expiry",{k:round(v) for k,v in gross.items()}, "0DTE share gross",gross['2026-11-11']/sum(gross.values()))
calls=sorted([(v,k[1]) for k,v in by.items() if k[0]=='call'],reverse=True)[:3]
puts=sorted([(v,k[1]) for k,v in by.items() if k[0]=='put'])[:3]
print("call walls",[(k,round(v)) for v,k in calls]); print("put walls",[(k,round(v)) for v,k in puts])
# net by strike
ns={}
for (t,k),v in by.items(): ns[k]=ns.get(k,0)+v
cum=0
for k in sorted(ns): print(k,round(ns[k]))
# zero gamma: recompute BS gamma across spot grid using iv, T
from scipy.stats import norm
T={'2026-11-11':(4.5/6.5)/252,'2026-11-12':(1+4.5/6.5)/252}
def bsg(s,K,iv,t):
    d1=(log(s/K)+0.5*iv*iv*t)/(iv*sqrt(t)); return norm.pdf(d1)/(s*iv*sqrt(t))
prev=None
for s in np.arange(276,290.01,0.05):
    net=0
    for r in rows:
        if not r['iv']: continue
        gm=bsg(s,float(r['strike']),float(r['iv']),T[r['expiry']])
        net+=gm*int(r['open_interest'])*100*s*s*0.01*(1 if r['type']=='call' else -1)
    if prev is not None and np.sign(net)!=np.sign(prev[1]): print("flip between",round(prev[0],2),round(s,2))
    prev=(s,net)
print("missing",missing)
