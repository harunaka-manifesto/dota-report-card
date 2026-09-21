"""Final locked pool (POST-MATCH-INSIGHT-DECISIONS-V1) — deterministic candidate generation + severity levels (research).

Every candidate returns a Card with:
  cid, tier (A/B), family, side (enemy/own/match/personal), band (1 NOTABLE, 2 STRONG, 3 EXTREME),
  lvl  = continuous level on the candidate's own threshold ladder (0 at qualify, 1 at strong, 2 at extreme, capped 3),
  exc  = (value - qualify) / (strong - qualify) clipped [0, 3]   (Model 2 input),
  value, facts (dict), text (diagnostic rendering, not product copy), guard flags.
Guards are parameterised in G so the audit can switch them on/off and measure the effect.
"""
from __future__ import annotations
import math, pickle, statistics as st
from collections import defaultdict

D = pickle.load(open("base.pkl", "rb"))
TH, CHECK, TB_TT = D["TH"], D["CHECK"], D["TB_TT"]

def Q(v, q):
    v = sorted(x for x in v if x is not None)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))] if v else None

# ---------------------------------------------------------------- empirical ladders (existing corpus, feed excluded)
_R = [r for r in D["rows"] if not r["feed"]]
_U = {}
for r in _R: _U.setdefault((r["mid"], r["side"]), r)
_U = list(_U.values())
LAD = {}
for b in ("STANDARD", "TURBO"):
    cores = [r for r in _R if r["bucket"] == b and r["role"] != "support" and r["lane"].get("lane_status") == "ok"]
    UB = [u for u in _U if u["bucket"] == b]
    late = [abs(r["lane"]["nwdiff_late"]) for r in cores]; swing = [abs(r["lane"]["nwdiff_late"] - r["lane"]["nwdiff_early"]) for r in cores]
    wins = [-u["turn"]["lead_min"] for u in UB if u["win"] and u["turn"].get("lead_min") is not None]
    flips = [max(u["flips"])[0] for u in UB if u["flips"]]
    srate = [u["hidden"]["enemy_smokes"] / u["dur"] * 600 for u in UB]
    LAD[b] = dict(
        e50=TH[b]["core"]["e50"], l50=TH[b]["core"]["l50"],
        lane_l=(Q(late, .90), Q(late, .95), Q(late, .99)),
        lane_sw=(Q(swing, .90), Q(swing, .95), Q(swing, .99)),
        comeback=(Q(wins, .90), Q(wins, .95), Q(wins, .99)),
        flip=(TH[b]["flip75"], Q(flips, .90), Q(flips, .975)),
        stacks=(7, 9, 13),
        smoke=(Q(srate, .90), Q(srate, .95), Q(srate, .99)),
        quick=((4, 5, 6) if b == "STANDARD" else (3, 4, 5)),
        sweep=(3, 4, 5),
        rich_gap=((3, 5, 7) if b == "STANDARD" else (3, 4, 6)),
        rich_min=(TH[b]["fast10"], TH[b]["fast5"], Q([u["hidden"]["enemy_fastest_goal"][0] for u in UB if u["hidden"].get("enemy_fastest_goal")], .01)),
        item_margin=(0.0, 0.12, 0.20),
        gold_floor=5000 if b == "STANDARD" else 8000,
        le_strong_peak=10000 if b == "STANDARD" else 15000,
        le_ext_peak=15000 if b == "STANDARD" else 22000,
    )

