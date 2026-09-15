"""Phase 3 structure-timeline modifiers (towers + barracks only; ancient excluded). All counts are facts; no causal claims."""
from shape import *

MP_BASE = dict(align_k=2, counter_k=2, nsc_min={"STANDARD": 8, "TURBO": 5}, nsc_tol=0, burst_n=3, burst_w=5, burst_excl=3, lag=0)

def edge_periods(r):
    """Sustained edge runs grouped by leader sign: {s: [(start_min, end_min), ...]}."""
    g = {1: [], -1: []}
    for s, a, b in r.get("runs", []): g[s].append((a, b))
    return g

def modifiers(u, r, MP=MP_BASE):
    out = {}
    if r["label"] == "SHORT_WINDOW": return out
    g = edge_periods(r)
    lag = MP["lag"]
    per = []
    for s in (1, -1):
        mins = sum(b - a + 1 for a, b in g[s])
        if not mins: continue
        lead_net = sum(s * net_structs(u, a * 60, (b + 1 + lag) * 60) for a, b in g[s])
        per.append((mins, s, lead_net))
        if lead_net >= MP["align_k"]: out.setdefault("STRUCTURE_ALIGNED", []).append(dict(leader=s, edge_minutes=mins, leader_net=lead_net))
        if lead_net <= -MP["counter_k"]: out.setdefault("STRUCTURE_COUNTERTREND", []).append(dict(leader=s, edge_minutes=mins, leader_net=lead_net))
        for a, b in g[s]:
            if b - a + 1 >= MP["nsc_min"][u["bucket"]]:
                n = s * net_structs(u, a * 60, (b + 1 + lag) * 60)
                if abs(n) <= MP["nsc_tol"]:
                    out.setdefault("NO_STRUCTURE_CONVERSION", []).append(dict(leader=s, start=a, end=b, leader_net=n))
    # burst: >= N structures of one owner inside W minutes, from analysis start to end - excl
    t_lo = r["S"] * 60; t_hi = u["dur"] - MP["burst_excl"] * 60
    for owner_us in (True, False):
        ts = sorted(t for t, us, k, tier in u["structs"] if us == owner_us and t_lo <= t < t_hi)
        best = None
        for i, t in enumerate(ts):
            j = i
            while j + 1 < len(ts) and ts[j + 1] - t <= MP["burst_w"] * 60: j += 1
            if j - i + 1 >= MP["burst_n"] and (best is None or j - i + 1 > best[0]): best = (j - i + 1, t, ts[j])
        if best: out.setdefault("STRUCTURE_BURST", []).append(dict(we_lost=owner_us, count=best[0], start=best[1], end=best[2]))
    return out
