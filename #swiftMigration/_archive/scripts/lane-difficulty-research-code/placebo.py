"""Falsification tests: is the lane-composition effect lane-local, or a bracket proxy?"""
import pickle, collections, random, statistics as st
from vardecomp import subset, fit, rows

# rebuild match-level index so we can look at OTHER lanes of the same match
by_match = collections.defaultdict(list)
for r in rows:
    by_match[r['match_id']].append(r)

def run(mode='ALL_PICK_RANKED'):
    d = [r for r in subset('POSITION_1', mode, structure='2v2') if r['cs10'] is not None]
    rnd = random.Random(5); idx = list(range(len(d))); rnd.shuffle(idx)
    folds = 5; scored = []
    for f in range(folds):
        test = [d[i] for j, i in enumerate(idx) if j % folds == f]
        train = [d[i] for j, i in enumerate(idx) if j % folds != f]
        grand, own, opp, ally, _ = fit(train, 'cs10', True, True, True, False)
        for r in test:
            env = sum(opp.get(h, 0.0) for h in r['opps']) + sum(ally.get(h, 0.0) for h in r['allies'])
            scored.append((r, env))
    def corr(xs, ys):
        mx, my = st.fmean(xs), st.fmean(ys)
        cov = st.fmean([(a-mx)*(b-my) for a, b in zip(xs, ys)])
        sx, sy = st.pstdev(xs), st.pstdev(ys)
        return cov/(sx*sy) if sx and sy else float('nan')

    # A. own lane cs10 (expected: clearly positive)
    print(f"\n[{mode}] n={len(scored)}")
    print(f"  A  corr(env_score, OWN cs10)                    = {corr([e for _,e in scored],[r['cs10'] for r,_ in scored]):+.3f}")
    # B. same-team MID player's cs10 (bracket-proxy test; expected ~0)
    pairs_mid = []; pairs_opp1 = []; pairs_enemy_mid = []
    for r, e in scored:
        for q in by_match[r['match_id']]:
            if q is r or q['cs10'] is None: continue
            if q['pos'] == 'POSITION_2' and q['radiant'] == r['radiant']:
                pairs_mid.append((e, q['cs10']))
            if q['pos'] == 'POSITION_2' and q['radiant'] != r['radiant']:
                pairs_enemy_mid.append((e, q['cs10']))
            if q['pos'] == 'POSITION_3' and q['radiant'] != r['radiant'] and q['phys'] == r['phys']:
                pairs_opp1.append((e, q['cs10']))
    print(f"  B  corr(env_score, ALLIED MID cs10)  n={len(pairs_mid):5d}   = {corr([a for a,_ in pairs_mid],[b for _,b in pairs_mid]):+.3f}   <- bracket-proxy test, want ~0")
    print(f"  B2 corr(env_score, ENEMY  MID cs10)  n={len(pairs_enemy_mid):5d}   = {corr([a for a,_ in pairs_enemy_mid],[b for _,b in pairs_enemy_mid]):+.3f}   <- want ~0")
    print(f"  C  corr(env_score, DIRECT LANE OPPONENT pos3 cs10) n={len(pairs_opp1):5d} = {corr([a for a,_ in pairs_opp1],[b for _,b in pairs_opp1]):+.3f}   <- want NEGATIVE (mirror)")

    # D. placebo: score built from the OTHER side lane's heroes
    placebo = []
    for r, e in scored:
        other = [q for q in by_match[r['match_id']] if q['phys'] not in (r['phys'], 'MID') and q['radiant'] == (not r['radiant'])]
        if len(other) < 2: continue
        # reuse opponent effects but from the wrong lane
        placebo.append((r, other))
    grand, own, opp, ally, _ = fit(d, 'cs10', True, True, True, False)
    pl = [(sum(opp.get(q['hero'], 0.0) for q in o), r['cs10']) for r, o in placebo]
    print(f"  D  corr(PLACEBO env from other lane, OWN cs10) n={len(pl):5d} = {corr([a for a,_ in pl],[b for _,b in pl]):+.3f}   <- want ~0")

run('ALL_PICK_RANKED')
run('TURBO')
