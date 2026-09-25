# Free DNA OpenDota Parsed-Data Feasibility

## Status

**PARTIAL — the stored corpus answers parsed coverage, field tiers, and cost. It does not contain longitudinal per-player detail payloads, so it cannot establish stability for the strongest Tier-2 Finding candidates.**

Recommendation: **C. USE PARSED DATA ONLY AS BACKGROUND ENRICHMENT.** Keep the current one-call 365-day Free report synchronous. Do not promise two new instant Findings from the history response: its parsed-derived surface is only lane, lane-role, and roaming context, and only 24.30% of eligible development profiles have 30 parsed matches. Test richer Findings behind a bounded background detail-fetch pilot after explicit owner approval.

## Preflight and firewall

```text
TASK TYPE: ANALYTICAL + DOCUMENTATION, offline feasibility research
ALLOWED SCOPE: immutable local OpenDota tuning corpus, captured provider responses, repository code/evidence, aggregate local diagnostics
FORBIDDEN SCOPE: providers, parse requests, STRATZ, old holdout, fresh sealed-validation analytics, production behavior, thresholds/artifacts, deployment
STOP CONDITIONS: digest/provenance failure; sealed data requirement; provider requirement; production change; raw identifiers in tracked output
RESEARCH BASE: 8e8b30ce92b91b9c47a8b1c77f09d5d080091755
LATEST MAIN: 6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95
PRIMARY WORKTREE STATUS: dirty with unrelated untracked owner work; untouched
TEMP WORKTREE: /tmp/dota-free-dna.VsPPam
CORPUS PATH: .local/corpora/opendota/v61-session-drift-expansion/
CORPUS READABLE: YES
CORPUS DIGEST VERIFIED: YES
```

No Phase-3 sibling corpus exists in the canonical local corpus directory, so no Phase-3 execution data has been appended. The fresh validation arm remained sealed and was not used analytically.

## Corpus integrity and audited population

| binding | expected | recomputed | result |
|---|---|---|---|
| raw corpus | `cb356a142b5ea59fca48b841e633a8e84adb4583f97228ec9afc820d06cd725d` | same | PASS |
| normalized corpus | `d964b3ff03db5c5aaa04203e147edbb9c1ae72db654c8e73aed44f7d763e9371` | same | PASS |
| split manifest | `800ff016abc0f6dcee558f0876fda194147efbcbd471290ca81f1c8f656bad31` | same | PASS |

- Provider: OpenDota only.
- Raw responses checked: 5,346; digest/file failures: 0.
- Normalized tuning-arm profiles checked: 2,848; digest/file failures: 0.
- Canonically eligible development/tuning profiles analyzed: 1,609.
- Eligible 365-day matches: 556,676.
- Fresh sealed validation used analytically: **NO**.
- Old revealed holdout used: **NO**.

The 1,609-profile population is the complete eligible tuning arm, not a high-parsed subset. Parsed-support thresholds are reported as coverage outcomes; they do not redefine a future calibration population.

## What “already parsed” means offline

Canonical rule for this capture:

```text
MATCH_ALREADY_PARSED = source_version == "22"
```

Confidence is **KNOWN FOR THIS CAPTURE**:

- All 56,219 positive eligible history rows have `source_version=22`, and `lane`, `lane_role`, and `is_roaming` are present.
- In 1,200 captured `/matches/{match_id}` responses, `version=22` and `od_data.has_parsed=true` co-occur exactly 19 times. The other 1,181 responses have `version=null` and `has_parsed=false`.
- Repository normalization maps history `version` to `source_version` without changing its value.

The history and detail samples are not match-ID-paired, and a future parser version may not be `22`. Production code should therefore accept only explicitly verified parser versions and revalidate after provider schema drift. `lane`, `lane_role`, and `is_roaming` support the rule but are not independent parse-state contracts.

## Parsed coverage

The 56,219 likely-parsed matches are 10.10% of all eligible history rows. Parsed matches per profile:

| P10 | P25 | median | P75 | P90 | P95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 11 | 29 | 76 | 152.6 |

| threshold | profiles | coverage |
|---:|---:|---:|
| ≥10 | 839 | 52.14% |
| ≥20 | 536 | 33.31% |
| ≥30 | 391 | 24.30% |
| ≥40 | 294 | 18.27% |
| ≥50 | 237 | 14.73% |
| ≥75 | 165 | 10.25% |
| ≥100 | 124 | 7.71% |

By eligible 365-day history depth:

| history depth | profiles | median parsed | ≥20 | ≥30 | ≥50 | ≥75 | ≥100 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 30–49 | 152 | 1 | 1.32% | 0.00% | 0.00% | 0.00% | 0.00% |
| 50–99 | 255 | 3 | 2.35% | 1.18% | 0.39% | 0.39% | 0.00% |
| 100–199 | 318 | 6 | 10.69% | 7.23% | 4.72% | 2.83% | 1.57% |
| 200+ | 884 | 23 | 55.88% | 41.29% | 25.00% | 17.53% | 13.46% |

