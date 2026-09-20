"""Build the production lane-context parameter set from STRATZ heroStats.laneOutcome
and validate it against our independent corpus."""
import json, pickle, collections, statistics as st, random, math

H={h['id']:h['displayName'] for h in json.load(open(
 '/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'
))['data']['constants']['heroes']}
LO=json.load(open('laneoutcome_all.json'))
HS={(r['heroId'],r['position'],r['time']):r for r in json.load(open('herostats_pop.json'))}
ROWS=pickle.load(open('metrics.pkl','rb'))

def corr(x,y):
    mx,my=st.fmean(x),st.fmean(y)
    return st.fmean([(a-mx)*(b-my) for a,b in zip(x,y)])/(st.pstdev(x)*st.pstdev(y))

def build(key, min_pair=100, min_tot=3000):
    """pooled marginal opponent/ally effect on CS, and the per-(A,B) pairwise table"""
    xs=[x for x in LO[key] if (x['matchCount'] or 0) >= min_pair]
    by1=collections.defaultdict(list)
    for x in xs: by1[x['heroId1']].append(x)
    pair={}; agg=collections.defaultdict(lambda:[0.0,0])
    for a,g in by1.items():
        n=sum(x['matchCount'] for x in g); c=sum(x['csCount'] or 0 for x in g)
        if n < min_tot: continue
        base=c/n
        for x in g:
            e=(x['csCount'] or 0)/x['matchCount'] - base
            pair[(a,x['heroId2'])]=e
            agg[x['heroId2']][0]+= e*x['matchCount']; agg[x['heroId2']][1]+= x['matchCount']
    pooled={h:s/n for h,(s,n) in agg.items() if n >= min_tot}
    return pooled, pair, sum(x['matchCount'] for x in xs)

def fit_ours(d,tgt,use_ally,k=40.,iters=6):
    ys=[r[tgt] for r in d]; g=sum(ys)/len(ys); own={}; opp={}; ally={}
    for _ in range(iters):
        def b(r):
            v=g+own.get(r['hero'],0.)+sum(opp.get(h,0.) for h in r['opps'])
            if use_ally: v+=sum(ally.get(h,0.) for h in r['allies'])
            return v
        s=collections.defaultdict(float); c=collections.Counter()
        for r in d: s[r['hero']]+=r[tgt]-(b(r)-own.get(r['hero'],0.)); c[r['hero']]+=1
        own={h:s[h]/(c[h]+k) for h in c}
        s=collections.defaultdict(float); c=collections.Counter()
        for r in d:
            for h in r['opps']: s[h]+=r[tgt]-(b(r)-opp.get(h,0.)); c[h]+=1
        opp={h:s[h]/(c[h]+k) for h in c}
        if use_ally:
            s=collections.defaultdict(float); c=collections.Counter()
            for r in d:
                for h in r['allies']: s[h]+=r[tgt]-(b(r)-ally.get(h,0.)); c[h]+=1
            ally={h:s[h]/(c[h]+k) for h in c}
    return own,opp,ally

POS={'Carry':'POSITION_1','Mid':'POSITION_2','Offlane':'POSITION_3'}
PARAM={}
print("="*92)
print("REPLICATION — STRATZ population laneOutcome vs our independently fitted corpus effects")
print("="*92)
for role,pos in POS.items():
    pooled,pair,tot = build(f"{pos}|vs")
    d=[r for r in ROWS if r['role']==role and r['bucket']=='STANDARD'
       and r['shape'] in ('2v2','1v1') and r.get('last_hits_at_10') is not None]
    own,opp,ally = fit_ours(d,'last_hits_at_10',False)
    cnt=collections.Counter(h for r in d for h in r['opps'])
    common=[h for h in pooled if h in opp and cnt[h]>=100]
    a=[pooled[h] for h in common]; b=[opp[h] for h in common]
    sl=sum((x-st.fmean(a))*(y-st.fmean(b)) for x,y in zip(a,b))/sum((x-st.fmean(a))**2 for x in a)
    print(f"\n{role} ({pos}) opponents: STRATZ lane observations={tot:,}  pooled heroes={len(pooled)}  "
          f"pairwise cells={len(pair)}")
    print(f"   corr(STRATZ pooled, our fitted partial) = {corr(a,b):+.3f} over {len(common)} heroes;  "
          f"slope ours~stratz = {sl:.3f};  sd stratz={st.pstdev(a):.2f} ours={st.pstdev(b):.2f}")
    PARAM[role]={'pooled':pooled,'pair':pair,'slope':sl,'n_obs':tot}
    rank=sorted(pooled.items(), key=lambda kv: kv[1])
    print("   hardest:", ", ".join(f"{H.get(h,h)} {v:+.1f}" for h,v in rank[:6]))
    print("   easiest:", ", ".join(f"{H.get(h,h)} {v:+.1f}" for h,v in rank[-6:][::-1]))
    # pairwise coverage
    pc=collections.Counter()
    for x in LO[f"{pos}|vs"]:
        pc[(x['matchCount'] or 0) >= 300] += 1
    print(f"   pairwise cells with >=300 weekly lane observations: {pc[True]}/{pc[True]+pc[False]}")
json.dump({r:{'pooled':{str(k):v for k,v in p['pooled'].items()},'slope':p['slope'],'n_obs':p['n_obs']}
           for r,p in PARAM.items()}, open('param_stratz.json','w'))
pickle.dump(PARAM, open('param_stratz.pkl','wb'))
print("\nsaved param_stratz.{json,pkl}")
