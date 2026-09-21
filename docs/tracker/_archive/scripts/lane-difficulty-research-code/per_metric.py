import pickle, json, collections, statistics as st
import vardecomp as V
rows = pickle.load(open('merged.pkl','rb')); V.rows = rows
H={h['id']:h['displayName'] for h in json.load(open('/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'))['data']['constants']['heroes']}
nm=lambda i:H.get(i,f"#{i}"); ID={v:k for k,v in H.items()}

def sub(pos,mode,struct,tgt):
    return [r for r in rows if r['pos']==pos and r['mode']==mode
            and f"{r['n_allies']+1}v{r['n_opps']}"==struct and r['patch'] in (180,181,182)
            and r.get(tgt) is not None]

TARGETS=('cs10','nw10','xp10','deaths10')
for pos,struct,heroes in (
    ('POSITION_1','2v2',['Underlord','Viper','Sniper','Witch Doctor','Enigma','Wraith King','Tidehunter','Warlock','Skywrath Mage']),
    ('POSITION_2','1v1',['Huskar','Outworld Destroyer','Necrophos','Shadow Fiend','Invoker','Keeper of the Light','Viper'])):
    print(f"\n{'='*92}\n{pos} STANDARD — OPPONENT hero effect per metric (same model, different target)")
    models={}
    for t in TARGETS:
        d=sub(pos,'ALL_PICK_RANKED',struct,t)
        models[t]=(V.fit(d,t,True,True,True,False,k=40.0), len(d),
                   st.fmean(r[t] for r in d), st.pstdev(r[t] for r in d),
                   collections.Counter(h for r in d for h in r['opps']))
    print(f"  {'hero':<22}" + "".join(f"{t:>26}" for t in TARGETS))
    print(f"  {'':<22}" + "".join(f"{'effect (% of sd)':>26}" for t in TARGETS))
    for hn in heroes:
        h=ID.get(hn)
        line=f"  {hn:<22}"
        for t in TARGETS:
            (m,n,mean,sd,cnt)=models[t]
            v=m[2].get(h)
            line+= f"{(f'{v:+8.1f} ({100*v/sd:+5.1f}%)' if v is not None else 'n/a'):>26}"
        print(line)
    for t in TARGETS:
        (m,n,mean,sd,cnt)=models[t]
        print(f"    [{t}] n={n} mean={mean:.1f} sd={sd:.1f}")

# ally effects incl. Pudge
print(f"\n{'='*92}\nPOS_1 STANDARD — ALLY (lane partner) hero effect per metric")
models={}
for t in TARGETS:
    d=sub('POSITION_1','ALL_PICK_RANKED','2v2',t)
    models[t]=(V.fit(d,t,True,True,True,False,k=40.0), st.pstdev(r[t] for r in d),
               collections.Counter(h for r in d for h in r['allies']))
for hn in ['Pudge','Undying','Winter Wyvern','Warlock','Shadow Shaman','Techies','Spirit Breaker','Crystal Maiden','Lion']:
    h=ID.get(hn); line=f"  {hn:<22}"
    for t in TARGETS:
        (m,sd,cnt)=models[t]; v=m[3].get(h)
        line+= f"{(f'{v:+8.1f} ({100*v/sd:+5.1f}%) n={cnt[h]}' if v is not None else 'n/a'):>32}"
    print(line)
