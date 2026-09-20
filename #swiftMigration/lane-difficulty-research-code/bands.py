import collections, random, statistics as st
from vardecomp import subset, fit

def experiment(pos, mode, struct, k, band):
    dd=[r for r in subset(pos,mode,structure=struct) if r['cs10'] is not None]
    rnd=random.Random(17); pool=list(dd); rnd.shuffle(pool); half=len(pool)//2
    m1=fit(pool[:half],'cs10',True,True,True,False,k=k)
    m2=fit(pool[half:],'cs10',True,True,True,False,k=k)
    def score(m,r): return sum(m[2].get(h,0.) for h in r['opps'])+sum(m[3].get(h,0.) for h in r['allies'])
    s1=[score(m1,r) for r in dd]; s2=[score(m2,r) for r in dd]
    def cuts(s): ss=sorted(s); return ss[int(band*(len(ss)-1))], ss[int((1-band)*(len(ss)-1))]
    lo1,hi1=cuts(s1); lo2,hi2=cuts(s2)
    def b(v,lo,hi): return 0 if v<=lo else (2 if v>=hi else 1)
    b1=[b(v,lo1,hi1) for v in s1]; b2=[b(v,lo2,hi2) for v in s2]
    agree=sum(1 for a,c in zip(b1,b2) if a==c)/len(b1)
    flip=sum(1 for a,c in zip(b1,b2) if abs(a-c)==2)/len(b1)
    # full-data model, effect size of the buckets
    mf=fit(dd,'cs10',True,True,True,False,k=k)
    sf=[score(mf,r) for r in dd]; lof,hif=cuts(sf)
    g=collections.defaultdict(list)
    for r,v in zip(dd,sf): g[b(v,lof,hif)].append(r)
    gap=st.fmean(x['cs10'] for x in g[2])-st.fmean(x['cs10'] for x in g[0])
    dgap=st.fmean(x['deaths10'] for x in g[0])-st.fmean(x['deaths10'] for x in g[2])
    print(f"  k={k:<4} band={band:.2f}  labelled {100*band:.0f}%/{100*(1-2*band):.0f}%/{100*band:.0f}%  "
          f"agree={100*agree:5.1f}%  extreme-flip={100*flip:5.2f}%  EASY-DIFF cs10 gap={gap:+5.2f}  deaths gap={dgap:+.2f}")

for pos,mode,struct in (('POSITION_1','ALL_PICK_RANKED','2v2'),('POSITION_2','ALL_PICK_RANKED','1v1'),('POSITION_1','TURBO','2v2')):
    print(f"\n=== {pos} {mode} {struct} ===")
    for k in (25.0, 60.0, 150.0):
        for band in (1/3, 0.25, 0.15, 0.10):
            experiment(pos,mode,struct,k,band)
