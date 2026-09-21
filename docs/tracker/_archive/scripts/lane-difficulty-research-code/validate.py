import pickle, json, collections, statistics as st, random
import vardecomp as V
rows = pickle.load(open('merged.pkl','rb')); V.rows = rows
H = {h['id']: h['displayName'] for h in json.load(open(
    '/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'
))['data']['constants']['heroes']}
nm = lambda i: H.get(i, f"#{i}")

def sub(pos, mode, struct):
    return [r for r in rows if r['pos']==pos and r['mode']==mode
            and f"{r['n_allies']+1}v{r['n_opps']}"==struct and r['patch'] in (180,181,182)
            and r['cs10'] is not None]

def build(pos, mode, struct, k=40.0):
    d = sub(pos,mode,struct)
    m = V.fit(d,'cs10',True,True,True,False,k=k)
    return d, m

for pos,mode,struct in (('POSITION_1','ALL_PICK_RANKED','2v2'),('POSITION_2','ALL_PICK_RANKED','1v1')):
    d,m = build(pos,mode,struct)
    grand,own,opp,ally,_ = m
    cnt_o = collections.Counter(h for r in d for h in r['opps'])
    cnt_a = collections.Counter(h for r in d for h in r['allies'])
    print(f"\n{'='*70}\n{pos} {mode} — CS@10 effects (n={len(d)}, grand mean {grand:.1f})")
    o = sorted(((v,h) for h,v in opp.items() if cnt_o[h]>=150))
    print("  HARDEST opponents (CS@10 cost):")
    for v,h in o[:10]: print(f"    {nm(h):<22} {v:+6.2f} CS   (n={cnt_o[h]})")
    print("  EASIEST opponents:")
    for v,h in o[-10:][::-1]: print(f"    {nm(h):<22} {v:+6.2f} CS   (n={cnt_o[h]})")
    if struct=='2v2':
        a = sorted(((v,h) for h,v in ally.items() if cnt_a[h]>=150))
        print("  WORST lane partners:")
        for v,h in a[:6]: print(f"    {nm(h):<22} {v:+6.2f} CS   (n={cnt_a[h]})")
        print("  BEST lane partners:")
        for v,h in a[-6:][::-1]: print(f"    {nm(h):<22} {v:+6.2f} CS   (n={cnt_a[h]})")

# ---- worked examples --------------------------------------------------------
d,m = build('POSITION_1','ALL_PICK_RANKED','2v2')
grand,own,opp,ally,_ = m
sc = sorted(sum(opp.get(h,0.) for h in r['opps'])+sum(ally.get(h,0.) for h in r['allies']) for r in d)
lo,hi = sc[int(.20*(len(sc)-1))], sc[int(.80*(len(sc)-1))]
print(f"\n{'='*70}\nPOS_1 STANDARD thresholds (20/60/20): DIFFICULT <= {lo:+.2f}, EASY >= {hi:+.2f}")

pa = [i for i,n in H.items() if n=='Phantom Assassin'][0]
print(f"\nWorked examples — Phantom Assassin safelane (hero effect {own.get(pa,0):+.2f} CS):")
ex = [r for r in d if r['hero']==pa]
print(f"  {len(ex)} PA safelane matches in corpus")
shown=collections.Counter()
for r in sorted(ex, key=lambda r: sum(opp.get(h,0.) for h in r['opps'])+sum(ally.get(h,0.) for h in r['allies'])):
    e = sum(opp.get(h,0.) for h in r['opps'])+sum(ally.get(h,0.) for h in r['allies'])
    b = 'DIFFICULT' if e<=lo else ('EASY' if e>=hi else 'NORMAL')
    if shown[b]>=3: continue
    shown[b]+=1
    pred = grand+own.get(pa,0)+e
    print(f"  match {r['match_id']} [{b:<9}] env={e:+5.2f}  PA + {'/'.join(nm(h) for h in r['allies'])}  "
          f"vs {'/'.join(nm(h) for h in r['opps'])}")
    print(f"      expected CS@10={pred:.1f}  actual={r['cs10']}  (delta {r['cs10']-pred:+.1f})  "
          f"nw10={r['nw10']} deaths<10={r['deaths10']} won={r['win']}")
    if sum(shown.values())>=9: break
