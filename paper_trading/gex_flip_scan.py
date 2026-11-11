import csv, math
S=694.52
closes=[729.87,717.51,716.08,710.93,713.44,706.32,710.72,711.37,721.11,716.43,716.76,707.64,709.24,717.67,718.96,718.36,716.31,708.69,714.88,709.18,704.54,704.72,716.92,721.45,741.47,747.46,741.21,741.10,744.50,736.53,737.93,739.77,742.03,749.58,756.20,759.66,757.73,747.58,751.27,746.04,743.57,728.95,728.00,709.80,718.36,717.63,725.20,704.47,704.40,712.20,721.25,725.61,715.34,690.49,681.09,685.28,691.95,647.05,656.10,679.35,674.76]
print("bars",len(closes),"SMA20",sum(closes[-20:])/20,"SMA50",sum(closes[-50:])/50)
rows=list(csv.DictReader(open('spy_paper/gex_QQQ_2026-11-11.csv')))
print("rows",len(rows))
miss=[r for r in rows if r['gamma'] in ('',None)]
print("missing gamma",len(miss))
for r in rows:
    g=float(r['gamma']);oi=int(r['open_interest'])
    sgn=1 if r['type']=='call' else -1
    r['gex']=sgn*g*oi*100*S*S*0.01
tot=sum(r['gex'] for r in rows)
d0=sum(r['gex'] for r in rows if r['expiry']=='2026-11-11')
print("net",tot,"0dte",d0,"1dte",tot-d0)
gabs=sum(abs(r['gex']) for r in rows); g0=sum(abs(r['gex']) for r in rows if r['expiry']=='2026-11-11')
print("0dte share of net",d0/tot,"of gross",g0/gabs)
print("call gex",sum(r['gex'] for r in rows if r['type']=='call'),"put gex",sum(r['gex'] for r in rows if r['type']=='put'))
by={}
for r in rows:
    k=(r['type'],float(r['strike'])); by[k]=by.get(k,0)+r['gex']
calls=sorted([(v,k[1]) for k,v in by.items() if k[0]=='call'],reverse=True)[:3]
puts=sorted([(v,k[1]) for k,v in by.items() if k[0]=='put'])[:3]
print("call walls",calls);print("put walls",puts)
net={}
for (t,k),v in by.items(): net[k]=net.get(k,0)+v
print("net by strike",sorted(net.items()))
# flip: BS gamma recomputed at hypothetical spot
def bsg(s,k,iv,T):
    d1=(math.log(s/k)+0.5*iv*iv*T)/(iv*math.sqrt(T))
    return math.exp(-d1*d1/2)/math.sqrt(2*math.pi)/(s*iv*math.sqrt(T))
Tm={'2026-11-11':3.25/24/365,'2026-11-12':27.25/24/365}
def G(s):
    t=0
    for r in rows:
        sg=1 if r['type']=='call' else -1
        t+=sg*bsg(s,float(r['strike']),float(r['iv']),Tm[r['expiry']])*int(r['open_interest'])*100*s*s*0.01
    return t
print("model G at spot",G(S))
prev=None
for i in range(0,3001):
    s=675+i*0.01
    v=G(s)
    if prev is not None and (prev<0)!=(v<0): print("flip",round(s,2))
    prev=v
for s in [680,685,688,690,692,694.52,697,700,705,708]: print(s,round(G(s)/1e6,1))
