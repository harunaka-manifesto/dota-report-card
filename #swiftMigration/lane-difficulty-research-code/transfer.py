import pickle, collections, statistics as st, random
import vardecomp as V
rows=pickle.load(open('merged.pkl','rb')); V.rows=rows
TAR=('cs10','nw10','xp10','deaths10')
def sub(pos,mode,struct,tgt):
    return [r for r in rows if r['pos']==pos and r['mode']==mode
            and f"{r['n_allies']+1}v{r['n_opps']}"==struct and r['patch'] in (180,181,182)
            and r.get(tgt) is not None]
def corr(x,y):
    mx,my=st.fmean(x),st.fmean(y)
    return st.fmean([(a-mx)*(b-my) for a,b in zip(x,y)])/(st.pstdev(x)*st.pstdev(y))

for pos,struct in (('POSITION_1','2v2'),('POSITION_2','1v1')):
    print(f"\n=== {pos} STANDARD: correlation between metric-specific opponent effects ===")
    eff={}
    for t in TAR:
        d=sub(pos,'ALL_PICK_RANKED',struct,t)
        m=V.fit(d,t,True,True,True,False,k=40.0)
        cnt=collections.Counter(h for r in d for h in r['opps'])
        sd=st.pstdev(r[t] for r in d)
        eff[t]={h:v/sd for h,v in m[2].items() if cnt[h]>=150}   # standardised
    common=set.intersection(*(set(eff[t]) for t in TAR))
    print(f"  heroes compared: {len(common)}")
    for i,a in enumerate(TAR):
        for b in TAR[i+1:]:
            print(f"    corr({a:<9},{b:<9}) = {corr([eff[a][h] for h in common],[eff[b][h] for h in common]):+.3f}")

    # transfer test: use a CS-trained env score to predict NW / XP / deaths
    print(f"  --- transfer: does a CS-trained difficulty score work for other metrics? (out-of-fold R2) ---")
    for t in TAR:
        d=sub(pos,'ALL_PICK_RANKED',struct,t)
        # need cs10 too
        d=[r for r in d if r['cs10'] is not None]
        rnd=random.Random(23); idx=list(range(len(d))); rnd.shuffle(idx)
        own_r2=[];tr_r2=[]
        sseO=sseT=sst=0.0
        gm=st.fmean(r[t] for r in d)
        for f in range(5):
            te=[d[i] for j,i in enumerate(idx) if j%5==f]; tr=[d[i] for j,i in enumerate(idx) if j%5!=f]
            mo=V.fit(tr,t,True,True,True,False,k=40.0)       # native
            mc=V.fit(tr,'cs10',True,True,True,False,k=40.0)  # cs-trained env
            # rescale cs env onto target via OLS on train
            envs=[sum(mc[2].get(h,0.) for h in r['opps'])+sum(mc[3].get(h,0.) for h in r['allies']) for r in tr]
            resid=[r[t]-(mo[0]+mo[1].get(r['hero'],0.)) for r in tr]
            me,mr=st.fmean(envs),st.fmean(resid)
            beta=sum((e-me)*(y-mr) for e,y in zip(envs,resid))/sum((e-me)**2 for e in envs)
            for r in te:
                base=mo[0]+mo[1].get(r['hero'],0.)
                pO=base+sum(mo[2].get(h,0.) for h in r['opps'])+sum(mo[3].get(h,0.) for h in r['allies'])
                envc=sum(mc[2].get(h,0.) for h in r['opps'])+sum(mc[3].get(h,0.) for h in r['allies'])
                pT=base+mr+beta*(envc-me)
                sseO+=(r[t]-pO)**2; sseT+=(r[t]-pT)**2; sst+=(r[t]-gm)**2
        print(f"    {t:<9} native-metric model R2={1-sseO/sst:+.4f}   CS-score-transferred R2={1-sseT/sst:+.4f}   beta={beta:+.2f}")
