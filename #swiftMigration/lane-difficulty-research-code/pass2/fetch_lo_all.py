"""Fetch heroStats.laneOutcome for every hero at P1/P2/P3, both directions."""
import sc, json, time
heroes=[h['id'] for h in sc.call('auth_probe','{ constants { heroes { id } } }')['data']['constants']['heroes']]
Q="""query($h:Short!,$w:Boolean!,$p:[MatchPlayerPositionType!]){heroStats{laneOutcome(heroId:$h,isWith:$w,positionIds:$p){heroId1 heroId2 week position matchCount csCount}}}"""
jobs=[("POSITION_1",False),("POSITION_1",True),("POSITION_2",False),("POSITION_3",False),("POSITION_3",True)]
out={}
t0=time.time(); done=0; fail=0
for pos,w in jobs:
    tag='with' if w else 'vs'
    acc=[]
    for h in heroes:
        r=sc.call(f'lo_{pos}_{tag}_{h}', Q, {"h":h,"w":w,"p":[pos]}, cache=True)
        done+=1
        if r.get('errors') or not (r.get('data') or {}).get('heroStats'):
            fail+=1; continue
        acc += (r['data']['heroStats']['laneOutcome'] or [])
    out[f"{pos}|{tag}"]=acc
    n=sum(x['matchCount'] or 0 for x in acc)
    print(f"{pos} {tag}: {len(acc)} pair-rows, {n:,} lane observations  [{done} calls, {fail} failed, {time.time()-t0:.0f}s]", flush=True)
json.dump(out, open('laneoutcome_all.json','w'))
print("saved. total calls:", done, "failed:", fail)
