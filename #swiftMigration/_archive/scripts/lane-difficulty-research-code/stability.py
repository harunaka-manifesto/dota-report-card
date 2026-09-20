import pickle, collections, random, math, statistics as st
from vardecomp import subset, fit, predict, cv_r2, rows

# --- 1. deaths as a target -------------------------------------------------
print("== Can lane composition predict deaths before 10:00? (pos1/2/3 STANDARD) ==")
for pos, struct in (('POSITION_1','2v2'), ('POSITION_2','1v1'), ('POSITION_3','2v2')):
    d = subset(pos, 'ALL_PICK_RANKED', structure=struct)
    for r in d: r['_d'] = r['deaths10']
    for name, flags in (("own hero",(True,False,False,False)), ("own+opp+ally",(True,True,True,False))):
        r2, gm, sd = cv_r2(d, '_d', flags)
        print(f"  {pos} deaths<10 {name:<14} mean={gm:.2f} sd={sd:.2f} CV R2={r2:+.4f}")

# --- 2. TURBO bucket -------------------------------------------------------
print("\n== TURBO bucket (pos1 2v2) ==")
d = [r for r in subset('POSITION_1','TURBO',structure='2v2') if r['cs10'] is not None]
print(f"  n={len(d)}")
for name, flags in (("own hero",(True,False,False,False)), ("own+opp+ally",(True,True,True,False))):
    r2, gm, sd = cv_r2(d, 'cs10', flags)
    print(f"  cs10 {name:<14} mean={gm:.1f} sd={sd:.1f} CV R2={r2:+.4f}")
# standard-trained params applied to turbo?
std = [r for r in subset('POSITION_1','ALL_PICK_RANKED',structure='2v2') if r['cs10'] is not None]
m_std = fit(std,'cs10',True,True,True,False)
m_tur = fit(d,'cs10',True,True,True,False)
common = set(m_std[2]) & set(m_tur[2])
xs=[m_std[2][h] for h in common]; ys=[m_tur[2][h] for h in common]
mx,my=st.fmean(xs),st.fmean(ys)
cov=st.fmean([(a-mx)*(b-my) for a,b in zip(xs,ys)])
print(f"  corr(opponent effect STANDARD, TURBO) over {len(common)} heroes = {cov/(st.pstdev(xs)*st.pstdev(ys)):+.3f}")
print(f"  effect sd: STANDARD={st.pstdev(xs):.2f}  TURBO={st.pstdev(ys):.2f}")

# --- 3. patch stability ----------------------------------------------------
print("\n== Patch stability of opponent effects (pos1+pos3 pooled, STANDARD+TURBO for sample) ==")
def pool(patches):
    out=[]
    for p in ('POSITION_1','POSITION_3'):
        out += [r for r in subset(p, 'ALL_PICK_RANKED', patches=patches, structure='2v2') if r['cs10'] is not None]
        out += [r for r in subset(p, 'TURBO', patches=patches, structure='2v2') if r['cs10'] is not None]
    return out
a=pool((180,181)); b=pool((182,))
print(f"  patch 180/181 n={len(a)}   patch 182 n={len(b)}")
ma=fit(a,'cs10',True,True,True,False); mb=fit(b,'cs10',True,True,True,False)
ca=collections.Counter(h for r in a for h in r['opps']); cb=collections.Counter(h for r in b for h in r['opps'])
common=[h for h in set(ma[2])&set(mb[2]) if ca[h]>=60 and cb[h]>=60]
xs=[ma[2][h] for h in common]; ys=[mb[2][h] for h in common]
mx,my=st.fmean(xs),st.fmean(ys)
cov=st.fmean([(p-mx)*(q-my) for p,q in zip(xs,ys)])
print(f"  corr(opponent effect 180/181 vs 182) over {len(common)} heroes (>=60 obs each) = {cov/(st.pstdev(xs)*st.pstdev(ys)):+.3f}")

# --- 4. sample size needed -------------------------------------------------
print("\n== How much data is needed? split-half reliability of opponent effects (pos1+pos3 STANDARD+TURBO patch182) ==")
base=[r for r in b]
rnd=random.Random(3)
for n in (2000, 5000, 10000, 20000, len(base)):
    if n>len(base): continue
    sub=rnd.sample(base,n)
    h1,h2=sub[:n//2],sub[n//2:]
    m1=fit(h1,'cs10',True,True,True,False); m2=fit(h2,'cs10',True,True,True,False)
    c1=collections.Counter(h for r in h1 for h in r['opps']); c2=collections.Counter(h for r in h2 for h in r['opps'])
    cm=[h for h in set(m1[2])&set(m2[2]) if c1[h]>=20 and c2[h]>=20]
    if len(cm)<10: print(f"  n={n}: too few comparable heroes"); continue
    xs=[m1[2][h] for h in cm]; ys=[m2[2][h] for h in cm]
    mx,my=st.fmean(xs),st.fmean(ys)
    cov=st.fmean([(p-mx)*(q-my) for p,q in zip(xs,ys)])
    print(f"  n={n:6d} rows/half={n//2:6d} heroes compared={len(cm):3d} split-half corr={cov/(st.pstdev(xs)*st.pstdev(ys)):+.3f}")
