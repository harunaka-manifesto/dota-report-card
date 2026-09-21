"""Cross-validated variance decomposition for laning metrics."""
import pickle, collections, random, math, sys

rows = pickle.load(open('rows.pkl', 'rb'))

def subset(pos, mode, patches=(180, 181, 182), structure=None):
    out = []
    for r in rows:
        if r['pos'] != pos or r['mode'] != mode or r['patch'] not in patches:
            continue
        if structure and f"{r['n_allies']+1}v{r['n_opps']}" != structure:
            continue
        if r['cs10'] is None or r['nw10'] is None:
            continue
        out.append(r)
    return out

def shrunk(sums, counts, grand, k):
    return {g: (sums[g] - counts[g] * grand) / (counts[g] + k) for g in counts}

def fit(train, target, use_own, use_opp, use_ally, use_pair, k=25.0, iters=6):
    ys = [r[target] for r in train]
    grand = sum(ys) / len(ys)
    own = {}; opp = {}; ally = {}; pair = {}
    for _ in range(iters):
        def base(r):
            v = grand
            if use_own: v += own.get(r['hero'], 0.0)
            if use_opp: v += sum(opp.get(h, 0.0) for h in r['opps'])
            if use_ally: v += sum(ally.get(h, 0.0) for h in r['allies'])
            if use_pair: v += pair.get(r['opps'], 0.0)
            return v
        if use_own:
            s = collections.defaultdict(float); c = collections.Counter()
            for r in train:
                res = r[target] - (base(r) - own.get(r['hero'], 0.0))
                s[r['hero']] += res; c[r['hero']] += 1
            own = {g: s[g] / (c[g] + k) for g in c}
        if use_opp:
            s = collections.defaultdict(float); c = collections.Counter()
            for r in train:
                for h in r['opps']:
                    res = r[target] - (base(r) - opp.get(h, 0.0))
                    s[h] += res; c[h] += 1
            opp = {g: s[g] / (c[g] + k) for g in c}
        if use_ally:
            s = collections.defaultdict(float); c = collections.Counter()
            for r in train:
                for h in r['allies']:
                    res = r[target] - (base(r) - ally.get(h, 0.0))
                    s[h] += res; c[h] += 1
            ally = {g: s[g] / (c[g] + k) for g in c}
        if use_pair:
            s = collections.defaultdict(float); c = collections.Counter()
            for r in train:
                res = r[target] - (base(r) - pair.get(r['opps'], 0.0))
                s[r['opps']] += res; c[r['opps']] += 1
            pair = {g: s[g] / (c[g] + k) for g in c}
    return grand, own, opp, ally, pair

def predict(model, r, use_own, use_opp, use_ally, use_pair):
    grand, own, opp, ally, pair = model
    v = grand
    if use_own: v += own.get(r['hero'], 0.0)
    if use_opp: v += sum(opp.get(h, 0.0) for h in r['opps'])
    if use_ally: v += sum(ally.get(h, 0.0) for h in r['allies'])
    if use_pair: v += pair.get(r['opps'], 0.0)
    return v

def cv_r2(data, target, flags, k=25.0, folds=5, seed=7):
    rnd = random.Random(seed)
    idx = list(range(len(data))); rnd.shuffle(idx)
    sse = 0.0; sst = 0.0
    ys = [data[i][target] for i in idx]
    gm = sum(ys) / len(ys)
    preds = []
    for f in range(folds):
        test = [data[i] for j, i in enumerate(idx) if j % folds == f]
        train = [data[i] for j, i in enumerate(idx) if j % folds != f]
        model = fit(train, target, *flags, k=k)
        for r in test:
            p = predict(model, r, *flags)
            preds.append((r[target], p))
    for y, p in preds:
        sse += (y - p) ** 2
        sst += (y - gm) ** 2
    return 1 - sse / sst, gm, math.sqrt(sst / len(preds))

MODELS = [
    ("M0 grand mean",              (False, False, False, False)),
    ("M1 own hero",                (True,  False, False, False)),
    ("M2 own + opponents",         (True,  True,  False, False)),
    ("M3 own + opp + ally",        (True,  True,  True,  False)),
    ("M4 + exact opponent pair",   (True,  True,  True,  True)),
]

def report(label, data, targets=('cs10', 'nw10')):
    print(f"\n### {label}  n={len(data)} matches~{len(set(r['match_id'] for r in data))}")
    for t in targets:
        d = [r for r in data if r[t] is not None]
        if len(d) < 400:
            print(f"  {t}: too few rows ({len(d)})"); continue
        line = []
        for name, flags in MODELS:
            r2, gm, sd = cv_r2(d, t, flags)
            line.append((name, r2))
        _, gm, sd = cv_r2(d, t, MODELS[0][1])
        print(f"  {t}: mean={gm:.1f} sd={sd:.1f}")
        for name, r2 in line:
            print(f"      {name:<28} CV R2 = {r2:+.4f}   (explains {max(r2,0)*100:5.2f}% of variance; sd_expl={sd*math.sqrt(max(r2,0)):.1f})")

if __name__ == '__main__':
    report("POS_1 STANDARD (ranked AP) 2v2", subset('POSITION_1', 'ALL_PICK_RANKED', structure='2v2'))
    report("POS_2 STANDARD mid 1v1",        subset('POSITION_2', 'ALL_PICK_RANKED', structure='1v1'))
    report("POS_3 STANDARD 2v2",            subset('POSITION_3', 'ALL_PICK_RANKED', structure='2v2'))
    report("POS_5 STANDARD 2v2",            subset('POSITION_5', 'ALL_PICK_RANKED', structure='2v2'))
