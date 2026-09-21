"""Does a population lane-difficulty offset improve the PERSONAL rolling baseline?"""
import pickle, collections, statistics as st, random
import vardecomp as V
rows = pickle.load(open('merged.pkl','rb')); V.rows = rows

ROLE = {'POSITION_1':'Carry','POSITION_2':'Mid','POSITION_3':'Offlane','POSITION_4':'Support','POSITION_5':'Support'}

def analysis(target, mode, positions, label, k=40.0):
    # 1. fit population effects on the FULL merged corpus (population model)
    pool = [r for r in rows if r['pos'] in positions and r['mode']==mode
            and r['patch'] in (180,181,182) and r.get(target) is not None
            and f"{r['n_allies']+1}v{r['n_opps']}" in ('2v2','1v1')]
    models = {}
    for p in positions:
        d=[r for r in pool if r['pos']==p]
        if len(d) < 3000: continue
        models[p]=V.fit(d,target,True,True,True,False,k=k)

    # 2. per-account chronological baselines (only rows that carry an account id)
    seq = collections.defaultdict(list)
    for r in pool:
        if not r.get('account') or r['pos'] not in models: continue
        seq[(r['account'], ROLE[r['pos']], mode)].append(r)

    res = collections.defaultdict(list)
    n_obs = 0
    for key, rs in seq.items():
        rs = sorted(rs, key=lambda r: (r['started'] or 0, r['match_id']))
        for i, r in enumerate(rs):
            prior = rs[max(0, i-20):i]
            if len(prior) < 5: continue
            n_obs += 1
            base = st.median(x[target] for x in prior)
            m = models[r['pos']]
            env = lambda q: (sum(m[2].get(h,0.) for h in q['opps']) + sum(m[3].get(h,0.) for h in q['allies']))
            hero = lambda q: m[1].get(q['hero'], 0.0)
            de = env(r) - st.median(env(x) for x in prior)
            dh = hero(r) - st.median(hero(x) for x in prior)
            res['unadjusted'].append(r[target] - base)
            res['difficulty-adjusted'].append(r[target] - (base + de))
            res['hero-adjusted'].append(r[target] - (base + dh))
            res['hero+difficulty'].append(r[target] - (base + de + dh))
    print(f"\n=== {label} | target={target} | comparable observations={n_obs} "
          f"(accounts={len(set(k[0] for k in seq))}, tracks={len(seq)})")
    baseV = st.pvariance(res['unadjusted'])
    for name in ('unadjusted','difficulty-adjusted','hero-adjusted','hero+difficulty'):
        v = res[name]
        print(f"  {name:<21} MAE={st.fmean(abs(x) for x in v):7.2f}  sd={st.pstdev(v):7.2f}  "
              f"variance reduction vs unadjusted = {100*(1-st.pvariance(v)/baseV):+5.2f}%")

for tgt in ('cs10','nw10'):
    analysis(tgt,'ALL_PICK_RANKED',['POSITION_1'],'Carry STANDARD')
    analysis(tgt,'ALL_PICK_RANKED',['POSITION_2'],'Mid STANDARD')
    analysis(tgt,'ALL_PICK_RANKED',['POSITION_3'],'Offlane STANDARD')
    analysis(tgt,'ALL_PICK_RANKED',['POSITION_4','POSITION_5'],'Support STANDARD')
    analysis(tgt,'TURBO',['POSITION_1'],'Carry TURBO')
