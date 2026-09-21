"""Plain factual renderings for review (not production copy)."""
from shape import *
def mmss(s): return f"{int(s)//60}:{int(s)%60:02d}"
def k(g): return f"{'+' if g >= 0 else '-'}{abs(g)/1000:.1f}k"
def timeline(u, r, step=None):
    step = step or (3 if u["bucket"] == "STANDARD" else 2)
    last = len(u["lc"]) - 1
    pts = list(range(r["S"], last + 1, step))
    if pts[-1] != last: pts.append(last)
    return " ".join(f"{t}:{k(u['lc'][t])}({100*u['R'][t]:+.0f}%)" for t in pts)
def struct_line(u, r):
    ev = [(t, us) for t, us, kind, tier in u["structs"]]
    took = [mmss(t) for t, us in ev if not us]; lost = [mmss(t) for t, us in ev if us]
    return f"took {len(took)} [{', '.join(took)}] | lost {len(lost)} [{', '.join(lost)}]"
def describe(u, r):
    lab = r["label"]; d = r.get("detail") or {}; b = base_of(lab)
    head = f"{u['bucket'][:3]} {'W' if u['win'] else 'L'} {u['dur']//60}m window {r['S']}:00-{r['Emin']}:00 (n={r['n']})"
    if lab == "SHORT_WINDOW": return head + " SHORT_WINDOW"
    runs = "; ".join(f"{'FOR' if s > 0 else 'AGAINST'} {a}-{b_}" for s, a, b_ in r["runs"]) or "none"
    lc = u["lc"]
    if b == "ETS": x = f"separated {'for' if r['dir']>0 else 'against'} us at {d['sep_minute']}:00; before: close share {d['close_share_before']:.0%}, median lead {100*d['lead_before']:+.1f}%; after: edge share {d['edge_share_after']:.0%}, median {100*d['lead_after']:+.1f}%; net structures after {d['structs_after']:+d}"
    elif b in ("LE", "DR"): x = f"{'our' if b=='LE' else 'their'} lead peaked {100*d['ref']:.1f}% at {d['ref_minute']}:00 ({k(lc[d['ref_minute']])}) and ended window at {100*d['late']:.1f}% (erosion {d['erosion']:.0%}); net structures since peak (leader view) {d['structs_after_peak']:+d}"
    elif b == "OS": x = f"{'we' if r['dir']>0 else 'they'} held a meaningful edge {d['edge_share']:.0%} of window from {d['first_edge_minute']}:00; strong-edge run {d['strong_minutes']} min; net structures {d['net_structs']:+d}"
    elif b == "SE": x = f"{'we' if r['dir']>0 else 'they'} held a meaningful edge {d['edge_share']:.0%} of window; net structures {d['net_structs']:+d}"
    elif b == "SWAP": x = f"sustained edges both ways ({d['n_runs']} runs)"
    else: x = f"close share {r['close_share']:.0%}, max sustained lead {100*r['max_sustained_lead']:.1f}%, lead changes {r['lead_changes']}, first edge {r['first_edge_minute']}, latest close {r['latest_close_minute']}"
    return f"{head} [{lab}] {x} || runs: {runs} || lead: {timeline(u, r)} || structures: {struct_line(u, r)}"
