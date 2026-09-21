import pickle, collections, random, statistics as st
import vardecomp as V
rows = pickle.load(open('merged.pkl','rb')); V.rows = rows

def sub(pos, mode, struct):
    return [r for r in rows if r['pos']==pos and r['mode']==mode
            and f"{r['n_allies']+1}v{r['n_opps']}"==struct and r['patch'] in (180,181,182)
            and r['cs10'] is not None]

def score(m, r): return sum(m[2].get(h,0.) for h in r['opps']) + sum(m[3].get(h,0.) for h in r['allies'])

def run(pos, mode, struct, k=40.0):
    d = sub(pos,mode,struct)
    rnd=random.Random(17); pool=list(d); rnd.shuffle(pool); half=len(pool)//2
    m1=V.fit(pool[:half],'cs10',True,True,True,False,k=k)
    m2=V.fit(pool[half:],'cs10',True,True,True,False,k=k)
    mf=V.fit(d,'cs10',True,True,True,False,k=k)
    s1=[score(m1,r) for r in d]; s2=[score(m2,r) for r in d]; sf=[score(mf,r) for r in d]
    mx,my=st.fmean(s1),st.fmean(s2)
    cov=st.fmean([(a-mx)*(c-my) for a,c in zip(s1,s2)])
    corr=cov/(st.pstdev(s1)*st.pstdev(s2))
    print(f"\n=== {pos} {mode} {struct}  n={len(d)}  half-sample score corr={corr:+.3f} (Spearman-Brown full={2*corr/(1+corr):+.3f})")
    for band in (1/3,0.25,0.20,0.15,0.10):
        cut=lambda s: (sorted(s)[int(band*(len(s)-1))], sorted(s)[int((1-band)*(len(s)-1))])
        lo1,hi1=cut(s1); lo2,hi2=cut(s2); lof,hif=cut(sf)
        b=lambda v,lo,hi: 0 if v<=lo else (2 if v>=hi else 1)
        b1=[b(v,lo1,hi1) for v in s1]; b2=[b(v,lo2,hi2) for v in s2]
        agree=sum(1 for x,y in zip(b1,b2) if x==y)/len(b1)
        flip=sum(1 for x,y in zip(b1,b2) if abs(x-y)==2)/len(b1)
        g=collections.defaultdict(list)
        for r,v in zip(d,sf): g[b(v,lof,hif)].append(r)
        def mn(i,f): return st.fmean(f(x) for x in g[i])
        print(f"  band={band:.2f} ({100*band:.0f}/{100-200*band:.0f}/{100*band:.0f})  agree={100*agree:5.1f}% extreme-flip={100*flip:4.2f}% | "
              f"cs10 D/N/E = {mn(0,lambda x:x['cs10']):.1f}/{mn(1,lambda x:x['cs10']):.1f}/{mn(2,lambda x:x['cs10']):.1f} (gap {mn(2,lambda x:x['cs10'])-mn(0,lambda x:x['cs10']):+.1f}) | "
              f"nw10 gap {mn(2,lambda x:x['nw10'])-mn(0,lambda x:x['nw10']):+.0f} | deaths {mn(0,lambda x:x['deaths10']):.2f}/{mn(2,lambda x:x['deaths10']):.2f} | "
              f"winrate {mn(0,lambda x:1 if x['win'] else 0):.3f}/{mn(2,lambda x:1 if x['win'] else 0):.3f}")

for a in (('POSITION_1','ALL_PICK_RANKED','2v2'),('POSITION_2','ALL_PICK_RANKED','1v1'),
          ('POSITION_3','ALL_PICK_RANKED','2v2'),('POSITION_5','ALL_PICK_RANKED','2v2'),
          ('POSITION_1','TURBO','2v2'),('POSITION_2','TURBO','1v1')):
    run(*a)
