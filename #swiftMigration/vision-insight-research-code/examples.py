import math, statistics as st, collections, pickle, random
from common import *
from geo import *
core, rep, pb = load_all()
U = pickle.load(open("hist_ident_units.pkl", "rb"))
rng = random.Random(11)
def Q(v, q): v = sorted(v); return v[min(len(v) - 1, int(round(q * (len(v) - 1))))] if v else None
def mm(s): return f"{int(s)//60}:{int(s)%60:02d}"
NAME = {"OWN_HALF": "your half of the map", "ENEMY_HALF": "their half of the map", "RIVER": "the river", "OWN_BASE": "your base", "ENEMY_BASE": "their base"}
# H2r-a (existing Tier A) per bucket
for b in ("STANDARD", "TURBO"):
    R = [u for u in U if u["bucket"] == b]
    krate = [u["killed"] / u["dur"] * 600 for u in R]; share = [u["killed"] / u["placed"] for u in R if u["placed"] >= 8]
    k90 = Q(krate, .9); s75 = Q(share, .75)
    for u in R: u["h2ra"] = u["placed"] >= 8 and u["killed"] / u["placed"] >= s75 and u["killed"] / u["dur"] * 600 >= k90
    q4 = lambda u: u["quick90"] >= (4 if b == "STANDARD" else 3) and u["quick90"] / max(1, u["placed"]) >= .25
    for u in R: u["quick_rule"] = q4(u); u["sweep_rule"] = u["cluster"] >= 3
    h = [u for u in R if u["h2ra"]]
    print(b, "H2r-a fires", round(100 * len(h) / len(R), 1), "| QUICK rule", round(100 * sum(u['quick_rule'] for u in R) / len(R), 1), "| SWEEP", round(100 * sum(u['sweep_rule'] for u in R) / len(R), 1),
          "| within H2r-a: quick", round(100 * sum(u['quick_rule'] for u in h) / len(h)), "% sweep", round(100 * sum(u['sweep_rule'] for u in h) / len(h)), "% either", round(100 * sum(u['quick_rule'] or u['sweep_rule'] for u in h) / len(h)), "%",
          "| outside H2r-a either", round(100 * sum((u['quick_rule'] or u['sweep_rule']) and not u['h2ra'] for u in R) / len(R), 1))
def team_desc(u):
    m = core[u["mid"]]
    return f"{u['bucket'][:3]} {'W' if u['win'] else 'L'} {u['dur']//60}m match {u['mid']} {'Radiant' if u['side'] else 'Dire'}"
def lead_at(u, t):
    lc = lead_curve(core[u["mid"]], u["side"]); return lc[min(len(lc) - 1, int(t // 60))]
def render(u):
    lines = [f"placed {u['placed']} observers; enemy destroyed {u['killed']} ({u['killed']/max(1,u['placed']):.0%}); identified {u['identified']}; cleared <=90s {u['quick90']} (<=60s {u['quick60']}); median life of identified clears {u['cleared_life_median']}s"]
    if u["cluster"] >= 3:
        rg, a, b = u["cluster_info"]
        c = [x for x in u["idd"] if x["region"] == rg and a <= x["t"] <= b]
        m = core[u["mid"]]
        es = sum(1 for p in m["players"] if p["isRadiant"] != u["side"] for w in p["stats"]["wards"] or [] if w["type"] == 1 and a - 90 <= w["time"] <= b and region(w["positionX"], w["positionY"], u["side"]) == rg)
        lines.append(f"sweep: {len(c)} observers in {NAME[rg]} destroyed {mm(a)}-{mm(b)} (lives {[x['life'] for x in c]}s); enemy placed {es} sentries in that region in the window; lead at start {lead_at(u,a):+}, at end+3m {lead_at(u,b+180):+}")
    if u["top_killer"]: lines.append(f"top dewarder {u['top_killer'][0]} (P{u['top_killer'][1]}) {u['top_count']} of {u['killed']}")
    lines.append(f"enemy sentries {u['esent']} ({u['esent_ownhalf']} in your half); lead at 10/20/end {lead_at(u,600):+}/{lead_at(u,1200):+}/{lead_at(u,u['dur']):+}")
    return " | ".join(lines)
pick = lambda f, k: rng.sample([u for u in U if f(u)], min(k, sum(1 for u in U if f(u))))
print("\n== QUICK + SWEEP both")
for u in pick(lambda u: u["quick_rule"] and u["sweep_rule"], 5): print(team_desc(u), "::", render(u))
print("\n== SWEEP own half")
for u in pick(lambda u: u["sweep_rule"] and u["cluster_info"][0] == "OWN_HALF" and not u["quick_rule"], 4): print(team_desc(u), "::", render(u))
print("\n== SWEEP in enemy base / late (likely end push)")
for u in pick(lambda u: u["sweep_rule"] and (u["cluster_info"][0] == "ENEMY_BASE" or u["cluster_info"][2] >= u["dur"] - 300), 4): print(team_desc(u), "::", render(u))
print("\n== H2r-a without quick/sweep (count only)")
for u in pick(lambda u: u["h2ra"] and not u["quick_rule"] and not u["sweep_rule"], 5): print(team_desc(u), "::", render(u))
print("\n== QUICK in stomp (killed high while far behind)")
for u in pick(lambda u: u["quick_rule"] and lead_at(u, 1200 if u['bucket']=='STANDARD' else 720) < -12000, 4): print(team_desc(u), "::", render(u))
print("\n== specialist")
for u in pick(lambda u: u["top_count"] >= 6 and u["top_count"] / max(1, u["killed"]) >= .7, 4): print(team_desc(u), "::", render(u))
pickle.dump(U, open("hist_ident_units2.pkl", "wb"))