G = dict(  # guard switches (audit toggles these)
    lane_blowout_min_band=1,       # BLOWOUT (dominated/crushed) shown from this band
    lane_supports=False,
    flip_exclude_final=3,          # a flip's new run must start before end - N minutes
    comeback_sustain=1,            # deficit/lead must be >= threshold for N consecutive minutes
    sweep_final=5, sweep_deficit=10000, quick_final=5,
    tb_min_conf=0.7,
    ets_loser_final_guard=True,
    late_rev_tail=0.25,
    rich_turbo_gap_only=False,
    item_subset_only=False,
    smoke_min_strong_diff=4,
    v2=False,                      # guard set v2 (audit round 1)
)
V2 = dict(lane_dramatic_enabled=False, comeback_sustain=1, comeback_truncate=3, flip_truncate=3, flip_pick="latest", le_end_guard=True,
          ct_min_share=0.75, ct_min_window={"STANDARD": 20, "TURBO": 16}, ets_max_pre_gap=7500, ets_min_window={"STANDARD": 18, "TURBO": 20},
          smoke_min_diff={"STANDARD": 4, "TURBO": 3}, quick_min={"STANDARD": 4, "TURBO": 4}, sweep_max_median_life=180, sweep_lead_abs=10000,
          rich_exclude_heroes={"Alchemist"}, rich_require_own=True, item_allow={"item_black_king_bar", "item_blink", "item_manta", "item_bfury", "item_radiance", "item_desolator", "item_maelstrom", "item_orchid"},
          item_min_margin=0.10, le_floor={"STANDARD": 5000, "TURBO": 10000}, smoke_modes={"STANDARD"}, sweep_min_start=300, rich_min_tail=8, le_min_peak_offset=6)
def g(k, default=None):
    return V2[k] if G["v2"] else default
ITEM_MED = {b: {} for b in ("STANDARD", "TURBO")}
for _u in _U:
    for _n, (_t, _h, _p) in _u["enemy_key_first"].items():
        if _p in (1, 2, 3): ITEM_MED[_u["bucket"]].setdefault(_n, []).append(_t)
ITEM_MED = {b: {n: st.median(v) for n, v in d.items()} for b, d in ITEM_MED.items()}
STRONG_ITEMS = {"item_black_king_bar", "item_blink", "item_radiance", "item_bfury", "item_manta"}

def ladder(v, q, s, e, reverse=False):
    """continuous level: 0 at q, 1 at s, 2 at e, capped at 3 (linear beyond e with step e-s)."""
    if reverse: v, q, s, e = -v, -q, -s, -e
    if v < q: return None
    if v < s: return (v - q) / (s - q) if s > q else 0.0
    if v < e: return 1 + (v - s) / (e - s) if e > s else 1.0
    return min(3.0, 2 + ((v - e) / (e - s) if e > s else 0.0))

def card(cid, tier, fam, side, lvl, value, exc, text, facts, band=None, **kw):
    b = band if band is not None else (1 if lvl < 1 else (2 if lvl < 2 else 3))
    return dict(cid=cid, tier=tier, family=fam, side=side, band=b, lvl=round(lvl, 3), exc=round(max(0.0, min(3.0, exc)), 3), value=value, text=text, facts=facts, **kw)

def ka(x): return f"{x/1000:+.1f}k"
def k0(x): return f"{abs(x)/1000:.1f}k"
def mmss(s): return f"{int(s)//60}:{int(s)%60:02d}"
def nm(item): return item.replace("item_", "").replace("_", " ")

# ================================================================ TIER A — LANE
def lane_dramatic(r):
    if G["v2"] and not V2["lane_dramatic_enabled"]: return None
    if r["feed"] or r["lane"].get("lane_status") != "ok": return None
    if r["role"] == "support" and not G["lane_supports"]: return None
    L = r["lane"]; b = r["bucket"]; Z = LAD[b]; e, l = L["nwdiff_early"], L["nwdiff_late"]; C = CHECK[b]
    if e is None or l is None: return None
    ctx = f"{ka(e)} @{C['early']}:00 → {ka(l)} @{C['late']}:00 vs {L['opp_hero']} (P{L['opp_pos']}); CS {L['cs_late']}-{L['opp_cs_late']}, deaths {L['deaths_late']}-{L['opp_deaths_late']}"
    if (e > 0) != (l > 0) and abs(e) >= Z["e50"] and abs(l) >= Z["l50"]:
        lv = ladder(abs(l - e), *Z["lane_sw"])
        if lv is None: return None
        sub = "REVERSAL_TO_BEHIND" if e > 0 else "REVERSAL_TO_AHEAD"
        return card("LANE_DRAMATIC", "A", "lane", "own", lv, abs(l - e), (abs(l - e) - Z["lane_sw"][0]) / (Z["lane_sw"][1] - Z["lane_sw"][0]), f"[{sub}] {ctx}", dict(sub=sub, early=e, late=l), sub=sub)
    lv = ladder(abs(l), *Z["lane_l"])
    if lv is None: return None
    if abs(e) < Z["e50"]: sub = "SEPARATED_AHEAD" if l > 0 else "SEPARATED_BEHIND"
    elif (e > 0) == (l > 0): sub = "BLOWOUT_AHEAD" if l > 0 else "BLOWOUT_BEHIND"
    else: return None
    c = card("LANE_DRAMATIC", "A", "lane", "own", lv, abs(l), (abs(l) - Z["lane_l"][0]) / (Z["lane_l"][1] - Z["lane_l"][0]), f"[{sub}] {ctx}", dict(sub=sub, early=e, late=l), sub=sub)
    if sub.startswith("BLOWOUT") and c["band"] < G["lane_blowout_min_band"]: return None
    return c

