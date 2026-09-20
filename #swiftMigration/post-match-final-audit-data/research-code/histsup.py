import pickle, statistics as st, json
from collections import defaultdict, Counter
H = pickle.load(open("hist_rows.pkl", "rb"))
out = {}
# 1) role effect on own item timing within account
d = defaultdict(lambda: defaultdict(list))
for a, rows in H.items():
    for r in rows:
        for n, t in r["own_items"].items(): d[(a, r["bucket"], n)][r["role"]].append(t)
diffs = defaultdict(list)
for (a, b, n), byr in d.items():
    good = {ro: st.median(v) for ro, v in byr.items() if len(v) >= 5}
    if "support" in good and any(k in good for k in ("carry", "mid", "offlane")):
        core = min(good[k] for k in ("carry", "mid", "offlane") if k in good)
        diffs[(b, n)].append(good["support"] - core)
    cores = [k for k in ("carry", "mid", "offlane") if k in good]
    if len(cores) >= 2:
        diffs[(b, n, "core-core")].append(max(good[k] for k in cores) - min(good[k] for k in cores))
out["item_role_gap_sec"] = {str(k): (len(v), round(st.median(v))) for k, v in diffs.items() if len(v) >= 3}
# how often an item "record" in bucket+item cohort happens in a different role than the prior record holder's role mix
# 2) mixing effect: records under bucket+item that are NOT records under bucket+role+item
mix = Counter()
for a, rows in H.items():
    p1 = defaultdict(list); p2 = defaultdict(list)
    for r in rows:
        for n, t in r["own_items"].items():
            k1 = (r["bucket"], n); k2 = (r["bucket"], r["role"], n)
            if len(p1[k1]) >= 20 and len(p2[k2]) >= 20:
                a1 = t < min(p1[k1]); a2 = t < min(p2[k2]); mix[(a1, a2)] += 1
            if len(p1[k1]) >= 20:
                srt = sorted(p1[k1]); 
                if t < srt[0] or t > srt[-1]:
                    roles = Counter(x[1] for x in []); 
            p1[k1].append(t); p2[k2].append(t)
out["fastest_record_bucketitem_vs_roleitem(both N>=20)"] = {str(k): v for k, v in mix.items()}
# 3) enemy metrics by user role (pooled)
for m in ("enemy_stacks", "enemy_smokes"):
    byr = defaultdict(list)
    for rows in H.values():
        for r in rows:
            if r["feed"] or m not in r: continue
            if m == "enemy_stacks" and r["bucket"] != "STANDARD": continue
            byr[(r["bucket"], r["role"])].append(r[m] / (r["dur"] / 600) if m == "enemy_smokes" else r[m])
    out[f"{m}_by_user_role_median_p90"] = {f"{k[0][:3]}|{k[1]}": (len(v), round(st.median(v), 2), round(sorted(v)[int(.9 * len(v))], 2)) for k, v in sorted(byr.items())}
# 4) patch drift (pooled + within account) for 180 vs 182
def pm(fn):
    res = {}
    for b in ("STANDARD", "TURBO"):
        by = defaultdict(list); wa = defaultdict(lambda: defaultdict(list))
        for a, rows in H.items():
            for r in rows:
                if r["bucket"] != b or r["feed"]: continue
                v = fn(r)
                if v is None: continue
                by[r["patch"]].append(v); wa[a][r["patch"]].append(v)
        paired = [st.median(x[182]) - st.median(x[180]) for x in wa.values() if len(x.get(180, [])) >= 15 and len(x.get(182, [])) >= 15]
        res[b] = dict(pooled={p: (len(v), round(st.median(v), 2)) for p, v in by.items() if len(v) >= 30},
                      within_account_182_minus_180=(len(paired), round(st.median(paired), 2) if paired else None, [round(x, 1) for x in paired]))
    return res
out["drift_lane_abs"] = pm(lambda r: abs(r["lane_diff"]) if r.get("lane_diff") is not None and r["role"] != "support" else None)
out["drift_opp_cs_core"] = pm(lambda r: r.get("opp_val") if r.get("opp_pos") in (1, 2, 3) else None)
out["drift_bkb_time"] = pm(lambda r: r["own_items"].get("item_black_king_bar"))
out["drift_blink_time"] = pm(lambda r: r["own_items"].get("item_blink"))
out["drift_enemy_stacks"] = pm(lambda r: r.get("enemy_stacks"))
out["drift_enemy_smoke_rate"] = pm(lambda r: r["enemy_smokes"] / r["dur"] * 600)
out["drift_enemy_goal"] = pm(lambda r: r["enemy_goal"][0] if r.get("enemy_goal") else None)
out["drift_duration"] = pm(lambda r: r["dur"] / 60)
# 5) time span of histories and patch mix per account
out["account_span_days"] = sorted(round((rows[-1]["start"] - rows[0]["start"]) / 86400) for rows in H.values() if rows)
out["accounts_with_both_180_182"] = sum(1 for rows in H.values() if Counter(r["patch"] for r in rows)[180] >= 15 and Counter(r["patch"] for r in rows)[182] >= 15)
# 6) Free at link: history = the 30 most recent bucket matches before the evaluation (bootstrap), cohort counts within that
free = defaultdict(Counter); tot = Counter()
for rows in H.values():
    byb = defaultdict(list)
    for r in rows:
        prior = byb[r["bucket"]][-30:]
        if len(byb[r["bucket"]]) >= 30:
            k = (r["bucket"], r["role"]); tot[k] += 1
            n_role = sum(1 for x in prior if x["role"] == r["role"])
            for N in (10, 20, 30): free[k][N] += n_role >= N
            items = r["own_items"]
            for it in items:
                n_it = sum(1 for x in prior if it in x["own_items"])
                free[(r["bucket"], "item")]["ev"] += 1
                for N in (10, 20): free[(r["bucket"], "item")][N] += n_it >= N
        byb[r["bucket"]].append(r)
out["free_bootstrap30_role_cohort_ge_N"] = {f"{k[0][:3]}|{k[1]}": {N: round(100 * free[k][N] / tot[k], 1) for N in (10, 20, 30)} for k in tot}
out["free_bootstrap30_item_cohort_ge_N"] = {b[:3]: {N: round(100 * free[(b, 'item')][N] / free[(b, 'item')]['ev'], 1) for N in (10, 20)} for b in ("STANDARD", "TURBO")}
json.dump(out, open("hist_sup.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:9000])
