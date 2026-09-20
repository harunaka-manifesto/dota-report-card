"""Final V1 form: CS-based, OPPONENTS ONLY. Band stability + effect size."""
import pickle, collections, statistics as st, random

ROWS=[r for r in pickle.load(open('metrics.pkl','rb'))
      if r['bucket']=='STANDARD' and r['shape'] in ('2v2','1v1')
      and r.get('last_hits_at_10') is not None]

def fit(d,tgt='last_hits_at_10',k=40.,iters=6):
    ys=[r[tgt] for r in d]; g=sum(ys)/len(ys); own={}; opp={}
    for _ in range(iters):
        b=lambda r: g+own.get(r['hero'],0.)+sum(opp.get(h,0.) for h in r['opps'])
        s=collections.defaultdict(float); c=collections.Counter()
        for r in d: s[r['hero']]+=r[tgt]-(b(r)-own.get(r['hero'],0.)); c[r['hero']]+=1
        own={h:s[h]/(c[h]+k) for h in c}
        s=collections.defaultdict(float); c=collections.Counter()
        for r in d:
            for h in r['opps']: s[h]+=r[tgt]-(b(r)-opp.get(h,0.)); c[h]+=1
        opp={h:s[h]/(c[h]+k) for h in c}
    return g,own,opp

print("FINAL V1 CANDIDATE — CS@10 score, opponents only, STANDARD")
for role in ('Carry','Mid','Offlane','Support'):
    d=[r for r in ROWS if r['role']==role]
    if len(d)<3000: continue
    rnd=random.Random(17); p=list(d); rnd.shuffle(p); h=len(p)//2
    _,_,o1=fit(p[:h]); _,_,o2=fit(p[h:]); gf,ownf,of=fit(d)
    S=lambda m,r: sum(m.get(x,0.) for x in r['opps'])
    s1=[S(o1,r) for r in d]; s2=[S(o2,r) for r in d]; sf=[S(of,r) for r in d]
    mx,my=st.fmean(s1),st.fmean(s2)
    cv=st.fmean([(a-b_)*(c-my) for a,b_,c in zip(s1,[mx]*len(s1),s2)])
    rr=cv/(st.pstdev(s1)*st.pstdev(s2))
    print(f"\n  {role}: n={len(d)}  half-sample score corr={rr:+.3f} (Spearman-Brown full={2*rr/(1+rr):+.3f})")
    for band in (0.25,0.20,0.15):
        cut=lambda s:(sorted(s)[int(band*(len(s)-1))], sorted(s)[int((1-band)*(len(s)-1))])
        l1,h1=cut(s1); l2,h2=cut(s2); lf,hf=cut(sf)
        B=lambda v,l,hh: 0 if v<=l else (2 if v>=hh else 1)
        b1=[B(v,l1,h1) for v in s1]; b2=[B(v,l2,h2) for v in s2]
        ag=sum(1 for a,b_ in zip(b1,b2) if a==b_)/len(b1)
        fl=sum(1 for a,b_ in zip(b1,b2) if abs(a-b_)==2)/len(b1)
        g=collections.defaultdict(list)
        for r,v in zip(d,sf): g[B(v,lf,hf)].append(r)
        mn=lambda i,f: st.fmean(f(x) for x in g[i])
        print(f"    band {band:.2f}: thresholds {lf:+.2f}/{hf:+.2f}  agree={100*ag:5.1f}% extreme-flip={100*fl:4.2f}% | "
              f"cs10 D/T/F = {mn(0,lambda x:x['last_hits_at_10']):.1f}/{mn(1,lambda x:x['last_hits_at_10']):.1f}/"
              f"{mn(2,lambda x:x['last_hits_at_10']):.1f} (gap {mn(2,lambda x:x['last_hits_at_10'])-mn(0,lambda x:x['last_hits_at_10']):+.1f}) | "
              f"nw10 gap {mn(2,lambda x:x['net_worth_at_10'])-mn(0,lambda x:x['net_worth_at_10']):+.0f} | "
              f"winrate {mn(0,lambda x:1 if x['win'] else 0):.3f}/{mn(2,lambda x:1 if x['win'] else 0):.3f}")
