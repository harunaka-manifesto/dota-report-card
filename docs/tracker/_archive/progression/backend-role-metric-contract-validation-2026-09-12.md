# Backend role metric contract validation — 2026-09-12

This is a targeted validation of the progression metrics. It does not change
the frozen V7 report-card query or analytical artifacts.

## Evidence boundary

- Corpus: `.local/corpora/stratz/v7-pass2-2026-09-04/canonical` (104,982 rows,
  read-only; no private identifiers are committed).
- Exact progression context: All Pick modes
  (`ALL_PICK`, `ALL_PICK_RANKED`, `ALL_PICK_UNRANKED`) with `RANKED` or
  `UNRANKED` lobby, clean leaver status, and native position context.
- Clean role-labeled rows: 34,472 — Carry 7,787, Mid 8,357, Offlane 6,472,
  Support 11,856.
- Provider use in this pass: three targeted STRATZ calls (one type
  introspection, one one-match probe, one eight-match probe); zero OpenDota
  calls; no playback requests and no corpus recollection.

## Findings

| Metric | STRATZ support | Semantic confidence | Cost | Implemented? | Final recommendation |
|---|---|---:|---:|---|---|
| Support Healing | `heroHealing` scalar; `healPerMinute` is corroborating trajectory data | High | Existing scalar | Yes | Lock `support.healing.v1` |
| Support Fight Presence | Ten scoreboard rows provide unique slots, 5/5 sides, and credited kills/assists | High | Existing all-player projection | Yes | Lock `support.fight_presence.v1` |
| Camps Stacked | `campStack` is a player-level non-decreasing step series | High | Existing trajectory | Yes | Lock `support.camps_stacked.v1`; do not call it Resources Enabled |
| Support Control | `actionReport` has attack/cast/move/ping/scan counters, not duration | High negative | No direct field | No | `support.control.v1` is `UNSUPPORTED_V1` |
| Mid Early Fight Presence | `allPlayers[].stats.killEvents { time }` is valid and parsed for 8/8 probe matches | Medium-high | New minimal field; provider returned no numeric complexity metadata | Yes | Lock with timestamp-event contract |
| Offlane Objective Involvement | `towerDamageReport { npcId damage }` is player-attributed and NPC-linkable; no timestamp | Medium-high | New small report; present in 6/8 probe matches | Yes | Lock with N/A on absent report and a 60s operational proximity rule |

### Camps Stacked

Among 31,180 rows with non-zero `campStack`, every series was non-decreasing and
step-shaped. In 30,966 rows the sum exceeded the final value, while 214 had sum
equal to final value. This establishes a cumulative counter, so V1 uses the
final value. In the clean role-labeled population, all 11,856 Support rows had
the series; 5,884 ended non-zero.

### Objective window selection

On 6,472 clean Offlane rows, there were 82,383 enemy-tower death events. Using
only kill/assist proximity, the candidate windows attributed 44,148 (53.6%),
51,915 (63.0%), and 60,307 (73.2%) events at 45s, 60s, and 90s respectively.
The attributed set changed in 3,648 rows from 45s to 60s, 3,673 rows from 60s
to 90s, and 4,647 rows from 45s to 90s. V1 therefore pins 60s as an explicit
operational heuristic; it is not claimed to be a causal threshold.

### Targeted live probe

The minimal probe selected the new all-player kill timestamps and the tracked
player tower report. Both batch sizes returned HTTP 200 and parsed completely:
1/1 and 8/8 matches. The eight-match probe returned 26,133 bytes; a serialized
same-response baseline with the new fields removed was 15,548 bytes, a measured
upper-bound increase of 10,585 bytes because the probe selected extra report
columns that the production operation omits. The provider returned no numeric
complexity header or extension; the accepted eight-match request establishes
that this selection fits the provider's limit, but no invented complexity score
is recorded. `towerDamageReport` had 30 entries in 6/8 matches, all non-zero,
and every sampled `npcId` overlapped a tower-death `npcId`. It has no timestamp,
so direct attribution joins on the specific building and proximity remains the
secondary rule.

The versioned production operation is `GetRoleMetricMatchBatch` v1.0.0,
document SHA-256
`aa143481e083a025ef52aa1164512b1d473216f728d325fe618d6b3216a6576d`.
It selects only match timing/mode, `towerDeaths { time isRadiant npcId }`,
all-player `playerSlot/isRadiant/kills/assists/stats.killEvents { time }`, and
the tracked player's role, leaver state, `heroHealing`, `stats.campStack`,
`killEvents { time }`, `assistEvents { time }`, and
`towerDamageReport { npcId damage }`. It does not select playback,
`actionReport`, match-level kill arrays, or proprietary fields.