Among profiles with at least one parsed match, the median newest parsed match is 15.49 days old and the median oldest is 280.29 days old. Coverage is strongly coupled to total match depth, so conditioning a calibration corpus on parsed count would change the target population.

## Field inventory and three tiers

### Tier 1 — instant history/cached projection

The current one-call history/cached layer contains:

- `version` → normalized `source_version` (parse-state audit);
- `lane`, `lane_role`, and `is_roaming` (parsed-derived context);
- `party_size` (not parse-dependent; null does not prove solo);
- `hero_variant` (not parse-dependent and not behavioral alone); and
- existing result, hero, K/D/A, duration, and chronology summary fields.

It does **not** contain purchases, wards, action counts, minute curves, objective events, teamfights, advantage timelines, or death chronology. Tier 1 can support a cautious Role Shape description, but not two high-value, distinct parsed Findings.

### Tier 2 — per-match parsed detail

Captured parsed detail responses verify these shapes when `version=22`:

- purchases and timing: `purchase_log`, `purchase`, `purchase_time`;
- action counts/APM: `actions`, `actions_per_min`;
- lane efficiency and early space: `lane_efficiency_pct`, `lane_pos`;
- vision: `obs_log`, `sen_log` and removal logs;
- buybacks: `buyback_log`, `buyback_count`;
- objectives and kill counters: `objectives`, `kills_log`, unit/objective counts;
- minute series: `gold_t`, `xp_t`, `lh_t`, `dn_t`;
- heuristic fight windows: `teamfights` and per-player fight aggregates;
- team state: `radiant_gold_adv`, `radiant_xp_adv`; and
- aggregate item/ability/damage interaction maps.

These require one `/matches/{match_id}` GET per selected match under the current REST design. An already-parsed match does not require a new parse submission, but this corpus has only 19 parsed seed details and no longitudinal per-player detail panel; field presence is established, not candidate stability.

### Tier 3 — asynchronous replay parsing/raw replay work

Full movement routes, ordered cast sequences, cooldown/mana state, exact inventory state through time, exact fight entry/exit, and raw combat chronology are not exposed by stock parsed detail. They require replay parsing or additional raw-replay processing and belong in Deep only.

## Do we need 100 parsed matches?

**No as a blanket feasibility rule.** For the Tier-1 context metrics that can actually be tested, repeated split-half behavior improves continuously:

| N | profiles | Role Shape correlation | direction agreement | dominant-role correlation | roaming correlation |
|---:|---:|---:|---:|---:|---:|
| 10 | 839 | 0.228 | 0.699 | 0.248 | 0.152 |
| 20 | 536 | 0.402 | 0.661 | 0.448 | 0.283 |
| 30 | 391 | 0.529 | 0.678 | 0.587 | 0.385 |
| 40 | 294 | 0.592 | 0.684 | 0.658 | 0.518 |
| 50 | 237 | 0.603 | 0.692 | 0.682 | 0.573 |
| 75 | 165 | 0.726 | 0.727 | 0.784 | 0.707 |
| 100 | 124 | 0.767 | 0.742 | 0.828 | 0.760 |

For descriptive Role Shape, **30–50 is a plausible research range**, not a production threshold. Stronger player-identity repeatability appears around 75, but only 10.25% of profiles reach it. Hero-mix sensitivity is moderate rather than catastrophic (full-versus-dominant-hero-removed correlations 0.88–0.92), while chronological half correlations are only 0.33–0.47. Patch sensitivity is blocked because patch was not retained in the canonical history projection.

For Build Adaptation, Resource Rhythm, Vision Rhythm, and Fight Clock, the required longitudinal detail panel is absent. Their useful N remains **UNKNOWN — REQUIRES A SEPARATELY APPROVED BACKGROUND PILOT**, not “100 by default.”

## Serious candidate shortlist

| candidate | behavioral question | tier | plausible support | main risk | disposition |
|---|---|---:|---:|---|---|
| Role Shape | one lane-role shape or repeated role movement? | 1 | 30 | parser vocabulary, hero/patch mix | hold for validation; only credible Tier-1 candidate |
| Roaming Tendency | how consistently does the parser call the player roaming? | 1 | 30 | rare positives, heuristic semantics | reject as sufficiently distinct second Finding |
| Build Adaptation | does item order change with lineup/state? | 2 | 30 | hero/role/patch/item graph | best background candidate |
| Resource Rhythm | does resource behavior change around fights/objectives? | 2 | 30 | state, role, minute resolution | best background candidate |
| Vision Rhythm | proactive/reactive/burst vision? | 2 | 20 opportunities | role and ward burden | background/Deep, role-conditional |
| Fight Clock | when do fight contributions occur? | 2 | 30 | heuristic teamfight detector, tempo | background candidate |

