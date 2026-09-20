"""PART 6 — if one CS-based label drives the badge, how often do the per-metric
adjustments visibly contradict it?"""
import pickle, collections, statistics as st, random

ROWS=[r for r in pickle.load(open('metrics.pkl','rb'))
      if r['bucket']=='STANDARD' and r['shape'] in ('2v2','1v1')
      and r['role'] in ('Carry','Mid','Offlane')]

def fit_opp(train,tgt,k=40.0,iters=6):
    ys=[r[tgt] for r in train]; g=sum(ys)/len(ys); own={}; opp={}
    for _ in range(iters):
        b=lambda r: g+own.get(r['hero'],0.)+sum(opp.get(h,0.) for h in r['opps'])
        s=collections.defaultdict(float); c=collections.Counter()
        for r in train: s[r['hero']]+=r[tgt]-(b(r)-own.get(r['hero'],0.)); c[r['hero']]+=1
        own={h:s[h]/(c[h]+k) for h in c}
        s=collections.defaultdict(float); c=collections.Counter()
        for r in train:
            for h in r['opps']: s[h]+=r[tgt]-(b(r)-opp.get(h,0.)); c[h]+=1
        opp={h:s[h]/(c[h]+k) for h in c}
    return own,opp,g

TG=['last_hits_at_10','net_worth_at_10','level_6_time','deaths_before_10']
for role in ('Carry','Mid','Offlane'):
    d=[r for r in ROWS if r['role']==role and all(r.get(t) is not None for t in TG)]
    if len(d)<3000: continue
    E={}; SD={}
    for t in TG:
        _,opp,_=fit_opp(d,t)
        E[t]=[sum(opp.get(h,0.) for h in r['opps']) for r in d]
        SD[t]=st.pstdev(r[t] for r in d)
    # direction: for level_6_time and deaths, LOWER is better, so a positive raw
    # offset means an EASIER lane once sign-corrected
    sgn={'last_hits_at_10':1,'net_worth_at_10':1,'level_6_time':-1,'deaths_before_10':-1}
    Z={t:[sgn[t]*v/SD[t] for v in E[t]] for t in TG}
    cs=Z['last_hits_at_10']; s=sorted(cs)
    lo,hi=s[int(.20*(len(s)-1))], s[int(.80*(len(s)-1))]
    lab=[0 if v<=lo else (2 if v>=hi else 1) for v in cs]
    print(f"\n=== {role} STANDARD  n={len(d)}  (label from CS env; thresholds z<= {lo:+.3f} / z>= {hi:+.3f})")
    for t in TG[1:]:
        z=Z[t]; ss=sorted(z); l2,h2=ss[int(.20*(len(ss)-1))], ss[int(.80*(len(ss)-1))]
        own=[0 if v<=l2 else (2 if v>=h2 else 1) for v in z]
        agree=sum(1 for a,b in zip(lab,own) if a==b)/len(lab)
        opposite=sum(1 for a,b in zip(lab,own) if abs(a-b)==2)/len(lab)
        # "visible contradiction": labelled DIFFICULT but this metric's own offset is
        # favourable by >= 0.10 sd (a shift the user could notice), or the mirror case
        vis=sum(1 for a,v in zip(lab,z) if (a==0 and v>=0.10) or (a==2 and v<=-0.10))/len(lab)
        r=st.fmean([(x-st.fmean(cs))*(y-st.fmean(z)) for x,y in zip(cs,z)])/(st.pstdev(cs)*st.pstdev(z))
        print(f"   CS-label vs {t:<18} corr={r:+.3f}  same-bucket={100*agree:5.1f}%  "
              f"opposite-bucket={100*opposite:5.2f}%  visible-contradiction={100*vis:5.2f}%")