# history-driven lane/item cards are produced by history.py (they need chronological priors)

# ================================================================ TIER A — MATCH LEAD STORY
def _sustained_extreme(lc, thr, sign, k):
    """longest run of minutes with sign*lead >= thr"""
    best = run = 0
    for v in lc:
        run = run + 1 if sign * v >= thr else 0; best = max(best, run)
    return best >= k

def comeback_or_lost(r):
    u = r; tu = u["turn"]; b = u["bucket"]; Z = LAD[b]
    if tu.get("lead_min") is None: return None
    lc = u["lc"]
    if G["v2"]:
        lc = lc[:max(1, len(lc) - V2["comeback_truncate"])]
        tu = dict(tu, lead_min=min(lc), lead_max=max(lc))
    if u["win"]:
        v = -tu["lead_min"]; lv = ladder(v, *Z["comeback"])
        if lv is None or not _sustained_extreme(lc, Z["comeback"][0], -1, g("comeback_sustain", G["comeback_sustain"])): return None
        worst = lc.index(tu["lead_min"])
        last_trail = max((t for t, x in enumerate(lc) if x < 0), default=None)
        return card("COMEBACK_WIN", "A", "lead", "match", lv, v, (v - Z["comeback"][0]) / (Z["comeback"][1] - Z["comeback"][0]),
                    f"[COMEBACK_WIN] trailed by {k0(v)} at {worst}:00 and won ({u['dur']//60}m); last behind at {last_trail}:00", dict(deficit=v, minute=worst, last_trail=last_trail))
    v = tu["lead_max"]; lv = ladder(v, *Z["comeback"])
    if lv is None or not _sustained_extreme(lc, Z["comeback"][0], 1, g("comeback_sustain", G["comeback_sustain"])): return None
    best = lc.index(v)
    return card("LOST_FROM_AHEAD", "A", "lead", "match", lv, v, (v - Z["comeback"][0]) / (Z["comeback"][1] - Z["comeback"][0]),
                f"[LOST_FROM_AHEAD] led by {k0(v)} at {best}:00 and lost ({u['dur']//60}m)", dict(lead=v, minute=best))

def _flips(lc, lane_end):
    signs = [1 if v >= 1500 else (-1 if v <= -1500 else 0) for v in lc]
    runs = []; cur, start = 0, 0
    for t, x in enumerate(signs + [None]):
        if x != cur:
            if cur != 0 and t - start >= 3: runs.append((cur, start, t - 1))
            cur, start = x, t
    out = []
    for a, c in zip(runs, runs[1:]):
        if a[0] != c[0] and c[1] >= lane_end:
            pa = max(abs(x) for x in lc[a[1]:a[2] + 1]); pc = max(abs(x) for x in lc[c[1]:c[2] + 1])
            out.append((min(pa, pc), a, c, pa, pc))
    return out

