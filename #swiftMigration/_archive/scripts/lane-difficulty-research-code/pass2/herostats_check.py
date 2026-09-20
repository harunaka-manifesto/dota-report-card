"""Can STRATZ heroStats.stats replace our own fitted own-hero effects?"""
import json, pickle, collections, statistics as st, random

HS = json.load(open('herostats_pop.json'))
hs = {(r['heroId'], r['position'], r['time']): r for r in HS}
ROWS = pickle.load(open('metrics.pkl', 'rb'))
H = {h['id']: h['displayName'] for h in json.load(open(
 '/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'
))['data']['constants']['heroes']}

def corr(x, y):
    mx, my = st.fmean(x), st.fmean(y)
    return st.fmean([(a-mx)*(b-my) for a, b in zip(x, y)])/(st.pstdev(x)*st.pstdev(y))

print("=== Does STRATZ heroStats track STANDARD or TURBO? (per-hero cs@10 / nw@10) ===")
for pos in ('POSITION_1','POSITION_2','POSITION_3'):
    for field, mk in (('cs','last_hits_at_10'), ('networth','net_worth_at_10')):
        line = f"  {pos} {field:<9}"
        for bucket in ('STANDARD','TURBO'):
            d = [r for r in ROWS if r['pos'] == pos and r['bucket'] == bucket and r.get(mk) is not None]
            g = collections.defaultdict(list)
            for r in d: g[r['hero']].append(r[mk])
            ours = {h: st.fmean(v) for h, v in g.items() if len(v) >= 40}
            common = [h for h in ours if (h, pos, 10) in hs and (hs[(h,pos,10)]['matchCount'] or 0) >= 300]
            if len(common) < 20: line += f" | {bucket}: too few"; continue
            a = [hs[(h,pos,10)][field] for h in common]
            b = [ours[h] for h in common]
            line += (f" | {bucket}: r={corr(a,b):+.3f} n={len(common)} "
                     f"mean STRATZ={st.fmean(a):8.1f} ours={st.fmean(b):8.1f}")
        print(line)

print("\n=== Sample: heroStats cs@10 vs our STANDARD pos1 mean ===")
d = [r for r in ROWS if r['pos']=='POSITION_1' and r['bucket']=='STANDARD' and r.get('last_hits_at_10') is not None]
g = collections.defaultdict(list)
for r in d: g[r['hero']].append(r['last_hits_at_10'])
rowsx = [(h, hs[(h,'POSITION_1',10)]['cs'], st.fmean(v), len(v), hs[(h,'POSITION_1',10)]['matchCount'])
         for h, v in g.items() if len(v) >= 60 and (h,'POSITION_1',10) in hs]
rowsx.sort(key=lambda x: -x[1])
print(f"  {'hero':<22}{'STRATZ cs@10':>14}{'ours':>9}{'our n':>7}{'STRATZ n':>10}")
for h, a, b, n, m in rowsx[:6] + rowsx[-6:]:
    print(f"  {H.get(h,h):<22}{a:>14.1f}{b:>9.1f}{n:>7}{m:>10}")
