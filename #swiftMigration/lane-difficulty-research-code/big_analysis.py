import pickle, collections, random, math, statistics as st
import vardecomp as V

rows = pickle.load(open('big.pkl','rb'))
V.rows = rows

def sub(pos, mode, struct=None, patches=(180,181,182)):
    out=[]
    for r in rows:
        if r['pos']!=pos or r['mode']!=mode or r['patch'] not in patches: continue
        if struct and f"{r['n_allies']+1}v{r['n_opps']}"!=struct: continue
        out.append(r)
    return out

MODELS=[("M0 grand mean",(False,False,False,False)),
        ("M1 own hero",(True,False,False,False)),
        ("M2 own+opp",(True,True,False,False)),
        ("M3 own+opp+ally",(True,True,True,False)),
        ("M4 +exact opp set",(True,True,True,True))]

print("="*78); print("VARIANCE DECOMPOSITION — 96.5k-match corpus"); print("="*78)
for pos,mode,struct in (('POSITION_1','ALL_PICK_RANKED','2v2'),('POSITION_2','ALL_PICK_RANKED','1v1'),
                        ('POSITION_3','ALL_PICK_RANKED','2v2'),('POSITION_4','ALL_PICK_RANKED','2v2'),
                        ('POSITION_5','ALL_PICK_RANKED','2v2'),('POSITION_1','TURBO','2v2'),
                        ('POSITION_2','TURBO','1v1')):
    d=[r for r in sub(pos,mode,struct) if r['cs10'] is not None]
    print(f"\n--- {pos} {mode} {struct}  n={len(d)}")
    for tgt in ('cs10','nw10','xp10','deaths10'):
        dd=[r for r in d if r.get(tgt) is not None]
        if len(dd)<1000: continue
        line=[]
        for name,flags in MODELS:
            r2,gm,sd=V.cv_r2(dd,tgt,flags)
            line.append(f"{name}={r2:+.4f}")
        _,gm,sd=V.cv_r2(dd,tgt,MODELS[0][1])
        print(f"   {tgt:<9} mean={gm:8.1f} sd={sd:7.1f} | " + "  ".join(line))
