# V7 STRATZ usage, storage, and redistribution review — 2026-09-01

Status: complete for the documentation/research phase; conservative local
collection may proceed, while public/raw redistribution and commercial launch
remain held pending written confirmation.

Task type: **DOCUMENTATION + RESEARCH**

Base: `84bc26d0272983b1d7661b5dc280adc1f4d2d866`

Branch: `v7/luna-b-terms-safety`

Review date: **2026-09-01** (Asia/Jakarta)

This is an evidence review, not a legal opinion. The labels below are release
and research controls based on first-party public statements. They are not a
determination of enforceable legal rights.

## Scope and phase checkpoint

This review covers the planned V7 STRATZ use:

- server-side GraphQL API calls for public Dota data;
- bounded research caching and local persistence of raw responses;
- provider attribution in a Dota Report Card product;
- possible web/product or commercial use;
- request limits, token classes, and referral conditions; and
- raw, row-level, and aggregate redistribution.

The review used only current STRATZ-owned/first-party public surfaces: the
STRATZ website, its API/GraphQL links, the STRATZ-owned Knowledge Base GitHub
repository and FAQ issues, and the STRATZ Medium publication. No third-party
repository or community claim is used to classify permission.

```text
PHASE: provider-terms and storage safety checkpoint
STRATZ GraphQL/REST data operations: 0
OpenDota calls: 0
Tokens, dotenv files, account data, and authorization headers touched: NO
Current API/docs pages read: public documentation navigation only
Clear provider prohibition of private local raw storage found: NO
Raw redistribution: DO NOT DO
Commercial/product launch: HOLD for written confirmation
Population/local research: PROCEED under the conservative local-only controls below
CHECKPOINT: PASS — LOCAL RESEARCH MAY PROCEED; PUBLIC/RAW REDISTRIBUTION AND COMMERCIAL LAUNCH HELD
```

The GraphiQL link was inspected only as a public documentation destination; no
query, introspection, token exchange, or data operation was submitted. The
planned ignored local corpus remains a conservative research arrangement, not a
provider-granted license. Because no clearly prohibited storage or collection
term was found, population research may proceed under the controls below;
unresolved terms continue to block redistribution and commercial use.

## Classification rubric

| label | meaning in this review |
|---|---|
| `CLEARLY_ALLOWED` | A first-party source expressly describes or endorses the use, subject to any stated token/attribution condition. |
| `CLEARLY_PROHIBITED` | A first-party source expressly says the use is not permitted. |
| `NOT_SPECIFIED` | The reviewed first-party sources do not answer the exact question. This is not permission. |
| `AMBIGUOUS` | A related first-party statement exists, but its age, scope, condition, or application to this use is not clear enough to rely on. |

No `CLEARLY_PROHIBITED` item was located in the reviewed public first-party
record. That does not convert any `NOT_SPECIFIED` or `AMBIGUOUS` item into an
allowed use.

Classification count across the 21 matrix rows: `CLEARLY_ALLOWED` 8,
`CLEARLY_PROHIBITED` 0, `NOT_SPECIFIED` 4, and `AMBIGUOUS` 9.

## Classification matrix

### API use and scope

