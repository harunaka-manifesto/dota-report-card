# Item timings and item insight cards — final

**Status:** ACTIVE — backend contract, final version. This is the single, final item-card and
item-timeline design; there is no planned successor.
**Scope:** The factual key-item timeline and its inline comparisons, stored with finalized Match
Detail analysis, plus the two item insight-card candidates they can produce.
**API contract:** `item-timings-v1` on [`GET /mobile/v1/matches/{match_ref}`](../api/README.md#match-detail-item-timings). Card contract: `post-match-insights 2.0.0` — the single insight contract for this and every other card family; there is no separate item-card version.
**Product authority:** [`SSOT.md`](SSOT.md) owns Match Detail meaning; this annex owns the item taxonomy, reference cohort, comparison algorithm and card rules.
**Population data:** [`ITEM-BUILD-PATTERNS-7.41.md`](ITEM-BUILD-PATTERNS-7.41.md) documents the per-hero reference cells this annex's baseline reads from.

## History

`ENEMY_EARLY_ITEM` and `OWN_ITEM_VS_HISTORY` (V1), and the `*_V2` / `*_V3` candidates from an
order-conditioned baseline design, were superseded before shipping — no stored analysis ever
used them. `ENEMY_HERO_ITEM` and `OWN_HERO_ITEM` under `post-match-insights 2.0.0` are the only
item cards that have ever shipped.

## Product boundary

The timeline is factual: it lists each key item from earliest to latest. Every role, including
Support, receives the timeline. Inline comparisons and item insight cards are limited to Carry,
Mid and Offlane. A missing comparison is `null`; it is never inferred from a different mode,
role, patch or item.

The timeline is replay-derived and becomes `AVAILABLE` with the finalized analysis snapshot. It
is backend-ready; iOS rendering remains pending — the iOS project does not exist yet. The
payload contains structured values and catalog-backed item names; localized prose belongs in the
content bank. Analysis and comparison selection are deterministic. No runtime LLM is used.

## Key-item timeline

A key item is any of:

- a purchasable, recipe-built item whose catalog cost is at least 1,400 gold;
- an upgraded descendant of base Boots; or
- a reviewed standalone strategic exception, including Blink Dagger.

Exclude base Boots, Magic Stick, Magic Wand, components, consumables, neutral items, recipes,
wards, detection, regeneration and teleport items. Keep the reviewed catalog
(`item_references.KEY_ITEMS`) as the single item identity/name source; do not infer eligibility
from a purchase name at runtime.

For each player, accept only well-formed canonical purchase events with an integer item identity
and a purchase time from `0` through match duration. Retain the first valid purchase of each
distinct key item. Ignore duplicate or rebuy rows, malformed rows, and events outside the match.
Base Boots and excluded components do not consume an order position. Each upgraded boot and each
later qualifying upgrade is a separate timeline entry.

Sort by `(purchase_time_seconds, item_id)` and number the resulting entries from one as
`key_item_order`. **This order is a match-local fact only.** It is never a baseline key, never a
build recommendation, and never conditions a population or personal comparison — the baseline is
hero × core role × mode × item. Item-order statistics computed from the corpus
([`ITEM-BUILD-PATTERNS-7.41.md`](ITEM-BUILD-PATTERNS-7.41.md)) are descriptive research context
only.

OpenDota and STRATZ purchase rows normalize to the same canonical event shape. Missing, malformed
or incompatible purchase evidence fails closed; it never creates an estimated time.

## Population reference artifact

The artifact (`services/api/app/tracker/item_references.json`, schema 3) is keyed by
`mode:hero:role:item` — **item-only, order plays no part in the key or in qualification.** It is
built from de-identified STRATZ corpus aggregates, patches 7.41b–7.41e pooled, and applies to
validated subpatch 7.41f (`CURRENT_PATCH`); its claims name the major patch "7.41".

Each reference stores:

```text
item_name: string
p10: int            # seconds, from 30-second purchase-time bins
p25: int
median: int
purchase_count: int  # first purchases of this item in this hero/role/mode cohort
cohort_games: int
purchase_rate: float # purchase_count / cohort_games
```

A cell publishes a reference only when:

1. the item was purchased in at least **50** first-purchase events for that hero, role and mode;
2. those purchases are at least **20%** of that cohort's games (`purchase_rate ≥ 0.20`); and
3. patch review has not suspended the hero/item pair (`SUSPENDED_HEROES` / `SUSPENDED_ITEMS`).

There is no per-cell item cap — every item that clears the gates gets a reference. The current
artifact has **791 references** across **762** hero × core-role × mode cells (127 heroes × 3
core roles × 2 modes): **153** cells carry at least one reference, **397** are `sparse`, **196**
are `patch_change_pending`, and **16** are `no_qualified_item`. Digest (sha256 of
`item_references.json`): `801853401f4181f2afb53525219468ce20a11d601e63ef8a975852c615aae852`. The
artifact contains no player identifiers; its deterministic digest is persisted with the analysis
snapshot.

Earlier letter-patch evidence may be pooled only for hero/item pairs unaffected by subsequent
patch notes. A changed pair needs current-letter evidence or stays `patch_change_pending`. Do not
clear a suspension based only on a matching provider version number. Patch review and the
checked-in suspension mapping (`SUSPENDED_HEROES`, `SUSPENDED_ITEMS` in `item_references.py`)
determine whether prior evidence remains usable. `reference(patch, mode, hero, role, item)`
returns `None` for any patch other than `CURRENT_PATCH`, so a match on an older patch never gets
a population reference — see "Old patches" below.

## Inline comparison selection

Evaluate at most one inline comparison for each core-role timeline item, in this order:

1. **`POPULATION_USUAL`** — the hero/role/mode/item population reference exists, the purchase is
   at or before its p25, and it beats the median by at least `max(10% of median, 60 seconds in
   Standard or 30 seconds in Turbo)`. `sample_size` is the reference's `purchase_count`.
2. **`PERSONAL_PREVIOUS_BEST`** — if no population comparison qualified, require at least 20
   strictly prior comparable purchases (same profile, hero, effective role, mode and major patch,
   same item) and beat the fastest prior time (the window minimum) by at least 60 seconds in
   Standard or 30 seconds in Turbo. `sample_size` is the window length.
3. **`PERSONAL_USUAL`** — if neither prior comparison qualified, require at least 10 strictly
   prior comparable purchases and beat their median by at least `max(10% of median, 60 seconds in
   Standard or 30 seconds in Turbo)`. `sample_size` is the window length.
4. Otherwise, return factual timing only (`comparison: null`).

The personal window holds at most the 50 most recent strictly prior observations for that exact
profile/hero/effective-role/mode/major-patch/item combination; it excludes the current match and
any later match. "Usual" means median. `delta_seconds` is `baseline_seconds -
purchase_time_seconds`, so a positive value means earlier. `cohort_patch` is the reference
artifact's major patch for population comparisons (references pool unaffected earlier lettered
updates) or the personal major-patch cohort for personal comparisons.

