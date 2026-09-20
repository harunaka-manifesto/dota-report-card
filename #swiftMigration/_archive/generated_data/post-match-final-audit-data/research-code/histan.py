"""History availability + stability by N (real chronological account histories)."""
import pickle, json, statistics as st, random
from collections import defaultdict, Counter
H = pickle.load(open("hist_rows.pkl", "rb"))
NS = [3, 5, 7, 10, 15, 20, 25, 30, 50]
SPIKE = ["item_black_king_bar", "item_blink", "item_radiance", "item_hand_of_midas", "item_manta", "item_desolator", "item_bfury", "item_maelstrom", "item_ultimate_scepter", "item_orchid"]
CORE = ("carry", "mid", "offlane")

def series(metric):
    """yield (acct, row, key_variants dict, value, direction) for each evaluation in chronological order"""
    for a, rows in H.items():
        for r in rows:
            if r["feed"]: continue
            b = r["bucket"]
            if metric == "own_lane":
                if r.get("lane_diff") is None: continue
                yield a, r, {"bucket": (b,), "bucket+role": (b, r["role"]), "bucket+pos": (b, r["pos"])}, r["lane_diff"], "both"
            elif metric == "opp_start":
                if r.get("opp_val") is None: continue
                yield a, r, {"bucket+role": (b, r["role"]), "bucket+opp_pos": (b, r["opp_pos"]), "bucket": (b,)}, r["opp_val"], "max"
            elif metric == "own_item":
                for n, t in r["own_items"].items():
                    yield a, r, {"bucket+item": (b, n), "bucket+role+item": (b, r["role"], n), "bucket+hero+item": (b, r["hero"], n)}, t, "both"
            elif metric == "enemy_stacks":
                if b != "STANDARD" or "enemy_stacks" not in r: continue
                yield a, r, {"bucket": (b,), "bucket+role": (b, r["role"])}, r["enemy_stacks"], "max"
            elif metric == "enemy_smoke_rate":
                yield a, r, {"bucket": (b,), "bucket+role": (b, r["role"])}, r["enemy_smokes"] / r["dur"] * 600, "max"
            elif metric == "enemy_goal":
                if not r.get("enemy_goal"): continue
                yield a, r, {"bucket": (b,), "bucket+role": (b, r["role"])}, r["enemy_goal"][0], "min"
            elif metric == "enemy_item":
                for n, (t, h, pos) in r["enemy_items"].items():
                    if n in ("item_black_king_bar", "item_blink", "item_manta", "item_radiance", "item_bfury", "item_desolator", "item_maelstrom", "item_orchid"):
                        yield a, r, {"bucket+item": (b, n), "bucket+role+item": (b, r["role"], n)}, t, "min"

METRICS = ["own_lane", "opp_start", "own_item", "enemy_stacks", "enemy_smoke_rate", "enemy_goal", "enemy_item"]
PRIMARY = {"own_lane": "bucket+role", "opp_start": "bucket+role", "own_item": "bucket+item", "enemy_stacks": "bucket", "enemy_smoke_rate": "bucket", "enemy_goal": "bucket", "enemy_item": "bucket+item"}

def prank(v, arr, direction):
    """share of prior strictly 'less extreme' than v in the claim direction (0..1)."""
    if direction == "min": return sum(1 for x in arr if x > v) / len(arr)
    return sum(1 for x in arr if x < v) / len(arr)

