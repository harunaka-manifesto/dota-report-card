import pickle, statistics as st, collections
import vardecomp as V
rows=pickle.load(open('merged.pkl','rb')); V.rows=rows
def sub(pos,mode,struct,tgt):
    return [r for r in rows if r['pos']==pos and r['mode']==mode
            and f"{r['n_allies']+1}v{r['n_opps']}"==struct and r['patch'] in (180,181,182)
            and r.get(tgt) is not None]
print("Which laning-stage checkpoint carries the cleanest draft signal?")
print("(M3 = own hero + lane opponents + lane ally; M1 = own hero only; ENV = M3-M1)")
for pos,mode,struct in (('POSITION_1','ALL_PICK_RANKED','2v2'),('POSITION_2','ALL_PICK_RANKED','1v1'),
                        ('POSITION_3','ALL_PICK_RANKED','2v2'),('POSITION_1','TURBO','2v2')):
    print(f"\n--- {pos} {mode}")
    for tgt in ('cs8','cs10','cs12','nw8','nw10','nw12'):
        d=sub(pos,mode,struct,tgt)
        if len(d)<3000: print(f"   {tgt}: n={len(d)} too few"); continue
        r1,_,_=V.cv_r2(d,tgt,(True,False,False,False))
        r3,gm,sd=V.cv_r2(d,tgt,(True,True,True,False))
        print(f"   {tgt:<6} n={len(d):6d} mean={gm:8.1f} sd={sd:7.1f}  M1={r1:+.4f} M3={r3:+.4f} ENV={r3-r1:+.4f} "
              f"(ENV as % of sd: {100*(( (r3)**.5 - (r1)**.5 )):.1f})")
