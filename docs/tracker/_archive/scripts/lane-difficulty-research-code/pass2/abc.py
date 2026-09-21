"""Model A / B / C against the real personal rolling-baseline contract, every locked metric.

A = personal baseline only
B = + population own-hero adjustment
C = + population lane-environment adjustment
Population effects are fitted account-out-of-fold so a player never contributes to
the hero effect applied to their own match.
"""
import pickle, collections, statistics as st, random, math, sys

ROWS = pickle.load(open('metrics.pkl', 'rb'))

METRICS = ['last_hits_at_10','net_worth_at_10','net_worth_at_20','cs_10_to_20','level_6_time',
           'deaths_total','death_rate_per10','hero_damage_share','tower_damage_share','fight_presence',
           'objective_involvement','observer_wards_per10','dewards_per10',
           'camps_stacked_at_20','healing_per10','deaths_before_10']
LOWER_BETTER = {'level_6_time','deaths_total','death_rate_per10','deaths_before_10'}

def fit(train, tgt, use_own, use_env, k=40.0, iters=6):
    ys=[r[tgt] for r in train]; grand=sum(ys)/len(ys)
    own={}; opp={}; ally={}
    for _ in range(iters):
        def base(r):
            v=grand
            if use_own: v+=own.get(r['hero'],0.)
            if use_env: v+=sum(opp.get(h,0.) for h in r['opps'])+sum(ally.get(h,0.) for h in r['allies'])
            return v
        if use_own:
            s=collections.defaultdict(float); c=collections.Counter()
            for r in train:
                s[r['hero']] += r[tgt]-(base(r)-own.get(r['hero'],0.)); c[r['hero']]+=1
            own={g:s[g]/(c[g]+k) for g in c}
        if use_env:
            s=collections.defaultdict(float); c=collections.Counter()
            for r in train:
                for h in r['opps']:
                    s[h]+=r[tgt]-(base(r)-opp.get(h,0.)); c[h]+=1
            opp={g:s[g]/(c[g]+k) for g in c}
            s=collections.defaultdict(float); c=collections.Counter()
            for r in train:
                for h in r['allies']:
                    s[h]+=r[tgt]-(base(r)-ally.get(h,0.)); c[h]+=1
            ally={g:s[g]/(c[g]+k) for g in c}
    return own, opp, ally

def run(tgt, role, bucket, shapes=('2v2','1v1'), folds=5, minprior=5, window=20):
    pool=[r for r in ROWS if r['role']==role and r['bucket']==bucket and r.get(tgt) is not None]
    if len(pool)<2000: return None
    lane_ok=[r for r in pool if r['shape'] in shapes]
    accts=sorted({r['account'] for r in pool})
    rnd=random.Random(9); rnd.shuffle(accts)
    foldof={a:i%folds for i,a in enumerate(accts)}
    models={}
    for f in range(folds):
        tr_own=[r for r in pool if foldof[r['account']]!=f]
        tr_env=[r for r in lane_ok if foldof[r['account']]!=f]
        own,_,_   = fit(tr_own,tgt,True,False)
        _,opp,ally= fit(tr_env,tgt,True,True) if len(tr_env)>1500 else ({},{},{})
        models[f]=(own,opp,ally)
    seq=collections.defaultdict(list)
    for r in pool: seq[r['account']].append(r)
    res=collections.defaultdict(list); n=0; n_env=0
    for a,rs in seq.items():
        rs=sorted(rs,key=lambda r:(r['started'] or 0, r['match_id']))
        own,opp,ally=models[foldof[a]]
        H=lambda q: own.get(q['hero'],0.)
        def E(q):
            if q['shape'] not in shapes: return None
            return sum(opp.get(h,0.) for h in q['opps'])+sum(ally.get(h,0.) for h in q['allies'])
        for i,r in enumerate(rs):
            prior=rs[max(0,i-window):i]
            if len(prior)<minprior: continue
            n+=1
            b=st.median(x[tgt] for x in prior)
            dh=H(r)-st.median(H(x) for x in prior)
            res['A'].append(r[tgt]-b)
            res['B'].append(r[tgt]-(b+dh))
            pe=[E(x) for x in prior]; pe=[x for x in pe if x is not None]
            e=E(r)
            if e is not None and len(pe)>=3:
                n_env+=1
                de=e-st.median(pe)
                res['C'].append(r[tgt]-(b+dh+de))
                res['C_A'].append(r[tgt]-b); res['C_B'].append(r[tgt]-(b+dh))
            else:
                res['C'].append(r[tgt]-(b+dh))
    vA=st.pvariance(res['A'])
    if vA <= 0 or n < 500: return None
    out=dict(tgt=tgt,role=role,bucket=bucket,n=n,n_env=n_env,
             meanA=st.fmean(abs(x) for x in res['A']), sdA=math.sqrt(vA))
    out['B_var']=100*(1-st.pvariance(res['B'])/vA)
    out['C_var']=100*(1-st.pvariance(res['C'])/vA)
    out['B_mae']=100*(1-st.fmean(abs(x) for x in res['B'])/out['meanA'])
    out['C_mae']=100*(1-st.fmean(abs(x) for x in res['C'])/out['meanA'])
    return out

if __name__=='__main__':
    hdr=f"{'metric':<24}{'role':<9}{'bucket':<9}{'n':>7}{'n_env':>7}{'sdA':>10}{'B var%':>8}{'C var%':>8}{'B MAE%':>8}{'C MAE%':>8}"
    for bucket in ('STANDARD','TURBO'):
        print(f"\n{'='*len(hdr)}\nBUCKET {bucket}\n{'='*len(hdr)}")
        print(hdr)
        for role in ('Carry','Mid','Offlane','Support'):
            for m in METRICS:
                o=run(m,role,bucket)
                if not o: continue
                print(f"{m:<24}{role:<9}{bucket:<9}{o['n']:>7}{o['n_env']:>7}{o['sdA']:>10.3f}"
                      f"{o['B_var']:>8.1f}{o['C_var']:>8.1f}{o['B_mae']:>8.1f}{o['C_mae']:>8.1f}")