| issue | classification | precise first-party evidence | V7 decision |
|---|---|---|---|
| Use the STRATZ API/GraphQL interface with a token | `CLEARLY_ALLOWED` | The current [STRATZ Welcome page](https://stratz.com/welcome) says the API is available for free and that STRATZ moved from REST to GraphQL. FAQ [#7](https://github.com/STRATZ-Esports/knowledge-base/issues/7) points developers to the GraphQL documentation and says STRATZ.com is powered by the API. | Use the named, server-side GraphQL operations already defined by the V7 provider boundary. |
| Request public Dota match/player data | `CLEARLY_ALLOWED` | FAQ [#7](https://github.com/STRATZ-Esports/knowledge-base/issues/7) says public game data is the API’s likely scope and contrasts it with private information such as actual MMR. The current [Welcome page](https://stratz.com/welcome) describes public-player profiles and public-match storage. | Keep the V7 projection to public, explicitly selected fields; fail closed for private/unavailable data. |
| Build a web application or community tool | `CLEARLY_ALLOWED` | FAQ [#37](https://github.com/STRATZ-Esports/knowledge-base/issues/37) says Individual Tokens are intended for “web applications and community projects.” FAQ [#7](https://github.com/STRATZ-Esports/knowledge-base/issues/7) names external tools built with the API. | The product shape is within the publicly described use case, but token tier and referral conditions still apply. |
| Use a Default Token for testing or a small personal project | `CLEARLY_ALLOWED` | FAQ [#37](https://github.com/STRATZ-Esports/knowledge-base/issues/37) describes the Default Token as requiring no special approval or referral links and as suitable for testing and small personal projects. | This supports bounded research use; do not infer that the historical Default-token description grants a multi-user product or public-output right. |
| Use Multi-Tokens for a distributed desktop application with per-user calls | `CLEARLY_ALLOWED` | FAQ [#37](https://github.com/STRATZ-Esports/knowledge-base/issues/37) describes Multi-Tokens as allowing separate individual tokens for users of a desktop application. | Not the planned server-side Dota Report Card pattern; do not select this token class by analogy. |
| Treat “free API” as a no-fee statement | `CLEARLY_ALLOWED` | The current [Welcome page](https://stratz.com/welcome) calls the API free; FAQ [#31](https://github.com/STRATZ-Esports/knowledge-base/issues/31) says it is “100% for free.” | Free pricing is not a data license. Keep licensing/storage questions open. |

### Attribution and referral conditions

| issue | classification | precise first-party evidence | V7 decision |
|---|---|---|---|
| Link back to STRATZ when using a Default Token | `AMBIGUOUS` | FAQ [#31](https://github.com/STRATZ-Esports/knowledge-base/issues/31) says that, for a Default Token, “all we ask” is a link back referencing the data source. “Ask” is not a clearly stated mandatory condition, and the FAQ is from 2020. | Add a visible plain-text STRATZ attribution link anyway; treat it as mandatory until STRATZ confirms otherwise. |
| Generate referral traffic when using Individual or Multi-Tokens | `AMBIGUOUS` | FAQ [#31](https://github.com/STRATZ-Esports/knowledge-base/issues/31) says users of the more powerful token classes are “required” to generate a certain amount of referral traffic, but gives no amount. FAQ [#37](https://github.com/STRATZ-Esports/knowledge-base/issues/37) directs users to the API page for token requirements. | Local research may proceed with visible attribution and an owner-approved token; record the unresolved referral condition and confirm it before public/product use. |
| Use a STRATZ attribution badge/link | `CLEARLY_ALLOWED` | FAQ [#31](https://github.com/STRATZ-Esports/knowledge-base/issues/31) expressly offers STRATZ badges as attribution links. | A plain linked “Data source: STRATZ API” label is the minimum; use an official badge only if its current asset/usage instructions are available. |

### Limits and request economics

| issue | classification | precise first-party evidence | V7 decision |
|---|---|---|---|
| Make requests within the applicable token quota | `CLEARLY_ALLOWED` | FAQ [#15](https://github.com/STRATZ-Esports/knowledge-base/issues/15) says the API uses second/minute/hour/day limits and that the service exposes remaining calls in “My Tokens.” FAQ [#37](https://github.com/STRATZ-Esports/knowledge-base/issues/37) repeats the token-rate-limit model. | Keep bounded concurrency, count physical attempts/retries, stop on 429/reset signals, and never treat retries as free. |
| Treat the exact numeric quotas published in FAQ #15 as the current 2026 contract | `AMBIGUOUS` | FAQ [#15](https://github.com/STRATZ-Esports/knowledge-base/issues/15) lists 2020-era figures (Default 20/sec, 250/min, 2,000/hour, 10,000/day; Individual 20/sec, 250/min, 4,000/hour, 20,000/day; Multi per-user limits), but the issue was opened on 2020-10-22 and the public API page does not expose a current unauthenticated quota table. | Do not cite those numbers as current permission. Use the token dashboard/response headers on an explicitly approved future probe and retain conservative local ceilings. |
| Acquire a high-volume research corpus or automate repeated harvesting | `AMBIGUOUS` | The first-party [STRATZ 2022 update](https://medium.com/stratz/stratz-2022-d640d549b6f6) says STRATZ addressed “unauthorized use of our API” but does not define the conduct. The FAQ describes tools and token tiers but not a corpus-retention or bulk-harvesting policy. | Population research may proceed under bounded, local-only controls, conservative local ceilings with recorded quota observations, minimum retention, and no redistribution; stop only if a clear provider prohibition or hard policy denial is encountered. |

### Caching, local persistence, and redistribution

| issue | classification | precise first-party evidence | V7 decision |
|---|---|---|---|
| Cache raw STRATZ responses locally for bounded research reproducibility | `NOT_SPECIFIED` | No reviewed first-party STRATZ website, API page, FAQ issue, or STRATZ Medium article expressly grants or prohibits raw-response caching or a cache TTL. The 2022 unauthorized-use note does not define caching. | Do not call this “licensed.” For population research, use a private, ignored, local-only raw archive with minimum necessary retention and no external sync. |
| Persist raw responses in a local research corpus/database | `NOT_SPECIFIED` | The reviewed first-party sources discuss API access, token classes, public data, and attribution, but do not state whether a user may retain raw response bodies, for how long, or in what storage. | For population research, keep raw bodies in the private ignored local archive only; exclude Git, production databases, shared caches, cloud drives, and external services, and apply minimum retention. |
| Commit raw response bodies, raw identities, or token-bearing request material | `NOT_SPECIFIED` from STRATZ; `DO NOT COMMIT` under the repository contract | No STRATZ source reviewed answers Git/repository publication. The repository contract separately forbids committing tokens/private identifiers and requires sanitization. | Commit only aggregate evidence, field names, hashes, and sanitized structure. Never commit raw provider bodies or authorization material. |
| Redistribute raw or row-level STRATZ responses to users, datasets, mirrors, or other services | `AMBIGUOUS` | FAQ [#7](https://github.com/STRATZ-Esports/knowledge-base/issues/7) confirms that outside tools use the API, but no first-party source reviewed grants a right to redistribute raw/row-level responses. The first-party 2022 unauthorized-use note makes an unconditional redistribution assumption unsafe. | No raw or row-level redistribution. Keep provider rows private and expose only the minimum derived/aggregate evidence needed by the product after owner review. |
| Publish derived aggregates or player-facing reports based on STRATZ data | `AMBIGUOUS` | First-party sources support external tools and web applications, but do not define whether derived reports, player-level aggregates, or public dashboards may be published, especially for a commercial product. | Keep public output aggregate/minimized, avoid raw identifiers and proprietary/model fields, retain source attribution, and obtain written confirmation before public or paid launch. |
| Retain raw data for a fixed period or indefinitely | `NOT_SPECIFIED` | No reviewed first-party source gives a retention schedule, deletion rule, archival right, or retraction process for API responses. | Use the shortest documented retention that still supports the active research question; delete raw bodies after the reproducibility window and retain only hashes/manifests/aggregate evidence where possible. |
| Store STRATZ custom/proprietary analytics and republish them | `AMBIGUOUS` | The current [Welcome page](https://stratz.com/welcome) says the API includes STRATZ custom data types and analysis results, but gives no separate reuse or redistribution rule for those values. | Exclude opaque scores/model outputs from the V7 canonical projection and do not publish them without explicit written permission. |

### Commercial and product use

| issue | classification | precise first-party evidence | V7 decision |
|---|---|---|---|
| Use STRATZ data in a free public web product | `AMBIGUOUS` | FAQ [#37](https://github.com/STRATZ-Esports/knowledge-base/issues/37) expressly mentions web applications/community projects, and FAQ [#31](https://github.com/STRATZ-Esports/knowledge-base/issues/31) says the API is free with attribution/referral conditions. No current product-use license or data redistribution clause was found. | Treat as a future approval gate, not an automatic grant. Use attribution and a conservative non-redistribution design. |
| Use STRATZ data in a monetized/commercial product | `AMBIGUOUS` | The public FAQ discusses web applications and free API access but does not say “commercial use permitted” or “commercial use prohibited.” The current [API page](https://stratz.com/api) exposes no public commercial-license text in its unauthenticated page shell. | HOLD. Obtain written STRATZ confirmation covering commercial use, token tier, referral obligations, retention, and player-level output before launch. |

## Conservative local-research protocol

Because raw caching/storage is **not clearly prohibited** but also **not
specified**, the planned research archive may be treated only as a controlled
working arrangement. It must not be described as a provider license.

```text
raw provider response
    -> ignored local-only archive, access restricted, minimum retention
    -> normalized provider-native projection (no guessed semantics)
    -> aggregate diagnostics / hashes / manifests
    -> committed evidence only after identifiers and raw bodies are removed
```

Required controls for any future live collection:

1. Use an owner-approved token and a server-side transport. Never expose a
   token in a browser, fixture, log, report, or committed file.
2. Keep raw response bodies under the ignored `.local/corpora/stratz/` tree
   only. Do not sync them to Git, a shared Redis cache, cloud storage, issue
   attachments, or third-party analysis services.
3. Key cache/archive records with provider, operation, query/schema version,
   account or match scope, and response hash. A bare account ID is not enough.
4. Record operation digest, schema/reference version, response hash, byte size,
   status, timestamp, and rate-limit observations. Never record authorization
   headers or raw tokens.
5. Salt or remove Steam/account/match/session identifiers before anything can
   leave the local archive. Do not retain chat, private fields, or opaque
   proprietary/model outputs for this research.
6. Set and document a short, purpose-bound retention period before collection.
   Delete raw bodies when the active reproducibility need ends; keep only the
   minimum aggregate evidence and non-reversible integrity metadata.
7. Publish no raw or row-level STRATZ data. Public commits remain aggregate-only
   and sanitized. A player-facing report is a derived publication and remains
   held until the commercial/redistribution question is answered.
8. Add a visible attribution link such as `Data source: STRATZ API →
   https://stratz.com/`. If the selected token tier has a current referral
   requirement, satisfy and measure it before live product use.
9. Stop the corpus phase if a current first-party term or provider response
   clearly prohibits local collection/storage, or a hard quota/policy denial is
   returned. Pause publication of the affected field and record unresolved
   ambiguity for owner review; ambiguity alone does not stop local research.

These controls are intentionally stricter than the public FAQ. They preserve
the research question while keeping the unresolved provider-rights surface
small and reversible.

## What the public record does not establish

The reviewed first-party material does **not** establish:

- a current 2026 numerical quota table or a current referral-traffic amount;
- a right to cache or persist raw response bodies;
- a retention/deletion period for cached or research data;
- a right to redistribute raw responses, row-level player records, or a bulk
  dataset;
- a license for player-level derived reports or aggregate publication;
- a commercial/paid-product right;
- a separate license for STRATZ proprietary metrics/model outputs; or
- whether the public FAQ’s 2020/2021 token conditions remain unchanged.

The correct status for these gaps is **not “allowed by silence.”** The owner
decision before public/product publication (including Corpus H or Corpus P
outputs) is:

```text
REQUEST WRITTEN STRATZ CONFIRMATION OF:
  (a) current token class and quota;
  (b) current backlink/referral obligations;
  (c) local raw caching and minimum/maximum retention;
  (d) raw/row-level redistribution versus derived aggregate output; and
  (e) free versus commercial/product use.
```

Until that answer exists, V7 may continue offline parser/normalizer work and
may run the population research corpus under the conservative local-only
protocol above. It must not add raw provider data to Git, redistribute raw or
row-level data, or launch a public/commercial STRATZ-backed product.

## First-party source record

| source | authority and use | freshness observed |
|---|---|---|
| [STRATZ Welcome](https://stratz.com/welcome) | Current site description: public match/profile scope, free API, REST→GraphQL transition, outside tools, custom data types, and attribution/footer identity. | Crawled/read 2026-09-01. |
| [STRATZ API page](https://stratz.com/api) | Official API navigation page; links the GraphQL explorer and identifies STRATZ, LLC. The unauthenticated page is mostly a shell, so it is not used to infer hidden terms. | Crawled/read 2026-09-01. |
| [GraphQL Explorer](https://api.stratz.com/graphiql) | Official destination linked by STRATZ; documentation navigation only. No query was submitted. | Read 2026-09-01. |
| [STRATZ Knowledge Base repository](https://github.com/STRATZ-Esports/knowledge-base) | First-party repository README says its issues are synced to the STRATZ Knowledge Base website. | Read 2026-09-01; repository content is historical FAQ material. |
| [FAQ #7 — What kind of data can be pulled?](https://github.com/STRATZ-Esports/knowledge-base/issues/7) | Public-data scope, GraphQL documentation, and examples of external tools. | Opened 2020-10-22; crawled/read 2026-09-01. |
| [FAQ #15 — Are there any rate limits?](https://github.com/STRATZ-Esports/knowledge-base/issues/15) | Token classes, historical quota figures, and the “My Tokens” remaining-call reference. | Opened 2020-10-22; crawled/read 2026-09-01. Treat exact numbers as historical. |
| [FAQ #31 — Is the STRATZ API free?](https://github.com/STRATZ-Esports/knowledge-base/issues/31) | Free pricing, Default-token backlink request, Individual/Multi referral requirement, and attribution badges. | Opened 2020-10-22; crawled/read 2026-09-01. |
| [FAQ #37 — Token class differences](https://github.com/STRATZ-Esports/knowledge-base/issues/37) | Default-token personal/testing scope, Individual-token web/community scope, Multi-token per-user desktop scope, and quota model. | Opened 2021-11-22; crawled/read 2026-09-01. |
| [STRATZ 2022 update](https://medium.com/stratz/stratz-2022-d640d549b6f6) | First-party warning that STRATZ addressed unauthorized API use; no conduct definition. | Published 2022-12-31; crawled/read 2026-09-01. |

## Validation and completion record

```text
TASK TYPE: DOCUMENTATION + RESEARCH
BASE SHA: 84bc26d0272983b1d7661b5dc280adc1f4d2d866
NEW SHA: see final commit in the completion handoff
CHANGED FILES: docs/evidence/free-dna-v7-stratz-usage-storage-review-2026-09-01.md
BACKEND FILES CHANGED: NO
ANALYTICAL FILES CHANGED: NO
PUBLIC REPORT CONTRACT CHANGED: NO
PERSISTED REPORT COMPATIBILITY TESTED: NOT APPLICABLE
PRODUCTION-SHAPED FIXTURE: NOT APPLICABLE
BROWSER E2E: NOT APPLICABLE
TYPECHECK: NOT APPLICABLE
LINT: NOT APPLICABLE
BUILD: NOT APPLICABLE
DOCS-CHECK: PASS (`make docs-check` → `docs-check: ok`)
ANALYTICAL BEHAVIOR CHANGED: NO
HOLDOUT RERUN: NO
RECALIBRATION: NO
OPENDOTA QA CALLS: 0
STRATZ API DATA/QUERY CALLS: 0
DEPLOYED: NO
SAFE TO MERGE: YES (documentation-only; owner review still required)
```
