"""PART 12 — how often does each awkward case actually occur?"""
import json, pickle, collections, statistics as st

H={h['id']:h['displayName'] for h in json.load(open(
 '/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'
))['data']['constants']['heroes']}
R=[r for r in pickle.load(open('metrics.pkl','rb')) if r['bucket']=='STANDARD' and r['role'] in ('Carry','Mid','Offlane')]
N=len(R)
print(f"STANDARD core-role tracked-player matches in corpus: n={N}\n")
c=collections.Counter(r['shape'] for r in R)
print("lane shape distribution:")
for k,v in c.most_common(10): print(f"   {k:<6} {v:6d}  {100*v/N:6.2f}%")
odd=collections.Counter(r['lane'] for r in R)
print("\nviewer lane label:")
for k,v in odd.most_common(): print(f"   {str(k):<12} {v:6d}  {100*v/N:6.2f}%")
# enemy lane composition oddities
tri=sum(1 for r in R if r['n_opps']>=3); solo=sum(1 for r in R if r['n_opps']==0)
print(f"\ntri-lane or bigger against the viewer: {tri} ({100*tri/N:.2f}%)")
print(f"no opponent resolved in the viewer's lane: {solo} ({100*solo/N:.2f}%)")
dual=sum(1 for r in R if r['pos'] in ('POSITION_1','POSITION_3') and r['n_allies']==0)
print(f"viewer core alone in a side lane (1vN): {dual} ({100*dual/N:.2f}%)")
# support hero played core / core hero played support, using STRATZ population position mix
HS=json.load(open('herostats_pop.json'))
mix=collections.defaultdict(dict)
for x in HS:
    if x['time']==10: mix[x['heroId']][x['position']]=x['matchCount'] or 0
def share(h,pos):
    t=sum(mix[h].values()) or 1
    return mix[h].get(pos,0)/t
offrole=[(r,share(r['hero'], r['pos'])) for r in R]
for thr in (0.05,0.02,0.01):
    k=sum(1 for r,s in offrole if s<thr)
    print(f"viewer hero played at a position it holds <{thr:.0%} of the time in the population: {k} ({100*k/N:.2f}%)")
rare=sorted({(round(s,4), H.get(r['hero'],r['hero']), r['pos']) for r,s in offrole if s<0.01})[:10]
print("   examples:", "; ".join(f"{h} as {p} ({100*s:.2f}%)" for s,h,p in rare[:8]))
# unknown-hero risk
known={x['heroId'] for x in HS}
unk=sum(1 for r in R if r['hero'] not in known)
print(f"\nviewer hero missing from the STRATZ population table: {unk} ({100*unk/N:.2f}%)")
opp_unk=sum(1 for r in R if any(h not in known for h in r['opps']))
print(f"any lane opponent missing from the population table: {opp_unk} ({100*opp_unk/N:.2f}%)")
# feeding guard overlap (>=8 deaths before 600 by ANY player is match-level; here viewer only)
fg=sum(1 for r in R if r['deaths_before_10']>=8)
print(f"\nviewer alone has >=8 deaths before 10:00 (insights feeding guard trips on any player): {fg} ({100*fg/N:.2f}%)")
# how many matches would get a lane-context label under the proposed gate?
ok=sum(1 for r in R if r['shape'] in ('2v2','1v1') and r['lane'] in ('SAFE_LANE','MID_LANE','OFF_LANE'))
print(f"\nmatches passing the proposed lane-context gate: {ok} ({100*ok/N:.2f}%)")
