"""Does STRATZ laneOutcome reproduce our fitted lane-environment effects?"""
import json, pickle, collections, statistics as st
import vardecomp as V

H={h['id']:h['displayName'] for h in json.load(open(
 '/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'
))['data']['constants']['heroes']}
LO=json.load(open('laneoutcome_p1.json'))
rows=pickle.load(open('merged.pkl','rb')); V.rows=rows

def marginal(tag, minpair=120):
    by1=collections.defaultdict(list)
    for x in LO[tag]:
        if (x['matchCount'] or 0) >= minpair: by1[x['heroId1']].append(x)
    eff=collections.defaultdict(lambda:[0.0,0])
    for a,xs in by1.items():
        n=sum(x['matchCount'] for x in xs); c=sum(x['csCount'] or 0 for x in xs)
        base=c/n
        for x in xs:
            e=(x['csCount'] or 0)/x['matchCount'] - base
            eff[x['heroId2']][0]+= e*x['matchCount']; eff[x['heroId2']][1]+= x['matchCount']
    return {h:(s/n) for h,(s,n) in eff.items() if n>=1500}

def corr(x,y):
    mx,my=st.fmean(x),st.fmean(y)
    return st.fmean([(a-mx)*(b-my) for a,b in zip(x,y)])/(st.pstdev(x)*st.pstdev(y))

d=[r for r in rows if r['pos']=='POSITION_1' and r['mode']=='ALL_PICK_RANKED'
   and r.get('cs10') is not None and f"{r['n_allies']+1}v{r['n_opps']}"=='2v2'
   and r['patch'] in (180,181,182)]
grand,own,opp,ally,_=V.fit(d,'cs10',True,True,True,False,k=40.0)
cnt_o=collections.Counter(h for r in d for h in r['opps'])
cnt_a=collections.Counter(h for r in d for h in r['allies'])

for tag,ours,cnt in (('vs',opp,cnt_o),('with',ally,cnt_a)):
    m=marginal(tag)
    common=[h for h in m if h in ours and cnt[h]>=120]
    a=[m[h] for h in common]; b=[ours[h] for h in common]
    sl=sum((x-st.fmean(a))*(y-st.fmean(b)) for x,y in zip(a,b))/sum((x-st.fmean(a))**2 for x in a)
    print(f"\n=== {tag}: {len(common)} heroes compared  corr(STRATZ laneOutcome marginal, our fitted partial) = {corr(a,b):+.3f}")
    print(f"    slope(ours ~ stratz) = {sl:+.2f}   sd: stratz={st.pstdev(a):.2f} ours={st.pstdev(b):.2f}")
    pairs=sorted(zip(common,a,b), key=lambda z:z[1])
    print(f"    {'hero':<22}{'STRATZ':>9}{'ours':>9}")
    for h,x,y in pairs[:6]: print(f"    {H.get(h,h):<22}{x:>9.2f}{y:>9.2f}")
    print("    ...")
    for h,x,y in pairs[-6:]: print(f"    {H.get(h,h):<22}{x:>9.2f}{y:>9.2f}")
