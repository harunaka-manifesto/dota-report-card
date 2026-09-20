import collections, random, statistics as st
from vardecomp import subset, fit, rows

print("== Effect of lane STRUCTURE (external, not hero-based) on cs10 — POS_1 STANDARD ==")
d=[r for r in subset('POSITION_1','ALL_PICK_RANKED') if r['cs10'] is not None]
tab=collections.defaultdict(list)
for r in d: tab[f"{r['n_allies']+1}v{r['n_opps']}"].append(r)
base=st.fmean(x['cs10'] for x in tab['2v2'])
for k in sorted(tab,key=lambda k:-len(tab[k]))[:7]:
    v=tab[k]
    print(f"  {k:<5} n={len(v):5d} ({100*len(v)/len(d):4.1f}%)  mean cs10={st.fmean(x['cs10'] for x in v):6.2f} "
          f"(vs 2v2 {st.fmean(x['cs10'] for x in v)-base:+6.2f})  mean nw10={st.fmean(x['nw10'] for x in v):7.0f} "
          f" deaths<10={st.fmean(x['deaths10'] for x in v):.2f}")

print("\n== leaverStatus / partner abandon is NOT in this corpus selection (leaverStatus was selected) ==")

print("\n== Bucket-label stability: same match scored by two independently-trained models ==")
for pos,struct,mode in (('POSITION_1','2v2','ALL_PICK_RANKED'),('POSITION_2','1v1','ALL_PICK_RANKED'),('POSITION_1','2v2','TURBO')):
    dd=[r for r in subset(pos,mode,structure=struct) if r['cs10'] is not None]
    rnd=random.Random(17); pool=list(dd); rnd.shuffle(pool)
    half=len(pool)//2
    m1=fit(pool[:half],'cs10',True,True,True,False)
    m2=fit(pool[half:],'cs10',True,True,True,False)
    def score(m,r): return sum(m[2].get(h,0.) for h in r['opps'])+sum(m[3].get(h,0.) for h in r['allies'])
    s1=[score(m1,r) for r in dd]; s2=[score(m2,r) for r in dd]
    lo1,hi1=sorted(s1)[len(s1)//3],sorted(s1)[2*len(s1)//3]
    lo2,hi2=sorted(s2)[len(s2)//3],sorted(s2)[2*len(s2)//3]
    def b(v,lo,hi): return 0 if v<=lo else (2 if v>=hi else 1)
    b1=[b(v,lo1,hi1) for v in s1]; b2=[b(v,lo2,hi2) for v in s2]
    agree=sum(1 for a,c in zip(b1,b2) if a==c)/len(b1)
    flip=sum(1 for a,c in zip(b1,b2) if abs(a-c)==2)/len(b1)
    mx,my=st.fmean(s1),st.fmean(s2)
    cov=st.fmean([(a-mx)*(c-my) for a,c in zip(s1,s2)])
    print(f"  {pos} {mode} {struct}: score corr={cov/(st.pstdev(s1)*st.pstdev(s2)):+.3f}  same-bucket={100*agree:.1f}%  EASY<->DIFFICULT flip={100*flip:.2f}%")

print("\n== How many distinct exact lane combinations exist in the data? (fragmentation) ==")
for pos,struct in (('POSITION_1','2v2'),('POSITION_2','1v1')):
    dd=[r for r in subset(pos,'ALL_PICK_RANKED',structure=struct) if r['cs10'] is not None]
    keys=collections.Counter((r['hero'],r['allies'],r['opps']) for r in dd)
    opp_only=collections.Counter(r['opps'] for r in dd)
    print(f"  {pos}: n={len(dd)}  distinct (own,ally,opps) combos={len(keys)}  "
          f"max obs for one combo={max(keys.values())}  singletons={100*sum(1 for v in keys.values() if v==1)/len(keys):.1f}%")
    print(f"         distinct opponent sets={len(opp_only)}  median obs/set={st.median(opp_only.values()):.0f}  "
          f"sets with >=30 obs={sum(1 for v in opp_only.values() if v>=30)}")
