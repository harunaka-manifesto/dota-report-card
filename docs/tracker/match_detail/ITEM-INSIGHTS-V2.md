# Hero-specific item insight cards V2

**Scope:** Carry, Mid, and Offlane in Standard and Turbo on validated patch 7.41f. The `/mobile/v1` route stays fixed; the iOS client must understand `ENEMY_HERO_ITEM_V2`, `OWN_HERO_ITEM_RECORD_V2`, and their slots before release. Older stored V1 results remain visible.

## Evidence and review

The private local STRATZ corpus was read offline. Only de-identified 30-second first-purchase histograms were committed in `services/api/app/tracker/item_shards/`. The four current shards cover 7.41b–e; the corpus ends before 7.41f. STRATZ version 182 alone does not distinguish these lettered updates, so release-day matches were excluded and known release dates were used with the provider version ID. OpenDota patch 60 maps to major 7.41. Missing or unknown patch or purchase evidence yields no V2 item card.

The artifact records all **127 heroes × 3 core roles × 2 modes = 762** combinations, with item choices or a no-card reason. An item needs at least **50 observed first purchases** and a **20% purchase rate** within its hero, role, and mode. At most five eligible items per combination enter the reference. References store a 10th-percentile time and median time, calculated from 30-second aggregate bins. The artifact SHA-256 is persisted with each V2 insight result.

The 7.41f update changed 35 heroes and several strategic items. Those entries are withheld in the artifact pending fresh purchase evidence. Battle Fury's change affected Chop Tree cooldown rather than acquisition timing, and [current PA builds](https://dota2protracker.com/hero/legacy/Phantom%2BAssassin) still feature Battle Fury and BKB. [Current Medusa builds](https://dota2protracker.com/builds?position=pos+1) and [recent match inventories](https://dota2protracker.com/matches/8856075348) continue to show Manta and Butterfly. These pages inform **relevance only**; no pro-match timings were copied into the reference. The [7.41f change list](https://dota2protracker.com/patches/7.41f) informs the suspension list.

A de-identified review sampled 54 observed early purchases, nine per role/mode combination. Fifty were judged relevant. Four were marginal build choices (Phantom Lancer Orchid, Death Prophet Blink, Juggernaut Blink, and Offlane Razor Orchid), retained under the 80% relevance target because each clears the observed prevalence gate. All 54 sample purchase keys and times matched the retained provider events; the V2 copy makes no causal claim. This is a relevance judgment on the sampled cards, not a measured win-rate effect.

## Card rules

- `ENEMY_HERO_ITEM_V2`: the enemy's observed first purchase must be at least 10% **and** 60 seconds (Standard) or 30 seconds (Turbo) before that exact hero-role-mode item's p10. The card compares the observed time with the **median for that hero and role**, not a generic core median. No card is emitted if any required source is missing.
- `OWN_HERO_ITEM_RECORD_V2`: the observed first purchase must beat the previous fastest by at least 60/30 seconds. The window contains 20–50 strictly prior purchases of the **same item, hero, effective role, mode, and major patch**. N=19 fails; N=20 can qualify.
- Both candidates retain their existing ranking classes and the three-card match ceiling. An item purchase is never described as a completed item, a win cause, or a universal build recommendation.

## Next lettered update

1. Add its release and first full-day dates, update `CURRENT_PATCH` and any new STRATZ version ID, and review the changed hero/item suspension sets in `item_references.py`. Review changed purchase patterns before clearing a suspension. A new major patch starts an empty shard window.
2. Run `scripts/build_item_references.py --source <new-normalized-corpus> --patch <new-lettered-patch>`. It scans only the new source, saves one aggregate shard, and composes the latest five shards from the same major patch. Commit only the new shard, artifact, and reviewed mapping changes.
3. Verify the artifact digest, 762 coverage entries, PA/Medusa cases, provider shape tests, and a fresh 50-card relevance sample. If stored current-patch matches need V2, `scripts/rebuild_current_patch_items.py` replays retained snapshots for those matches without provider calls or notifications. Do not run it against production until the backend and iOS release is approved.

OpenDota research calls for this release: **0**. STRATZ research calls for this release: **0**. No provider calls were needed beyond the authorized local corpus.