The population reference takes precedence over personal history. **Support never receives a
comparison** — inline comparisons and cards are limited to Carry, Mid and Offlane
(`item_timings.CORE_ROLES`). Population comparisons are cohort facts, not "your usual"; personal
claims always state the prior sample count `N` and refer only to the previous window. No wording
says "all-time" or "personal record."

**Old patches:** a match played on a patch other than `CURRENT_PATCH` never resolves a population
reference (`_population` requires an exact `CURRENT_PATCH` match), so its timeline items can only
receive `PERSONAL_PREVIOUS_BEST` or `PERSONAL_USUAL` comparisons, gated on the match's own major
patch. The timeline itself is always available regardless of patch.

## Card rules

Cards are stricter than the inline row: an item can qualify for an inline comparison without ever
producing a card.

- **Population reference required.** A card candidate must have a population reference for that
  exact hero, role, mode and item. Without one, the item cannot become a card even with a
  qualifying personal comparison, except via `PERSONAL_PREVIOUS_BEST` below.
- **Boots upgrades and bare components never make cards.** `CARD_EXCLUDED_ITEMS` — every upgraded
  boot (Power Treads, Phase Boots, Arcane Boots, Tranquil Boots, both Travel Boots tiers,
  Guardian Greaves, Boots of Bearing) plus Sange, Yasha, Kaya and Crystalys — stays in the
  timeline and can still drive an inline comparison, but is excluded from card selection. The
  50-card relevance review found their early timings not noteworthy on their own.
