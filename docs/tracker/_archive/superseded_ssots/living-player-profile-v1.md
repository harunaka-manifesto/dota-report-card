# Living Dota Player Profile — Research, Intelligence Model & Final SSOT

Status: PROPOSED SSOT — product contract pending the owner decisions in §25.6
Scope: the Profile surface ("this is who I am as a Dota player"), its identity model, trait catalog, update architecture, and V1 hierarchy
Last audited: 2026-09-14
Depends on: [Role Metrics & Personal Baselines V1](role-metrics-and-baselines-v1.md), [Match Lifecycle V1](match-lifecycle-v1.md)

This document decides what a player Profile shows, why, how each claim is computed, how claims change, and what is deliberately excluded. It does not define metric formulas (the Role Metrics SSOT does), match readiness (the Lifecycle SSOT does), Swift architecture, database design, or visual design.

Authority order when sources disagree:

1. the two ACTIVE SSOTs above, for anything they define;
2. locked decisions recorded in this document once the owner accepts it;
3. measured V7 evidence in `docs/evidence/`;
4. older V5/V6/V6.1 research, which is evidence, not contract.

Status words used below: **LOCKED-PROPOSED** (recommended final rule, awaiting owner acceptance), **PROVISIONAL** (a threshold that must be calibrated on corpus data before release), **P0** (ships in Profile V1), **P1** (next, gated on a named prerequisite), **EXPERIMENTAL** (research only, never user-facing until validated), **REJECT** (do not build).

A note on evidence gathering: direct Reddit retrieval was blocked for this session's tools. Community evidence below therefore combines Reddit threads already collected and cited in the repository's V7 Master Experience Plan (7 September 2026), Steam Community and Dotabuff forum threads, and product documentation. It is a purposive sample of language and tensions, not a prevalence survey.

---

## 1. Executive Recommendation

### The thesis

**The Profile is a short list of claims about you that keep being true — each with receipts — plus a clearly separate strip showing what is moving right now.**

It is not a page of numbers about you. It is a page of *sentences about you*, each of which a player can tap and see exactly which matches made it true.

In one line for the team: **Progression measures. Post-match notices. The Profile concludes.**

### What the Profile fundamentally is

1. **Role-first.** Dota players already describe themselves by position ("pos 5 player", "carry main"). The strongest, cheapest, most defensible identity signal we have is the player's effective role mix, and our own role-based progression model is built on it. The Profile opens there.
2. **Hero-shaped.** Heroes are the second thing players recognise instantly. But "most played" is only one of several hero relationships players distinguish (go-to, longtime, rising, favourite, best record). The Profile separates them rather than collapsing them into one list.
3. **Slow by design.** Identity claims move only when the evidence moves decisively, with enter/exit hysteresis. One odd match never changes who you are.
4. **Self-relative before population-relative.** V1 claims compare you with your own history and describe the structure of your own play (role mix, pool shape, hero longevity, recent runs against your own baseline). Claims that need "compared with other Carry players" wait for a validated reference population (P1).
5. **Evidence-trailed.** Every claim carries its definition, window, sample, and the matches behind it. If a claim cannot produce a "Why am I seeing this?" panel, it does not ship.
6. **Refusal is a valid state.** A new player sees facts and a gentle "still getting to know your Dota", not a manufactured personality.

### What it should not be

- **Not a stats dashboard.** DotaBuff, OpenDota (25+ profile tabs), and STRATZ already provide the inventory. Repeating KDA/GPM/win rate is table stakes nobody installs an app for.
- **Not a skill grade.** No overall score, no radar of 0–100 skills (Mobalytics-style), no "good/bad" grades, no rank-derived labels. Rank stays fenced exactly as V7 already enforces in code.
- **Not a personality test.** No "resilient", "tilted", "brave", "selfish". The V7 archetype grid stays in the Annual Report where "for fun" framing is licensed; it is not the V1 Profile headline (reasons in §6.4).
- **Not a second Progression screen.** The Profile never re-displays a metric delta the Progression screen already shows. It summarises state ("Carry laning is on an up-run") and links there.
- **Not an annual report that updates.** The Annual Report says what characterised a year. The Profile says what currently appears to be true, and keeps a frozen history of how that changed.

### The product thesis, stated plainly

A DotaBuff profile answers *"what are this account's numbers?"* Our Profile answers *"what kind of Dota player is this, and how sure are we?"* — and becomes more accurate the more you play. The defensible V1 is smaller than the brief imagines: **role identity, hero identity with separated meanings, two or three confirmed structural traits, a current-form strip fed by Progression, personal bests, and a change feed.** That is enough to produce "yeah, that's me" for most established players, because role and heroes *are* how Dota players see themselves. The "I didn't know that" layer comes from contrasts inside that structure (your Support pool is three times wider than your Carry pool; you are a Mid player in Turbo and a Support in Standard; Luna went from nothing to a third of your Carry games) — all computable from data we already collect.

The riskiest attractive ideas — "you fall off outside your comfort heroes", "you recover well after bad lanes", "you perform strongly even in losses" — were already measured by V7 and **carry no between-player signal** (τ = 0). They are rejected, and the evidence is in §22.

---

## 2. Research Findings

### 2.1 Dota products

