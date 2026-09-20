import pickle, json, statistics as st, os, sys
from collections import defaultdict
sys.path.insert(0, "../candidate-validation-2026-09-15"); os.chdir("../candidate-validation-2026-09-15")
from primitives import ITEMS, HEROES, pos_num, bucket
os.chdir("../final-audit-2026-09-16")
import histbuild as HB   # reuses loaded matches M and elig
TH = pickle.load(open("base.pkl", "rb"))["TH"]
SP = {"item_black_king_bar","item_blink","item_radiance","item_hand_of_midas","item_manta","item_desolator","item_bfury","item_maelstrom","item_ultimate_scepter","item_orchid"}
hero_item = defaultdict(list); fires = []
for m in HB.M.values():
    if HB.elig(m): continue
    b = bucket(m)
    for p in m["players"]:
        if pos_num(p) > 3: continue
        for n, t in HB.first_buy(p).items():
            hero_item[(b, p["heroId"], n)].append(t)
            T = TH[b]["enemy_item"].get(n)
            if T and t <= T[1]: fires.append((b, p["heroId"], n, t, (T[1]-t)/T[1]))
res = {}
for label, cond in (("all p5 fires", lambda f: True), ("margin>=10%", lambda f: f[4] >= .10), ("no midas/aghs", lambda f: f[2] not in ("item_hand_of_midas","item_ultimate_scepter")),
                    ("no midas/aghs & margin>=10%", lambda f: f[2] not in ("item_hand_of_midas","item_ultimate_scepter") and f[4] >= .10),
                    ("BKB/Blink/Manta only", lambda f: f[2] in ("item_black_king_bar","item_blink","item_manta")),
                    ("BKB/Blink/Manta & margin>=10%", lambda f: f[2] in ("item_black_king_bar","item_blink","item_manta") and f[4] >= .10)):
    sel = [f for f in fires if cond(f)]
    typ = []
    for b, h, n, t, mg in sel:
        v = sorted(hero_item[(b, h, n)])
        if len(v) < 30: continue
        rank = sum(1 for x in v if x < t) / len(v)   # share of this hero's own purchases earlier than this one
        typ.append(rank)
    res[label] = dict(fires=len(sel), with_hero_ref=len(typ), share_early_for_hero_p10=round(sum(1 for x in typ if x <= .10)/len(typ),3) if typ else None,
                      share_typical_for_hero_gt_p25=round(sum(1 for x in typ if x > .25)/len(typ),3) if typ else None)
print(json.dumps(res, indent=1))
json.dump(res, open("hero_typicality.json","w"), indent=1)
