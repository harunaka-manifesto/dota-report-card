import pickle, collections
a = pickle.load(open('rows.pkl','rb'))   # probe corpus, 10 rows/match
b = pickle.load(open('big.pkl','rb'))    # pass-2 corpus, 1 row/match
for r in a: r.setdefault('account', None); r.setdefault('xp10', None); r.setdefault('lvl6', None)
key = lambda r: (r['match_id'], r['hero'], r['pos'])
seen, out = set(), []
for r in b + a:                           # pass-2 rows win on conflict
    k = key(r)
    if k in seen: continue
    seen.add(k); out.append(r)
print("merged rows:", len(out), "from", len(a), "+", len(b))
print("unique matches:", len(set(r['match_id'] for r in out)))
c = collections.Counter((r['pos'], r['mode']) for r in out
                        if f"{r['n_allies']+1}v{r['n_opps']}" in ('2v2','1v1'))
for k, v in sorted(c.items(), key=lambda x: str(x[0])):
    if v > 2000: print(f"  {k}: {v}")
pickle.dump(out, open('merged.pkl','wb'))