def lead_flip(r):
    u = r; b = u["bucket"]; Z = LAD[b]; lc = u["lc"]; endm = len(lc) - 1
    if G["v2"]:
        fl = _flips(lc[:max(0, len(lc) - V2["flip_truncate"])], CHECK[b]["lane_end"])
        fl = [f for f in fl if f[0] >= Z["flip"][0]]
        if not fl: return None
        mn, a, c, pa, pc = fl[-1]          # latest qualifying flip (the one that leads into the final state)
    else:
        fl = [f for f in u["flips"] if f[2][1] <= endm - G["flip_exclude_final"]]
        if not fl: return None
        mn, a, c, pa, pc = max(fl)
    lv = ladder(mn, *Z["flip"])
    if lv is None: return None
    sub = "FLIP_AGAINST" if a[0] > 0 else "FLIP_FOR"
    return card("LEAD_FLIP", "A", "lead", "match", lv, mn, (mn - Z["flip"][0]) / (Z["flip"][1] - Z["flip"][0]),
                f"[{sub}] {'your team' if a[0] > 0 else 'enemy'} led up to {k0(pa)} ({a[1]}:00–{a[2]}:00), then {'enemy' if a[0] > 0 else 'your team'} led up to {k0(pc)} ({c[1]}:00–{c[2]}:00); result {'W' if u['win'] else 'L'}",
                dict(sub=sub, peak_before=pa, peak_after=pc, run_before=a, run_after=c), sub=sub)

# ================================================================ TIER A — HIDDEN ENEMY
def stacking(r):
    h = r["hidden"]; b = r["bucket"]
    if b != "STANDARD" or "enemy_stacks" not in h: return None
    e, o = h["enemy_stacks"], h["own_stacks"]
    if e - o < 4: return None
    lv = ladder(e, *LAD[b]["stacks"])
    if lv is None: return None
    return card("ENEMY_STACKING", "A", "hidden", "enemy", lv, e, (e - 7) / 2, f"[ENEMY_STACKING] enemy stacked {e} camps by 20:00 vs your team {o}", dict(enemy=e, own=o))

def _vision_ids(r):
    v = r["vis"]
    return v["idd"] if v else None

def vision_quick(r):
    v = r["vis"]; b = r["bucket"]
    if not v or not v["placed"]: return None
    idd = [a for a in v["idd"] if a["t"] < r["dur"] - G["quick_final"] * 60]
    k = sum(1 for a in idd if a["life"] <= 90); k60 = sum(1 for a in idd if a["life"] <= 60)
    if k / v["placed"] < .25: return None
    q = LAD[b]["quick"]
    if G["v2"]: q = (V2["quick_min"][b], V2["quick_min"][b] + 1, V2["quick_min"][b] + 2)
    lv = ladder(k, *q)
    if lv is None: return None
    return card("VISION_QUICK_CLEARS", "A", "hidden", "enemy", lv, k, (k - q[0]) / (q[1] - q[0]),
                f"[QUICK_CLEARS] {k} of your {v['placed']} observers destroyed within 90s of placement ({k60} within 60s); enemy destroyed {v['killed']} total", dict(k=k, k60=k60, placed=v["placed"], killed=v["killed"]))