- **Population cards need a bigger margin than the inline gate.** A `POPULATION_USUAL` card must
  beat the reference's **p10** (not just p25) by at least `max(10% of p10, 60 seconds Standard /
  30 seconds Turbo)`.
- **`OWN_HERO_ITEM`** is the single best-qualifying item among the viewer's own purchases: the one
  with the largest `delta_seconds` among items that clear either the population-card margin above
  or `PERSONAL_PREVIOUS_BEST`. `PERSONAL_USUAL` never produces a card — it stays inline only.
- **`ENEMY_HERO_ITEM`** is the single best population card (by the same p10 margin, `kind ==
  POPULATION_USUAL` only — enemy purchases never get a personal comparison) among enemy positions
  1–3 across both teams relative to the viewer.
- Both candidates share the same three-card selection ceiling as every other post-match insight
  family; a qualifying purchase may appear both inline and as a selected card.

## 50-card relevance review

An offline review against the local corpus harness — zero provider calls — judged 50 sampled
card-worthy purchases for build-choice relevance. The first pass, gated only on p25 with boots
and bare components allowed to become cards, judged **34 of 50** relevant, and cards fired on
most sampled games; the gate above (p10 margin, boots/components excluded) was adopted in
response. The final sample under the shipped gate judged **48 of 50** relevant, with **0**
incorrect purchase facts and **0** causal claims. Two off-meta but retained cards: Earthshaker
Mid buying Yasha and Kaya, and Wraith King Offlane buying Bloodthorn — both cleared the
population gate on genuine corpus evidence. Under the shipped gates, cards fire on roughly 3,950
of the corpus's 39,935 core (Carry/Mid/Offlane) rows, combining both card kinds.

## Match Detail response

`item_timings` appears only on Match Detail. It has no localized strings:

```text
ItemTimingsView
  state: AVAILABLE | PENDING | UNAVAILABLE
  contract_version: "item-timings-v1" | null
  reason: string | null
  reference_digest: string | null
  items: ItemTimingView[]

ItemTimingView
  item_id: int
  item_key: string
  item_name: string
  purchase_time_seconds: int
  key_item_order: int
  comparison: ItemTimingComparisonView | null

ItemTimingComparisonView
  kind: POPULATION_USUAL | PERSONAL_PREVIOUS_BEST | PERSONAL_USUAL
  baseline_seconds: int
  delta_seconds: int
  sample_size: int
  cohort_patch: string
```

Readiness and reason codes:

- `PENDING` while analysis has not finished, or while there is no active analysis and the match
  is not yet in a terminal lifecycle state.
- `UNAVAILABLE` with `reason: "MODE"` when the match's bucket is neither Standard nor Turbo; with
  `reason: "SOURCE_EVIDENCE"` when purchase evidence for the viewer is absent; with `reason:
  "MATCH_<lifecycle>"` when the match itself is terminally unavailable or needs action with no
  analysis at all; or with `reason: "ANALYSIS_VERSION"` when the active analysis predates this
  contract.
- `AVAILABLE` when purchase evidence exists, including an empty `items` list when no key item was
  bought.

The response list uses the same `(purchase_time_seconds, item_id)` order as the frozen analysis.
Rows without a qualifying comparator carry `comparison: null`. Frontend copy, ordinals and
localized time formatting are not part of this backend schema.

## Refresh procedure

Population data is item-only; build order is never part of the baseline, so a refresh never
needs order statistics beyond the descriptive numbers in
[`ITEM-BUILD-PATTERNS-7.41.md`](ITEM-BUILD-PATTERNS-7.41.md).

For each new lettered patch:

1. Update the patch-date mapping (`PATCH_START`, `PATCH_RELEASE`, `CURRENT_PATCH`) and review
   patch notes for changed hero/item pairs in `item_references.py`'s `SUSPENDED_HEROES` /
   `SUSPENDED_ITEMS`. A changed pair stays `patch_change_pending` until current-letter evidence
   clears it.
2. Build from the prepared normalized purchase-event corpus, never live provider responses:

   ```bash
   uv run python scripts/build_item_references.py --source <normalized-corpus> --patch <lettered-patch>
   ```

   `--patch` may repeat for more than one lettered patch in a single run. This writes/updates a
   shard per patch under `item_shards/` and recomposes `item_references.json` from the five
   newest saved shards.
3. Commit the updated shards and `item_references.json`. Verify the deterministic digest, all 762
   coverage cells, the explicit `sparse` / `patch_change_pending` / `no_qualified_item` reasons,
   the purchase-count/purchase-rate thresholds, and the absence of player identifiers.
4. Re-run the 50-card relevance review against the refreshed artifact before it ships.
5. Enqueue `rebuild.enqueue_methodology_rebuilds` to re-evaluate retained matches from stored
   evidence — provider-free. This is the only rebuild path; `run_item_insight_rebuild` and
   `scripts/rebuild_current_patch_items.py` were deleted, and nothing replaces them for a
   backend-only artifact refresh. Role correction independently recomputes the timeline and card
   snapshot from retained purchase events. Repeating a rebuild must remain deterministic and
   idempotent, and it sends no notifications.

Methodology rebuilds and QA use stored source evidence, fixtures and recorded responses. They
make **0 OpenDota calls and 0 STRATZ calls**. An absent compatible analysis is not silently
upgraded by Match Detail reads.

## iOS status

The backend contract is complete and frozen. The native iOS project does not exist yet, so
rendering of `item_timings` and its two card templates is pending. Target EN/ID copy lives in the
Figma content bank (file `D3uhn7WPXFsX1DiCIVklyg`, page `575:4018`): frame 01 for the card and
history-line templates, frame 02a for the item-timings keys, and frame 09 for per-cell coverage.
