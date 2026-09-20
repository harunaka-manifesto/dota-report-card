"""Does the lane-PARTNER term earn its keep, given it carries the only leakage risk?"""
import pickle, collections, statistics as st, random, math

ROWS=pickle.load(open('metrics.pkl','rb'))

def fit(train,tgt,use_ally,k=40.0,iters=6):
    ys=[r[tgt] for r in train]; g=sum(ys)/len(ys); own={}; opp={}; ally={}
    for _ in range(iters):
        def base(r):
            v=g+own.get(r['hero'],0.)+sum(opp.get(h,0.) for h in r['opps'])
            if use_ally: v+=sum(ally.get(h,0.) for h in r['allies'])
            return v
        s=collections.defaultdict(float); c=collections.Counter()
        for r in train: s[r['hero']]+=r[tgt]-(base(r)-own.get(r['hero'],0.)); c[r['hero']]+=1
        own={h:s[h]/(c[h]+k) for h in c}
        s=collections.defaultdict(float); c=collections.Counter()
        for r in train:
            for h in r['opps']: s[h]+=r[tgt]-(base(r)-opp.get(h,0.)); c[h]+=1
        opp={h:s[h]/(c[h]+k) for h in c}
        if use_ally:
            s=collections.defaultdict(float); c=collections.Counter()
            for r in train:
                for h in r['allies']: s[h]+=r[tgt]-(base(r)-ally.get(h,0.)); c[h]+=1
            ally={h:s[h]/(c[h]+k) for h in c}
    return own,opp,ally

def run(tgt,role,folds=5,window=20,minprior=5):
    pool=[r for r in ROWS if r['role']==role and r['bucket']=='STANDARD' and r.get(tgt) is not None]
    lane=[r for r in pool if r['shape'] in ('2v2','1v1')]
    if len(lane)<3000: return
    accts=sorted({r['account'] for r in pool}); rnd=random.Random(9); rnd.shuffle(accts)
    fo={a:i%folds for i,a in enumerate(accts)}
    M={}
    for f in range(folds):
        tr=[r for r in lane if fo[r['account']]!=f]
        M[f]=(fit(tr,tgt,False), fit(tr,tgt,True))
    seq=collections.defaultdict(list)
    for r in pool: seq[r['account']].append(r)
    res=collections.defaultdict(list); n=0
    for a,rs in seq.items():
        rs=sorted(rs,key=lambda r:(r['started'] or 0,r['match_id']))
        (o1,p1,_),(o2,p2,al2)=M[fo[a]]
        H1=lambda q:o1.get(q['hero'],0.); H2=lambda q:o2.get(q['hero'],0.)
        def E1(q): return None if q['shape'] not in ('2v2','1v1') else sum(p1.get(h,0.) for h in q['opps'])
        def E2(q): return None if q['shape'] not in ('2v2','1v1') else sum(p2.get(h,0.) for h in q['opps'])+sum(al2.get(h,0.) for h in q['allies'])
        for i,r in enumerate(rs):
            pr=rs[max(0,i-window):i]
            if len(pr)<minprior: continue
            e1=E1(r); e2=E2(r)
            q1=[E1(x) for x in pr]; q1=[x for x in q1 if x is not None]
            q2=[E2(x) for x in pr]; q2=[x for x in q2 if x is not None]
            if e1 is None or len(q1)<3: continue
            n+=1
            b=st.median(x[tgt] for x in pr)
            d1=H1(r)-st.median(H1(x) for x in pr)
            d2=H2(r)-st.median(H2(x) for x in pr)
            res['A'].append(r[tgt]-b)
            res['B'].append(r[tgt]-(b+d1))
            res['C_opp_only'].append(r[tgt]-(b+d1+e1-st.median(q1)))
            res['C_opp_ally'].append(r[tgt]-(b+d2+e2-st.median(q2)))
    if n<500: return
    vA=st.pvariance(res['A'])
    print(f"  {tgt:<18}{role:<9}n={n:<6}sdA={math.sqrt(vA):8.2f} | " +
          "  ".join(f"{k}: {100*(1-st.pvariance(res[k])/vA):+5.2f}%" for k in ('B','C_opp_only','C_opp_ally')))

print("STANDARD — personal-baseline residual variance reduction")
for tgt in ('last_hits_at_10','net_worth_at_10','level_6_time','deaths_before_10'):
    for role in ('Carry','Mid','Offlane'):
        run(tgt,role)