OUT = {"availability": {}, "stability": {}, "availability_by": {}}
for metric in METRICS:
    avail = defaultdict(lambda: Counter()); tot = Counter()
    by_bucket_role = defaultdict(lambda: Counter()); tot_br = Counter()
    evals = defaultdict(list)   # keyname -> list of (prior list, value, direction, row)
    prior = defaultdict(lambda: defaultdict(list))
    for a, r, keys, v, d in series(metric):
        for kn, k in keys.items():
            pr = prior[kn][(a,) + k]
            n = len(pr); tot[kn] += 1
            for N in NS:
                if n >= N: avail[kn][N] += 1
            if kn == PRIMARY[metric]:
                seg = (r["bucket"], r["role"]); tot_br[seg] += 1
                for N in (5, 10, 20, 30):
                    if n >= N: by_bucket_role[seg][N] += 1
                evals[kn].append((list(pr), v, d, r))
            pr.append(v)
    OUT["availability"][metric] = {kn: {N: round(100 * avail[kn][N] / tot[kn], 1) for N in NS} | {"evaluations": tot[kn]} for kn in tot}
    OUT["availability_by"][metric] = {f"{s[0][:3]}|{s[1]}": {N: round(100 * by_bucket_role[s][N] / tot_br[s], 1) for N in (5, 10, 20, 30)} | {"n": tot_br[s]} for s in sorted(tot_br)}
    # ---- stability vs reference window (most recent REF prior values)
    REF = 60 if metric not in ("own_item", "enemy_item") else 40
    stab = {}
    E = [e for e in evals[PRIMARY[metric]] if len(e[0]) >= REF]
    for N in NS:
        if N > REF: continue
        rec_n = rec_prec = top3_n = top3_prec = unu_n = unu_prec = 0; perr = []; merr = []; cnt = 0
        for pr, v, d, r in E:
            ref = pr[-REF:]; win = pr[-N:]; cnt += 1
            dirs = ["max", "min"] if d == "both" else [d]
            q1, q3 = sorted(ref)[len(ref) // 4], sorted(ref)[3 * len(ref) // 4]; iqr = (q3 - q1) or 1
            merr.append(abs(st.median(win) - st.median(ref)) / iqr)
            for dd in dirs:
                pw, pf = prank(v, win, dd), prank(v, ref, dd)
                perr.append(abs(pw - pf))
                is_rec = pw == 1.0
                if is_rec:
                    rec_n += 1; rec_prec += (pf >= 0.95)          # still within the most extreme 5% of the long reference
                top3 = sum(1 for x in win if (x > v if dd == "max" else x < v)) < 3 and N >= 5
                if top3:
                    top3_n += 1; top3_prec += (pf >= 0.90)
                if N >= 10:
                    srt = sorted(win); p90 = srt[int(0.9 * (len(srt) - 1))] if dd == "max" else srt[int(0.1 * (len(srt) - 1))]
                    un = v > p90 if dd == "max" else v < p90
                    srf = sorted(ref); r90 = srf[int(0.9 * (len(srf) - 1))] if dd == "max" else srf[int(0.1 * (len(srf) - 1))]
                    if un:
                        unu_n += 1; unu_prec += (v > r90 if dd == "max" else v < r90)
        nd = cnt * (2 if E and E[0][2] == "both" else 1)
        stab[N] = dict(evals=cnt, record_rate=round(100 * rec_n / nd, 1) if nd else None, record_precision_top5pct_ref=round(100 * rec_prec / rec_n, 1) if rec_n else None,
                       top3_rate=round(100 * top3_n / nd, 1) if nd and N >= 5 else None, top3_precision_top10pct_ref=round(100 * top3_prec / top3_n, 1) if top3_n else None,
                       unusual_rate=round(100 * unu_n / nd, 1) if N >= 10 and nd else None, unusual_precision=round(100 * unu_prec / unu_n, 1) if unu_n else None,
                       pct_rank_abs_err=round(st.mean(perr), 3) if perr else None, median_err_iqr=round(st.mean(merr), 3) if merr else None)
    OUT["stability"][metric] = dict(reference_window=REF, evaluations_with_ref=len(E), by_N=stab)
json.dump(OUT, open("hist_results.json", "w"), indent=1)
for metric in METRICS:
    print("\n=====", metric)
    for kn, v in OUT["availability"][metric].items(): print("  avail", kn, v)
    for s, v in OUT["availability_by"][metric].items(): print("   ", s, v)
    S = OUT["stability"][metric]; print("  stability ref", S["reference_window"], "n", S["evaluations_with_ref"])
    for N, v in S["by_N"].items(): print("   N", N, v)