def vision_sweep(r):
    v = r["vis"]; b = r["bucket"]
    if not v: return None
    lc = r["lc"]; best = None
    idd = v["idd"]
    for a in idd:
        c = [x for x in idd if x["region"] == a["region"] and a["t"] <= x["t"] <= a["t"] + 300]
        end = max(x["t"] for x in c)
        if end >= r["dur"] - G["sweep_final"] * 60: continue
        lead0 = lc[min(len(lc) - 1, a["t"] // 60)]
        if lead0 <= -G["sweep_deficit"]: continue
        if G["v2"] and (a["t"] < V2["sweep_min_start"] or abs(lead0) >= V2["sweep_lead_abs"] or st.median(x["life"] for x in c) > V2["sweep_max_median_life"]): continue
        if best is None or len(c) > len(best[0]): best = (c, a["region"], a["t"], end, lead0)
    if not best: return None
    c, reg, t0, t1, lead0 = best
    lv = ladder(len(c), *LAD[b]["sweep"])
    if lv is None: return None
    lives = sorted(x["life"] for x in c)
    return card("VISION_REGION_SWEEP", "A", "hidden", "enemy", lv, len(c), len(c) - 3,
                f"[SWEEP] {len(c)} observers in {reg} destroyed {mmss(t0)}–{mmss(t1)} (lived {lives} s); lead at start {ka(lead0)}", dict(n=len(c), region=reg, t0=t0, t1=t1, lives=lives, lead0=lead0))

def smoke_volume(r):
    h = r["hidden"]; b = r["bucket"]; rate = h["enemy_smokes"] / r["dur"] * 600; Z = LAD[b]
    e, o = h["enemy_smokes"], h["own_smokes"]
    if G["v2"] and b not in V2["smoke_modes"]: return None
    if e < (4 if b == "STANDARD" else 3) or e < o + (V2["smoke_min_diff"][b] if G["v2"] else 2): return None
    lv = ladder(rate, *Z["smoke"])
    if lv is None: return None
    if lv >= 1 and e - o < G["smoke_min_strong_diff"]: lv = min(lv, 0.999)
    return card("ENEMY_SMOKE_VOLUME", "A", "hidden", "enemy", lv, rate, (rate - Z["smoke"][0]) / (Z["smoke"][1] - Z["smoke"][0]),
                f"[SMOKES] enemy used Smoke {e} times ({rate:.2f}/10min) vs your team {o}; {r['dur']//60}m", dict(enemy=e, own=o, rate=rate))

def early_rich(r):
    h = r["hidden"]; b = r["bucket"]; Z = LAD[b]
    if not h.get("enemy_fastest_goal"): return None
    m, hero, pos = h["enemy_fastest_goal"]; own = h.get("own_fastest_goal")
    if m > Z["rich_min"][0]: return None
    if G["v2"] and (hero in V2["rich_exclude_heroes"] or (V2["rich_require_own"] and own is None) or r["dur"] / 60 - m < V2["rich_min_tail"]): return None
    gap = (own - m) if own is not None else 99
    if gap < 3: return None
    g = min(gap, 12)
    lv = ladder(g, *Z["rich_gap"])
    # band caps by minute ladder (Turbo p10 == p5 so the gap carries the band there)
    if lv >= 1 and not (m <= Z["rich_min"][1] or (b == "TURBO")): lv = 0.999
    if lv >= 2 and not (m <= Z["rich_min"][2] or own is None): lv = 1.999
    goal = CHECK[b]["nw_goal"]
    return card("ENEMY_EARLY_RICH", "A", "hidden", "enemy", lv, g, (g - 3) / (Z["rich_gap"][1] - 3),
                f"[EARLY_RICH] {hero} (P{pos}) reached {goal//1000}k NW at {m}:00; your team's first {('at ' + str(own) + ':00') if own is not None else 'never'}", dict(hero=hero, pos=pos, minute=m, own=own, gap=gap))

# ================================================================ TIER A — POWER SPIKES
def enemy_item(r):
    b = r["bucket"]; T = TH[b]["enemy_item"]; best = None
    for n, (t, hero, pos) in r["enemy_key_first"].items():
        if n not in T or pos not in (1, 2, 3): continue
        if G["item_subset_only"] and n not in STRONG_ITEMS: continue
        if G["v2"] and n not in V2["item_allow"]: continue
        p5 = T[n][1]
        if t > p5: continue
        mg = (p5 - t) / p5
        if G["v2"] and mg < V2["item_min_margin"]: continue
        if best is None or mg > best[0]: best = (mg, n, t, hero, pos, p5)
    if not best: return None
    mg, n, t, hero, pos, p5 = best
    lad = (0.10, 0.15, 0.22) if G["v2"] else LAD[b]["item_margin"]
    lv = ladder(mg, *lad)
    med = ITEM_MED[b].get(n)
    return card("ENEMY_EARLY_ITEM", "A", "power", "enemy", lv, mg, (mg - lad[0]) / (lad[1] - lad[0]),
                f"[ENEMY_EARLY_ITEM] {hero} (P{pos}) bought {nm(n)} at {mmss(t)} (typical core {nm(n)} {mmss(med)}; bucket core p5 {mmss(p5)}; {mg:.0%} earlier than p5)", dict(item=n, t=t, hero=hero, pos=pos, p5=p5, median=med, margin=mg, strong_item=n in STRONG_ITEMS))

# ================================================================ TIER B — MATCH SHAPE
def _tb(r):
    t = r["tb"]
    if not t or t["label"] in ("SHORT_WINDOW", "UNCLEAR"): return None
    if r["feed"]: return None
    return t

def _mods(r):
    m = r["tb_mods"] or {}; out = []
    for x in m.get("STRUCTURE_COUNTERTREND", []): out.append(f"+counter: trailing side destroyed {-x['leader_net']} more structures during {x['edge_minutes']} lead minutes")
    for x in m.get("NO_STRUCTURE_CONVERSION", []): out.append(f"+noconv: {'your team' if x['leader'] > 0 else 'enemy'} led {x['start']}:00–{x['end']}:00 with no net structure change")
    return out

def tier_b(r):
    t = _tb(r)
    if not t: return []
    conf = r["tb_conf"] or 0
    if conf < G["tb_min_conf"]: return []
    b = r["bucket"]; lab = t["label"]; d = t.get("detail") or {}; lc = r["lc"]; S0, E0 = t["S"], t["Emin"]; Z = LAD[b]; out = []
    mods = _mods(r)
    if lab == "CT":
        if G["v2"] and (t["close_share"] < V2["ct_min_share"] or t["n"] < V2["ct_min_window"][b]): return _late_rev(r, t, [])
        cs = t["close_share"]; lateclose = (t.get("latest_close_minute") or 0) >= E0 - 2
        longw = t["n"] >= (25 if b == "STANDARD" else 14)
        lv = 0.5 * max(0, (cs - 0.6) / 0.4)
        if cs >= 0.8 and lateclose and longw: lv = 1 + 0.5 * max(0, (cs - 0.8) / 0.2)
        out.append(card("CLOSE_MOST_OF_GAME", "B", "shape", "match", lv, cs, (cs - 0.6) / 0.2,
                        f"[CLOSE_MOST] {S0}:00–{E0}:00 close {cs:.0%} of minutes; gap never held above {k0(t['max_sustained_gold'])} for 3 min; latest close {t.get('latest_close_minute')}:00 (window {t['n']}m, match {r['dur']//60}m) " + " ".join(mods),
                        dict(close_share=cs, msg=t["max_sustained_gold"], late_close=lateclose, n=t["n"]), conf=conf))
    elif lab.startswith("ETS"):
        s = t["dir"]; sep = d["sep_minute"]; pre_end = max(S0, sep - 3)
        mx = max(abs(lc[x]) for x in range(S0, pre_end + 1))
        if G["ets_loser_final_guard"] and ((s > 0) != r["win"]): return _late_rev(r, t, [])
        if G["v2"]:
            pre_sus = max(abs(x) for x in lc[S0:max(S0, sep - 3) + 1])   # v3: single-minute max, same number the copy states
            if pre_sus > V2["ets_max_pre_gap"] or t["n"] < V2["ets_min_window"][b]: return _late_rev(r, t, [])   # separation for the side that then lost the game
        late_sep = sep >= (30 if b == "STANDARD" else 18)
        lv = 0.5 if not late_sep else 1.2
        out.append(card("EVEN_THEN_SEPARATED", "B", "shape", "match", lv, sep, 0.0,
                        f"[ETS_{'FOR' if s > 0 else 'AGAINST'}] until {pre_end}:00 the gap never exceeded {k0(mx)}; from {sep}:00 {'your team' if s > 0 else 'enemy'} held a sustained lead: {k0(lc[sep])} at {sep}:00, {k0(lc[E0])} at {E0}:00; result {'W' if r['win'] else 'L'} ({r['dur']//60}m) " + " ".join(mods),
                        dict(dir=s, sep=sep, pre_max=mx), conf=conf))
    elif lab in ("LE", "DR"):
        g_ref, g_late = d["gold_ref"], d["gold_late"]; ge = (g_ref - g_late) / g_ref if g_ref > 0 else 0
        sgn = 1 if lab == "LE" else -1
        endv = sgn * lc[E0]
        floor = V2["le_floor"][b] if G["v2"] else Z["gold_floor"]
        if G["v2"]:
            interim = min(sgn * lc[m] for m in range(d["ref_minute"], E0 + 1))
            if (g_ref < floor or not (-floor <= endv <= max(0.5 * floor, 0.25 * g_ref)) or interim < -2 * floor
                    or d["ref_minute"] < S0 + V2["le_min_peak_offset"]): return _late_rev(r, t, [])
        lv = 0.4 * min(1, (ge - 0.5) / 0.5)
        if g_ref >= Z["le_strong_peak"] and ge >= 0.75: lv = 1.2
        if g_ref >= Z["le_ext_peak"] and ge >= 0.9: lv = 2.2
        cid = "LEAD_ERODED" if lab == "LE" else "DEFICIT_RECOVERED"
        who = "your team" if lab == "LE" else "enemy"
        out.append(card(cid, "B", "shape", "match", lv, ge, (ge - 0.5) / 0.25,
                        f"[{cid}] {who}'s lead peaked {k0(g_ref)} at {d['ref_minute']}:00 and was {k0(endv) if endv > 0 else ('gone (' + ka(lc[E0]) + ' for your side)')} at {E0}:00; result {'W' if r['win'] else 'L'} ({r['dur']//60}m); final-minute lead {ka(lc[-1])} " + " ".join(mods),
                        dict(g_ref=g_ref, g_late=g_late, gold_erosion=ge, peak_min=d["ref_minute"]), conf=conf))
    return _late_rev(r, t, out)

def _late_rev(r, t, out):
    b = r["bucket"]; lc = r["lc"]; S0, E0 = t["S"], t["Emin"]; Z = LAD[b]; conf = r["tb_conf"] or 0
    if r["win"] and t.get("runs"):
        last = t["runs"][-1]
        if last[0] == -1 and last[2] >= S0 + (1 - G["late_rev_tail"]) * t["n"] - 1:
            peak = max(-lc[m] for m in range(last[1], last[2] + 1))
            if peak >= Z["gold_floor"]:
                lv = 0.5 if peak < Z["le_strong_peak"] else 1.3
                out.append(card("LATE_REVERSAL", "B", "shape", "match", lv, peak, (peak - Z["gold_floor"]) / (Z["le_strong_peak"] - Z["gold_floor"]),
                                f"[LATE_REVERSAL] enemy held a sustained lead {last[1]}:00–{last[2]}:00 (up to {k0(peak)}); at {E0}:00 {ka(lc[E0])}; you won at {r['dur']//60}:{r['dur']%60:02d}; final-minute lead {ka(lc[-1])}",
                                dict(run=last, peak=peak, end_lead=lc[E0]), conf=conf))
    return out

NONHIST = [lane_dramatic, comeback_or_lost, lead_flip, stacking, vision_quick, vision_sweep, smoke_volume, early_rich, enemy_item]

def generate(r, hist_cards=()):
    cards = []
    for f in NONHIST:
        c = f(r)
        if c: cards.append(c)
    cards += tier_b(r)
    cards += list(hist_cards)
    return cards

# ================================================================ FINAL SEVERITY LADDERS (v3) — applied when G["v2"]
LADDER = {   # (NOTABLE qualify, STRONG, EXTREME) on the candidate's own magnitude; per mode where needed
    "COMEBACK_WIN":        {"STANDARD": (12000, 19500, 31000), "TURBO": (18300, 23700, 33500)},   # max deficit (gold), p90/p95/p99
    "LOST_FROM_AHEAD":     {"STANDARD": (12000, 19500, 31000), "TURBO": (18300, 23700, 33500)},   # max lead (gold)
    "LEAD_FLIP":           {"STANDARD": (7900, 12100, 21900), "TURBO": (14200, 19400, 27500)},    # min(peak before, peak after), p75/p90/p97.5 of flips
    "ENEMY_STACKING":      {"STANDARD": (7, 9, 13)},                                              # enemy stacks by 20:00, p90/p95/p99
    "VISION_QUICK_CLEARS": {"STANDARD": (4, 5, 6), "TURBO": (4, 5, 6)},                           # observers destroyed <=90s
    "VISION_REGION_SWEEP": {"STANDARD": (3, 4, 5), "TURBO": (3, 4, 5)},                           # observers in one region within 5 min
    "ENEMY_SMOKE_VOLUME":  {"STANDARD": (4, 6, 8)},                                               # enemy minus own smoke uses (rate gate separate)
    "ENEMY_EARLY_RICH":    {"STANDARD": (3, 5, 7), "TURBO": (3, 4, 6)},                           # minutes before your team's first to the goal
    "ENEMY_EARLY_ITEM":    {"STANDARD": (0.10, 0.15, 0.22), "TURBO": (0.10, 0.15, 0.22)},         # share earlier than bucket core p5
}
def _mag(c):
    f = c["facts"]; cid = c["cid"]
    if cid == "COMEBACK_WIN": return f["deficit"]
    if cid == "LOST_FROM_AHEAD": return f["lead"]
    if cid == "LEAD_FLIP": return min(f["peak_before"], f["peak_after"])
    if cid == "ENEMY_STACKING": return f["enemy"]
    if cid == "VISION_QUICK_CLEARS": return f["k"]
    if cid == "VISION_REGION_SWEEP": return f["n"]
    if cid == "ENEMY_SMOKE_VOLUME": return f["enemy"] - f["own"]
    if cid == "ENEMY_EARLY_RICH": return min(f["gap"], 12)
    if cid == "ENEMY_EARLY_ITEM": return f["margin"]
def tierb_band(c, r):
    """Tier B categorical ladders: NOTABLE by default; STRONG only for the exceptional version; no EXTREME except LE/DR."""
    f = c["facts"]; b = r["bucket"]; cid = c["cid"]
    if cid == "CLOSE_MOST_OF_GAME":
        strong = f["close_share"] >= 0.9 and f["late_close"] and f["n"] >= (30 if b == "STANDARD" else 20)
        return (2, 1.0 + (f["close_share"] - 0.9) * 5) if strong else (1, (f["close_share"] - 0.75) / 0.15 * 0.99)
    if cid == "EVEN_THEN_SEPARATED":
        strong = f["sep"] >= (30 if b == "STANDARD" else 20) and f["pre_max"] <= 5000
        return (2, 1.0) if strong else (1, 0.5)
    if cid in ("LEAD_ERODED", "DEFICIT_RECOVERED"):
        pk, ge = f["g_ref"], f["gold_erosion"]
        if pk >= (15000 if b == "STANDARD" else 22000) and ge >= 0.9: return (3, 2.0)
        if pk >= (10000 if b == "STANDARD" else 15000) and ge >= 0.75: return (2, 1.0 + min(0.99, (ge - 0.75) * 4))
        return (1, min(0.99, (ge - 0.5) * 2))
    if cid == "LATE_REVERSAL":
        strong = f["peak"] >= (10000 if b == "STANDARD" else 15000)
        return (2, 1.0) if strong else (1, 0.5)
    return (c["band"], c["lvl"])
def finalize(c, r):
    if c["tier"] == "B":
        c["band"], c["lvl"] = tierb_band(c, r); c["exc"] = c["lvl"]; return c
    L = LADDER.get(c["cid"], {}).get(r["bucket"])
    if L:
        v = _mag(c); lv = ladder(v, *L)
        if lv is None: lv = 0.0
        c["lvl"] = round(lv, 3); c["band"] = 1 if lv < 1 else (2 if lv < 2 else 3)
        c["exc"] = round(max(0.0, min(3.0, (v - L[0]) / (L[1] - L[0]))), 3)
    return c

_generate_v1 = generate
def generate(r, hist_cards=()):
    cs = _generate_v1(r, hist_cards)
    if not G["v2"]: return cs
    out = [finalize(c, r) for c in cs]
    # specific combination guard candidates are evaluated in the cross-card audit (not applied here)
    return out
