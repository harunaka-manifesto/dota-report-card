"""How large is the lane-environment adjustment, and do 3 buckets carry it?"""
import pickle, collections, random, math, statistics as st
from vardecomp import subset, fit, predict

def env_analysis(label, pos, mode, structure, target='cs10', k=25.0):
    data = [r for r in subset(pos, mode, structure=structure) if r[target] is not None]
    rnd = random.Random(11)
    idx = list(range(len(data))); rnd.shuffle(idx)
    folds = 5
    out = []
    for f in range(folds):
        test = [data[i] for j, i in enumerate(idx) if j % folds == f]
        train = [data[i] for j, i in enumerate(idx) if j % folds != f]
        grand, own, opp, ally, pair = fit(train, target, True, True, True, False, k=k)
        for r in test:
            env = sum(opp.get(h, 0.0) for h in r['opps']) + sum(ally.get(h, 0.0) for h in r['allies'])
            hero_e = own.get(r['hero'], 0.0)
            out.append((r, env, hero_e, grand))
    envs = sorted(e for _, e, _, _ in out)
    heros = sorted(h for _, _, h, _ in out)
    n = len(envs)
    q = lambda v, p: v[int(p * (len(v) - 1))]
    mean = st.fmean(r[target] for r, _, _, _ in out)
    sd = st.pstdev(r[target] for r, _, _, _ in out)
    print(f"\n=== {label} | target={target} n={n} mean={mean:.1f} sd={sd:.1f}")
    print(f"  ENV (opp+ally) offset: p05={q(envs,.05):+.2f} p10={q(envs,.10):+.2f} p25={q(envs,.25):+.2f} "
          f"p50={q(envs,.50):+.2f} p75={q(envs,.75):+.2f} p90={q(envs,.90):+.2f} p95={q(envs,.95):+.2f} sd={st.pstdev(envs):.2f}")
    print(f"  OWN HERO offset:       p05={q(heros,.05):+.2f} p10={q(heros,.10):+.2f} p50={q(heros,.50):+.2f} "
          f"p90={q(heros,.90):+.2f} p95={q(heros,.95):+.2f} sd={st.pstdev(heros):.2f}")
    # tercile buckets on env
    lo, hi = q(envs, 1/3), q(envs, 2/3)
    buckets = collections.defaultdict(list)
    for r, e, h, g in out:
        b = 'DIFFICULT' if e <= lo else ('EASY' if e >= hi else 'NORMAL')
        buckets[b].append((r[target], r['deaths10'], r['win']))
    print(f"  tercile cuts on env: <= {lo:+.2f} DIFFICULT, >= {hi:+.2f} EASY")
    for b in ('DIFFICULT', 'NORMAL', 'EASY'):
        v = buckets[b]
        print(f"    {b:<10} n={len(v):6d} mean {target}={st.fmean(x[0] for x in v):7.2f}  "
              f"mean deaths<10={st.fmean(x[1] for x in v):.3f}  winrate={st.fmean(1 if x[2] else 0 for x in v):.3f}")
    spread = st.fmean(x[0] for x in buckets['EASY']) - st.fmean(x[0] for x in buckets['DIFFICULT'])
    print(f"    EASY - DIFFICULT gap = {spread:+.2f} {target}  ({100*spread/mean:+.1f}% of mean, {spread/sd:.2f} sd)")
    # how much of the continuous env signal survives 3-bucket collapse?
    bmeans = {b: st.fmean(x[0] for x in buckets[b]) for b in buckets}
    sse_c = sum((r[target] - (g + h + e)) ** 2 for r, e, h, g in out)
    sse_b = sum((r[target] - (g + h + (bmeans['DIFFICULT'] if e <= lo else (bmeans['EASY'] if e >= hi else bmeans['NORMAL'])) + 0)) ** 2 for r, e, h, g in out)
    print(f"    (diagnostic only) continuous vs 3-bucket residual SSE ratio: {sse_b/sse_c:.4f}")
    # correlation env vs deaths (circularity sniff)
    es = [e for _, e, _, _ in out]; ds = [r['deaths10'] for r, _, _, _ in out]
    me, md = st.fmean(es), st.fmean(ds)
    cov = st.fmean([(a-me)*(b-md) for a, b in zip(es, ds)])
    corr = cov / (st.pstdev(es) * st.pstdev(ds))
    print(f"    corr(env_score, deaths_before_10) = {corr:+.3f}")
    return out

if __name__ == '__main__':
    for tgt in ('cs10', 'nw10'):
        env_analysis("POS_1 STANDARD 2v2", 'POSITION_1', 'ALL_PICK_RANKED', '2v2', tgt)
        env_analysis("POS_2 STANDARD 1v1", 'POSITION_2', 'ALL_PICK_RANKED', '1v1', tgt)
        env_analysis("POS_3 STANDARD 2v2", 'POSITION_3', 'ALL_PICK_RANKED', '2v2', tgt)
