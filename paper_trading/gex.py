import csv,sys
D=sys.argv[1]; S=757.655
rows=[]
for l in open(D+'/rows.txt'):
    e,t,k,g,oi,b,a,iv,u=l.strip().split(',')
    rows.append(dict(expiry=e,type=t,strike=float(k),gamma=float(g) if g else None,open_interest=int(oi),bid=float(b),ask=float(a),iv=float(iv) if iv else None,updated_at=u))
with open(D+'/gex_2026-11-11.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['expiry','type','strike','gamma','open_interest','bid','ask','iv','updated_at','gex'])
    w.writeheader()
    for r in rows:
        r['gex']= 0.0 if r['gamma'] is None else r['gamma']*r['open_interest']*100*S*S*0.01*(1 if r['type']=='call' else -1)
        w.writerow(r)
print('rows',len(rows),'missing gamma',[(r['expiry'],r['type'],r['strike']) for r in rows if r['gamma'] is None])
per={}; perexp={}
for r in rows:
    per[r['strike']]=per.get(r['strike'],0)+r['gex']
    perexp[(r['expiry'],r['type'])]=perexp.get((r['expiry'],r['type']),0)+r['gex']
tot=sum(per.values())
print('total %.0f'%tot)
for k,v in sorted(perexp.items()): print(k,'%.0f'%v)
for e in ['2026-11-11','2026-11-12']: print(e,'%.0f'%sum(v for (x,t),v in perexp.items() if x==e))
s=sorted(per.items(),key=lambda x:x[1])
print('top+',[(k,round(v)) for k,v in s[::-1][:3]])
print('top-',[(k,round(v)) for k,v in s[:3]])
c=0;prev=None
for k in sorted(per):
    c+=per[k]
    if prev is not None and (prev<0)!=(c<0): print('flip between',kp,k,'cum %.0f -> %.0f'%(prev,c))
    prev=c;kp=k
for k in sorted(per): print(int(k),'%.0f'%per[k])