All six ask different questions from Transfer, Post-Loss, and Session Drift. Fight Clock has medium correlation risk with Post-Loss/Session Drift unless restricted to within-match event timing. Roaming Tendency would likely feel like another role label, so it does not solve the product requirement for a second distinct Finding.

## Coverage for two parsed Findings

The only two Tier-1 concepts use the same support rows:

| N | enough data for both | descriptively stable for both | future qualified | published |
|---:|---:|---:|---|---|
| 20 | 33.31% | 27.91% | not evaluated | not evaluated |
| 30 | 24.30% | 20.94% | not evaluated | not evaluated |
| 50 | 14.73% | 13.11% | not evaluated | not evaluated |
| 75 | 10.25% | 9.45% | not evaluated | not evaluated |
| 100 | 7.71% | 7.15% | not evaluated | not evaluated |

This table is deliberately not a publication forecast. “Data available” precedes support eligibility, stable signal, future statistical qualification, and publication. More importantly, Roaming Tendency was rejected as a strong second Finding, so Tier-1 two-Finding product coverage is effectively **zero** under the quality bar even where both fields exist.

## Architecture and cost

Owner-supplied cost assumption: **Rp200/100 calls; $0.01/100 calls**, applied independently and pro rata.

| architecture | physical calls/user | IDR/user | USD/user | retained data | latency class |
|---|---:|---:|---:|---|---|
| history-only baseline | 1 | 2 | 0.0001 | summary history | current instant class |
| history + two Tier-1 concepts | 1 | 2 | 0.0001 | same summary history | current instant class |
| history + 20 detail GETs | 21 | 42 | 0.0021 | summary + 20 details | likely synchronous, unverified |
| history + 50 detail GETs | 51 | 102 | 0.0051 | summary + 50 details | likely delayed |
| history + 100 detail GETs | 101 | 202 | 0.0101 | summary + 100 details | likely delayed |
| parse submissions + polling | unknown | unknown | unknown | replay-derived | asynchronous |

Architecture A cannot produce two strong new Findings. Architecture B needs no parse job for already-parsed matches, but 20/30/50 parsed-match support covers only 33.31%/24.30%/14.73% and latency was not measured. Architecture C is incompatible with the instant Free promise and belongs in Deep.

## Recommended Free architecture

Return the current 365-day Free report immediately from its one history call. Preserve `source_version` and parsed match IDs only in the private evidence layer. After the report completes, an owner-approved background enrichment worker may deterministically select a small cap of already-parsed matches, fetch detail without parse submission, cache the immutable detail, and evaluate experimental candidates. Never delay or suppress the current report while enrichment runs; omit any parsed Finding when support is absent.

Start with Build Adaptation and Resource Rhythm because they are personal, Dota-native, distinct from the current families, and available from ordinary parsed detail. Keep Vision Rhythm role-conditional. Keep raw movement, cast-order, and replay-state concepts in Deep.

## Minimal provider QA still needed

No provider call is needed to classify the stored corpus. Before any live background pilot, use at most four explicitly owner-approved calls:

| question | calls | resolving result | maximum pro-rata cost | stop condition |
|---|---:|---|---:|---|
| history marker agrees with detail state | 2 | one stored positive and one negative agree on version/`has_parsed` | Rp4 / $0.0002 | any disagreement |
| parsed detail returns Tier-2 shape without parse job | 1 | expected logs/arrays, no submission | Rp2 / $0.0001 | missing shape or parse workflow |
| measured one-call latency | 1 | timing recorded, no SLA inferred | Rp2 / $0.0001 | rate limit/billing/schema drift |

Total maximum: **4 calls, Rp8, $0.0004 pro rata**. Owner approval is required. The execution prompt is `docs/prompts/free-dna-opendota-parsed-pilot-luna.md` and stops before any call by default.

## Reproducibility

- Runner: `scripts/free_dna_opendota_parsed_feasibility.py`
- Local diagnostics: `.local/diagnostics/free-dna-opendota-parsed-feasibility/`
- Required artifacts: all 15 requested outputs are present; an additional `captured_detail_field_audit.json` records aggregate detail-shape evidence.

## Integrity

```text
OPENDOTA CALLS = 0
PARSE JOBS SUBMITTED = 0
STRATZ CALLS = 0
OLD HOLDOUT EVALUATED = 0
FRESH SEALED VALIDATION ANALYTICALLY EVALUATED = 0
PRODUCTION ANALYTICAL BEHAVIOR CHANGED = NO
DEPLOYED = NO
```