| Product | What it prioritises | What players get from it | What we take / leave |
|---|---|---|---|
| **Dota 2 client profile** | Self-expression: a customisable Profile Showcase (heroes, trophies, stickers, stat blocks), a mini-profile on friend hover; gated behind a communication score above 6000 ([Hawk Live](https://hawk.live/posts/profile-showcase-customization-dota-2)). | "This is my stuff." Curation, not interpretation. | **Take:** the player chooses part of their public face (favourite hero pin). **Leave:** cosmetics as identity. |
| **Old client "playstyle" bars** | Five opaque bars — Fighting, Farming, Supporting, Pushing, Versatility — scored to 1.00 with an undisclosed formula. Players speculated how to raise them ([Steam discussion](https://steamcommunity.com/app/570/discussions/0/492379159711591639/)). | Recognisable dimensions; confusion about meaning; incentive to chase a bar. | **Take:** players intuitively accept role-like style dimensions. **Leave:** opaque axes and "max it out" framing. This is the clearest historical warning against unexplained style scores. |
| **Dota Plus / Battle Report** | Seasonal best hero, role and overall stats compared with similarly skilled players; highlights of trends and records; a Deep Analysis filter view ([esports.net](https://www.esports.net/news/dota-battle-report-update-delivers-cosmetics-needed-features/), [player.one](https://www.player.one/dota-2-battle-report-weekend-spotlight-dota-plus-147992)). Hero levels/challenges and Relics (per-hero counters) create hero investment ([Dota Plus](https://www.dota2.com/plus)). | "Best hero", "best role", records, "compared to my bracket". | **Take:** per-hero investment and records matter. **Leave:** skill-bracket comparison (rank-derived, and we fence rank). Battle Report already occupies "seasonal summary + highlights"; the Profile must be living and interpretive, not a second seasonal recap. |
| **DotaBuff** | Lifetime aggregates with filters across heroes, items, records and scenarios; role/lane scenarios; hero rankings that require 30 matches on a hero plus one every 30 days to stay ranked ([DotaBuff blog](https://www.dotabuff.com/blog/2016-10-31-big-improvements-to-match-pages-and-player-profiles), search summary of [Rankings](https://www.dotabuff.com/pages/rankings)). | Lookup and lurking — especially of teammates. | **Take:** the ranking rule is a useful precedent for "signature" requiring volume *and* recency. **Leave:** everything-with-a-filter. |
| **OpenDota** | Maximal inventory: Overview, Heroes, Peers, Records, Totals, Histograms, Trends, Wardmap, Wordcloud, and more ([OpenDota blog](https://blog.opendota.com/2015/09/22/actions-trends/), [odota/web](https://github.com/odota/web/blob/master/src/lang/en-US.json)). | Exploration for enthusiasts. | **Take:** records and trends are loved by a minority. **Leave:** tab sprawl. Wordcloud is a reminder that "weird stats" delight but can expose private chat — we do not request chat at all. |
| **STRATZ** | IMP, a proprietary −100…+100 match-performance score used for awards ([STRATZ Medium](https://medium.com/stratz/imp-decoding-your-performance-c251dcb42b93)); a per-hero position meter; recent-25-match streak strip; an Activity score for the last 10–20 days; top teammates; toxicity/behaviour indicators ([STRATZ Medium](https://medium.com/stratz/stay-in-your-lane-fa4363f1273), [STRATZ](https://stratz.com/)). | The closest existing thing to identity is **position-by-hero**. | **Take:** role-by-hero structure; short activity recency. **Leave:** IMP and behaviour scores — the repository already rejects them as opaque, unversionable model outputs (`research/stratz-enrichment/01-field-inventory.md` §6). |
| **Pro stat sites** (Liquipedia, datdota, D2PT) | Unique heroes per player/team at an event, hero pick counts with win rate, average duration, draft/ban data ([Liquipedia Statistics](https://liquipedia.net/dota2/Portal:Statistics), [datdota](https://datdota.com/), [rdy.gg TI 2026](https://rdy.gg/en/dota2/news/the-international-team-and-hero-statistics)). | Hero-pool depth and signature heroes are the lingua franca of pro characterisation. | **Take:** "unique heroes" and "signature hero" are native vocabulary. **Leave:** draft/ban analysis — pubs have no opponent scouting. |

**Conclusions from the Dota ecosystem**

1. Every existing product answers *what* (numbers) rather than *who* (interpretation). The one interpretive attempt that reached the client — playstyle bars — failed on explainability.
2. The data players reach for first when judging a player is **heroes and roles**, then win rate, then recency. This matches both STRATZ's position meter and the pro-stat convention.
3. "Compared with similar skill" is Valve's territory and relies on rank. We cannot and should not compete there.
4. Proprietary performance scores exist and are widely shown. Their opacity is exactly the gap an evidence-trailed product can occupy.

### 2.2 How professional players are characterised

Pro analysis and broadcast statistics characterise players through a small, recurring vocabulary: hero pool depth (unique heroes played, e.g. Team Spirit fielding 49 unique heroes in 29 games at TI 2026), signature heroes (heroes a player is known for, with pick count and win rate), role/position, farm priority, pace (average game duration), and standout single performances ([rdy.gg](https://rdy.gg/en/dota2/news/the-international-team-and-hero-statistics)). Position numbers themselves encode farm priority — position 1 has the highest claim on gold, position 5 the lowest ([Dotesports role guide](https://dotesports.com/dota-2/news/dota2-role-guide-23954), [Hawk Live positions](https://hawk.live/posts/dota-2-positions)). Team-building guidance distinguishes a hero you *enjoy* (comfort) from a hero you *can be relied on to deliver under draft pressure* (pocket pick), argues that depth means playing a hero well from behind and into bad matchups, and that "jobs outlive patches" while hero viability changes ([Guild Order](https://guildorder.com/games/dota2/guides/hero-pool-construction)).

Classification of pro concepts for ordinary players:

| Concept | Class | Reason |
|---|---|---|
| Role specialisation | **A — applies directly** | Effective role is already our progression key. |
| Hero pool depth / breadth | **A** | Effective-hero counts per role are exact from match history. |
| Signature heroes | **A/C** | Frequency and longevity apply directly; "distinctive" needs a reference pick rate (C). |
| Warding, stacking, healing | **A (Support, role-scoped)** | Already registered Support metrics. |
| Fight participation | **A/C** | Registered as Fight Presence for Mid/Offlane/Support; "high for a Support" needs a reference population (C). |
| Farm source (lane vs jungle) | **C** | STRATZ `farmDistributionReport` is acquired; heavily hero-confounded, needs hero-normalisation. |
| Economy conversion, damage distribution | **C** | Hero Damage Share / Tower Damage Share exist per role; interpreting "high" needs reference. |
| Laning performance | **A/C** | Registered lane metrics support self-relative form (A); "lane-strong" identity needs matchup/hero normalisation (C). |
| Consistency / volatility | **C** | Meaningful only role- and hero-conditioned and against a reference spread. |
| Patch adaptation | **C (later)** | `gameVersionId` is 100% covered; needs long histories and pool-evolution machinery. |
| Tempo / early vs late impact | **C, weak** | V7 measured it: reliably ordered but tightly packed (terciles 0.015–0.018 apart) and heavily mode-confounded. |
| Drafting flexibility, ban resistance | **B — pro only** | Pubs have no scouting and a single player does not draft for five. |
| Clutch performance, performance under pressure | **B/D** | Outcome-defined; no identification; V7 lead/comeback contrasts are low-reliability. |
| Initiation, control | **D — impossible now** | Support Control is UNSUPPORTED in the Role Metrics SSOT; no trusted disable-duration telemetry. |
| Map movement, positioning | **D** | Requires playback, which is a prohibited acquisition surface and ≈4.6 MB per match for ten players. |
| Aggression | **D as a trait** | No valid measure without positions; every proxy (kills/min, deaths) collapses into role, hero, and skill. |

**Takeaway:** pro analysis describes players mostly through **what they play** (roles, heroes, depth) and secondarily through **how** (farm priority, participation). That ordering is the right ordering for the Profile.

### 2.3 Community language and behaviour

Evidence sources: Reddit threads cited in the repository's V7 Master Experience Plan §2 ([hero spam affection](https://www.reddit.com/r/DotA2/comments/tj9u5f), [spammer fatigue](https://www.reddit.com/r/DotA2/comments/1fpaoop), [Turbo recognition](https://www.reddit.com/r/DotA2/comments/v8b6kn), [separate modes](https://www.reddit.com/r/DotA2/comments/v8dihq), [mixed highlights](https://www.reddit.com/r/DotA2/comments/1l6wnnu), [session endings](https://www.reddit.com/r/DotA2/comments/z1q40j), [farming vs fighting](https://www.reddit.com/r/learndota2/comments/1frewzk), [pos 5 usefulness](https://www.reddit.com/r/learndota2/comments/1cxc190), [conscious improvement](https://www.reddit.com/r/learndota2/comments/135adx4), [rank vs improvement](https://www.reddit.com/r/learndota2/comments/18wce5y), [Battle Report side speculation](https://www.reddit.com/r/DotA2/comments/1ha85kr)); Steam Community threads on role identity ([why do you play support?](https://steamcommunity.com/app/570/discussions/0/1738841319802235475/), [carry vs support](https://steamcommunity.com/app/570/discussions/0/494632338489634417), [carry and support at the same time](https://steamcommunity.com/app/570/discussions/0/1474221865198987501/)), and older DotaBuff forum topics on hero versatility.

Recurring themes, ranked by how consistently they appear:

| Theme | Language players use | Underlying dimension | Strength of pattern |
|---|---|---|---|
| **Role as identity** | "support main", "I only play pos 1", "why do you play support?", support-as-selfless vs carry-as-greedy stereotypes | Role specialisation and which role | **Strong, recurring.** People defend and explain their role. |
| **Hero loyalty** | "hero spammer", "one-trick", "my Pudge", affection and familiarity vs boredom/fatigue | Pool concentration and longevity | **Strong.** Both warm and pejorative; the dimension is real, the valence is contested. |
| **Mode as a world** | Turbo players asking to be counted; others wanting Turbo kept separate | Mode split | **Strong.** Matches our Standard/Turbo bucket isolation exactly. |
| **Rank anxiety vs growth** | "stuck", "improving but not climbing", wanting one or two priorities, disagreement that rank captures everything | Personal growth separate from outcome | **Strong** on r/learndota2. Supports self-relative form and PBs. |
| **Farming vs fighting** | "AFK farmer", "farm or fight?", "space creator", "greedy" | Resource style (role- and hero-dependent) | **Moderate.** Real vocabulary; inherently role-conditioned. |
| **Support usefulness beyond winning** | feeling useful despite losses; wards, stacks, rotations | Role-scoped contribution | **Moderate.** Supports role-scoped metrics. |
| **Sessions and "one more game"** | continuing until a win, stopping after one, burnout | Session habits | **Moderate**, but emotionally loaded (tilt, addiction). |
| **Teammate stalking** | checking a teammate's profile for most-played heroes and win rate before blaming or trusting them | Other-player view: roles + heroes + recency | **Moderate** (widely referenced; hard to quantify). |
| **Surprise stats invite speculation** | Battle Report Radiant/Dire split discussion with sample-size objections | Curiosity; risk of noise | **Isolated but instructive.** Surprise sells; noise backfires. |

Words to learn from but not print as labels: "one-trick" and "spammer" (pejorative), "AFK farmer" (judgement), "tilted" (psychology), "greedy" (moral), "space creator" (unmeasurable for us). The dimensions behind them — concentration, loyalty, farm source, session continuation — are usable; the labels are not.

### 2.4 Identity and profile products outside Dota

| Product | Mechanic | Lesson for the Profile |
|---|---|---|
| **Spotify Wrapped** | Personal stories, a "Listening Personality" (16 MBTI-like types in 2024), and identity-first sharing; third-party reporting cites 10.5M in-app shares in 2024 ([Forbes](https://www.forbes.com/sites/dianaspehar/2024/12/06/how-spotify-wrapped-2025-explores-identity-culture-and-nostalgia/), [NoGood](https://nogood.io/blog/spotify-wrapped-marketing-strategy/)). Media compared personality features to astrology; reaction was mixed — some found 2024 underwhelming, others missed the quirky personality bits ([Fast Company](https://www.fastcompany.com/90817606/spotify-wrapped-just-reinvented-zodiac-signs-for-music-addicts), [TechCrunch](https://techcrunch.com/2024/12/04/spotify-users-are-disappointed-by-an-underwhelming-wrapped-this-year)). | People share *what the result says about them*, not the app. Personality framing delights and draws the astrology charge in the same breath — acceptable once a year, corrosive on a page you check daily. |
| **Letterboxd** | The profile "writes itself" as a log of posters; legible through indirectness ([Irrational Technology](https://irrationaltechnology.substack.com/p/the-log-is-replacing-social-media), [Boston Globe](https://www.bostonglobe.com/2025/11/01/business/strava-letterboxd-niche-social-media/)). | A Dota player's hero portraits are the posters. Identity through what you choose, with no manual curation required. |
| **Strava** | Trophy case with the four most recent on the profile; automatic Best Efforts/PRs; Athlete Intelligence uses generative AI to summarise an activity against recent history ([Trophy Case](https://support.strava.com/en-us/articles/15402068-the-strava-trophy-case), [Best Efforts](https://support.strava.com/en-us/articles/15401646-best-efforts-overview), [Athlete Intelligence](https://press.strava.com/articles/stravas-athlete-intelligence-translates-workout-data-into-simple-and)). | PBs are automatic and scoped (distance ↔ our role+metric). An LLM can *narrate* a computed comparison; it should not originate it. |
| **Hevy** | Profile statistics over 30 days / 3 months / year / all time; compare with another athlete ([Hevy profiles](https://www.hevyapp.com/features/user-profiles/), [comparison](https://www.hevyapp.com/features/workout-comparison/)). | Explicit time windows are a normal, understood UI concept. |
| **Apple Fitness Trends** | Compares the last 90 days with the last 365 using up/down arrows and a coaching nudge ([iPhoneLife](https://www.iphonelife.com/content/understanding-fitness-trends-apple-fitness-challenges)). | Two nested windows are enough to express "recent vs usual" without statistics jargon. |
| **Oura** | Personal baseline learned over ~two weeks; 14-day behaviour compared with a two-month trend, recent days weighted more ([Oura Readiness Contributors](https://support.ouraring.com/hc/en-us/articles/360057791533-Readiness-Contributors)). | A consumer precedent for self-baselines with a learning period — our "baseline building" state. |
| **Riot (League)** | Challenge titles and up to three chosen tokens shown on profile, lobby and loading screen ([Riot Challenges FAQ](https://support.riotgames.com/en-us/league-of-legends/gameplay/challenges-faq-league-of-legends/)); ranked entries expose tiny state flags `hotStreak`, `veteran`, `freshBlood`, `inactive` ([Riot API types](https://github.com/fightmegg/riot-api/blob/master/src/@types/index.ts)), surfaced by OP.GG as badges. | Users choose which earned things to display. Tiny, time-scoped state badges ("hot streak") are a proven, low-cognitive-load pattern for *current form*. |
| **Mobalytics GPI** | Eight 0–100 scores (Aggression, Consistency, Farming, Fighting, Teamplay, Toughness, Versatility, Vision) drawn as a "fingerprint" shape ([Mobalytics GPI](https://mobalytics.gg/gpi/)). | The anti-pattern: style and skill fused into grades. Our Profile must not become a radar chart of scores. |
| **Steam** | Showcases, including a Rarest Achievement showcase that auto-selects the six rarest and lets the user swap ([Steam guide](https://steamcommunity.com/sharedfiles/filedetails/?id=456998095)). | Auto-selection with user override is the right default for "what I show". |
| **Duolingo Year in Review** | Reported that the top 10% of XP earners generated over half of shares; unstable statistics were omitted; share images designed to be understood standalone (cited in the V7 Master Experience Plan). | Ordinary players need an identity surface that is not a volume brag, or only heavy players share. |

**What makes someone view their own profile:** it changed (new state, new PB, new hero rising), or they want reassurance/recognition after playing. **What makes someone view another's:** a decision is attached (queueing with them, blaming them, recruiting them) — they want roles, heroes, recency, and a sense of reliability, fast. **What makes a profile shareable:** a result that says something flattering-but-true about the person, legible without the app, and different from friends' results so it invites comparison. **What creates "wait, what's mine?":** a named, finite set of outcomes where the viewer can imagine their own (role + hero portraits + one surprising line does this without a personality taxonomy).

---

## 3. Jobs of the Profile

### Why do I open MY profile?

1. **Recognition.** "Does this app see my Dota the way I do?" (Role, heroes, how I play them.)
2. **Change.** "Something about me moved." (A new hero rising, a role shift, a trait confirmed, a PB.)
3. **Reassurance independent of rank.** "Am I getting better at anything, even when MMR is flat?" (Current form, PBs.)
4. **Curiosity.** "Tell me something I didn't know about my own history." (One signature finding.)

### Why do I share MY profile?

1. To say **who I am in Dota** in one image: role, heroes, one true line.
2. To mark a **moment of change**: "Support is now my main", "new PB".
3. To **invite comparison** from friends: "what does yours say?"

People do not share averages, losses, or weaknesses. The share card therefore uses only identity and favourable-or-neutral claims (§16).

### Why would I view SOMEONE ELSE'S profile? (future)

1. **Before queueing with them:** what roles do they actually play, on which heroes, and are they active?
2. **After a match:** was that their usual hero and role, or were they off-role?
3. **Forming a stack:** do our roles fit; how deep is their pool in the role we need?

The other-player view needs *less* than the self view — roles, heroes, recency — and must never show adverse traits or form (§17).

### What the Profile contributes that other surfaces do not

| Surface | Question it answers | What only the Profile does |
|---|---|---|
| Match detail / post-match | "What happened tonight that I didn't notice?" | Promotes repeated observations into durable claims, or refuses to. |
| Progression | "How did this match compare with my usual in this role, and is that changing?" | Summarises across roles and metrics into identity-level statements without re-showing numbers. |
| Annual Report | "What characterised this year?" | Is living, persistent, and explicitly separates stable identity from recent form. |
| Challenges / before play | "What should I focus on next?" | Supplies the context for focus ("you're a Carry specialist on an up-run in laning"), never the instruction itself. |

---

## 4. Profile Information Architecture

The brief's candidate hierarchy (Identity → Playstyle → Role → Heroes → Strengths → Form → Progression → Patterns → Findings → Achievements → History → Social card) has twelve layers. That is a dashboard. Challenged against the four tests (DATA, TRUTH, HUMAN, PRODUCT), it collapses to **seven sections**, because several of the proposed layers are the same information seen at different speeds:

- *Identity*, *Playstyle*, *Patterns* and *Strengths/Tradeoffs* are all "confirmed claims about how you play" → one section, **What keeps showing up**.
- *Role Identity* and *Hero Identity* stay separate because they are the two things players read first.
- *Current Form* and *Progression* are the same moving data at two resolutions → the Profile shows **Right now** and links to Progression for the numbers.
- *Signature Findings* are claims with higher surprise value → they live inside **What keeps showing up** as one reserved slot, not a separate page of trivia.
- *History* and *profile evolution* → **Changes**, plus a later History screen.

### Final sections

| # | Section | Job | Content | Hierarchy | Update cadence | Data requirements | Release |
|---|---|---|---|---|---|---|---|
| 1 | **Header** | Establish whose Dota and how much of it we know. | Name, avatar, mode mix ("Mostly Standard"), eligible matches tracked and since when, last played. | Top; small. | Every READY match. | STRATZ profile + lifecycle counts. | P0 |
| 2 | **Identity line + Role map** | "What kind of player am I?" in one sentence, then the role mix behind it. | Deterministic identity sentence; four role tracks per bucket with role tier and share. | First screen, primary. | Recomputed per READY match; *changes* only on confirmed state transitions. | Effective role per match (upstream/correction). | P0 |
| 3 | **Your heroes** | Which heroes define me, with meanings separated. | Up to three heroes per primary role, each tagged Go-to / Longtime / Rising / Favourite. | First screen, secondary. | Per READY match; tags use hysteresis. | Hero ID, effective role, chronology. | P0 |
| 4 | **What keeps showing up** | Durable interpreted claims, with receipts. | Up to three confirmed claims from the P0 catalog; one slot reserved for the highest-value signature finding. | First screen (first claim) and just below. | Evaluated per READY match; state changes need persistence rules. | Role/hero aggregates; later, reference population. | P0 (structural claims); P1 (style claims) |
| 5 | **Right now** | What is moving recently — visibly temporary. | Up to two current-form runs per recently played role from Progression snapshots; PB momentum. | Below identity; distinct visual treatment (dated, "last 10 Carry matches"). | Per READY match. | Finalised progression snapshots (direction_delta). | P0, gated on Progression Batches A–F |
| 6 | **Personal bests** | What I've achieved, scoped honestly. | Current best-known PBs per role/bucket; the three most recent PB celebrations. | Below the fold. | Per READY match. | PB engine (Role Metrics SSOT). | P0, gated on Progression Batch F |
| 7 | **Changes** | Profile evolution as content. | Reverse-chronological ledger of confirmed identity changes. | Below the fold; entry point from notifications/feed. | Append-only on state transitions. | Trait state machine. | P0 |
| — | **Share card** | Compact public identity. | Generated from a whitelisted projection of sections 1–4. | Action from header. | On request. | Public projection. | P0 |
| — | **Records** | Fun single-match extremes (largest deficit won from, longest game, most camps stacked by 20:00). | Records list. | Separate screen. | Per READY match. | Deep match data. | P1 |
| — | **History / Eras** | How my identity changed over years. | Frozen quarterly snapshots of identity line, role map, heroes. | Separate screen. | Quarterly freeze. | Snapshot store + ≥ 2 quarters of history. | P1 |
| — | **Style** | How I play my role compared with other players of that role. | Role-scoped style claims (vision uptime, farm source, fight presence). | Folds into section 4 when available. | Per READY match. | Validated reference population per role × bucket. | P1 |
| — | **Archetype** | Playful calling card. | V7 archetype label. | Annual Report only in V1. | Annual. | V7 archetype runtime. | EXPERIMENTAL on Profile |

---

## 5. Profile Hero / First View

The first screen must fit on an iPhone without scrolling and read in under ten seconds. It carries five things, in this order, and nothing else.

```text
┌───────────────────────────────────────────────┐
│ [avatar] Nika                                  │  HEADER
│ Mostly Standard · 1,240 matches since Mar 2024 │  (facts, small)
├───────────────────────────────────────────────┤
│ Carry specialist with a narrow, steady pool.   │  IDENTITY LINE
│                                                │  (one sentence, largest type)
│ Carry ████████████████░░░  74%   Anchor        │  ROLE MAP
│ Support ███░░░░░░░░░░░░░░  16%   Regular       │  (Standard bucket; Turbo toggle)
│ Mid ▌ 6% · Offlane ▌ 4%                        │
├───────────────────────────────────────────────┤
│ [Juggernaut]   [Wraith King]   [Luna]          │  YOUR HEROES
│  Go-to          Longtime        Rising         │  (portraits + meaning tag)
├───────────────────────────────────────────────┤
│ Your Support pool is three times wider         │  WHAT KEEPS SHOWING UP
│ than your Carry pool.            Why? ›        │  (one claim visible, more below)
├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤
│ RIGHT NOW · last 10 Carry matches              │  RIGHT NOW
│ CS at 10:00 above your usual in 8 of 10  ›     │  (dashed/dated; visibly temporary)
└───────────────────────────────────────────────┘
```

| Slot | Exactly what | Why it earns the space | If confidence is insufficient |
|---|---|---|---|
| Header | Display name + avatar; dominant bucket phrase; eligible match count with first tracked month; last played relative time. | Scope and trust: the player sees how much we know. | Always shown. Below 10 matches the phrase reads "Getting to know your Dota". |
| Identity line | One sentence composed from the Role Shape state and the primary role's Hero Shape state (templates in §23). | The single "yep, that's me" moment. Role + pool shape is the most recognisable true statement we can make. | Role lean only ("Mostly Carry so far"), or omitted under 30 eligible matches in the bucket. Never a default archetype. |
| Role map | Four roles in the selected bucket with share of the identity window and role tier (Anchor/Regular/Occasional/Rare). Bucket toggle only when both buckets have ≥ 30 matches. | Players describe themselves by role; bars make the identity line checkable at a glance. | Shares shown as counts ("11 Carry, 3 Support") under 30 matches; tiers hidden. |
| Your heroes | Up to three portraits for the primary role; each with exactly one tag. Tap for all roles. | Heroes are the posters of a Dota identity. Tags teach that most played ≠ longest-running ≠ rising. | Under 10 matches in role: "Most played so far" list with counts, no tags. |
| One claim | The highest-priority confirmed claim (priority rules in §23), with "Why?" | The "I didn't know that" hook. | Omitted until a claim is confirmed. No filler facts in this slot. |
| Right now | One current-form run from the most recently played role, with its window label. | Makes the profile feel alive without letting recent noise masquerade as identity. | Omitted when no run qualifies; never replaced by a non-qualifying metric. |

Deliberately **not** on the first screen: win rate, KDA, GPM, rank, match graphs, archetype, weaknesses, recommendation, records, full PB list.

Visual grammar that the design pass must preserve (content rule, not visual spec): **stable identity is solid; current form is visibly dated and temporary** (a window label is mandatory on every "Right now" item).

---

## 6. Identity Model

### 6.1 The model

```text
MATCH (READY, effective role, bucket)
  ↓
SIGNAL        one measurable per-match value
              (effective role, hero, a registered role metric observation, a direction_delta)
  ↓
AGGREGATE     a windowed summary of signals
              (role shares, effective heroes, hero longevity blocks, last-10 run counts)
  ↓
CLAIM         an operational definition that maps an aggregate to a state
              with enter/exit thresholds, sample gates, and an evidence payload
              (Role Shape = SPECIALIST; Luna = RISING in Carry)
  ↓
CLAIM STATE   CANDIDATE → CONFIRMED → FADING → RETIRED   (hysteresis)
  ↓
PROFILE       a deterministic selection of confirmed claims into sections
  ↓
NARRATIVE     templated copy bound to claim state and evidence values
```

A player is represented by **many simultaneous claims**, grouped by scope:

- **Account scope:** mode mix, overall role shape per bucket.
- **Role scope (per bucket):** hero shape, exploration, heroes and tags, current-form runs, PBs, later style claims.
- **Hero scope (per role):** tags only (Go-to/Longtime/Rising/Favourite), later best record.
- **Cross-scope contrasts:** role-pool contrast, mode-split identity, role migration, pool turnover.

There is **one sentence** (the identity line) but it is a composition of two claims, not an archetype. There is **no single archetype** in the V1 Profile.

### 6.2 Why claims, not an archetype

1. **Players are several things at once.** The brief is right: "hero-specialised, lane-strong, safe, currently more aggressive" are independent. A single label either hides most of them or becomes a grid of 18–200 combinations nobody can explain.
2. **A living label must not flap.** A single categorical label changes whenever *any* input crosses *any* boundary. Independent claims with their own hysteresis change rarely and legibly ("Luna is now Rising" does not rewrite who you are).
3. **Evidence stays attached.** Each claim has one operational definition and one "Why am I seeing this?" panel. An archetype's evidence is a combination of axes, which is exactly where astrology creeps in.
4. **Refusal is granular.** A player can have a confirmed role shape and no confirmed hero shape. An archetype must refuse wholesale (V7 correctly does), which on a daily surface means many players get nothing.

### 6.3 Audit of the earlier Report Card systems — what still holds up

| Earlier element | Verdict for the living Profile | Why |
|---|---|---|
| **V5 Element = one observable axis, no motive/personality claim** | **Holds.** Becomes the "Claim" contract. | The discipline is right; the implementation was OpenDota summary-only. |
| **V5 Pattern = qualified relationship between Elements** | **Holds as a concept, deferred.** | Relationship claims (e.g. presence × deaths) are valuable but need validated style claims first (P1+). |
| **V5 five-zone spectra (e.g. Focused → Wide)** | **Rejected for the Profile.** Replaced by three states: lean A / no clear lean / lean B. | V7 D2 measured that 65.2% of 4,983 player-Findings would carry an interval straddling a band boundary; five zones are false precision and would flap. |
| **V5 18 Elements, 11 Patterns** | **Mostly retired.** | Built on summary history; several proxies (involvement as (K+A)/min) are confounded by duration and team tempo (`02-finding-reassessment.md`). |
| **V5 Comfort Edge / Partial Transfer / Proven Flexibility** (performance on vs off comfort pool) | **Rejected as identity claims.** | V7 measured `transfer_risk` and `transfer_activity` at τ = 0 across 501 players: no between-player signal beyond measurement error. |
| **V5 Bounceback / Performance Slide, Session Fade / Rise** | **Rejected for the Profile.** | Session drift was rejected in STRATZ research; post-loss dimensions have V7 reliabilities of 0.38–0.54; the language invites tilt/resilience claims. |
| **V5 Hero Portfolio: Pool Evolution** (equal chronological windows, Jensen–Shannon shift, stable-core detection) | **Holds.** Adopted for Pool Turnover and Role Migration (§7). | Balanced windows are auditable and resist one-off heroes. |
| **V5 Hero Mirror boundary copy** ("Not your best hero. Not necessarily your most played.") | **Holds as a copy principle.** | Exactly the separation the Signature Hero system needs. |
| **V5/V6 refusal as a product state** | **Holds.** | Carried into every claim. |
| **V6.1 hierarchical family correction, 128 generated supporting signals** | **Not carried.** | STRATZ research found the 128-signal catalog generated, not designed; the Profile needs few, individuated claims. |
| **V7 mode stratification** | **Holds and is load-bearing.** | Mode-blind tempo correlated 0.889 with Turbo share; admitting Turbo moved pool breadth by +1.75 effective heroes on the specimen. All Profile aggregates are per bucket. |
| **V7 "a contrast is an insight; a number is not"** | **Holds.** | Drives the signature findings catalog. |
| **V7 "diagnosis sits upstream of the result"; recommendation is a separate computation** | **Holds.** | Recommendations stay out of the Profile. |
| **V7 16 population-ranked Finding dimensions** | **Partially carried as P1 style claims.** | High-reliability, behaviour-emitted dimensions (vision uptime 0.985, neutral-farm share 0.924, deaths-in-quiet-minutes 0.893) are strong candidates once a reference population is validated for per-role, per-bucket, living use. Low-reliability or outcome-defined dimensions are not carried. |
| **V7 no strength bands; reliability ≠ confidence; no percentiles as skill** | **Holds.** | Profile copy never says "top X%" or "strong/moderate/slight". |
| **V7 rank fence** | **Holds.** | Rank never enters any Profile claim. |
| **V7 archetype grid** | **Kept for Annual Report; EXPERIMENTAL on Profile.** | See §6.4. |

### 6.4 The V7 archetype on a living Profile

The archetype is well-built for an annual keepsake and poorly suited to a daily identity surface:

- **Population-relative cuts drift.** Tempo terciles and fight-style cuts are population statistics within a mode stratum; as the population changes, a player's label can change without their play changing.
- **Tempo is tightly packed.** Terciles sit 0.015–0.018 apart on a p5–p95 range of ≈ 0.075. Many players live near a boundary; on a living profile they would oscillate.
- **The modifier is outcome-derived and ambiguous near its cut.** Session win-rate dispersion has a population median of 0.976 against a cut of 1.0, with a known uncorrected downward bias.
- **"Ghost" and similar axis words need an annual, playful frame to be safe.**

Recommendation: the Annual Report keeps the archetype as its calling card. The Profile may *display the most recent annual archetype as a dated badge* ("2026 calling card: The Timekeeper") — P1 — but must not compute a live one until hysteresis on all three axes is designed and measured to change for fewer than ~10% of established players per quarter without a play change. That is EXPERIMENTAL.

### 6.5 Performance vs identity

Every claim in §7 is labelled with its **skill-proxy risk**: the degree to which the claim would rise or fall with skill alone rather than style. Rules:

1. P0 claims must have **low** skill-proxy risk. Role shape, pool shape, exploration, hero tags, and mode split are choices, not skill.
2. Current form is self-relative and therefore not a skill *level*, but it is an honest *performance change* signal; it is labelled "recent", never "you are good at".
3. P1 style claims with moderate risk (fight presence, vision uptime) must be framed as *how often* or *how much*, never *how well*, and must be conditioned on role and bucket.
4. Any claim whose favourable direction is universal ("more is always better") is a skill claim wearing style clothes. It may appear in Right now or PBs, not in identity.

---

## 7. Trait / Pattern Catalog

### 7.1 Shared definitions used by every claim

| Term | Definition (LOCKED-PROPOSED unless marked) |
|---|---|
| **Eligible match** | A READY match with progression classification STANDARD or TURBO and a resolved effective role, under the Match Lifecycle and Role Metrics SSOTs. The Profile uses the same eligibility (≥ 600 s, fail-closed integrity) so that every profile number reconciles with Progression. NONE(reason) matches are counted in the header as "tracked" but never feed claims. |
| **Bucket** | STANDARD or TURBO. Every aggregate and claim is per bucket. No claim mixes buckets except the explicit Mode-Split contrast, which compares two bucket-level results without pooling their matches. |
| **Identity window** | The most recent **200** eligible matches in the bucket, excluding matches older than **24 months** (PROVISIONAL sizes). Used for account-scope claims. |
| **Role window** | The most recent **100** eligible matches in the bucket with that effective role, excluding matches older than **24 months** (PROVISIONAL). Used for role-scope claims. |
| **Chronology** | `(provider_started_at, provider_source_match_id)`, as in the Lifecycle SSOT. |
| **Evaluation** | Recompute a claim's aggregate after each READY eligible match in its scope. |
| **Persistence rule** | A claim changes state only when the new state's *enter* condition holds at two evaluations separated by **≥ 10** newly eligible matches in the claim's scope. Leaving a state uses the looser *exit* condition with the same persistence rule. |
| **Effective sample for shares** | Matches are clustered in sessions and hero/role choices are autocorrelated. For binomial intervals use `n_eff = n / 2` (a design-effect of 2; PROVISIONAL, to be measured on the corpus by session-block variance). |
| **Claim states** | `CANDIDATE` (enter condition met once) → `CONFIRMED` (persistence satisfied; visible) → `FADING` (exit condition met once; still visible, marked "less clear lately") → `RETIRED` (exit persistence satisfied; removed, change event written). Or `CANDIDATE` → discarded when the enter condition fails before persistence. |
| **Evidence payload** | Every visible claim carries: claim ID + version, bucket, scope (role/hero), window definition, n, the aggregate values, thresholds crossed, state since (match + date), and up to five representative match references. |
| **Calibration requirement** | Every PROVISIONAL threshold must be set on the development corpus against two targets before release: (1) state distribution is non-degenerate (no state holds > 80% or < 3% of established players, unless the behaviour genuinely is that concentrated — record which); (2) quarterly churn for established players with stable play is < 10% (measured by replaying chronology). |

### 7.2 Priority summary

| Rank | Claim | Recommendation |
|---:|---|---|
| 1 | Role Shape | **P0** |
| 2 | Hero tags (Go-to / Longtime / Rising / Favourite) — §8 | **P0** |
| 3 | Hero Shape (per role) | **P0** |
| 4 | Current-Form Run | **P0** (gated on Progression) |
| 5 | Role Migration | **P0** |
| 6 | Mode-Split Identity | **P0** |
| 7 | Role-Pool Contrast | **P0** |
| 8 | Exploration | **P0** |
| 9 | Pool Turnover | **P0** (history ≥ 200 role matches) |
| 10 | PB Momentum | **P0** (gated on PB engine) |
| 11 | Observer Uptime (Support) | **P1** — reference population |
| 12 | Farm Source (cores) | **P1** — reference population + hero normalisation |
| 13 | Fight Presence Level | **P1** — reference population |
| 14 | Presence ↔ Exposure tradeoff | **P1** — private only |
| 15 | Then vs Now (durable growth) | **P1** |
| 16 | Steadier Lately (consistency change) | **P1** |
| 17 | Position Switching | **P1** |
| 18 | Best Record hero — §8 | **P1** |
| 19 | Distinctive Pick — §8 | **P1** |
| 20 | Records | **P1** |
| 21 | Comfort Steadiness | EXPERIMENTAL |
| 22 | Lane Outcome Record | EXPERIMENTAL |
| 23 | Build Loyalty | EXPERIMENTAL |
| 24 | Return-After-Break Hero | EXPERIMENTAL |
| 25 | Live Archetype | EXPERIMENTAL |
| 26 | Patch Adaptation | EXPERIMENTAL |
| — | Aggression, tilt/post-loss, recovery after bad lanes, strong-in-losses, falls-off-outside-comfort, clutch/closer, tempo label, session streakiness, party vs solo, time of day, overall score/skill radar, initiator/control, IMP/behaviour, rank-derived, map movement, team-oriented | **REJECT** |

### 7.3 P0 claims

#### C1 · Role Shape — **P0**

| Field | Specification |
|---|---|
| Player-friendly meaning | How your games spread across Carry, Mid, Offlane and Support in this mode. |
| Example copy | "Carry specialist." · "Carry first, Support second." · "Carry and Support, almost evenly." · "You cover three roles regularly." |
| Why players care | Role is the primary way Dota players describe themselves and each other ("support main"); STRATZ research ranked Role Shape highest of 52 candidates (96.8/100) as "the most-discussed, least-measured thing in Dota self-description". |
| Metrics | Count of eligible matches per effective role in the identity window. |
| Formula / detection | `s_r = n_r / n` for each role, sorted `s_1 ≥ s_2 ≥ …`. States, first match wins: **SPECIALIST** `s_1 ≥ 0.75` (exit `< 0.68`); **ANCHORED** `0.50 ≤ s_1 < 0.75` and `s_2 ≥ 0.15` (exit `s_1 < 0.45`); **DUAL** `s_1 < 0.50`, `s_2 ≥ 0.30`, `s_1 + s_2 ≥ 0.80` (exit `s_2 < 0.25`); **FLEXIBLE** `s_1 < 0.50` and at least three roles with `s ≥ 0.15` (exit `s_1 ≥ 0.55`); otherwise **NO_CLEAR_SHAPE**. Enter additionally requires the Wilson 80% lower bound of `s_1` (with `n_eff`) to be ≥ the state's exit threshold. All thresholds PROVISIONAL. |
| Role applicability | Account scope, per bucket. Support means Positions 4 and 5 combined (Role Metrics SSOT). |
| Hero normalisation | None needed; role is the measurement. |
| Sample requirement | `n ≥ 30` eligible matches in the bucket window. |
| Confidence rule | Wilson gate above + persistence rule. |
| Stability | Slow. A SPECIALIST at 80% needs roughly 25–30 consecutive off-role matches to exit. |
| Update window | Identity window (200 / 24 months). |
| Confounders | Role classification errors (mitigated: user correction is authoritative and triggers rebuild); ranked role queue forcing roles; party play (a friend always takes Carry); Turbo vs Standard differences (handled by bucket). |
| Skill-proxy risk | Low. |
| Explainability | "Of your last 200 Standard matches: Carry 148, Support 32, Mid 12, Offlane 8." |
| Shareability | High. Core of the share card. |
| Data availability | **AVAILABLE NOW** — effective role from upstream resolution (STRATZ `position` observed at 91% on the specimen) with user correction. Unresolved matches are excluded and counted ("6 matches without a role"). |

#### C2 · Hero Shape — **P0**

| Field | Specification |
|---|---|
| Player-friendly meaning | Whether you go deep on a few heroes in a role or spread across many. |
| Example copy | "A narrow Carry pool: most games on about three heroes." · "A steady rotation of around six Support heroes." · "A wide Mid pool." |
| Why players care | "Hero spammer", "one-trick", "hero pool" are core community vocabulary; pro coverage leads with unique heroes. |
| Metrics | Hero counts within the role window. |
| Formula / detection | Effective number of heroes via the unbiased inverse Simpson index: `H = n(n−1) / Σ n_h(n_h−1)`. States: **NARROW** `H ≤ 4.0` (exit `> 5.0`); **ROTATION** `4.0 < H < 10.0`; **WIDE** `H ≥ 10.0` (exit `< 8.5`). The unbiased form prevents small windows from looking artificially narrow. PROVISIONAL cut points. |
| Role applicability | Role scope, per bucket; every role with ≥ 30 role-window matches. |
| Hero normalisation | Not applicable; however Turbo breadth is systematically different (repo specimen: +1.75 effective heroes when Turbo admitted), hence per bucket. |
| Sample requirement | ≥ 30 matches in role window. |
| Confidence rule | Persistence rule; additionally a session-block bootstrap 80% interval for `H` must not cross the exit threshold at entry. |
| Stability | Slow-medium. |
| Update window | Role window (100 / 24 months). |
| Confounders | Meta and patch shifts (pool churn is real behaviour, but may be externally induced); random/All Random picks (STRATZ `isRandom` retained; random matches excluded from Hero Shape — PROVISIONAL decision); ranked role queue. |
| Skill-proxy risk | Low. Pool width is choice. Copy never implies "narrow is worse" or "wide is better". |
| Explainability | "In your last 100 Carry matches: Juggernaut 38, Wraith King 22, Luna 14, 9 others 26." |
| Shareability | High in combination with role ("Carry specialist, narrow pool"). |
| Data availability | **AVAILABLE NOW.** |

#### C3 · Exploration — **P0**

| Field | Specification |
|---|---|
| Player-friendly meaning | How often you pick a hero you haven't played recently. |
| Example copy | "You mostly stick with heroes you know." · "About one game in three is a hero you haven't played lately." |
| Why players care | Loyal vs experimental is how players describe themselves ("I'm trying new heroes this patch"); V7 `hero_novelty` had meaningful between-player spread (reliability 0.736). |
| Metrics | Per match: whether the hero appears in the player's previous 100 eligible matches in the same bucket (any role). |
| Formula / detection | `x = share of the last 50 eligible role matches whose hero was absent from the preceding 100 bucket matches`. States: **LOYAL** `x ≤ 0.08` (exit `> 0.12`); **MIXED**; **EXPLORING** `x ≥ 0.25` (exit `< 0.20`). Match-count lookback (not 30 days) so irregular players are not called explorers merely for returning after a break. PROVISIONAL. |
| Role applicability | Role scope, per bucket; applies to all roles. |
| Hero normalisation | None. |
| Sample requirement | ≥ 150 bucket matches of history (100 lookback + 50 evaluation), of which ≥ 30 in the role. |
| Confidence rule | Wilson gate on `x` with `n_eff`, plus persistence. |
| Stability | Medium. |
| Update window | Last 50 role matches with 100-match lookback. |
| Confounders | Major patches or new hero releases (a real but external cause — the explanation panel notes a patch boundary when > 40% of new-hero picks follow one); account sharing. |
| Skill-proxy risk | Low. |
| Explainability | "17 of your last 50 Support matches were on heroes you hadn't played in your previous 100 matches." |
| Shareability | Medium ("Explorer" framing is flattering; "Loyal" is warm). |
| Data availability | **AVAILABLE NOW.** |

#### C4 · Role-Pool Contrast — **P0** (signature finding)

| Field | Specification |
|---|---|
| Player-friendly meaning | You treat your roles differently: deep in one, broad in another. |
| Example copy | "Your Support pool is about three times wider than your Carry pool." |
| Why players care | Non-obvious from any existing profile (DotaBuff lists heroes, not per-role pool shapes); it describes a real habit players recognise once named. |
| Metrics | `H` (C2) for each role with a confirmed Hero Shape in the same bucket. |
| Formula / detection | For roles `a, b` with confirmed Hero Shape: ratio `H_a / H_b ≥ 2.0` and the bootstrap 80% interval of the ratio excludes 1.5. Copy rounds to "about twice / three times". |
| Role applicability | Cross-role, same bucket. |
| Hero normalisation | None. Note that Support hero choice is structurally broader in many metas; the claim describes the player, not a rarity, and never says "unusual". |
| Sample requirement | Both roles ≥ 30 role-window matches. |
| Confidence rule | Interval rule above + persistence. |
| Stability | Slow. |
| Update window | Role windows. |
| Confounders | Unequal sample sizes (a 30-match role vs a 100-match role) — the unbiased index and bootstrap handle most of it; require the smaller role ≥ 30. |
| Skill-proxy risk | Low. |
| Explainability | Two small hero-count tables side by side. |
| Shareability | Medium-high ("I'm a one-hero Carry and a whatever-we-need Support"). |
| Data availability | **AVAILABLE NOW.** |

#### C5 · Mode-Split Identity — **P0** (signature finding)

| Field | Specification |
|---|---|
| Player-friendly meaning | You are a different player in Turbo than in Standard. |
| Example copy | "In Standard you're a Support. In Turbo, you're a Mid." |
| Why players care | Players already treat Turbo as its own world (community threads); this makes the split explicit and is often genuinely surprising. |
| Metrics | Role Shape (C1) and primary-role heroes per bucket. |
| Formula / detection | Both buckets have confirmed Role Shape with different top roles, **or** the same top role with zero overlap between their Go-to/Longtime heroes. |
| Role applicability | Account scope. |
| Hero normalisation | None. |
| Sample requirement | Confirmed Role Shape in both buckets (≥ 30 matches each). |
| Confidence rule | Inherits both confirmations. |
| Stability | Slow. |
| Update window | Identity windows. |
| Confounders | Queue context (Turbo with friends, Standard solo) — the claim describes observable choice, not motive. |
| Skill-proxy risk | None. |
| Explainability | Two role bars, labelled by mode. |
| Shareability | High. |
| Data availability | **AVAILABLE NOW.** |

#### C6 · Role Migration — **P0** (change claim)

| Field | Specification |
|---|---|
| Player-friendly meaning | Your role mix has shifted. |
| Example copy | "Support went from 8% to 31% of your Standard games." · "Offlane has overtaken Mid as your second role." |
| Why players care | Role changes are life events in Dota ("I switched to support this year"); STRATZ research scored Role Migration 85.0, gated on Role Shape. |
| Metrics | Role shares in two equal, adjacent chronological windows. |
| Formula / detection | Adapted from V5 Pool Evolution: windows `W_prev` = matches 101–200 back, `W_recent` = last 100 (bucket). Trigger when (a) any role's share changes by ≥ 15 percentage points **and** a two-proportion test with `n_eff` gives an 80% interval excluding 8 pp, or (b) the rank order of the top two roles swaps with both ≥ 15% in `W_recent`. PROVISIONAL. |
| Role applicability | Account scope, per bucket. |
| Hero normalisation | None. |
| Sample requirement | ≥ 200 bucket matches (two full windows); a lighter 50/50 version (`≥ 100 matches`, 20 pp threshold) is allowed for players with 100–199. |
| Confidence rule | Interval rule + persistence (must still hold 10 matches later). |
| Stability | Event-like: produces a change event, then a dated claim that expires after 100 further matches. |
| Update window | Two 100-match windows. |
| Confounders | Role-queue availability; friends' presence; seasonal events. |
| Skill-proxy risk | None. |
| Explainability | Two stacked role bars "then" and "now" with window dates. |
| Shareability | Medium-high as a moment ("Support era"). |
| Data availability | **AVAILABLE NOW**; needs history import for older windows (production acquisition depth: 500 deep matches per account; history pages deeper). |

#### C7 · Pool Turnover — **P0** (change claim)

| Field | Specification |
|---|---|
| Player-friendly meaning | How much your hero pool in a role has changed. |
| Example copy | "Only one of your top five Carry heroes from a year ago is still in your top five." · "Same Support heroes as last year — your core hasn't moved." |
| Why players care | "Hero pool changes with patches" is common talk; players rarely know how much theirs moved. |
| Metrics | Hero distributions in two equal adjacent role windows. |
| Formula / detection | Windows of 50 role matches each (latest 50 vs previous 50) — or 100/100 when ≥ 200 role matches exist. Compute top-5 overlap and normalised Jensen–Shannon distance between hero distributions (as in V5 Pool Evolution). **RESHAPED**: top-5 overlap ≤ 2 and JSD ≥ 0.45; **STABLE CORE**: top-3 identical sets and JSD ≤ 0.25. PROVISIONAL. |
| Role applicability | Role scope, per bucket. |
| Hero normalisation | None; windows are balanced to avoid the V5 flaw of comparing a long past with a short present. |
| Sample requirement | ≥ 100 role matches (50/50); 100/100 version preferred at ≥ 200. |
| Confidence rule | Bootstrap interval of JSD must sit entirely on one side of the midpoint between thresholds; persistence. |
| Stability | Event-like, re-evaluated per 25 new role matches. |
| Update window | Two balanced role windows. |
| Confounders | Patch or hero reworks (flagged in explanation when the window boundary coincides with a major patch via `gameVersionId`); hero bans in the meta. |
| Skill-proxy risk | None. |
| Explainability | Side-by-side top-5 lists "then" and "now". |
| Shareability | Medium. |
| Data availability | **AVAILABLE NOW**, **NEEDS MORE HISTORICAL DATA** for new users (≥ 100 role matches). |

#### C8 · Current-Form Run — **P0** (Right now; gated on Progression Batches A–F)

| Field | Specification |
|---|---|
| Player-friendly meaning | A registered role metric has been consistently above or below your own usual lately. |
| Example copy | "CS at 10:00 has been above your usual in 8 of your last 10 Carry matches." · "Healing per 10 minutes has been below your usual in 8 of your last 10 Support matches." |
| Why players care | Growth independent of rank is the dominant r/learndota2 concern; the Hot Streak badge pattern proves short, time-scoped state is legible. |
| Metrics | Finalised progression snapshots: for each of the last 10 BASELINE_READY observations of one progression identity (`bucket + role + metric_id + metric_version`), its `direction_delta` against the baseline known *at the time of that match*. |
| Formula / detection | `f = #(direction_delta > 0)`, `u = #(direction_delta < 0)` over the last 10. **UP-RUN** when `f ≥ 8` and the median `direction_delta` of the 10 is ≥ 0.5 × IQR of the 20-observation baseline window of the most recent snapshot. **DOWN-RUN** symmetric. Exit when `f ≤ 5` (resp. `u ≤ 5`). Stale (hidden) if the latest observation is older than 30 days. PROVISIONAL cut points. |
| Role applicability | Every registered V1 metric in every role (20 metrics). |
| Hero normalisation | None — inherits Progression's rule that heroes never split a role track. The explanation panel lists hero composition of the 10 matches and warns when one hero is ≥ 7 of them ("mostly Luna games"). |
| Sample requirement | 10 BASELINE_READY observations, i.e. ≥ 15 measured observations in that identity. |
| Confidence rule | Using each match's *own* finalised baseline avoids hindsight. A sign count alone is not enough: under independence P(≥ 8 of 10) ≈ 5.5%, and with up to 6 metrics per role ≈ 29% chance of at least one spurious run. The magnitude gate plus a calibration target — **≤ 10% of player-weeks show a run when chronology is shuffled within the player** — must be met before release. |
| Stability | Fast, by design. Because the baseline rolls (previous 20), a sustained improvement stops counting as "above usual" within ~20 matches; the run expires naturally and durable change becomes a Then-vs-Now claim (C14, P1). |
| Update window | Last 10 observations. |
| Confounders | Hero composition; short-match N/A patterns (N/A never counts); party play; opponent skill changes (MMR movement changes lobby difficulty); patch changes. |
| Skill-proxy risk | Moderate by nature (it is a performance change), mitigated by being self-relative and labelled "recent". |
| Explainability | Ten dots (above/below usual) with dates, heroes, and the baseline median; link to Progression. |
| Shareability | UP-RUN only, opt-in, with window label. DOWN-RUN never shared. |
| Data availability | **DERIVABLE NOW** once Progression persists snapshots; five of 20 metrics are implemented on candidate branch `d691008`, none on `main`. |

#### C9 · PB Momentum — **P0** (Right now; gated on Progression Batch F)

| Field | Specification |
|---|---|
| Player-friendly meaning | You've been setting personal bests lately. |
| Example copy | "3 Carry personal bests in your last 20 Carry matches." |
| Why players care | PRs drive Strava and Hevy habits; PBs are already a locked product concept. |
| Metrics | PB celebration ledger events per bucket + role. |
| Formula / detection | `k = PB events within the last 20 eligible role matches`; surface when `k ≥ 2`. |
| Role applicability | All roles. |
| Hero normalisation | None (PBs are role-scoped by SSOT). |
| Sample requirement | Inherits PB five-prior gate. |
| Confidence rule | Descriptive fact; no inference claimed. Copy never implies a trend beyond the count. |
| Stability | Fast. |
| Update window | Last 20 role matches. |
| Confounders | Early-history inflation (many PBs in the first 30 observations of a new metric). Mitigation: count only PBs set after ≥ 20 prior observations of that identity. Imported/recovered history never creates events (Lifecycle SSOT). |
| Skill-proxy risk | Moderate. |
| Explainability | List of the PB events with dates and values. |
| Shareability | High. |
| Data availability | **DERIVABLE NOW** after PB engine exists. |

### 7.4 P1 claims

Every P1 style claim (C10–C13) needs a **reference distribution** per `role × bucket` (and, where marked, per hero) built from a declared, versioned population, with the V7 rules intact: no rank, "reference population" wording, no percentiles presented as skill, no "top X%". The V7 new-lineage population artifacts are development-grade (sealed validation unopened), so these are P1.

State rule for all style claims: three states — **leans high / no clear lean / leans low** — using the player's shrunk role-window estimate against reference quantiles 0.25 and 0.75 (enter) and 0.32/0.68 (exit), with persistence. No five-zone spectra.

#### C10 · Observer Uptime (Support) — **P1**

| Field | Specification |
|---|---|
| Meaning / copy | "Your wards stay up: an observer of yours is alive in most minutes of your Support games." |
| Why players care | Warding is the most visible support duty; community discussion ties support usefulness to vision. |
| Metrics / formula | V7 `vision_coverage`: mean per-match share of minutes with an own observer alive (`stats.wards` type 0 validated as Observer). Role window, Support only. |
| Normalisation | Reference: Support × bucket. Hero effect small but present (heroes that roam with smoke); P1 checks hero-level residual variance before shipping. |
| Sample / confidence | ≥ 30 Support matches; V7 reliability 0.985 (DISCOVERY median). |
| Stability / confounders | Slow. Confounders: team already has a second warder; match duration; the Role Metrics SSOT tracks Wards Placed per 10 (placement) — uptime is a different estimand and must not be conflated. |
| Skill-proxy risk | Moderate (diligence, not placement quality). Copy says "stay up", never "good vision". |
| Shareability | High when leaning high; never when low. |
| Data availability | **DERIVABLE NOW** (fields acquired in `GetDeepMatchBatch`); **REQUIRES** validated reference population. |

#### C11 · Farm Source (Carry/Mid/Offlane) — **P1**

| Field | Specification |
|---|---|
| Meaning / copy | "More of your creep gold comes from the jungle than for most Carry games on the same heroes." / "…from lanes…" |
| Why players care | "Farming vs fighting", "jungle farmer" vocabulary. |
| Metrics / formula | V7 `lane_vs_jungle_share`: neutral-creep share of creep gold from `farmDistributionReport`. |
| Normalisation | **Hero-normalised** residual required: reference per `hero × role × bucket` where cell size allows, falling back to hero-function groups from the hero-knowledge snapshot; recorded fallback level. Legion/Axe-style junglers otherwise dominate. |
| Sample / confidence | ≥ 30 role matches; V7 reliability 0.924. |
| Confounders | Hero pool (hence normalisation), lane dominance, meta. |
| Skill-proxy risk | Low-moderate. Never valenced. |
| Shareability | Medium. |
| Data availability | **DERIVABLE NOW**; **REQUIRES EXPERIMENTATION** on hero-normalised reference. |

#### C12 · Fight Presence Level (Mid/Offlane/Support) — **P1**

| Field | Specification |
|---|---|
| Meaning / copy | "As Offlane, you're in on more of your team's kills than most Offlane players." |
| Metrics / formula | Role Metrics SSOT `*.fight_presence.v1` comparison values (credited K+A over team credited kills), median over role window. |
| Normalisation | Reference per role × bucket; Turbo cuts differ materially (V7: participation tercile 0.405 Standard vs 0.492 Turbo). |
| Sample / confidence | ≥ 30 role matches. |
| Confounders | Hero kit (global ultimates), team kill volume, stomps. |
| Skill-proxy risk | **Moderate-high.** Higher presence correlates with winning and skill. Framed as "how often you're involved", paired with C13 where possible. |
| Shareability | Medium, high-lean only. |
| Data availability | **DERIVABLE NOW** for Support (implemented on candidate branch); Offlane/Mid pending calculators. |

#### C13 · Presence ↔ Exposure tradeoff — **P1, private only**

| Field | Specification |
|---|---|
| Meaning / copy | "You're in a lot of your team's fights as Offlane, and more of your deaths come in minutes when your team isn't fighting." |
| Metrics / formula | C12 lean + V7 `deaths_alone_share` (reliability 0.893) or Carry `dead_time_rate` when implemented. Claim only when both halves are confirmed in the same role/bucket. |
| Rationale | V5's Controlled Presence / Presence Tax pairing is the right *honest* shape: a tradeoff, not a weakness. |
| Confounders | Hero kit (initiators die), team composition. "Quiet minute" is a proxy for isolation, not measured distance (V7 master plan copy constraint). |
| Skill-proxy risk | High on the exposure half. Never on share card or other-player view. |
| Data availability | **REQUIRES EXPERIMENTATION.** |

#### C14 · Then vs Now — **P1**

| Field | Specification |
|---|---|
| Meaning / copy | "Your Carry CS at 10:00 has settled higher than a year ago: typical 52 now, 44 then." |
| Formula | Median of last 20 observations vs median of the 20 observations ending 100 observations earlier (fixed, non-overlapping reference), same progression identity and metric version; claim when the session-block bootstrap 90% interval of the difference excludes 0 and |difference| ≥ 0.5 × pooled IQR. |
| Why P1 | Needs ≥ 120 observations per identity; interacts with metric versioning (never across versions). Rolling baselines cannot express durable change, which is why this exists. |
| Confounders | Hero pool shift (report composition), patch, rank movement changing opponents. |
| Data availability | **NEEDS MORE HISTORICAL DATA.** |

#### C15 · Steadier Lately — **P1**

| Field | Specification |
|---|---|
| Meaning / copy | "Your Support healing has become steadier: less swing game to game than earlier." |
| Formula | Robust spread (IQR / median, only for strictly positive metrics; IQR for signed metrics) in last 40 vs previous 40 observations; claim when the ratio < 0.7 with bootstrap interval < 0.9. Self-relative only. |
| Why not "consistent player" | "Consistent" as a population trait is not established: variance mixes hero pool, match length and team context; V7 found session-level dispersion ambiguous around its cut. Change in own spread is defensible; absolute consistency is not. |
| Data availability | **NEEDS MORE HISTORICAL DATA.** |

#### C16 · Position Switching — **P1**

| Field | Specification |
|---|---|
| Meaning / copy | "You often change role between games in the same session." |
| Formula | V7 `position_flexibility`: share of consecutive in-session match pairs with different effective role (session = gap < 60 minutes, PROVISIONAL). Reliability 0.828 (Pass-1, parsed-dependent). |
| Why P1 | Adds nuance to FLEXIBLE role shape; requires session definition and correction handling. |
| Data availability | **DERIVABLE NOW.** |

#### Records — **P1**

Descriptive single-match extremes, per bucket and role where relevant: largest net-worth deficit won from (from `radiantNetworthLeads`, oriented by side), longest match, most camps stacked by 20:00, earliest level 6 as Mid, most credited towers as Offlane. Records are facts, never identity claims, never "comeback specialist". **DERIVABLE NOW.**

### 7.5 EXPERIMENTAL claims

| Claim | Question | Why not yet |
|---|---|---|
| **Comfort Steadiness** | Are your role metrics less variable on your Go-to heroes than on the rest? | Hero kit differences dominate raw spread; V7 transfer dimensions (performance on vs off pool) measured τ = 0. Only a hero-normalised variance comparison could say something, and it may also be noise. |
| **Lane Outcome Record** | Do you win your lane more than you win your games? | STRATZ `*LaneOutcome` needs a verified lane→side mapping; a sign error inverts the finding invisibly (`research/stratz-enrichment/00` T2-B). |
| **Build Loyalty** | Do you buy the same first items on a hero every game? | Item vocabulary exists, but patch fragility and "item timing" language guard; interesting, not identity-critical. |
| **Return-After-Break Hero** | Which hero do you pick first after a long break? | Delightful, but few breaks per player → tiny n. |
| **Live Archetype** | V7 grid computed continuously. | Flapping near packed tempo cuts and population drift (§6.4). |
| **Patch Adaptation** | How fast does your pool move after a major patch? | Needs multiple patches per player and a definition of "major". |

### 7.6 REJECTED

| Idea | Why rejected |
|---|---|
| **Aggressive ↔ conservative** | No valid aggression measurement without positions; every proxy (kills/min, deaths/min, damage) collapses into role, hero kit, and skill. Map movement requires playback (prohibited). |
| **Tilt / post-loss behaviour** (keeps queueing, switches hero, requeues faster) | V7 reliabilities 0.380–0.537; psychological framing ("tilt", "can't stop") is exactly the astrology/judgement the product forbids. Kept for the private Annual Report where already specified. |
| **Recovers well after poor lanes** | `lane_recovery_participation` measured τ = 0 (no between-player signal). |
| **Strong personal performance in losses** | The win/loss gap exists for nearly everyone (median player 2.4 fewer last hits at 10:00 in losses; 248/262 negative) but between-player difference in the gap measured τ_d = 0. There is no "unusually good in losses" to find. |
| **Falls off outside your top five heroes** | `transfer_risk` / `transfer_activity` measured τ = 0 across 501 players. The brief's first example is not supportable. |
| **Clutch / closer / comeback player** | Outcome-defined; `closer_vs_comeback` reliability 0.651, `lead_retention` 0.480; both excluded from recommendations as downstream of the result. Records (C20) can show a big comeback as a fact. |
| **Early-game ↔ late-game player** | Tempo is reliable but packed (terciles 0.015–0.018 apart) and mode-confounded; a label would imply a large difference that does not exist. |
| **Streaky ↔ steady (session results)** | Outcome-based dispersion with population median 0.976 near a 1.0 cut; ambiguous by construction. |
| **Solo vs party player** | STRATZ `partyId` observed at 8% with null semantics unestablished. **NOT RELIABLE.** |
| **Night owl / time of day** | Local-time inference rejected (no trustworthy timezone). |
| **Overall score, skill radar, "GPI"-style grades** | Contradicts the locked "no global score" rule; fuses skill and style; the old client playstyle bars show the failure mode. |
| **Initiator / controller / disabler** | Support Control is UNSUPPORTED in V1; no trusted disable-duration telemetry; cast counts are banned proxies. |
| **IMP, awards, behaviour score, toxicity** | Proprietary, unversionable; forbidden surfaces in the provider contract. |
| **Anything rank-derived** (bracket-relative labels, "plays above rank") | Rank fence enforced in code. |
| **Team-oriented ↔ independent** | Not observable; would be inferred from farm share and presence, which are role and hero effects. |
| **Side (Radiant/Dire) preference** | `side_sensitivity` is V7's negative control and measured τ = 0. It must never be surfaced. |

---

## 8. Signature Hero System

### 8.1 The concepts players use, and what we do with each

| Concept (player meaning) | Measurable? | Decision |
|---|---|---|
| **Most played** — raw frequency | Yes, exact | Shown as the **Go-to** tag inside a role. A global "most played" list exists only in the hero detail screen. |
| **Main** — the hero you are known for in a role | Frequency + role | Same as Go-to. "Main" is community vocabulary; we use "Go-to" to avoid implying it is the player's best. |
| **Comfort pick** — the hero you return to and feel safe on | Return behaviour yes; "feeling safe" no | Measured part becomes **Longtime** (sustained return over many blocks). We do not claim comfort or confidence. |
| **Longtime** — has been in your rotation for ages | Yes | **P0 tag.** |
| **Rising / emerging** — a hero taking over recently | Yes | **P0 tag.** |
| **Fading / former main** | Yes | P1, History and change feed only ("Wraith King has left your rotation"). |
| **Favourite** — the hero you love | No — only the player knows | **P0: user-pinned.** Nintendo's Year in Review lets people choose favourites rather than inferring them. |
| **Signature** — the hero people associate with you, unusual for your role | Frequency × longevity × distinctiveness vs typical pick rates | **P1 tag**, needs reference pick rates per role × bucket. Until then the word "signature" is not used in copy. |
| **Best record** — the hero you win most on | Win rate with shrinkage | **P1 tag**, labelled "Best record", never "best hero". |
| **Strongest** — the hero you *play best* | Needs hero-normalised role metrics | **EXPERIMENTAL.** Raw comparisons across heroes measure hero kits (Alchemist CS vs Troll CS), not the player. |
| **Pocket pick** — a rarely played hero you are reliable on | Tiny samples by definition | **REJECT** as a computed tag. A player can pin it as a favourite. |
| **Specialist hero** — a hero you are deep on | Equivalent to Go-to within a NARROW Hero Shape | Merged: "Go-to" + Hero Shape NARROW conveys it. |

### 8.2 Algorithms

All computed per **bucket × effective role**. A hero appears at most once per role; if it qualifies for several tags, show the highest-priority tag and list the others in its detail panel.

Priority on the Profile: **Go-to → Rising → Longtime → Favourite** (Favourite is always displayable in the pinned slot if the player set one).

**Candidate floor:** hero has ≥ 10 eligible matches in the role window and ≥ 8% of role-window matches. Random-assigned picks (`isRandom`) excluded (PROVISIONAL).

**Go-to (P0)**
```text
share_h = n_h(role window) / n(role window)
Go-to = argmax share_h over candidates
ties → more matches in the last 30 role matches → earlier first appearance
hysteresis: the incumbent Go-to is replaced only when a challenger's share
exceeds the incumbent's by ≥ 3 percentage points at two evaluations ≥ 10 role matches apart
```

**Longtime (P0)**
```text
Split all known role history (no 24-month cap) into consecutive blocks of 20 role matches.
blocks_h = number of blocks containing ≥ 2 plays of h
presence_h = blocks_h / blocks since h's first appearance
Longtime when blocks_h ≥ 6 AND presence_h ≥ 0.60 AND h played at least once in the last 40 role matches
```
Longevity uses all history (it is a historical fact) but requires recent presence, so ancient heroes cannot hold the tag.

**Rising (P0)**
```text
recent = last 30 role matches; before = the 100 role matches preceding them
Rising when plays_recent ≥ 6 AND share_recent ≥ 0.20 AND share_before ≤ 0.05
Persistence: still true after 10 more role matches (otherwise the candidate is discarded silently)
Expires: after 60 further role matches (it has either become Go-to/Longtime or not)
```

**Favourite (P0)** — player-selected, any hero, one per account; shown with a heart/pin; never inferred; never used in analytics.

**Distinctive / Signature (P1)**
```text
lift_h = share_h(role window) / p_h(reference role × bucket pick rate, same patch era)
Signature when (Go-to OR Longtime) AND lift_h ≥ 5 AND n_h ≥ 15
Copy: "You play Meepo about seven times as often as a typical Mid game features him."
```
Reference pick rates must be computed by us from a declared corpus; STRATZ precomputed aggregates are an unversionable provenance risk (`01-field-inventory.md` §1.4).

**Best Record (P1)**
```text
prior = player's win rate in that role and bucket (role window), strength k = 20 pseudo-matches
wr_shrunk_h = (wins_h + k·prior) / (n_h + k)            (empirical-Bayes style shrinkage)
Best Record when n_h ≥ 20 AND the Beta-posterior 80% interval of wr_h excludes prior
                 AND wr_shrunk_h is the maximum among candidates
Copy: "Best record: Ogre Magi, 31–17 in your Support games."
```
Shrinkage prevents 5–0 heroes from winning ([Variance Explained](http://varianceexplained.org/r/empirical_bayes_baseball/)). Matchmaking pulls win rates toward 50%, so few players will have one — that scarcity is honest.

### 8.3 What the hero section never says

- "Your best hero" (unless P1 Best Record, and then "best record").
- "Your comfort pick" as a claim about feelings.
- A hero tag computed across roles (a Carry Go-to and a Support Go-to are different facts).
- A hero tag computed across buckets.

---

## 9. Role Identity

### 9.1 What the Profile says about roles

| Topic | Definition |
|---|---|
| **Primary role** | The top role in the bucket's identity window, displayed as an **Anchor** only when its share ≥ 50% and Role Shape is confirmed. Otherwise the Profile shows the top role without the Anchor tier. |
| **Role tiers** (per role, per bucket) | **Anchor**: top role, ≥ 50%. **Regular**: ≥ 20%. **Occasional**: 5–20%. **Rare**: < 5%. Hysteresis ± 3 pp. PROVISIONAL. |
| **Secondary role** | The highest non-Anchor Regular. If none, "no regular second role". |
| **Specialisation** | Role Shape state (C1). Specialist and Flexible are presented as equal identities; neither is praise. |
| **Role evolution** | Role Migration events (C6) and, from P1, quarterly frozen History eras. |
| **Playstyle across roles** | V1: per-role Hero Shape, Exploration and hero tags differ by role (C2–C4). P1: per-role style claims (C10–C13). The Profile never compares a metric across roles. |

### 9.2 Consistency with the Role Metrics SSOT

- Effective role is consumed, never recomputed. A user correction triggers deterministic rebuild of every Profile aggregate in the affected bucket (§21.4).
- Positions 4 and 5 are one Support role. The Profile does not split them in V1. A descriptive "mostly position 5" sub-label from native `position` would be a separate owner decision (§25.6) because it would diverge from the progression key.
- Standard and Turbo are separate. The Profile shows one bucket at a time with a toggle, defaulting to the bucket with more eligible matches in the last 90 days.
- No combined all-role score, anywhere. The identity line is a sentence, not a score.
- Role-scoped current form and PBs come from Progression; the Profile never re-derives them.

### 9.3 Role uncertainty

Matches without a resolved effective role are excluded from every role claim and counted visibly in the role map footnote ("4 matches without a role — tap to set"). This turns classifier gaps into a correction affordance rather than silent bias. If more than 20% of a bucket's identity window lacks a role, Role Shape is withheld.

---

## 10. Style Dimensions

Dimensions tested against DATA (measurable now or soon), TRUTH (defensible interpretation, low skill-proxy), and HUMAN (a player recognises it).

### 10.1 Surviving dimensions

| Dimension | Poles | Actual behaviour measured | Scope | Release |
|---|---|---|---|---|
| **Role specialisation** | Specialist ↔ Flexible | Share of matches in top role; number of regular roles | Account × bucket | P0 |
| **Pool depth** | Narrow ↔ Wide | Effective number of heroes (unbiased inverse Simpson) | Role × bucket | P0 |
| **Loyalty** | Loyal ↔ Exploring | Share of picks absent from the previous 100 matches | Role × bucket | P0 |
| **Vision rhythm** | Wards lapse ↔ Wards stay up | Share of minutes with own observer alive | Support × bucket | P1 |
| **Farm source** | Lane-fed ↔ Jungle-fed | Neutral share of creep gold, hero-normalised | Core roles × bucket | P1 |
| **Fight involvement** | Selective ↔ Involved | Credited kill participation share | Mid/Offlane/Support × bucket | P1 |
| **Role switching** | Settled ↔ Switching | In-session consecutive role changes | Account × bucket | P1 |

### 10.2 Rejected dimensions (from the brief's list)

| Proposed | Verdict |
|---|---|
| Aggressive ↔ conservative | REJECT — unmeasurable without positions; skill proxy. |
| Independent ↔ team-oriented | REJECT — not observable. |
| Economy-oriented ↔ activity-oriented | REJECT as a cross-role axis — it is the role itself (farm priority). Within a role, Farm Source and Fight Involvement cover the measurable part. |
| Lane-focused ↔ scaling-focused | REJECT — lane outcomes unmapped; scaling not identifiable. |
| Stable ↔ volatile | REJECT as identity — see C15 for the defensible self-relative form. |
| Objective-oriented | P1 only as Offlane Objective Involvement form/PB (Progression); `fight_conversion` reliability 0.257 rules out a trait. |
| Fight-oriented | Covered by Fight Involvement (P1). |
| Survivability-oriented | Only as the private Presence ↔ Exposure pairing (P1). |
| Map/resource enabler | REJECT — stacks are countable (Support metric), "enabling" is not. |
| Initiator | REJECT — Control unsupported. |
| Recovery-oriented | REJECT — τ = 0. |
| Early ↔ late impact | REJECT — packed and mode-confounded. |

---

## 11. Strengths / Tradeoffs

### 11.1 Decision

**V1 has no "Strengths" section.** Every candidate strength available in V1 is either a skill proxy (a metric where more is better for everyone) or needs a reference population. Instead V1 expresses the positive side of a player through three honest channels:

1. **Identity claims that are flattering by recognition, not grading** ("Carry specialist", "Longtime Wraith King"). Being seen accurately is the reward.
2. **Right now** — up-runs against your own usual.
3. **Personal bests** — achievements scoped to role and metric.

### 11.2 From P1: tradeoffs, not grades

When style claims arrive, adverse information is shown only as **one half of a measured pair in the same role and bucket**, and only on the private profile:

| Tradeoff pair | Copy shape |
|---|---|
| Fight Involvement ↔ Exposure | "Involved in a lot of Offlane fights — and more of your deaths come in quiet minutes." |
| Farm Source (jungle-fed) ↔ Fight Involvement (selective) | "Jungle-fed Carry games, with fewer early kill involvements." |
| Pool depth (narrow) ↔ Exploration (loyal) | "Deep on a few Carry heroes, rarely trying new ones." (neutral pair; no adverse half) |

Rules:
- A tradeoff requires both halves CONFIRMED.
- Neither half is described as good or bad.
- No tradeoff appears on the share card or other-player view.
- A standalone adverse style claim (e.g. only exposure is confirmed) is not surfaced on the Profile. It may appear in the Annual Report's "one rough edge" scene, which already has proportion rules.

---

## 12. Current Form

### 12.1 What belongs in Right now

| Item | Source | Release |
|---|---|---|
| Current-Form Runs (C8), up to two per recently played role | Progression snapshots | P0 |
| PB Momentum (C9) | PB ledger | P0 |
| Rising hero announcement ("new in your Carry games") — mirrored from the hero section while in its first 30 matches | Hero tags | P0 |
| "Active role" note when the last 10 eligible matches are ≥ 70% a role that is not the Anchor ("Lately: mostly Support") | Role counts | P0 |

### 12.2 What does not belong

Win/loss streaks (outcome, already in the client and STRATZ), recent KDA, rank movement, "hot/cold" labels without a metric, any metric not in the Role Metrics registry.

### 12.3 Conceptual distinction (content rules for design)

| Stable identity | Current form |
|---|---|
| Sentence, no window label needed on the face (window in "Why?") | Every item carries its window: "last 10 Carry matches", "since 3 Sep" |
| Changes rarely; changes create a Change event | Changes often; no Change events |
| Solid presentation | Presentation must read as temporary (dated, dashed, or otherwise marked by design) |
| Share-eligible | Only UP-RUN and PB momentum are share-eligible, opt-in |
| Never shows a decline on the first screen | DOWN-RUNs are visible in the Right now list, never first, never shared |

### 12.4 Empty state

"Nothing unusual in your recent Carry matches — you're playing to your usual." This is a legitimate, reassuring state, not a failure.

---

## 13. Signature Findings — the "I didn't know that" catalog

A signature finding is a claim whose value is surprise. It must pass the same evidence rules as any claim, and it must be a **contrast** (role vs role, then vs now, frequency vs longevity, mode vs mode) — never a bare number.

Ranked by non-obviousness × defensibility.

| # | Finding | Example copy | Detection (claim) | Minimum data | Verdict |
|---:|---|---|---|---|---|
| 1 | **Two different players by mode** | "In Standard you're a Support. In Turbo, you're a Mid." | C5 | Confirmed Role Shape in both buckets | **P0** |
| 2 | **Your roles have different pool shapes** | "Your Support pool is about three times wider than your Carry pool." | C4 | Two roles ≥ 30 matches | **P0** |
| 3 | **Most played isn't longest-running** | "Juggernaut is your go-to, but Wraith King has been in your Carry rotation the longest — since early 2024." | Go-to ≠ Longtime hero in same role | Longtime (≥ 120 role matches of history) | **P0** |
| 4 | **A quiet role shift** | "Support went from 8% to 31% of your Standard games." | C6 | 200 bucket matches | **P0** |
| 5 | **Your pool reshaped / held** | "Only one of your top five Carry heroes from 100 games ago is still in your top five." / "Same top three Support heroes as 200 games ago." | C7 | 100–200 role matches | **P0** |
| 6 | **A hero took over** | "Luna went from 3 of 100 Carry games to 7 of your last 30." | Rising tag | 130 role matches | **P0** |
| 7 | **Loyal in one role, exploring in another** | "You rarely try new Carry heroes, but one Support game in three is a hero you haven't played lately." | C3 in two roles with opposite states | 150 bucket matches, two roles ≥ 30 | **P0** |
| 8 | **PBs clustering now** | "3 of your 5 Carry personal bests came in the last month." | PB ledger dates | PB engine | **P0** |
| 9 | **A role you think you play less than you do** | "You queue as a Carry player, but Support is 34% of your last 100 games." | Role tier Regular for a non-Anchor above 30% + role correction behaviour (no corrections into it) | 100 bucket matches | **P1** (needs user-declared preferred role; §25.6) |
| 10 | **A metric settled at a new level** | "Your typical CS at 10:00 as Carry is 52 now; 100 games ago it was 44." | C14 | 120 observations | **P1** |
| 11 | **Steadier than before** | "Your Support healing swings less game to game than it used to." | C15 | 80 observations | **P1** |
| 12 | **Distinctive pick** | "You play Meepo about seven times as often as a typical Mid game features him." | Distinctive tag | Reference pick rates | **P1** |
| 13 | **Best record isn't your go-to** | "Juggernaut is your go-to; your best record is Wraith King." | Best Record ≠ Go-to | Best Record gates | **P1** |
| 14 | **Wards that stay up** | "An observer of yours is alive in most minutes of your Support games." | C10 leans high | Reference population | **P1** |
| 15 | **Your biggest comeback** | "Your biggest recorded comeback: won from 16k behind at 34:00 on Wraith King." | Records | Deep match | **P1** (record, not trait) |
| 16 | **Return-after-break hero** | "After every long break, you come back on Pudge." | EXPERIMENTAL | Several breaks | EXPERIMENTAL |
| 17 | **Lane record vs game record** | "You win your lane more often than you win the game." | Lane outcome mapping | Lane→side validation | EXPERIMENTAL |
| 18 | **Same build every time** | "Same first three items on Juggernaut in 9 of 10 games." | Build loyalty | Item vocabulary + patch handling | EXPERIMENTAL |
| — | "Your win rate hides strong performance in losses" | — | τ_d = 0 | — | **REJECT** |
| — | "You recover unusually well after poor lanes" | — | τ = 0 | — | **REJECT** |
| — | "You fall off outside your top five" | — | τ = 0 | — | **REJECT** |
| — | "Early game improved while late game declined" | — | Cross-phase claim needs comparable phase metrics per role; Carry has CS@10 and CS 10–20 but "late game" is not a registered measurement | — | **REJECT** as phrased; C14 on individual metrics is the honest version |
| — | "You play better at night / with friends / on Radiant" | — | Timezone, `partyId`, negative control | — | **REJECT** |

Selection rule for the one reserved first-screen slot: see §23.3.

---

## 14. Profile Evolution

### 14.1 How claims emerge, strengthen, weaken, and retire

```text
                 enter condition met
   (nothing) ─────────────────────────▶ CANDIDATE  (invisible)
                                            │
             enter still met ≥10 matches    │   enter fails before persistence
             later, across ≥2 distinct days │   ─────────────▶ discarded (silent)
                                            ▼
                                        CONFIRMED  (visible; change event written)
                                            │
                              exit met once │   minimum dwell: 30 scope matches
                                            ▼
                                         FADING   (visible, "less clear lately")
                                            │
             exit still met ≥10 matches     │   enter met again
             later                          │   ─────────────▶ back to CONFIRMED (no event)
                                            ▼
                                        RETIRED   (removed; change event written)
```

- **Emerge:** a claim is computed from windowed aggregates, never from counting post-match observations. A CANDIDATE is invisible.
- **Strengthen:** we do not show strength adjectives (V7 D2). A claim "strengthens" only in its evidence panel: "Confirmed since March · based on 200 matches". Longer-held claims win ties for display.
- **Weaken:** FADING is shown with a subtle marker in the "Why?" panel only; the face copy is unchanged to avoid alarming churn.
- **Retire:** removal writes a change event where a meaningful successor exists ("Your Carry pool has widened"). Retirements with no successor are silent.
- **Minimum dwell:** a CONFIRMED claim cannot begin FADING until it has been confirmed for ≥ 30 matches in scope (except after a role correction rebuild).
- **Distinct days:** the persistence span must include matches on at least two calendar days (UTC), so a single marathon session cannot confirm a claim.

### 14.2 How the identity line changes

The identity line is recomposed from CONFIRMED and FADING states only. It therefore changes **only** when Role Shape or primary-role Hero Shape transitions CONFIRMED ↔ RETIRED. Expected frequency for a player with stable habits: less than once a quarter (calibration target in §7.1).

### 14.3 Graduation from post-match observations

```text
MATCH OBSERVATION   "Another Luna game."                (post-match engine)
      ↓  only if the observation maps to a registered Profile claim input
REPEATED SIGNAL     Luna plays accumulate in the role window
      ↓  claim aggregate crosses enter condition
EMERGING            Rising = CANDIDATE                  (invisible)
      ↓  persistence rule satisfied
CONFIRMED TENDENCY  Rising = CONFIRMED                  (Profile + change event)
      ↓  becomes Go-to or Longtime over time
PROFILE TRAIT       Luna = Go-to in Carry
```

Safeguards:

1. **Post-match cannot create claims.** It may *reference* claim state ("That's 7 of your last 30 Carry games on Luna"), using the same aggregate, never a separate count.
2. **Only registered claim inputs graduate.** A striking one-off observation (a 40-kill game) is a Record, not an emerging trait.
3. **One match never flips identity.** Enforced by windows, hysteresis, persistence, dwell, and distinct days.
4. **No hindsight.** Claims about "then" use only data available then for form (per-match finalised baselines), and frozen snapshots for history.

### 14.4 Profile change as content

**Change events** (append-only ledger, account-scoped, deduplicated by claim ID + version + state + scope):

| Event class | Trigger | Example | Surfaces |
|---|---|---|---|
| Identity shift | Role Shape state change | "You're now a Carry specialist in Standard." | Change feed, Profile badge |
| Role migration | C6 confirmed | "Support has overtaken Offlane as your second role." | Change feed |
| Hero arrival | Rising confirmed; Go-to replaced | "Luna is rising in your Carry games." / "Luna is now your Carry go-to." | Change feed, Right now |
| Hero departure (P1) | Former Go-to/Longtime drops below 3% of last 50 role matches | "Wraith King has left your Carry rotation." | Change feed only |
| Pool shape | Hero Shape transition; C7 confirmed | "Your Support pool has widened." | Change feed |
| Mode split | C5 confirmed/retired | "Turbo-you and Standard-you now play different roles." | Change feed |
| PB | PB celebration (Progression-owned) | "New Carry PB: CS at 10:00." | Existing PB surfaces; listed in Profile |

**Thresholds for surfacing:** only state transitions of CONFIRMED claims produce events. Numeric movement inside a state never does.

**Rate limits (PROVISIONAL):** at most one identity-class event (Identity shift, Pool shape, Mode split) per bucket per 30 days; if more qualify, bundle into one "Your profile changed" entry. Hero arrival/PB events are not rate-limited beyond deduplication.

**Delivery in V1:** in-app only — a Change feed plus an unread badge on the Profile tab. The Match Lifecycle SSOT limits V1 push notifications to READY lifecycle effects; whether a READY notification's copy may *mention* a profile change is an owner decision (§25.6). No separate profile push in V1.

**Methodology changes never notify.** Events produced by rebuilds after a claim version change are written with `cause = METHODOLOGY` and hidden from the feed.

### 14.5 Historical profile evolution (P1)

Freeze a **Profile Snapshot** at the end of each calendar quarter per bucket: identity line, role map, hero tags, confirmed claims, claim versions. Snapshots are immutable (like READY match snapshots). A History screen shows "eras" when consecutive snapshots differ in identity line or Go-to heroes. Snapshots are never recomputed under new methodology; a methodology change is shown as a boundary marker.

### 14.6 Data aging

| Question | Decision |
|---|---|
| Should a three-year-old match weigh like yesterday's? | **No, for identity.** Identity and role windows are match-count windows capped at 24 months. Ancient history cannot dominate current identity. |
| Recency weighting (EWMA)? | **Not in V1.** Hard windows with hysteresis are easier to explain ("your last 200 matches") and to rebuild deterministically. EWMA can be revisited if windows prove too jumpy at their trailing edge; the persistence rule already damps that. |
| Patches? | **No reset**, consistent with the Role Metrics SSOT. Pool Turnover and Exploration explanations flag major patch boundaries via `gameVersionId`. |
| Seasons? | Quarterly snapshots (P1) preserve history; the Annual Report owns the year. |
| Long gaps in play | Right now hides after 30 days without a match in that role. Identity remains, with "last played" in the header. After 180 days without any match, the identity line gains "(as of {month year})". |
| Old data retention | Keep all eligible history for Longtime, Records, PB history and snapshots. Aging affects *weighting in identity*, not retention. |

---

## 15. Profile Maturity

**UX decision:** do not put a profile-wide level ("Learning → Emerging → Established") on the page. Maturity differs by bucket and role (2,000 Standard matches and 6 Turbo; 300 Carry and 12 Mid), so a global level misleads. Instead every claim carries its own readiness, and the page uses **one gentle header phrase only below 30 eligible matches**. Unavailable claims are omitted, not teased, except for one line inviting play: "Your hero pool read unlocks after 30 Carry matches."

Counts below are eligible matches in one bucket, for a player concentrated in one role.

| Eligible matches | What we can responsibly reveal | What we withhold | First-screen reads |
|---|---|---|---|
| **5** | Header facts; heroes played with counts; roles seen with counts; Progression "baseline building" status. | Every claim; hero tags; form; PBs (five-prior gate). | "Getting to know your Dota · 5 matches" · "Carry 4 · Support 1" · hero list. Prompt to confirm roles. |
| **20** | Role lean in counts ("Mostly Carry so far"); most played heroes so far; first PBs possible on frequently measured metrics (sixth observation onward). | Role Shape (needs 30 + persistence); Hero Shape; tags; form (needs 15 measured observations with 10 baseline-ready); exploration. | "Mostly Carry so far." Hero list with counts. "Your first Carry personal best." when true. |
| **50** | Role Shape CONFIRMED if strong (30 + persistence); Hero Shape for a role with ≥ 30 role matches; Go-to tag; Current-Form Runs in the main role; PB list. | Longtime (needs 6 blocks = 120 role matches); Rising (130 role matches); Exploration (150); Migration (200 / light version at 100); Pool Turnover (100 role matches); mode split unless both buckets ≥ 30. | Full first screen minus signature finding in most cases. |
| **200** | Every P0 claim: Exploration, Role Migration (full), Longtime, Rising, Role-Pool Contrast, Pool Turnover, Mode Split where applicable. | P1 claims until their prerequisites ship; Then vs Now (120 observations per identity is often reached around here for the Anchor role). | Complete V1 Profile. |
| **2,000** | Everything above, with identity based on the last 200 (capped at 24 months); rich Longtime heroes; Records; quarterly snapshots/eras (P1); Then vs Now across several eras. | Nothing extra is inferred merely from volume. Volume is not a trait. | Same Profile; History screen becomes valuable. |

Imported history counts immediately toward maturity once admitted (it is trustworthy evidence), but never creates celebration or change events for the period before import (Lifecycle SSOT rule on imported/recovered history).

---

## 16. Shareable Player Card

### 16.1 Content model

| Field | Required | Source | Rule |
|---|---|---|---|
| Display name | Optional (default on for self-shares, player can hide) | STRATZ `steamAccount.name` | Escaped; never Steam ID or match IDs. |
| Avatar | Optional | STRATZ avatar | Same as name. |
| Bucket label | **Required** | Profile | "Standard" or "Turbo" printed on the card; cross-mode cards are not allowed. |
| Identity line | **Required** | C1 + C2 | Only from CONFIRMED states. |
| Role mini-bar | **Required** | C1 | Rounded to nearest 5%. |
| Hero portraits (≤ 3) with tags | **Required** (≥ 1) | §8 | Only Go-to, Longtime, Rising, Favourite (P1 adds Signature, Best Record). |
| One finding line | Optional, preferred | Whitelist: C3 (either state), C4, C5, C6, C7, Longtime-vs-Go-to contrast, PB momentum, UP-RUN (opt-in) | Never a DOWN-RUN, tradeoff, adverse style claim, recommendation, or rank. |
| Scope footer | **Required** | Windows | "Based on my last 200 Standard matches · Sep 2026". |
| Rank label | Off by default, explicit opt-in | Rank display (fenced) | Displayed as a label only, separate from all claims. |
| Attribution | **Required** | Static | App name. |

**Minimum viable card:** bucket + identity line + one hero portrait with tag + scope footer. If the identity line is not confirmed, there is no identity card; the player can share a hero card ("Most played so far") instead.

**Why this is the smallest high-signal version:** the identity line answers "who is this player", portraits answer "on what", the finding line answers "what's interesting", and the footer makes it honest. Rank, win rate and match count answer "how good/how much", which is the vanity axis the card avoids by default.

### 16.2 Examples

1. **Nika · Standard** — "Carry specialist with a narrow pool." Carry ████ 75% · Support 15%. [Juggernaut · Go-to] [Wraith King · Longtime] [Luna · Rising]. "Wraith King has been in my Carry rotation the longest." Last 200 Standard matches · Sep 2026.
2. **Mira · Standard** — "Support first, Offlane second." [Ogre Magi · Go-to] [Rubick · Longtime] [Tusk · Rising]. "About one Support game in three is a hero I haven't played lately."
3. **k1dd · Turbo** — "Mid specialist with a narrow pool." [Invoker · Go-to]. "Invoker in 58 of my last 100 Turbo games." (fact line from Hero Shape evidence)
4. **Tomo · Standard** — "Covers three roles regularly." Carry 35% · Offlane 30% · Support 25%. [Mars · Go-to] [Snapfire · Longtime]. "Offlane has overtaken Carry as my second role."
5. **Ren · Standard** — "Carry and Support, almost evenly." [Faceless Void · Go-to] [Shadow Shaman · Go-to]. "My Support pool is three times wider than my Carry pool."
6. **Ash · Both modes (two-card carousel)** — Standard card: "Support specialist." Turbo card: "Mid first, Carry second." Shared finding: "In Standard I'm a Support. In Turbo, I'm a Mid."
7. **Jun · Standard** — "Offlane specialist with a steady rotation." [Axe · Go-to] [Centaur Warrunner · Longtime] [Primal Beast · Rising]. "3 Offlane personal bests this month."
8. **Oli · Standard** — "Support first, Mid second." [Crystal Maiden · Favourite ♥] [Lion · Go-to]. "Same top three Support heroes as 200 games ago."

What makes someone ask "what's mine?": the card is instantly readable by any Dota player, and the role + portraits make every friend's card look different.

---

## 17. Other-Player View (future; not V1)

### 17.1 What becomes valuable when viewing someone else

| Useful | Why |
|---|---|
| Bucket-specific role map and identity line | "Will they actually play Support?" |
| Hero tags per role | "What will they pick?" |
| Recency ("last played", "Lately: mostly Mid") | "Is this still true?" |
| Pool depth in the role you need | Stack formation. |
| Mode split | "Turbo friend vs ranked teammate." |

### 17.2 What must never be shown to others

Current-form DOWN-RUNs, tradeoffs or adverse style claims, recommendations, post-loss/session habits (not in Profile anyway), private match references, rank unless the owner opted in, and any claim computed for an account that has not consented to derived-claim visibility.

### 17.3 Architecture requirements so V1 does not block this

1. **Claims are computed per account, not per app user.** The pipeline must accept any Steam account with public STRATZ data, even if the Profile is only rendered for the signed-in user in V1.
2. **Every claim declares a visibility class** — `PUBLIC_SAFE` (role map, identity line, hero tags, C4/C5/C6/C7), `SELF_ONLY` (form, tradeoffs, PB lists), `NEVER_PUBLIC` (none in V1 Profile, reserved) — and the payload is produced through projections, mirroring V7's `PublicProjection` pattern.
3. **Respect provider privacy flags** (`isAnonymous`, `isStratzPublic`) as refusal states.
4. **Owner-controlled visibility** settings per class, default private until a social feature ships.
5. **Acquisition cost** for non-users is real (≈ 45 deep requests per account at full depth, per V7 acquisition policy); a lighter "history-tier-only" projection (role map, hero tags) needs no deep data and should be the default for other-player lookups.

---

## 18. Relationship to Other Product Surfaces

### 18.1 Ownership map

| Surface | Owns | Consumes from | Must not show |
|---|---|---|---|
| **Post-match retrospective** | Single-match observations ("what you probably didn't notice") | Progression snapshot for that match; Profile claim state for references | Identity conclusions from one match |
| **Progression** | Metric observations, baselines, deltas, trend, PBs per role/bucket | Lifecycle READY matches | Identity sentences; cross-role summaries |
| **Profile** | Identity claims, hero tags, claim states, change events, share card, snapshots | Effective roles, hero IDs, Progression snapshots, PB ledger | Raw metric deltas already on Progression (links instead); single-match stories; recommendations |
| **Challenges / before play** | Focus prompts and goals | Profile context (role anchor, Rising hero, UP/DOWN runs), Progression | Identity claims restated as instructions |
| **Achievements** (future) | Milestones and badges (counts, longevity) | PB ledger, Profile Longtime/hero counts | Grades or rank-based badges |
| **Annual Report** | What characterised a year: Findings, one recommendation, archetype, keepsake | Same underlying data, frozen at report time | Living claims presented as annual facts |

### 18.2 One fact, different lenses (no duplicated numbers)

| Underlying fact | Post-match | Progression | Profile | Annual Report |
|---|---|---|---|---|
| CS at 10:00 rising | "61 CS at 10:00 — 7 above your usual." | Chart and deltas; PB if strict record. | "CS at 10:00 above your usual in 8 of your last 10 Carry matches." (Right now, links to Progression) → later "Settled at a new level" (C14). | "Your Carry laning climbed through the spring." (if a Finding) |
| Luna picks | "Another Luna game." | — | "Luna is rising in your Carry games." | "Luna arrived in April." (memory scene) |
| Support share growing | Off-role note if user corrected role. | Support histories fill. | "Support went from 8% to 31%." | "The year you became a Support." |
| Ward uptime | "Your observer was up 72% of the game." | Wards Placed per 10 (placement metric). | P1: "Wards stay up." | V7 Finding `vision_coverage` / Lighthouse special. |

Rule: **a number is displayed on exactly one surface as the primary representation**; others summarise in words and link.

---

## 19. Data Feasibility

| Component | Classification | Notes |
|---|---|---|
| Header: name, avatar, privacy | **AVAILABLE NOW** | `GetPlayerProfile`. |
| Header: eligible match counts, mode mix, last played | **DERIVABLE NOW** | Lifecycle classification; requires lifecycle persistence (Batches A–D). |
| Effective role per match | **AVAILABLE NOW** (provider position) / **DERIVABLE NOW** (corrections) | Upstream role-resolution contract still to be written; correction rebuild is Lifecycle Batch E. |
| C1 Role Shape, role tiers | **DERIVABLE NOW** | Thresholds PROVISIONAL → **REQUIRES EXPERIMENTATION** (calibration). |
| C2 Hero Shape | **DERIVABLE NOW** | Calibration. |
| C3 Exploration | **DERIVABLE NOW**; **NEEDS MORE HISTORICAL DATA** (≥ 150 matches) | |
| Go-to / Longtime / Rising / Favourite | **DERIVABLE NOW** (Favourite needs a user setting) | Longtime needs ≥ 120 role matches. |
| C4 Role-Pool Contrast, C5 Mode Split | **DERIVABLE NOW** | |
| C6 Role Migration, C7 Pool Turnover | **DERIVABLE NOW**; **NEEDS MORE HISTORICAL DATA** | Import depth matters: V7 policy acquires 500 deep matches; role for history-tier rows comes from `position` in `GetPlayerHistoryPage`. |
| C8 Current-Form Run | **DERIVABLE NOW** after Progression Batches A–F | 5 of 20 calculators exist on candidate branch `d691008`; none on `main`. Candidate uses mean (must be median). |
| C9 PB Momentum | **DERIVABLE NOW** after PB engine | |
| C10 Observer Uptime | **DERIVABLE NOW** (fields acquired) + **REQUIRES EXPERIMENTATION** (reference population) | |
| C11 Farm Source | **DERIVABLE NOW** (`farmDistributionReport` acquired) + **REQUIRES EXPERIMENTATION** (hero normalisation) | |
| C12 Fight Presence Level | **DERIVABLE NOW** for Support; Mid/Offlane pending calculators + reference | |
| C13 Presence ↔ Exposure | **REQUIRES EXPERIMENTATION** | Carry dead-time needs return-to-play intervals: **NEEDS ADDITIONAL STRATZ COLLECTION**. |
| C14 Then vs Now, C15 Steadier Lately | **NEEDS MORE HISTORICAL DATA** | |
| C16 Position Switching | **DERIVABLE NOW** | Session definition PROVISIONAL. |
| Distinctive / Signature tag | **REQUIRES EXPERIMENTATION** | Own reference pick-rate corpus; STRATZ aggregates rejected for provenance. |
| Best Record tag | **DERIVABLE NOW** | Shrinkage gates. |
| Records | **DERIVABLE NOW** | Side orientation of `radiantNetworthLeads` required. |
| Quarterly snapshots / eras | **DERIVABLE NOW** (storage) / **NEEDS MORE HISTORICAL DATA** (value) | |
| Lane Outcome Record | **REQUIRES EXPERIMENTATION** | Lane→side mapping unvalidated. |
| Build Loyalty | **REQUIRES EXPERIMENTATION** | Item vocabulary exists; patch handling. |
| Live archetype | **REQUIRES EXPERIMENTATION** | |
| Pos 4 vs 5 split | **AVAILABLE NOW** (native `position`) but conflicts with progression key | Owner decision. |
| Party/solo | **NOT RELIABLE** | `partyId` 8%, null semantics unknown. |
| Time of day | **NOT RELIABLE** | No trustworthy local time. |
| Aggression, map movement | **NOT RELIABLE** | Playback prohibited. |
| Control / initiation | **NOT RELIABLE** | UNSUPPORTED_V1. |
| IMP, awards, behaviour | **NOT RELIABLE** (forbidden) | |

---

## 20. Intelligence Architecture

```text
STRATZ MATCH (immutable raw → provider-normalised → V7 canonical)
  ↓
LIFECYCLE          READY · bucket classification · chronology            [Match Lifecycle SSOT]
  ↓
ROLE RESOLUTION    effective_role (user correction authoritative)         [upstream]
  ↓
DERIVED METRICS    role metric observations, comparison values, N/A       [Role Metrics SSOT]
  ↓
PROGRESSION        prior-20 median baseline · direction_delta · PB ledger [Role Metrics SSOT]
  ↓
PROFILE AGGREGATES per account × bucket (× role × hero):
                   ordered match index, role counts in windows,
                   hero counts in windows, 20-match role blocks,
                   last-10 progression deltas per identity
  ↓
NORMALISATION      V1: none beyond bucket/role scoping
                   P1: reference distributions per role × bucket (× hero), versioned
  ↓
CLAIM DETECTORS    pure functions: aggregate → candidate state + evidence   (claim_id@version)
  ↓
CONFIDENCE GATES   sample gates · Wilson/bootstrap intervals · n_eff
  ↓
CLAIM STATE        state machine with hysteresis, persistence, dwell, distinct days
  ↓
CHANGE EVENTS      append-only ledger on CONFIRMED/RETIRED transitions
  ↓
PROFILE MODEL      deterministic selection: identity line, role map, hero tags,
                   up to 3 claims, Right now, PBs, changes; visibility classes
  ↓
NARRATIVE          versioned copy templates bound to claim state + evidence values
  ↓
UI PAYLOAD         self projection · public projection · share projection
```

| Layer | Responsibility | Deterministic? | Storage |
|---|---|---|---|
| Lifecycle / roles / metrics / progression | Already specified by ACTIVE SSOTs. The Profile never re-derives them. | Yes | Existing |
| Profile aggregates | Cheap incremental counters and bounded ring buffers keyed by `account + bucket (+ role, + hero)`; rebuildable from the ordered match index. | Yes | Derived, rebuildable |
| Normalisation (P1) | Reference distributions frozen as versioned artifacts (digest + population declaration), refreshed on a schedule, never silently. | Yes | Versioned artifact |
| Claim detectors | One pure function per `claim_id@version`; input = aggregates; output = candidate state, values, thresholds, evidence refs. | Yes | Code + registry |
| Confidence gates | Part of the detector contract; declared gates must execute (analytical learnings rule 5). | Yes (bootstrap with seeded RNG) | — |
| Claim state machine | Applies transitions in chronological order; stores current state, since-match, last-evaluated-match. | Yes | `ClaimState` rows |
| Change events | Append-only; immutable once written; superseded flag on correction; `cause ∈ {PLAY, CORRECTION, METHODOLOGY, IMPORT}`. | Yes | Ledger |
| Profile model | Selection and ordering rules (§23); visibility projections. | Yes | `ProfileSnapshot` (current + quarterly frozen) |
| Narrative | Templates with typed slots. | Yes | Copy registry, versioned |
| UI payload | Thin DTO for Swift; the app never recomputes claims (consistent with the iOS reuse audit). | Yes | — |

### Where an LLM is useful — and where it is not

- **Not in V1 runtime.** Every V1 sentence is a template over a small number of states; deterministic copy is cheaper, testable, and cannot hallucinate.
- **Authoring time (useful):** drafting template variants in the house tone of voice, reviewed and frozen into the copy registry.
- **Later, optional "Tell me more":** narrate one claim's evidence payload in longer prose. Contract: input is only the evidence payload; a validator rejects any output containing a number, hero, role, date or comparison not present in the payload; no causal verbs from a banned list ("because", "caused", "made you"); never on share cards, never for other players. Strava's Athlete Intelligence is the precedent for narration over computed comparisons; the Spotify Archive engineering account in the V7 Master Experience Plan is the precedent for fluent copy over a wrong computed fact — the validator exists for that failure.
- **Never:** selecting claims, deciding identity from raw payloads, computing thresholds, or summarising a year of raw matches.

---

## 21. Incremental Update Strategy

### 21.1 What updates how

| Item | Method |
|---|---|
| Role counts, hero counts, window membership | **Incremental** (add newest, drop the match that leaves the window). |
| Unbiased inverse Simpson, shares | **Incremental** from counts. |
| Longtime blocks | **Incremental** (append to current 20-match block; close block at 20). |
| Last-10 progression runs | **Incremental** from Progression snapshots. |
| Wilson intervals | Recomputed from counts per evaluation (constant time). |
| Bootstrap intervals (C2, C4, C7) | Recomputed only when the point estimate is within 20% of a threshold; otherwise the previous interval side is retained (PROVISIONAL optimisation; must be verified equal to full recomputation in parity tests). |
| Claim states | **Incremental** state-machine step. |
| Quarterly snapshots | **Batch** at quarter end. |
| Reference distributions (P1) | **Batch**, versioned, scheduled. |
| Role correction, late recovery, claim version change | **Rebuild** affected scope by replay (§21.4). |

Recency weighting is not used in V1 (§14.6). Nothing in V1 requires re-running analysis over the whole history on each match.

### 21.2 Worked example — Match N+1 arrives

Player: Standard bucket, 187 eligible matches, all within 24 months.

**State before the match**

| Item | Value |
|---|---|
| Role counts (identity window = all 187) | Carry 138 · Support 31 · Mid 12 · Offlane 6 → Carry 73.8% |
| Role Shape | **SPECIALIST**, CONFIRMED since match 121 (entered at 76%) |
| Carry role window (last 100 Carry) | Juggernaut 38 · Wraith King 22 · Luna 10 · 10 others 30 |
| Carry Hero Shape | `H = 4.9` → **NARROW**, CONFIRMED since match 150 |
| Luna, Rising detector | last 30 Carry: 6 Luna (20%); previous 100 Carry: 3 (3%) → **CANDIDATE** since match 176 |
| Carry CS@10:00 last 10 `direction_delta` | 7 positive, median +4.0; baseline IQR 9 |
| Identity line | "Carry specialist with a narrow pool." |

**Match 188: Luna, Carry, Standard, 41 minutes, READY.** CS at 10:00 = 61; that match's finalised baseline median = 54 → `direction_delta = +7`.

**Step by step**

1. **Lifecycle → READY**, bucket STANDARD, effective role Carry. Profile processing starts only after READY (and after chronological release in the bucket).
2. **Progression** has already finalised the CS@10 observation, baseline and delta; the Profile reads them.
3. **Aggregates:** Carry 139/188 = **73.9%**. Carry role window: the oldest Carry match in the 100-window (a Juggernaut game) drops out; Luna enters → Juggernaut 37 · Wraith King 22 · Luna 11 · others 30.
4. **Role Shape detector:** 73.9% is below the SPECIALIST *enter* threshold (75%) but above its *exit* threshold (68%). State stays **SPECIALIST**. *Without hysteresis a naive 75% cut would have flipped this player out of "specialist" several times between matches 150 and 188.*
5. **Hero Shape detector:** `H` rises to **5.2**, above NARROW's exit (5.0) and inside ROTATION's enter range → NARROW becomes **FADING** (first exit observation); ROTATION becomes **CANDIDATE**. Identity line unchanged (FADING still counts).
6. **Rising detector (Luna):** last 30 Carry now 7 Luna (23%); still ≤ 5% before. Persistence check: CANDIDATE since 176; 12 Carry matches since, across 3 distinct days → **CONFIRMED**. Change event: *"Luna is rising in your Carry games."* Right now shows the arrival; the hero section shows [Juggernaut · Go-to] [Wraith King · Longtime] [Luna · Rising].
7. **Current-Form detector (CS@10):** last 10 now 8 positive; median delta +5.5 ≥ 0.5 × IQR (4.5) → **UP-RUN** qualifies (fast claim; no persistence). Right now: *"CS at 10:00 above your usual in 8 of your last 10 Carry matches."*
8. **Profile model:** first-screen claim slot unchanged (Role-Pool Contrast still highest priority). Right now shows the UP-RUN first; Luna's arrival second.
9. **Snapshot + payload:** current ProfileSnapshot version increments; self projection updated; public projection gains the Rising tag. **No push notification** (V1 push is READY-only; the READY notification for match 188 was already governed by the Lifecycle SSOT). The Profile tab gets an unread badge for one change event.

**Ten Carry matches later (match 198)**, suppose Luna and two new heroes keep appearing and `H = 5.6`:

- NARROW's exit condition has now held at two evaluations ≥ 10 matches apart across distinct days, and NARROW has dwelt ≥ 30 matches → **RETIRED**.
- ROTATION's enter has held with persistence → **CONFIRMED**.
- Identity line becomes **"Carry specialist with a steady rotation."**
- One change event: *"Your Carry pool has widened: about five regular heroes now, up from about four."* (identity-class; rate limit satisfied).

**Counter-case:** if match 189–197 had been mostly Juggernaut and `H` fell back to 4.7, NARROW would have returned from FADING to CONFIRMED with **no event**, and ROTATION's candidate would have been silently discarded. That is the anti-flapping guarantee.

### 21.3 A match that changes nothing

Most matches look like this: counts move, no detector crosses any threshold, no state changes, the identity line and hero tags are unchanged, and only Right now (if a run starts or ends) and the header counts update. That is the intended experience: **the Profile feels alive in Right now and stable everywhere else.**

### 21.4 Rebuilds

| Trigger | Scope | Procedure | Events |
|---|---|---|---|
| **Role correction** (e.g. match 140 Support → Carry) | Affected bucket only | After Progression rebuilds affected role histories, replay Profile aggregates and state machines for that bucket from the corrected match onward, in chronological order. | Previously delivered change events are immutable; mark contradicted ones `superseded`; new events from the replay carry `cause = CORRECTION` and appear in the feed only if the *current* state differs from the currently displayed state. |
| **Late recovery** of an earlier match | Affected bucket | Insert at true chronology; replay aggregates from the insertion point; do not rewrite frozen quarterly snapshots. | No retroactive events; current state may change, producing at most one `cause = IMPORT` event if the displayed state changes. |
| **History import** | Account | Build aggregates and replay silently. | None (import never celebrates). |
| **Claim or copy version change** | All accounts, that claim | Replay the claim's state machine under the new version; keep old snapshots readable under old versions. | `cause = METHODOLOGY`, never notified. |
| **Reference population refresh** (P1) | All accounts, style claims | New artifact version; replay style claims. | METHODOLOGY. |
| **Parity check** | Sampled accounts, scheduled | Full rebuild from the ordered match index; diff against incremental state. Any diff fails the job and blocks deploys of claim code. | None. |

Replay cost is small: at most a few thousand eligible matches per bucket, a handful of counters, and O(1) detectors per match — no provider calls (raw data is already persisted per the V7 acquisition policy).

---

## 22. Failure Modes and Adversarial Pass

### 22.1 How this could go wrong

| Failure | How it happens | Prevention |
|---|---|---|
| **Misleading** | A claim describes a hero kit, meta, teammate, or mode mix rather than the player. | Bucket isolation everywhere; role scoping; no cross-hero performance claims in V1; hero composition shown in every form explanation; P1 hero-normalised references; negative-control-style calibration (shuffle chronology) for every detector. |
| **Astrology** | Adjectives about character; labels without operational definitions; flattering vagueness. | Claim contract requires definition, window, n, and evidence; banned vocabulary list (resilient, tilted, brave, selfish, clutch, greedy, lazy); no archetype on the live Profile; three-state spectra only. |
| **Redundant** | Same number on Post-match, Progression, Profile, Annual Report. | §18 rule: one primary surface per number; Profile summarises in words and links. |
| **Boring** | Established players see the same page forever. | Right now moves; Change feed; Rising/Longtime heroes; signature findings tied to real change; quarterly eras. Boring-but-true beats volatile-but-false. |
| **Too complicated** | Evidence panels become statistics lectures; too many sections. | Seven sections; one sentence per claim; "Why?" shows counts and windows, never p-values, z-scores, or reliability. |
| **Too volatile** | Labels flip near thresholds; small samples confirm claims. | Enter/exit hysteresis; persistence (10 matches, 2 days); 30-match dwell; Wilson/bootstrap gates with `n_eff`; churn calibration target < 10%/quarter. |
| **Just another stats page** | Filling empty states with KDA/GPM/win rate. | Hard rule: no win rate, KDA, GPM, or rank on the Profile face; empty slots stay empty. |
| **Quietly a skill grade** | Style claims that rise with MMR. | Skill-proxy risk label per claim; P0 restricted to low-risk claims; favourable-for-everyone metrics confined to Right now and PBs. |
| **Hurtful** | Adverse findings shared or shown to others. | Visibility classes; share whitelist; no DOWN-RUNs or tradeoffs outside the self view. |

### 22.2 Adversarial pass per major signal

| Attack | Role Shape | Hero Shape / Exploration | Hero tags | Current-Form Run | Role Migration / Pool Turnover | P1 style claims |
|---|---|---|---|---|---|---|
| **Hero selection bias** | n/a | Real behaviour, not bias | Real behaviour | Run may be a hero-mix change → composition warning | Real behaviour | Farm Source must be hero-normalised; Uptime check hero residuals |
| **Role selection bias** | Is the measurement | Per role | Per role | Per role | Is the measurement | Per role |
| **Skill changes** | Low effect | Low | Low | Real performance change; labelled recent, self-relative | Low | Fight presence rises with skill → framed as "how often" |
| **Matchmaking quality / opponents** | n/a | n/a | Best Record regresses to 50% (honest scarcity) | Climbing raises opposition → runs can reverse; acceptable, it is recent-only | n/a | Reference not rank-stratified (fence) → style claims describe behaviour in the player's own lobbies |
| **Party vs solo** | Friends dictate roles → describes observed play | Same | Same | Party games may differ; cannot control (`partyId` unreliable) — disclosed limitation | Same | Same |
| **Game duration** | n/a | n/a | n/a | Checkpoint metrics N/A in short games (never zero) | n/a | Uptime is a share of minutes (duration-normalised) |
| **Stomps** | n/a | n/a | n/a | Stomps inflate/deflate single deltas; sign-count + median gate damps | n/a | Presence in stomps inflates; median over window |
| **Win/loss leakage** | None | None | Best Record is outcome-based by definition (labelled) | Many metrics correlate with winning; a run can reflect a win streak → explanation shows W/L of the 10 matches | None | Fight presence partially outcome-linked; paired with exposure |
| **Patch / meta changes** | Role meta shifts | Pool churn after patches → flagged | Rising after a buff → still true | Metric meaning may shift → metric versioning rules | Flag patch boundaries | Reference refresh per patch era |
| **Tiny samples** | 30-match gate + Wilson | 30-match gate + unbiased index + bootstrap | Floors (10 matches, 8%) | 10 baseline-ready observations + magnitude gate | 100/200 match gates | 30 role matches + shrinkage |
| **Turbo vs Standard** | Per bucket | Per bucket (Turbo breadth differs) | Per bucket | Per bucket (SSOT) | Per bucket | Per bucket cuts (V7: 0.405 vs 0.492 participation) |
| **Role corrections** | Rebuild | Rebuild | Rebuild | Progression rebuild then replay | Rebuild | Rebuild |
| **Misclassification** | Visible unassigned count; >20% missing → withhold | Wrong role pollutes pool → correction affordance | Same | Same as Progression | Same | Same |
| **Heroes that distort metrics** | n/a | n/a | n/a | Composition warning (≥ 7 of 10 one hero) | n/a | Hero normalisation or hero-function fallback |
| **Lane matchups** | n/a | n/a | n/a | Lane metrics noisy by matchup; median gate | n/a | Lane-strong identity rejected |
| **Gaming the stats** | Playing off-role to change label → it *is* your play | Picking randoms to look "wide" → randoms excluded | Pinning a favourite is allowed and labelled | Farming CS at 10 at the expense of the game → self-relative only; no leaderboard | n/a | No leaderboards, no public ranking of style |
| **Misleading correlations** | No causal copy | No causal copy | "Best record" not "best hero" | "Above your usual", never "because" | No causal copy | No causal copy; tradeoffs are co-occurrence |
| **Survivorship bias** | Players who quit roles vanish from windows → describes current play, which is the intent | Same | Longtime requires recent presence | Only matches actually played | Windows compare what was played | Reference population declared; representativeness not claimed |

**Downgrades applied from this pass:** Strongest hero → EXPERIMENTAL; Pocket pick → REJECT; Lane-strong → REJECT as identity; Consistency as a trait → REJECT (self-relative change only, P1); Fight Presence Level retains P1 but with mandatory "how often" framing and pairing.

---

## 23. FINAL V1 PROFILE

This section is the implementation-facing contract. Everything not listed here is out of V1.

### 23.1 Hierarchy

```text
PROFILE (bucket selector: Standard | Turbo)
├── 1. HEADER
├── 2. IDENTITY
│   ├── Identity line
│   └── Role map
├── 3. YOUR HEROES
├── 4. WHAT KEEPS SHOWING UP  (≤ 3 claims; first is on the first screen)
├── 5. RIGHT NOW              (≤ 2 items on page, 1 on first screen)
├── 6. PERSONAL BESTS
├── 7. CHANGES
└── Action: SHARE CARD
```

### 23.2 Components

#### 1 · Header

| | |
|---|---|
| **Shown** | Display name, avatar; bucket phrase ("Mostly Standard" when the selected bucket holds ≥ 70% of eligible matches in the last 90 days; otherwise "Standard and Turbo"); "{n} matches since {Mon YYYY}" for the selected bucket; "Last played {relative}". |
| **Why** | Scope and honesty: how much we know. |
| **Data** | STRATZ profile; lifecycle eligible counts; chronology. |
| **Insufficient confidence** | n < 10: "Getting to know your Dota · {n} matches". Private/anonymous STRATZ profile: refusal state explaining how to make match data public; no fabricated content. |

#### 2 · Identity

**Identity line**

| | |
|---|---|
| **Shown** | One sentence from the template table below. |
| **Why** | The "yep, that's me" moment. |
| **Data** | C1 Role Shape (CONFIRMED/FADING) + C2 Hero Shape of the Anchor or top role (CONFIRMED/FADING). |
| **Insufficient confidence** | Role Shape unconfirmed and n ≥ 10: "Mostly {top role} so far." (if top role ≥ 50%) or "A bit of everything so far." n < 10: no line. |

| Role Shape | Hero Shape of top role | Template |
|---|---|---|
| SPECIALIST | NARROW | "{Role} specialist with a narrow pool." |
| SPECIALIST | ROTATION | "{Role} specialist with a steady rotation." |
| SPECIALIST | WIDE | "{Role} specialist with a wide pool." |
| SPECIALIST | unconfirmed | "{Role} specialist." |
| ANCHORED | any / unconfirmed | "{Role} first, {Role2} second." |
| DUAL | any / unconfirmed | "{Role} and {Role2}, almost evenly." (order by share) |
| FLEXIBLE | any / unconfirmed | "Covers {k} roles regularly." |
| NO_CLEAR_SHAPE | any | "No single role, no clear favourite." |

Role names: Carry, Mid, Offlane, Support. No "pos 1" in the line (optional in detail).

**Role map**

| | |
|---|---|
| **Shown** | Four rows (Carry, Mid, Offlane, Support) for the selected bucket: share of identity window rounded to 1%, count, tier chip (Anchor/Regular/Occasional/Rare). Footnote: "{k} matches without a role — set roles". Tap: counts by window and "Lately" (last 20). |
| **Why** | Makes the identity line checkable; turns missing roles into corrections. |
| **Data** | Effective roles; C1 aggregates. |
| **Insufficient confidence** | n < 30: counts only, no tiers, no percentages. |

Bucket toggle visible only when both buckets have ≥ 30 eligible matches; otherwise the minor bucket is reachable from the header menu.

#### 3 · Your heroes

| | |
|---|---|
| **Shown** | For the top role: up to three hero portraits, each with one tag (Go-to / Rising / Longtime / Favourite by priority) and one fact line ("38 of last 100 Carry", "Since Feb 2024", "7 of last 30"). A role switcher shows the same for other roles with ≥ 10 role matches. Favourite pin control. |
| **Why** | Heroes are the most recognisable identity content; separated meanings create the "most played isn't longest-running" discovery. |
| **Data** | §8 algorithms. |
| **Insufficient confidence** | Role matches < 10: "Most played so far" with counts, no tags. No candidate passes the floor: most-played list with counts and "No go-to yet". |

#### 4 · What keeps showing up

| | |
|---|---|
| **Shown** | Up to three CONFIRMED claims from: C4 Role-Pool Contrast, C5 Mode Split, C6 Role Migration (active ≤ 100 matches after confirmation), C7 Pool Turnover, C3 Exploration (LOYAL or EXPLORING), Go-to-vs-Longtime contrast. Each: one sentence + "Why?" evidence sheet (window, counts, dates, state since). |
| **Why** | Durable interpretation; the "I didn't know that" layer. |
| **Data** | §7 claims. |
| **Insufficient confidence** | Section hidden when no claim is confirmed. Maturity hint only when n ≥ 30: "More reads unlock as you play — next: your Carry hero pool at 30 Carry matches." |

### 23.3 Claim priority (first-screen slot and ordering)
1. C5 Mode Split
2. C4 Role-Pool Contrast
3. C6 Role Migration (active)
4. Go-to-vs-Longtime contrast
5. C7 Pool Turnover
6. C3 Exploration in a role where it is the opposite state of another role (the "loyal here, exploring there" contrast)
7. C3 Exploration (single role)

Ties: more recently confirmed first. No rotation for novelty's sake — a claim holds its slot until a higher-priority claim is confirmed or it retires. (Stable surfaces build trust; Right now and Changes supply motion.)

#### 5 · Right now

| | |
|---|---|
| **Shown** | Up to two items: Current-Form UP-RUN (preferred first), Rising hero arrival (first 30 matches after confirmation), PB Momentum, "Lately: mostly {role}" note, DOWN-RUN (never first). Every item shows its window label. Tap links to Progression for numbers. |
| **Why** | Aliveness without contaminating identity. |
| **Data** | Progression snapshots; PB ledger; hero tags; role counts. |
| **Insufficient confidence** | Nothing qualifies: "Nothing unusual lately — you're playing to your usual." Progression not yet ready for any metric: section hidden. |

#### 6 · Personal bests

| | |
|---|---|
| **Shown** | For the selected bucket: the three most recent PB celebrations (date, role, metric, value); "All PBs" list grouped by role showing current best-known records. |
| **Why** | Achievement independent of rank. |
| **Data** | PB engine and celebration ledger; current best-known index vs celebration history per the future Personal Records SSOT. |
| **Insufficient confidence** | "Personal bests start after 5 measured matches in a role." |

#### 7 · Changes

| | |
|---|---|
| **Shown** | Reverse-chronological change events (cause PLAY, CORRECTION when displayed state changed, IMPORT when displayed state changed); superseded events greyed with "updated after role correction". |
| **Why** | Evolution as content; auditability. |
| **Data** | Change ledger. |
| **Insufficient confidence** | "Your profile will note changes here as they happen." |

#### Share card

Content model in §16. Generated server-side from the public/share projection; the app previews the exact image. Unavailable when no identity line is confirmed (hero card fallback only).

### 23.4 Non-normative payload sketch

```json
{
  "profile_contract_version": "profile-1.0.0",
  "account": {"display_name": "Nika", "avatar_url": "…", "privacy": "PUBLIC"},
  "bucket": "STANDARD",
  "header": {"eligible_matches": 1240, "since": "2024-03", "last_played_at": "2026-09-13T21:04:00Z", "mode_phrase": "MOSTLY_STANDARD"},
  "identity": {
    "line": {"template_id": "specialist_rotation", "slots": {"role": "CARRY"}},
    "role_shape": {"claim_id": "role_shape@1", "state": "CONFIRMED", "value": "SPECIALIST", "since_match_ref": "m_121"},
    "role_map": [{"role": "CARRY", "count": 148, "share": 0.74, "tier": "ANCHOR"}],
    "unassigned_matches": 4
  },
  "heroes": {"CARRY": [{"hero_id": 8, "tag": "GO_TO", "fact": {"n": 38, "window": 100}}]},
  "claims": [{"claim_id": "role_pool_contrast@1", "state": "CONFIRMED", "copy": {"template_id": "pool_ratio", "slots": {"wide_role": "SUPPORT", "narrow_role": "CARRY", "ratio_words": "three_times"}}, "evidence_ref": "ev_…", "visibility": "PUBLIC_SAFE"}],
  "right_now": [{"kind": "FORM_UP_RUN", "role": "CARRY", "metric_id": "carry.last_hits_at_10.v1", "favourable": 8, "window": 10, "visibility": "SELF_ONLY"}],
  "personal_bests": {"recent": []},
  "changes": {"unread": 1, "items": []},
  "refusals": [{"component": "exploration", "reason": "INSUFFICIENT_HISTORY", "needed": 150}],
  "versions": {"claims_registry": "profile-claims-1.0.0", "copy": "profile-copy-1.0.0", "aggregates": "profile-aggregates-1.0.0"}
}
```

Field names are illustrative; the thin mobile DTO rules in the iOS reuse audit apply (closed enums where truly closed, explicit refusal codes, no client recomputation).

### 23.5 V1 dependencies (build order)

1. Lifecycle Batches A–D (READY, buckets, chronology) and a written upstream role-resolution contract.
2. Profile aggregates + C1, C2, hero tags (Go-to, Longtime, Rising, Favourite) + identity line + role map. **This alone is a shippable first Profile.**
3. C3–C7 claims + Change ledger.
4. Progression Batches A–F → C8 Current-Form Runs, C9 PB Momentum, Personal bests section.
5. Share card.
6. Role correction replay (Lifecycle Batch E) — required before public launch, since corrections are a promised behaviour.

---

## 24. Example Complete Profiles

Numbers are illustrative, rounded as the product would round them, and not measurements of real players.

### A · Dedicated Carry specialist — Standard, 1,240 matches

> **Nika** · Mostly Standard · 1,240 matches since Mar 2024 · last played yesterday
>
> **Carry specialist with a narrow pool.**
> Carry 74% Anchor · Support 16% Regular · Mid 6% Occasional · Offlane 4% Rare
>
> **Your heroes (Carry):** Juggernaut — Go-to · 38 of last 100 · Wraith King — Longtime · since Feb 2024 · Luna — Rising · 7 of last 30
>
> **What keeps showing up**
> - Your Support pool is about three times wider than your Carry pool. *Why?*
> - Juggernaut is your go-to, but Wraith King has been in your Carry rotation the longest.
> - You rarely try new Carry heroes, but about one Support game in three is a hero you haven't played lately.
>
> **Right now** · CS at 10:00 above your usual in 8 of your last 10 Carry matches · 2 Carry personal bests in your last 20 Carry matches
>
> **Changes** · Luna is rising in your Carry games (Sep 11)

### B · Flexible Support — Standard, 420 matches

> **Mira** · Mostly Standard · 420 matches since Jan 2025
>
> **Support first, Offlane second.**
> Support 61% Anchor · Offlane 24% Regular · Mid 9% Occasional · Carry 6% Occasional
>
> **Your heroes (Support):** Ogre Magi — Go-to · Rubick — Longtime · Tusk — Rising
>
> **What keeps showing up**
> - About one Support game in three is a hero you haven't played lately.
> - Offlane went from 9% to 24% of your Standard games.
>
> **Right now** · Healing per 10 minutes above your usual in 8 of your last 10 Support matches

### C · Hero spammer — Turbo, 610 matches

> **k1dd** · Mostly Turbo · 610 matches since Jun 2025
>
> **Mid specialist with a narrow pool.**
> Mid 82% Anchor · Carry 11% Occasional · Offlane 4% · Support 3%
>
> **Your heroes (Mid):** Invoker — Go-to · 58 of last 100 · also Longtime
>
> **What keeps showing up**
> - Same top three Mid heroes as 200 games ago.
> - You mostly stick with heroes you know.
>
> **Right now** · Nothing unusual lately — you're playing to your usual.
>
> *Note: the Profile never calls this player a "spammer" or "one-trick". The facts carry the recognition; the valence is theirs.*

### D · Genuine multi-role player — Standard, 350 matches

> **Tomo** · Mostly Standard · 350 matches since Oct 2024
>
> **Covers three roles regularly.**
> Carry 35% Regular · Offlane 30% Regular · Support 25% Regular · Mid 10% Occasional
>
> **Your heroes:** Carry — Faceless Void (Go-to) · Offlane — Mars (Go-to), Centaur Warrunner (Longtime) · Support — Snapfire (Go-to)
>
> **What keeps showing up**
> - Offlane has overtaken Support as your second role in Standard.
> - Your Offlane pool is about twice as wide as your Carry pool.
>
> **Right now** · Lately: mostly Offlane (8 of your last 10) · Objective involvement above your usual in 8 of your last 10 Offlane matches

### E · Inconsistent newer player — Standard, 24 matches

> **Pip** · Getting to know your Dota · 24 matches
>
> **Mostly Support so far.**
> Support 15 · Carry 6 · Mid 3 *(counts only — percentages and tiers appear at 30 matches)* · 2 matches without a role — set roles
>
> **Most played so far:** Lion 5 · Witch Doctor 4 · Sniper 3
>
> **Personal bests** · Your first Support personal best: Wards Placed per 10 minutes (Sep 9)
>
> *No "What keeps showing up", no Right now runs (not enough baseline-ready observations). The page is short and honest, and invites play and role confirmation.*

### F · Long-time player whose style is changing — Standard, 3,100 matches

> **Ash** · Standard and Turbo · 3,100 Standard matches since 2019 (tracked history)
>
> **Support first, Offlane second.**
> Support 55% Anchor · Offlane 30% Regular · Carry 10% Occasional · Mid 5% Rare
>
> **Your heroes (Support):** Shadow Shaman — Go-to · Crystal Maiden — Favourite ♥ · Dark Willow — Rising
>
> **What keeps showing up**
> - In Standard you're a Support. In Turbo, you're a Mid.
> - Support went from 22% to 55% of your Standard games.
> - Only one of your top five Support heroes from 100 games ago is still in your top five.
>
> **Right now** · Lately: mostly Support · Camps stacked by 20:00 above your usual in 8 of your last 10 Support matches
>
> **Changes** · You're now "Support first, Offlane second" in Standard (Aug 2) · Your Support pool has widened (Jul 20) · *History (P1): Eras — 2024 "Offlane specialist" → 2025 "Offlane first, Support second" → 2026 "Support first, Offlane second"*

---

## 25. Final Verdict

### 25.1 The five most valuable things a Profile should communicate

1. **Which role(s) you actually play, per mode** — as a sentence and a checkable map.
2. **Which heroes define you, with meanings separated** — go-to, longtime, rising, favourite.
3. **The shape of your habits inside each role** — narrow or wide, loyal or exploring, and how those differ between your roles and modes.
4. **What is moving right now against your own usual** — clearly temporary.
5. **How your Dota has changed** — role migration, pool turnover, confirmed changes, and personal bests.

### 25.2 Attractive ideas to reject

- A single living archetype or personality label (keep the archetype in the Annual Report).
- "You fall off outside your comfort heroes", "you recover after bad lanes", "you're strong even in losses" — measured τ = 0.
- Aggressive/conservative, clutch/closer, early/late-game player, streaky/steady, team-oriented, initiator.
- Tilt and post-loss behaviour on the Profile.
- Skill radars, overall scores, strength bands, percentiles, "top X%".
- "Strongest hero" from raw cross-hero metrics; computed pocket picks.
- Solo vs party, time of day, Radiant/Dire.
- IMP, awards, behaviour scores, and anything rank-derived.
- An LLM that reads a year of matches and writes who you are.

### 25.3 What current data supports convincingly

Role shape, role tiers and role migration; hero shape, exploration and pool turnover per role; go-to, longtime and rising heroes; mode-split identity and role-pool contrasts; current-form runs and PB momentum once Progression persists; records. All from fields already acquired, with no provider changes.

### 25.4 What still requires validation

- Every PROVISIONAL threshold (role shape, hero shape, exploration, migration, turnover, form magnitude gate) against the non-degeneracy and < 10% quarterly churn targets.
- The design effect `n_eff = n/2` (measure session-block variance).
- Current-form false-surfacing rate under shuffled chronology (≤ 10% of player-weeks).
- Role classification accuracy and correction rates (an upstream role-resolution SSOT).
- P1 reference populations per role × bucket (× hero for Farm Source), including heterogeneity and skill-proxy correlation checks.
- Lane→side mapping (for any lane-outcome claim); dead-time intervals (for Carry exposure).
- Whether players actually recognise themselves: a moderated test of the identity line and signature findings with 15–20 players across the six example types, measuring recognition ("that's me", "that's wrong", "so what") before release.

### 25.5 The smallest Profile that already says "Yeah, that's me"

**Header + identity line + role map + three tagged heroes.** Buildable from effective role, hero ID and chronology alone (§23.5 step 2). For established players this is recognisable on its own, because it is exactly how Dota players describe themselves — and unlike DotaBuff it *says it in a sentence* and *separates go-to from longtime from rising*.

### 25.6 Owner decisions required before this becomes ACTIVE

1. Identity window 200 matches / role window 100 / 24-month cap.
2. Profile eligibility equals progression eligibility (≥ 600 s, fail-closed integrity), with ineligible matches counted only in the header.
3. Random-assigned picks excluded from hero shape and tags.
4. DOWN-RUNs visible on the self Profile (recommended: yes, never first, never shared).
5. Profile change events in-app only in V1; whether READY notification copy may mention a profile change.
6. Descriptive Position 4 vs 5 sub-label (recommended: not in V1).
7. A dated annual-archetype badge on the Profile (recommended: P1).
8. Other-player visibility defaults (recommended: private until a social feature ships).
9. Rank label opt-in on share cards (recommended: off by default, explicit per-share opt-in).
10. A "preferred role" user declaration (enables finding #9; recommended: P1).

### 25.7 What makes someone screenshot or share it

An identity line that is instantly true, portraits of their heroes with a tag that shows we understand the difference between a go-to and a longtime pick, and one line that surprises friends ("Support in Standard, Mid in Turbo"). It is flattering by recognition, not by grade — which means ordinary players share it too, not only the high-volume or high-rank ones.

### 25.8 Is this differentiated enough to be a reason to install?

**Yes — conditionally.** DotaBuff, OpenDota and STRATZ show more numbers than we ever will; the Dota client and Battle Report show seasonal summaries against similarly skilled players. None of them:

- states who you are in a sentence and shows the receipts;
- separates stable identity from recent form, so improvement is visible when rank is flat;
- keeps separate, isolated identities for Standard and Turbo and for each role;
- tells you when your profile has genuinely changed — and refuses to change when it hasn't.

The condition: the V1 must ship *with* Progression-backed Right now and PBs, not just the static identity. Identity alone is a delightful first open; identity plus visible movement is a reason to come back after every session. And it must hold the line on restraint — the moment the empty slots get filled with win rate and KDA, it becomes the fourth stats site.

---

## Sources

### Repository (authoritative internal evidence)

- `#swiftMigration/role-metrics-and-baselines-v1.md` — ACTIVE SSOT (roles, buckets, 20 metrics, median baseline, PBs, correction).
- `#swiftMigration/match-lifecycle-v1.md` — ACTIVE SSOT (READY, chronology, immutability, READY-only push).
- `docs/architecture/dota-dna-ssot.md` — V5.2 Elements/Patterns, V6/V6.1 additive paths.
- `docs/architecture/hero-portfolio.md` — Common Thread, Exception, Pool Evolution, Hero Mirror.
- `docs/product/v7-backend-capability-manifest.md` — 16 Finding dimensions and reliabilities, τ = 0 dimensions, recommendation model, archetype, refusal matrix, acquisition policy.
- `docs/evidence/v7-archetype-axes-2026-09-06.md` and `v7-new-lineage-archetype-fit-2026-09-08.json` — mode confound, packed tempo, modifier bias.
- `docs/evidence/v7-finding-pipeline-2026-09-05.md` — per-dimension reliability table.
- `docs/evidence/v7-owner-decisions-2026-09-06.md` — D1–D9 (no strength bands).
- `docs/evidence/v7-report-narrative-and-data-requirements-2026-09-04.md` — contrast principle, upstream-of-result principle.
- `docs/agent/analytical-learnings-and-gotchas.md` — reach, heterogeneity, provider semantics, role/position/lane separation.
- `research/stratz-enrichment/00-research-report.md`, `01-field-inventory.md`, `03-candidate-catalog.md` — Role Shape/Migration ranking, field semantics, rejected fields.
- `services/api/app/stratz/queries.py` — `GetPlayerProfile`, `GetPlayerHistoryPage`, `GetDeepMatchBatch` acquired fields.
- `V7 Master Experience Plan v1.md` — recap product research and cited Reddit community threads.
- `#swiftMigration/native-ios-backend-reuse-audit.md` — server-owned computation, thin mobile DTO.

### External

- Dota client and Dota Plus: [Hawk Live — Profile Showcase](https://hawk.live/posts/profile-showcase-customization-dota-2); [Steam — playstyle stats discussion](https://steamcommunity.com/app/570/discussions/0/492379159711591639/); [Dota Plus](https://www.dota2.com/plus); [esports.net — Battle Report](https://www.esports.net/news/dota-battle-report-update-delivers-cosmetics-needed-features/); [player.one — Battle Report](https://www.player.one/dota-2-battle-report-weekend-spotlight-dota-plus-147992).
- Stat sites: [DotaBuff blog — player profiles](https://www.dotabuff.com/blog/2016-10-31-big-improvements-to-match-pages-and-player-profiles); [DotaBuff Rankings](https://www.dotabuff.com/pages/rankings); [OpenDota blog](https://blog.opendota.com/2015/09/22/actions-trends/); [odota/web strings](https://github.com/odota/web/blob/master/src/lang/en-US.json); [STRATZ — IMP](https://medium.com/stratz/imp-decoding-your-performance-c251dcb42b93); [STRATZ — Stay In Your Lane](https://medium.com/stratz/stay-in-your-lane-fa4363f1273); [STRATZ](https://stratz.com/).
- Pro analysis: [Liquipedia Statistics Portal](https://liquipedia.net/dota2/Portal:Statistics); [datdota](https://datdota.com/); [rdy.gg — TI 2026 statistics](https://rdy.gg/en/dota2/news/the-international-team-and-hero-statistics); [Guild Order — hero pool construction](https://guildorder.com/games/dota2/guides/hero-pool-construction); [Dotesports — role guide](https://dotesports.com/dota-2/news/dota2-role-guide-23954); [Hawk Live — positions](https://hawk.live/posts/dota-2-positions).
- Community: Reddit threads as listed in §2.3 (collected in the V7 Master Experience Plan); [Steam — why do you play support?](https://steamcommunity.com/app/570/discussions/0/1738841319802235475/); [Steam — carry vs support](https://steamcommunity.com/app/570/discussions/0/494632338489634417); [Steam — carry and support at the same time](https://steamcommunity.com/app/570/discussions/0/1474221865198987501/).
- Identity products: [Forbes — Wrapped and identity](https://www.forbes.com/sites/dianaspehar/2024/12/06/how-spotify-wrapped-2025-explores-identity-culture-and-nostalgia/); [NoGood — Wrapped strategy](https://nogood.io/blog/spotify-wrapped-marketing-strategy/); [Fast Company — Wrapped as zodiac](https://www.fastcompany.com/90817606/spotify-wrapped-just-reinvented-zodiac-signs-for-music-addicts); [TechCrunch — underwhelming Wrapped 2024](https://techcrunch.com/2024/12/04/spotify-users-are-disappointed-by-an-underwhelming-wrapped-this-year); [Irrational Technology — the log](https://irrationaltechnology.substack.com/p/the-log-is-replacing-social-media); [Boston Globe — niche social apps](https://www.bostonglobe.com/2025/11/01/business/strava-letterboxd-niche-social-media/); [Strava Trophy Case](https://support.strava.com/en-us/articles/15402068-the-strava-trophy-case); [Strava Best Efforts](https://support.strava.com/en-us/articles/15401646-best-efforts-overview); [Strava Athlete Intelligence](https://press.strava.com/articles/stravas-athlete-intelligence-translates-workout-data-into-simple-and); [Hevy profiles](https://www.hevyapp.com/features/user-profiles/); [Hevy comparison](https://www.hevyapp.com/features/workout-comparison/); [iPhoneLife — Apple Fitness Trends](https://www.iphonelife.com/content/understanding-fitness-trends-apple-fitness-challenges); [Oura Readiness Contributors](https://support.ouraring.com/hc/en-us/articles/360057791533-Readiness-Contributors); [Riot Challenges FAQ](https://support.riotgames.com/en-us/league-of-legends/gameplay/challenges-faq-league-of-legends/); [Riot API types (hotStreak, veteran, freshBlood)](https://github.com/fightmegg/riot-api/blob/master/src/@types/index.ts); [Mobalytics GPI](https://mobalytics.gg/gpi/); [Steam profile showcases guide](https://steamcommunity.com/sharedfiles/filedetails/?id=456998095).
- Method: [Variance Explained — empirical Bayes estimation](http://varianceexplained.org/r/empirical_bayes_baseball/).
