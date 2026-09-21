# Native iOS backend reuse audit

Status: architecture audit only. No runtime, analytical, schema, provider, or deployment change is proposed by this document.

Audit base: `ed5f7acc77091625ccb3317b385df91038a60f91`

## A. Executive recommendation

**Recommendation: Architecture A — native SwiftUI client over the existing FastAPI/Python backend.** Keep STRATZ credentials, GraphQL acquisition, quotas, retries, shared caching, normalization, canonical history, analytical truth, recalculation, persistence, and versioning on the server. Generate a Swift transport layer from a deliberately small, versioned mobile OpenAPI contract. Write only networking/session storage, presentation models, formatting, navigation, animation, and local UI state in Swift.

Do not expose the existing private V7 capability document as the mobile contract. The only currently exposed V7 response is the privacy-safe `PublicProjection`, which is deliberately too thin for the proposed continuous scorecard. Add a mobile-focused API boundary later, backed by the same provider, repository, and domain layers. Preserve all old report endpoints and persisted report shapes while the new endpoint evolves.

Architectural estimate of the **existing backend/domain investment** (the iOS UI itself is excluded):

- **90% reusable unchanged:** provider transport and queries, provider-native parsing, canonical boundary, cache/retry/rate-limit behavior, repository and job lifecycle, V7 frozen artifacts/runtime, fixtures, and research evidence/tests.
- **7% reusable with adaptation:** expose a mobile creation/read contract, add authentication/ownership, add role corrections and role-scoped progress persistence, and extend canonical deep evidence only where the approved scorecard requires fields not yet collected.
- **3% genuinely belongs in Swift:** generated API DTOs/client plus handwritten client state, formatting, presentation ordering, navigation, animation, and local cache of server responses.

These are architecture estimates, not line counts. The continuous role scorecard is new product work and therefore is not evidence that old backend work failed to survive; it should be added at the existing server domain boundary.

What remains, moves, and retires:

- **Remains server-side:** all STRATZ access and secrets; raw/provider-normalized data; canonicalization; eligibility; role assignment and correction application; last-20 prior-role median; minimum-support gates; Personal Best; history rebuilds; report/progress persistence; analytical versions and provenance.
- **Reused as artifacts:** versioned population/context JSON, item vocabulary, hero taxonomy snapshots, sanitized provider/canonical/report fixtures, content catalogs where still product-relevant, and golden request/response examples.
- **Generated for Swift:** the mobile endpoint's `Codable` DTOs, closed enums, error bodies, and API client from FastAPI OpenAPI. Do not generate Swift models for internal provider or canonical rows.
- **Written in Swift:** SwiftUI screens and navigation, `URLSession` integration around generated operations, Keychain storage for user/session credentials, local display preferences, response caching for resilience, formatting, accessibility, and presentation-only ordering.
- **Not migrated into the app:** research corpus readers, split controls, collectors/probes, calibration/tournament scripts, raw STRATZ payloads, provider token, Celery, Redis, SQLAlchemy, FastAPI, or V6/V6.1/V7 analytical implementations.
- **Eventually retired, after parity and owner approval:** the Next.js report renderer, its API proxy, React story state, CSS/motion implementation, and legacy web-only presentation types. Do not delete them during migration; they remain the current production consumer and compatibility reference.

## B. Current architecture map

### Actual production and V7 paths

The repository currently contains two adjacent paths, not one fully switched path:

```text
Current public generation path

Next.js analysis form
  apps/web/app/components/analysis-form.tsx
        │ POST /v1/analyses; poll /v1/analyses/{job_id}
        ▼
FastAPI routes
  services/api/app/api/routes.py
        ▼
AnalysisService (V6/V6.1/legacy Free only)
  services/api/app/analysis/service.py
        ├── OpenDota source/parse transport
        │   services/api/app/opendota/*
        ├── summary/detail normalization and eligibility
        │   services/api/app/ingestion/*
        ├── features/domain/report assembly
        │   services/api/app/features/*
        │   services/api/app/player_analysis_v6/*
        │   services/api/app/player_analysis_v61/*
        │   services/api/app/reports/*
        └── repository + Celery
            services/api/app/storage/*
            services/api/app/workers/tasks.py
                  ▼
          PostgreSQL / Redis
                  ▼
GET /v1/reports/{report_id}
                  ▼
Next.js V6/V6.1 renderer
  apps/web/app/report/[reportId]/*

Validated V7 STRATZ path

STRATZ GraphQL
  services/api/app/stratz/queries.py
        ▼
authenticated bounded transport, cache, retries, rate handling
  services/api/app/stratz/client.py
        ▼
provider-native typed models / deep fail-closed normalization
  services/api/app/stratz/models.py
  services/api/app/stratz/deep.py
        ▼
provider-neutral canonical history
  services/api/app/stratz/normalize.py
  services/api/app/providers/base.py
        ▼
V7RuntimeService acquisition + frozen runtime
  services/api/app/player_analysis_v7/service.py
  services/api/app/player_analysis_v7/runtime.py
        ▼
capability assembly, persistence, public projection
  services/api/app/player_analysis_v7/assembly.py
  services/api/app/player_analysis_v7/capability_payload.py
  services/api/app/player_analysis_v7/lifecycle.py
  services/api/app/player_analysis_v7/public_projection.py
        ▼
PostgreSQL repository
  services/api/app/storage/repository.py
        ▼
GET /v1/v7/reports/{report_id}
or GET /v1/reports/{report_id}
  returns only PublicProjection for V7
```

`services/api/app/main.py` constructs `app.state.v7_runtime_service` when `DATA_PROVIDER=stratz`, but `services/api/app/api/routes.py` never calls `V7RuntimeService.generate`. `POST /v1/analyses` always calls `AnalysisService.create_analysis`, which explicitly accepts only Free reports and retains the OpenDota V6/V6.1 path. The V7 generation seam is therefore executable and integration-tested, but not a public production generation entry point.

`services/api/app/workers/tasks.py` also dispatches only `AnalysisService.run_job`; it does not run `V7RuntimeService.generate`. A mobile rollout must therefore add an explicit V7/new-scorecard application-service task rather than assuming existing Celery dispatch covers it.

### Layer-by-layer implementation

| Layer | Actual implementation | Versioned | Tested | Should Swift know it? |
| --- | --- | --- | --- | --- |
| Provider operation | `services/api/app/stratz/queries.py` (`GraphQLOperation`, named/versioned documents and SHA-256) | Yes, per operation | Yes | No |
| Provider transport | `services/api/app/stratz/client.py` | Behavior/config versioned indirectly by operation, cache key, and analytical identity | Yes | No |
| Provider object validation | `services/api/app/stratz/models.py` | `stratz-history-schema-1.0.0` | Yes | No |
| Deep provider normalization | `services/api/app/stratz/deep.py` | Bound to `GetDeepMatchBatch` operation version; output lacks a standalone schema constant | Yes | No |
| Provider-neutral canonical history | `services/api/app/providers/base.py`; adapter in `services/api/app/stratz/normalize.py` | Provider schema and `stratz-v7-normalization-1.0.0` | Yes | No |
| V7 runtime feature adapter/domain | `services/api/app/player_analysis_v7/runtime.py`, using selected modules under `research/` as imported production logic | `v7-analytical-runtime-1.0.0` plus frozen artifact identities | Yes | No |
| Frozen population/context | `player_analysis_v7/data/*.json`, loaders in `population.py` and `context_projection.py` | Yes, digest-checked and compatibility-bound | Yes | No |
| Persisted capability document | `capability_payload.py`, assembled by `assembly.py` | `v7-capability-payload-2.0.0` | Yes | No; private/internal |
| Public V7 DTO | `public_projection.py` | `v7-public-projection-1.0.0` exists in provenance, though response body does not carry it | Yes | Only if this limited view is used |
| Legacy report DTOs | `api/report_schemas*.py`, `api/story_payload_schemas_v61.py` | Yes | Yes | Only for legacy report viewing |
| API/job/session DTOs | `api/schemas.py`, routes in `api/routes.py` | Partly; interaction state is versioned | Yes | Generate only selected public operations |
| Storage | `storage/models.py`, `storage/repository.py`, Alembic `0001`–`0005` | DB head `0005_v6_interactions_deep` | Unit/integration | No |
| Web compatibility boundary | `apps/web/app/report/[reportId]/v6/normalize-v61-report.ts` | Consumer-side | Unit/E2E with historical fixture | No code reuse; retain behavior as migration evidence |

## C. Migration matrix

Classification is intentionally at meaningful module/group granularity; individual files with the same responsibility and destination are grouped.

| Current path/module | Responsibility | Production or research | Current language | iOS needs it? | Classification | Destination | Rewrite required? | Risk | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `services/api/app/main.py` | FastAPI composition, lifecycle, provider/repository wiring, readiness | Production | Python | Indirectly | KEEP_SERVER | Railway API | No | Medium: V7 service is wired but not routed for generation | `create_app`; provider architecture tests |
| `services/api/app/core/config.py` | Environment, provider selection, production guards, timeouts/retries | Production | Python | No | KEEP_SERVER | Server | No | High if secrets/config leak client-side | production validation and config tests |
| `services/api/app/core/security.py` | identifier parsing, redaction, API rate limiting | Production | Python | Behavior only | KEEP_SERVER | Server/API gateway | No | High | security tests |
| `services/api/app/core/cache.py` | memory/Redis cache abstraction and payload hashing | Production | Python | No | KEEP_SERVER | Server Redis | No | Medium | cache use in both provider and service |
| `services/api/app/core/errors.py` | stable server/provider error taxonomy | Production | Python | Selected public codes | GENERATE_FOR_SWIFT | Mobile OpenAPI error DTO | No logic rewrite | Medium: current exception responses are not exhaustively declared in OpenAPI | provider/API tests |
| `services/api/app/core/release.py`, `core/metrics.py`, `core/logging.py` | release identity, observability, secret-safe logging | Production | Python | Read-only release metadata at most | KEEP_SERVER | Server | No | Medium | release identity tests/readiness |
| `services/api/app/providers/base.py` | provider-neutral profile/history/match contracts and provenance | Production | Python | No | KEEP_SERVER | Server domain boundary | No | Low | provider architecture tests |
| `services/api/app/providers/__init__.py` | explicit V7 provider selection | Production | Python | No | KEEP_SERVER | Server | No | Low | `test_v7_provider_architecture.py` |
| `services/api/app/stratz/queries.py` | reviewed GraphQL shapes, versions, response model names, document hashes | Production plus probe/research operations | Python strings | No | KEEP_SERVER | Server STRATZ adapter | No | High if duplicated or casually changed | named-operation tests and frozen acquisition evidence |
| `services/api/app/stratz/client.py` | auth, bounded pagination, per-process throttle, header parsing, retries/backoff, request ledger, cache, dedupe | Production | Python | No | KEEP_SERVER | Server STRATZ adapter | No | High: token/quota/cost | `test_stratz_client.py` |
| `services/api/app/stratz/models.py` | fail-closed provider-native schema and native enum preservation | Production | Python | No | KEEP_SERVER | Server STRATZ adapter | No | High: schema drift/null semantics | client/normalizer tests |
| `services/api/app/stratz/normalize.py` | provider-native to `V7CanonicalHistory`/match/profile | Production | Python | No | KEEP_SERVER | Server canonical boundary | No | High: product truth input | `test_stratz_normalize.py` |
| `services/api/app/stratz/deep.py` | fail-closed deep match/event/trajectory normalization and forbidden-field fence | Production, derived from Pass-2 research | Python | No | KEEP_SERVER | Server canonical deep evidence | No, except approved additive fields | High | runtime nullable-evidence and deep-batch tests |
| `services/api/app/stratz/item_vocabulary.json` | committed STRATZ item metadata snapshot | Production/research artifact | JSON | Usually no; names only if UI requires them | REUSE_AS_SHARED_ARTIFACT | Server resource; optionally derive a minimal display catalog | No | Medium: staleness/licensing/oversharing | loader and exact-set tests |
| `services/api/app/stratz/item_vocabulary.py` | validates vocabulary and classifies recipes/consumables/real items | Production analytical support | Python | No | KEEP_SERVER | Server | No | Medium: metric semantics | `test_stratz_item_vocabulary.py` |
| `services/api/app/player_analysis_v7/acquisition_policy.py` | full-depth, batching, quota economics and equal-tier policy | Production policy | Python | No | KEEP_SERVER | Server | No | High: provider cost | acquisition policy tests/evidence |
| `player_analysis_v7/service.py` | fetch/reuse deep evidence, execute frozen runtime, persist | Production-capable but not publicly routed | Python | Indirectly | KEEP_SERVER | Server application service | Adapt route/auth only | High | `test_v7_runtime_service.py` |
| `player_analysis_v7/lifecycle.py` | version-derived job coalescing/reuse and persistence | Production-capable | Python | No | KEEP_SERVER | Server | No | High: stale reuse | lifecycle/runtime service tests |
| `player_analysis_v7/runtime.py` | authoritative per-player V7 calculation using frozen artifacts | Production | Python | Results only | KEEP_SERVER | Server domain | No | High: duplicated truth | V7 runtime/parity/bugfix suites |
| `player_analysis_v7/assembly.py` | non-analytical capability assembly | Production | Python | Results only | KEEP_SERVER | Server | No | Medium | capability tests |
| `player_analysis_v7/capability_payload.py` | private persisted V7 capability, availability/refusal/provenance/privacy validation | Production | Python/Pydantic | Not directly | KEEP_SERVER | Server persistence boundary | No | High: contains private capability material | payload and route privacy tests |
| `player_analysis_v7/public_projection.py` | minimal allowlisted unauthenticated view | Production | Python/Pydantic | Maybe | GENERATE_FOR_SWIFT | Generated DTO for legacy/public V7 read | No | Low, but too thin for scorecard | typed OpenAPI route tests |
| `player_analysis_v7/report_contract.py` | older full narrative contract; much is contract-shaped rather than produced | Mixed specification/production types | Python/Pydantic | No for V1 scorecard | RESEARCH_ONLY | Retain for Pro/annual report | No | High if mistaken for current capability | capability manifest and contract tests |
| `player_analysis_v7/descriptive.py` | deterministic bounded history facts | Production | Python | Results may be useful | KEEP_SERVER | Server domain; project only needed facts | No | Low | descriptive tests |
| `player_analysis_v7/display_semantics.py` | canonical labels/units/format hints for V7 dimensions | Production presentation metadata | Python/Pydantic | Some | REUSE_AS_SHARED_ARTIFACT | Project relevant metadata through mobile DTO or generated JSON | No | Medium: old V7 concepts may not fit new scorecard | semantics binding tests |
| `player_analysis_v7/context_projection.py`, `population.py`, `data/*.json` | load and verify frozen analytical parameters and provenance | Production artifacts/runtime | Python + JSON | No | KEEP_SERVER | Server artifact bundle | No | Critical | digest, compatibility, runtime parity tests |
| `player_analysis_v7/research/features.py`, `pass2_observations.py`, `pass2_tables.py`, `ranking.py`, `recommendation.py`, `archetype.py`, `inference.py`, registries | research-derived algorithms; selected modules are imported by `runtime.py` | Mixed: imported subset is production runtime; corpus loaders are research | Python | No | KEEP_SERVER | Server package; later separate runtime imports from research namespace without changing math | No immediate rewrite | High: namespace invites accidental migration/deletion | runtime import graph and V7 tests |
| Remaining `player_analysis_v7/research/*` corpus/screen/tournament/red-team/variant/verdict modules | cohort access, experiment design, evidence generation | Research | Python | No | RESEARCH_ONLY | Backend research/archive | No | High if shipped or allowed to read reserved splits | corpus/access tests |
| `services/api/app/ingestion/*` | legacy OpenDota normalization, eligibility, summary-history contract | Production V6/V6.1 | Python | No | KEEP_SERVER | Server for persisted legacy reports; reuse eligibility concepts carefully | No | Medium | eligibility/summary contract tests |
| `services/api/app/features/*`, `dna/*`, `behavior/*`, `insights/*`, `patterns/*`, `hero_portfolio/*` | legacy Free/V5 product calculations | Production legacy | Python | No for new V1 | KEEP_SERVER | Existing report support; candidate reuse by explicit review only | No | Medium: concepts are not automatically new product truth | broad unit suite |
| `services/api/app/player_analysis_v6/*`, `player_analysis_v61/*`, `reports/*` | frozen/legacy annual report analytics and assembly | Production persisted-report support | Python | Optional annual/Pro results only | KEEP_SERVER | Server annual report path | No | Critical backward compatibility | V6/V6.1 contract/calibration suite |
| `services/api/app/api/schemas.py` | create/status/session/deep DTOs and client-state validation | Production | Python/Pydantic | Selected operations | GENERATE_FOR_SWIFT | Mobile contract generation input | Adapt/add explicit mobile DTOs | Medium: several `dict[str, Any]` weaken generation | API/interaction tests |
| `services/api/app/api/report_schemas*.py`, `story_payload_schemas_v61.py` | versioned legacy report validation | Production compatibility | Python/Pydantic | Only if iOS displays old reports | GENERATE_FOR_SWIFT | Separate legacy-report generated target, not core app model | No | High due to optional historical shapes | contract tests and production-shaped fixture |
| `services/api/app/api/routes.py` | jobs, SSE, persisted reads, interactions, deep analysis, share, health | Production | Python/FastAPI | Yes, through selected endpoints | KEEP_SERVER | Server; add mobile-focused router later | Adapt | High: current V7 create gap and untyped generic report response | API and V7 route tests |
| `services/api/app/storage/models.py`, `storage/database.py`, `storage/repository.py`, `migrations/*` | PostgreSQL documents/jobs/raw cache/interactions, dedupe, retention, DB revision | Production | Python/SQLAlchemy | No | KEEP_SERVER | Server PostgreSQL | Extend later for role history/corrections | High: existing reports are contracts | migration/repository tests |
| `services/api/app/workers/tasks.py` | Celery execution, retention, worker release identity | Production | Python | No | KEEP_SERVER | Railway worker | Adapt when new scorecard jobs need async execution | Medium | worker tests/readiness |
| `scripts/stratz_v7_corpus_runner.py`, `stratz_v7_pass1_recollect.py`, `stratz_v7_pass2_runner.py`, supervisors | bounded corpus acquisition and archival | Research | Python | No | RESEARCH_ONLY | Retain offline/backend only | No | Critical quota/privacy | runner/supervisor tests |
| `scripts/stratz_v7_live_microprobe.py`, `stratz_v7_pass2_probe.py`, `stratz_v7_fetch_item_vocabulary.py` | empirical schema/semantics probes and one-time vocabulary fetch | Research/maintenance | Python | No | RESEARCH_ONLY | Controlled backend maintenance | No | Critical quota/schema | probe/microprobe tests and evidence |
| `scripts/v7_*` analysis/freeze/export/parity scripts | corpus analysis, frozen artifact derivation, parity | Research/release tooling | Python | No | RESEARCH_ONLY | Backend research/release | No | Critical lineage integrity | evidence manifests and script tests |
| `.local/corpora/stratz/*` | raw/normalized/canonical private research corpora | Research | JSON/files | No | RESEARCH_ONLY | Private durable research storage only | No | Critical privacy/provider terms | corpus guard and durability tests |
| `tests/fixtures/stratz/*`, selected V7 JSON fixtures | sanitized deterministic shapes | Test artifact | JSON | Yes, selected public/golden shapes | REUSE_AS_SHARED_ARTIFACT | Shared contract fixture directory | No | Low after privacy scan | provider/runtime tests |
| `docs/evidence/*v7*`, STRATZ evidence | decisions, empirical semantics, provenance, known limitations | Research evidence | Markdown/JSON | No runtime need | RESEARCH_ONLY | Repository evidence/archive | No | Low; may become stale | compare against executable tests/code |
| `apps/web/app/components/analysis-form.tsx` | create/poll/navigate client flow | Production web | TypeScript/React | Pattern only | DEPRECATE | Replace with native flow after parity | Yes, natively | Low | Playwright home tests |
| `apps/web/app/v1/[...path]/route.ts` | same-origin Vercel-to-API proxy | Production web | TypeScript | No | DEPRECATE | Native app calls API gateway directly | No port | Medium: replace CORS with real mobile auth/TLS policy | proxy implementation |
| `apps/web/app/report/[reportId]/page.tsx` and V6 story components | report fetch, runtime normalization, React presentation/state | Production web | TypeScript/React | Product behavior, not code | DEPRECATE | Rebuild presentation in SwiftUI; retain until migration complete | Yes, UI only | High: historical compatibility | historical production fixture and E2E suite |
| `apps/web/.../v6/normalize-v61-report.ts` | historical persisted-report compatibility normalization | Production web | TypeScript | If native opens old reports | REUSE_AS_SHARED_ARTIFACT | Treat degradation rules/fixtures as spec; implement a narrow Swift decoder | Yes, behavior not source | High | historical fixture/E2E |
| `apps/web/.../story/copy.ts`, `format.ts`, `motion.ts`, content constants | web presentation copy/format/motion | Production web | TypeScript | Selectively | PORT_TO_SWIFT | SwiftUI presentation resources/helpers | Yes | Medium: avoid carrying stale V7/V6 product direction | story unit/E2E |
| `apps/web/styles/*`, CSS modules, React components | browser UI implementation | Production web | CSS/TSX | No | DEPRECATE | None | No mechanical port | Low | native UI rebuild |

## D. STRATZ reuse map

### Preserve as the authoritative production path

1. **Queries:** `stratz/queries.py` contains named, versioned GraphQL documents with purpose, expected response model, and a document SHA-256. Core runtime uses `GetPlayerProfile`, `GetPlayerHistoryPage`, `GetMatchCore`, and `GetDeepMatchBatch`; the remaining sentinel/probe operations encode research knowledge and should stay controlled tooling, not normal runtime calls.
2. **Client behavior:** `stratz/client.py` owns the bearer token, required `STRATZ_API` user-agent, bounded history pagination, request ledgers, provider-aware cache keys, cache TTLs, deduplication, retry/backoff, `Retry-After`, rate-limit header parsing, HTML challenge detection, GraphQL partial/error handling, schema-error distinction, redaction, and conservative local throttling.
3. **Provider-native schemas:** `stratz/models.py` validates required structure, preserves unknown native enum strings, preserves nullable fields, and refuses mismatched account/match identities. Do not translate these types to Swift.
4. **Normalization:** `stratz/normalize.py` maps only validated provider fields into `CanonicalProfile`, `V7CanonicalMatch`, and `V7CanonicalHistory`, retaining native role/position/lane separately and attaching operation/document/raw-payload provenance.
5. **Deep evidence:** `stratz/deep.py` normalizes trajectories, events, farm distribution, tower deaths, and nullable values. It rejects forbidden opaque provider analytics and unrequested/duplicate matches. This is the base to extend only when an approved role metric needs additional factual fields.
6. **Vocabulary:** `item_vocabulary.json` and loader predicates encode an empirically reviewed snapshot and analytical distinctions such as recipe/consumable/real item. Keep the raw artifact server-side. If the app needs item names/icons, expose a smaller versioned display catalog rather than the analytical classification rules.
7. **Caching and reuse:** Redis is selected in production for the STRATZ client; repository raw-payload records reuse deep rows across runs. V7 lifecycle coalesces in-flight work and reuses compatible completed reports by analytical identity. This cross-user/server control cannot be reproduced efficiently per device.

### Verified operational gaps to close before mobile production

- `StratzClient._throttle` is an in-memory request timestamp list owned by one client/process. It honors observed response headers and conservative ceilings, but it is **not a distributed quota coordinator** across API and Celery replicas. Redis caches responses; it does not currently reserve provider quota. Add a shared quota/lease mechanism before horizontally scaling STRATZ callers.
- Job coalescing exists at the repository lifecycle level, but the STRATZ cache has no cache-miss single-flight lock. Concurrent distinct jobs can issue the same uncached provider request. The mobile sync path should coalesce per account/operation before acquisition.
- `V7RuntimeService` persists the accumulated normalized deep-row list under one account endpoint. It does not satisfy `acquisition_policy.PERSISTENCE_REQUIREMENTS` literally: raw provider payloads and versioned derived features are not stored per match, and the stored value is normalized deep evidence rather than a provider-native archive. The policy docstring still says the pipeline does not exist, although the service now exists. Treat the requirements as an uncompleted target, not evidence of current storage behavior.
- History-page responses are cached in Redis for 120 seconds and profile responses for 300 seconds; immutable match/deep calls have no TTL. Repository report/raw retention can still purge database material. “Fetch once, reuse forever” is therefore a policy intent, not an end-to-end guarantee under current retention and cache eviction.
- The V7 lifecycle reuse identity binds analytical artifacts/runtime/deep operation, but its completed-report lookup does not first compare a current history hash. Without a sync/invalidation check, a returning player can receive a compatible older report even after playing new matches. The continuous tracker must key freshness to the newest observed match/cutoff.
- No canonical product-user authentication/owner credential exists for private V7 reads. Current V7 routes correctly expose only `PublicProjection`. Mobile private scorecards and role corrections require an explicit ownership model; UUID knowledge is not authorization.

These are bounded adaptations to the existing backend. None is a reason to move provider or analytical logic into the app.

### Executable knowledge versus prose

| Knowledge | Executable source of truth | Documentation/evidence role |
| --- | --- | --- |
| GraphQL shapes and selected fields | `stratz/queries.py` | Probe and acquisition evidence explains why |
| Required/null provider shapes | `stratz/models.py`, `stratz/deep.py` | Field audits record observations |
| Native enum preservation | `stratz/models.py`, `stratz/normalize.py` | Docs explain rejected OpenDota-style remapping |
| Pagination/deduplication | `stratz/client.py` | Corpus plans estimate volume |
| Batch size | `acquisition_policy.py`, deep client validation | Research runners independently encode their own bounded research policies |
| Retry/rate handling | `stratz/client.py` | Usage review warns published quotas are not a current grant |
| Cache identity and TTL | `stratz/client.py`, `providers/base.py`, repository | Usage review constrains raw archival/redistribution |
| Per-minute/event semantics | `stratz/deep.py`, `research/features.py`, `pass2_observations.py`, `pass2_tables.py` and tests | Evidence captures empirical reasoning and limitations |
| Item semantics | `item_vocabulary.py` and JSON | Fetch script is maintenance tooling only |
| Frozen analytical results | runtime plus digest-bound `data/*.json` | evidence is provenance, not an alternate runtime |

When prose conflicts with tests and current runtime, current executable validation wins. For example, the older capability manifest says the full `ReportPayload` had no producer and an unversioned contract; current code now produces `V7CapabilityPayload` version `2.0.0` and persists it, while the older nine-section `ReportPayload` remains largely a specification. Conversely, the current completion ledger accurately states that the V7 generation route is still partial: only typed persisted reads are public.

### Security and cost conclusion

Direct device-to-STRATZ access is rejected. It would expose `STRATZ_API_TOKEN`, multiply calls by device, eliminate central request coalescing and shared cache reuse, weaken global throttling and abuse controls, complicate query/analytical invalidation, and make provider changes depend on App Store releases. The repository's provider-use review also advises against redistributing raw or row-level STRATZ data; a thin derived mobile DTO is the safer boundary.

## E. Canonical/schema reuse map

```text
STRATZ provider JSON
  query: services/api/app/stratz/queries.py
  transport: services/api/app/stratz/client.py
        │ private, provider-shaped
        ▼
Provider-native validated object
  services/api/app/stratz/models.py
  services/api/app/stratz/deep.py
  schema: stratz-history-schema-1.0.0 + operation versions
        │ server-only
        ▼
Provider-neutral canonical history/evidence
  services/api/app/providers/base.py
  services/api/app/stratz/normalize.py
  normalizer: stratz-v7-normalization-1.0.0
        │ server-only product input
        ▼
Product domain truth
  existing annual V7: player_analysis_v7/runtime.py
  new continuous tracker: new server module, not yet implemented
  frozen inputs: player_analysis_v7/data/*.json
        │ server-owned calculations and recalculation
        ▼
Persisted internal capability / progress state
  player_analysis_v7/capability_payload.py
  storage/models.py + storage/repository.py
        │ authenticated, versioned projection
        ▼
Mobile API DTO
  new explicit Pydantic models/router (future work)
  OpenAPI document
        │ generate selected operations only
        ▼
Swift Codable + API client
        │ map to presentation state
        ▼
SwiftUI
```

Swift should consume the thin mobile DTO, never the raw STRATZ schema or internal canonical history. The canonical history includes operational/provider detail and is allowed to evolve with server analytics. A stable DTO should carry only player-visible scorecard facts, exact nullable/unavailable/refused states, display metadata, and provenance/version identifiers needed to interpret/cache the response.

The proposed Carry/Mid/Support metrics are product-domain truth and remain server-side:

- role qualification and eligible mode filtering;
- current-match exclusion;
- last 20 eligible **prior** matches in the confirmed role;
- median and minimum five prior matches;
- raw display values and normalized comparison values;
- Personal Best eligibility and role scope;
- damage/objective shares requiring team denominators;
- whole-match dead time and duration normalization;
- observer wards and attributed `wardDestruction` counts with the explicitly limited subtype semantics;
- user-confirmed role corrections and deterministic rebuild of affected role histories.

The app displays those results; it must not independently recalculate them. Offline mode may show the last server-issued scorecard/history with its version and staleness, but must not award a new Personal Best or mutate authoritative progress while offline.

## F. Recommended target architecture

```text
┌───────────────────────────────┐
│ Native iOS / SwiftUI          │
│ generated DTO/client          │
│ presentation + local UI state │
└───────────────┬───────────────┘
                │ HTTPS, user auth, idempotency/version headers
                ▼
┌────────────────────────────────────────────┐
│ FastAPI mobile boundary                    │
│ latest-match / scorecard / history / role  │
│ stable errors + refusal states + OpenAPI   │
└───────────────┬────────────────────────────┘
                ▼
┌────────────────────────────────────────────┐
│ Python product domain (authoritative)      │
│ eligibility → role → prior-20 median       │
│ scorecard → role history → Personal Best   │
│ correction-triggered deterministic rebuild │
└───────┬───────────────────────┬────────────┘
        │                       │
        ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│ PostgreSQL/Celery │   │ shared Redis cache│
│ progress/reports  │   │ jobs/provider data│
└───────────────────┘   └─────────┬─────────┘
                                  ▼
                         ┌───────────────────┐
                         │ STRATZ adapter    │
                         │ existing queries │
                         │ client/normalize │
                         └─────────┬─────────┘
                                   ▼
                                STRATZ

Separate retained path:
existing V6/V6.1 and V7 annual/Pro report generation + persisted report reads
```

### Architecture comparison

| Concern | A: native + existing backend | B: iOS direct to STRATZ | C: mixed calculations | D: Swift rewrite |
| --- | --- | --- | --- | --- |
| Token security | Best; secret stays server-side | Unacceptable | Good only if STRATZ stays server-side | Good only with a separate Swift server, at high cost |
| Rate limits/cost/cache | Central, shared, deduplicated | Per-device duplication/abuse | Central acquisition, but duplicated compute/cache semantics | Must rebuild all controls |
| Determinism/versioning | One authority | App-version fragmentation | Two truth implementations | Long parity period and migration risk |
| Role correction/PB/history rebuild | Central transactional recomputation | Hard and device-local | Cross-boundary invalidation complexity | Must recreate data and job infrastructure |
| Offline | Cached last known response | Partial provider access still unreliable | Can calculate stale/partial truth incorrectly | No inherent advantage |
| Latency | One optimized API call; background job where needed | Multiple provider calls | Extra coordination | Unknown until rebuilt |
| Maintenance/test reuse | Maximum | Minimum | Analytical tests duplicated | Existing Python suite largely discarded |
| App Store operation | Server fixes ship without review | Provider/schema fixes require app release | Client formula fixes require app release | Same plus backend rewrite risk |
| Migration effort | Lowest | High | High | Extreme |

Architecture A is the single recommendation. Architecture C is not justified for authoritative metrics; limited local formatting and cached display do not count as mixed computation.

## G. Swift boundary specification

### Contract shape

Create a new versioned mobile namespace only after its exact product contract is approved; preserve `/v1/reports/*` and `/v1/v7/reports/*`. A suitable shape is:

- `POST /v1/mobile/players/{player}/sync` — idempotently discover/import newest available matches and return a job or completed snapshot;
- `GET /v1/mobile/syncs/{job_id}` — typed job state (polling is simpler than SSE for the first slice; add streaming only if measured latency needs it);
- `GET /v1/mobile/players/me/latest-scorecard` — authenticated latest immutable scorecard;
- later, `GET /v1/mobile/players/me/progress?role=...` and `PATCH /v1/mobile/matches/{match_id}/role` with optimistic concurrency/idempotency.

Exact route names are recommendations, not implementation in this audit. The smallest slice needs only sync/status plus one scorecard read; history and role correction follow after the domain contract exists.

Use explicit Pydantic response models with `extra="forbid"`, finite-number validation, closed enums where truly closed, and nullable fields where unavailable evidence is valid. Avoid `dict[str, Any]` in generated operations. Declare all stable error models in OpenAPI.

Minimum scorecard DTO concepts:

- `contract_version`, `metric_catalog_version`, `calculation_version`, provider/normalizer provenance digest, generated/observed timestamps;
- stable player-scoped match reference (never provider secret material);
- assigned role, role source (`inferred` or `user_confirmed`), correction revision;
- mode eligibility and explicit non-updating reason;
- per metric: stable key, raw display value/unit, comparison value/unit only if the UI needs it, baseline median, prior eligible count, baseline window cap, direction/polarity metadata, availability/refusal code, and Personal Best state;
- progress mutation revision and recalculation status;
- typed errors such as authentication required, private/unavailable profile, provider unavailable/rate limited, insufficient prior role matches, ineligible mode, schema/version unsupported, correction conflict, and job failed.

### Generation and networking

- FastAPI already emits OpenAPI and already types the V7 public read route. Make the future mobile operations fully typed, export a pinned OpenAPI artifact, and generate only those operations into a dedicated Swift module.
- Prefer Apple's `URLSession` underneath the generated client. Do not add a third-party networking dependency unless generated-client limitations are measured.
- Use generated `Codable` transport types. Map them into small handwritten Swift presentation models only where SwiftUI needs derived display state. Never hand-copy backend enums if generation can preserve them.
- Treat unknown future enum values as an explicit compatibility concern. For server-controlled closed semantics, coordinate version bumps; for evolving display/refusal codes, generate a tolerant wrapper or preserve an `unknown(String)` mapping in the Swift-facing generator template.
- Keep authentication separate from the STRATZ token. The app holds only a product user/session credential in Keychain. The server resolves ownership and never returns provider credentials.
- Keep authoritative caches in Redis/PostgreSQL. The app may cache immutable JSON responses or decoded snapshots for fast launch/offline reading, keyed by user + contract/calculation version, with server timestamps and stale labeling.
- Store only presentation preferences and resumable UI state locally. Role corrections, progress, PBs, history, and calculation versions are server records.

The checked-in root `api.json` and `scripts/generate_api_client.py` describe an older TypeScript client workflow and should not be assumed current enough for Swift. Regenerate a reviewed OpenAPI snapshot from the mobile router when that router exists, then use an OpenAPI-to-Swift generator selected in the iOS project. Do not generate the entire legacy API surface into the app.

Before production, the server cache boundary must additionally provide distributed STRATZ quota accounting, per-account sync coalescing, and newest-match freshness/invalidation. The device must never be the coordination authority for any of those concerns.

## H. Research/corpus disposition

| System/artifact | Disposition | Runtime dependency? | iOS bundle? | Useful test role |
| --- | --- | --- | --- | --- |
| `.local/corpora/stratz/v7-*` raw/normalized/canonical corpora | Keep private/durable as backend evidence subject to retention/provider review | No direct production read found | Never | Source for sanitized structural fixtures only |
| DISCOVERY/CANDIDATE_TEST split controls and access ledger | Keep as research governance | No | Never | Test reserved-split fences |
| CALIBRATION_RESERVED/SEALED_VALIDATION | Preserve untouched per analytical governance | No | Never | Release evidence only after explicit authorization |
| Pass-1/Pass-2 collectors, supervisors, probes | Retain controlled research/maintenance tooling | No | Never | Their offline unit fixtures protect acquisition semantics |
| `player_analysis_v7/research/corpus.py`, durability guards | Retain research-only | `deep.py` imports only `forbidden_fields_in`; runtime otherwise does not read corpus paths | Never | Keep privacy/access tests |
| Research feature/inference/ranking/recommendation modules imported by `runtime.py` | Keep server-side; they are production code despite directory name | Yes, selected modules | Never | Existing analytical suite remains authoritative |
| Frozen `player_analysis_v7/data/context-projection-2.0.0.json` and `population-parameters-2.0.0.json` | Keep immutable server artifacts | Yes | Never | Digest/binding/parity tests |
| `item_vocabulary.json` | Keep shared repository artifact, server runtime primary | Yes for item analyses | Only a derived UI subset if required | Same JSON can support loader tests; do not expose classifications casually |
| `tests/fixtures/stratz/get_player_history_page.json` | Retain sanitized provider fixture | Tests only | No | Provider parse/normalize regression |
| V7 capability/public fixtures | Retain and add sanitized mobile golden outputs later | Tests only | Selected public golden JSON in Swift test target | Cross-language decode compatibility |
| `docs/evidence/v7-*` | Keep as version/provenance evidence; archive stale narrative claims rather than deleting | No | Never | Audit trail, not executable truth |

No production runtime read of `.local` corpus files was found. Production loads only checked-in frozen JSON artifacts. The one architectural smell is namespace coupling: `runtime.py` imports selected analytical implementations from `player_analysis_v7/research`, and `stratz/deep.py` imports the research package's `forbidden_fields_in`. This does **not** justify a rewrite. Later, a behavior-preserving package move may clarify ownership, but only with parity tests and no formula change.

Production iOS needs no corpus data. Preserve a few sanitized, deterministic fixtures as shared contract tests:

```text
sanitized provider JSON
  → expected canonical JSON (Python-only internal golden)
  → expected mobile DTO JSON (cross-language public golden)

Python tests: provider → canonical → domain → mobile JSON
Swift XCTest: decode the exact mobile JSON → expected client state/presentation
```

Only create cross-language calculation goldens if calculation genuinely moves to Swift. No authoritative calculation is recommended to move, so Swift should test decoding and presentation behavior, not re-run hundreds of analytical assertions.

## I. API contract assessment

### What exists

- The closest complete **internal** V7 contract is `V7CapabilityPayload`. It carries private recommendation, provenance, refusals, availability, descriptive facts, and public projection. It is suitable for persistence, not direct unauthenticated mobile consumption.
- The closest safe **public** V7 contract is `PublicProjection` at `GET /v1/v7/reports/{report_id}`. It is typed in OpenAPI and privacy-tested, but intentionally exposes one selected public fact and no private recommendation/provenance. It cannot drive the continuous scorecard.
- The legacy generic report endpoint returns different shapes by persisted schema version and has no response model. It is a compatibility endpoint, not a clean generated mobile API.
- Job creation/status models are typed and reusable in concept, but `POST /v1/analyses` is explicitly V6/V6.1 Free-only. V7 generation has no route.
- Interaction/deep endpoints preserve important auth, ETag/revision, refusal, and server-owned-state patterns, but their loose dictionary fields make them poor direct generation inputs.

### Recommendation

Expose a new authenticated mobile DTO while preserving the same repository/provider/domain layers. Do not bend the legacy report contract into a per-match tracker and do not expose canonical matches. Preserve exact distinctions among:

- absent/unavailable evidence;
- insufficient support;
- ineligible game mode;
- refused analytical capability;
- provider/private profile failure;
- queued/running/completed/failed job;
- stale but readable cached result;
- user-confirmed versus inferred role;
- correction accepted, conflict, and recalculation pending/completed;
- generated versus reused output and all calculation/contract versions.

## J. Web frontend disposition

Purely web-specific and eventually retired: Next.js routing/layout/loading/error surfaces, the `/v1` Vercel proxy, React components/hooks, CSS modules/global CSS, browser share/clipboard code, web analytics event plumbing, Playwright browser mechanics, and DOM/motion implementation.

Knowledge worth carrying, not mechanically porting:

- request → job polling → report navigation from `analysis-form.tsx`;
- persisted-payload normalization and omission behavior from `normalize-v61-report.ts`;
- stable metric labels, units, evidence/methodology copy, and privacy rules after checking they still fit the new product;
- accessibility behaviors: reduced motion, keyboard/native control semantics, focus, no horizontal overflow, and readable error/empty states;
- sanitized historical fixtures and scenario coverage.

Potentially misplaced product logic in the web layer includes story composition, page/card selection, fallback/omission rules, formatting, and some copy gating under `v6/story/*`. Presentation ordering and formatting belong in Swift; any rule that changes analytical availability, qualification, PB status, baseline, or role history must instead be made explicit in the server DTO/domain before migration.

## K. Testing strategy

### Existing protection inventory

| Boundary | Existing protection |
| --- | --- |
| STRATZ auth/query/error/retry/rate/cache/paging/dedupe | `tests/unit/test_stratz_client.py` |
| Provider-native to canonical semantics | `tests/unit/test_stratz_normalize.py`, STRATZ fixture |
| Item vocabulary/classification | `tests/unit/test_stratz_item_vocabulary.py` |
| Provider selection/secrets/cache identity | `tests/unit/test_v7_provider_architecture.py` |
| Acquisition policy/frozen query surface | `test_stratz_v7_acquisition_freeze.py`, runner/probe tests |
| Deep nullable/schema semantics | STRATZ client, V7 backend bugfix, pass2 observation/table tests |
| V7 runtime and persistence/reuse | `test_v7_runtime.py`, `test_v7_runtime_service.py`, `test_v7_sql_repository.py` |
| Capability/refusal/privacy/provenance contract | `test_v7_capability_payload.py`, `test_v7_public_projection.py`, `test_v7_report_contract.py` |
| Population/context binding and parity | population/context tests and `v7_runtime_parity.py` evidence |
| API jobs/errors/persisted reads | `tests/contract/test_api.py`, V7 route tests |
| PostgreSQL/migrations/cache lifecycle | migration, SQL repository, worker, readiness tests |
| Historical web reports | `apps/web/tests/fixtures/persisted-reports/v61-historical-production.json` plus Playwright/unit story tests |

### Migration boundary

```text
Backend tests
  prove STRATZ → provider-normalized → canonical → product truth

Shared public golden fixtures
  prove product truth → exact versioned mobile JSON

Swift XCTest
  prove generated decoding, unknown/null/refusal handling,
  networking/auth behavior, local cache, formatting, and UI state

SwiftUI tests
  prove accessibility, navigation, loading/error/offline states,
  role-correction flow, and scorecard presentation
```

Add one sanitized current and one backward-compatible public mobile fixture per material contract generation. Python must emit/validate them; Swift must decode the same files. Keep internal provider/canonical fixtures out of the app target. Do not duplicate provider or analytical test suites in Swift.

## L. Migration sequence

### Phase 0 — freeze and audit

Definition of Done:

- this audit is owner-reviewed;
- current public endpoints, persisted report compatibility, V7 artifact digests, and STRATZ query/normalizer versions are recorded;
- no provider call or formula change occurs;
- the new role scorecard vocabulary, eligibility, correction semantics, and auth owner are explicitly approved.

### Phase 1 — stabilize the mobile-facing server contract

Definition of Done:

- authenticated mobile Pydantic DTOs and stable error/refusal enums are approved;
- the smallest sync/status/latest-scorecard routes use existing provider/repository seams;
- the role baseline is server-authoritative: last 20 eligible prior matches, current excluded, median, minimum five;
- mode eligibility and PB rules are executable and versioned;
- legacy report routes and stored reports remain unchanged;
- provider-to-mobile golden tests pass with zero new QA collection calls.

### Phase 2 — generate the Swift contract layer

Definition of Done:

- a pinned reviewed OpenAPI artifact contains only the mobile surface;
- generated Swift `Codable` DTOs/client compile in Xcode;
- selected current/compatibility golden JSON decodes in Python and Swift;
- nullable, refusal, error, and unknown-version cases fail/degrade intentionally.

### Phase 3 — native networking/session shell

Definition of Done:

- Swift uses `URLSession`, product auth in Keychain, and no STRATZ secret;
- sync/status cancellation, retry UX, offline last-known display, and cache invalidation use server versions;
- app logs/analytics contain no private identifiers or tokens.

### Phase 4 — first latest-match vertical slice

Definition of Done:

- user identifies/authenticates, requests sync, observes typed progress, and receives one real server-calculated latest-match scorecard;
- the response path is STRATZ server adapter → canonical history/deep evidence → server scorecard domain → persisted mobile DTO → generated Swift decoder → SwiftUI;
- an eligible and an ineligible-mode fixture both work;
- no analytical calculation is duplicated in Swift.

### Phase 5 — progress/history and role correction

Definition of Done:

- role-scoped history and PBs persist server-side;
- user-confirmed role is authoritative, revisioned, audited, and triggers deterministic recalculation of affected role histories;
- optimistic concurrency/idempotency prevents duplicate or lost corrections;
- tests cover role movement across both old and new histories, minimum support, current-match exclusion, and record revocation/re-award after recomputation.

### Phase 6 — annual/Pro report integration

Definition of Done:

- owner decides which V6/V6.1/V7 outputs remain annual/Pro;
- iOS consumes only an explicit versioned projection;
- old persisted reports either render through a tested compatibility DTO or continue on the web; no regeneration is required.

### Phase 7 — retire obsolete web-only code

Definition of Done:

- native feature/compatibility parity and production adoption are measured;
- existing persisted report access has an approved destination;
- owner separately authorizes decommissioning;
- Next.js proxy/UI removal does not remove backend contracts, fixtures, or evidence still used by iOS/server tests.

## M. Required final answers

### 1. Do we need to rewrite the existing backend in Swift because the app is now native iOS?

**NO.** A native client changes the presentation/runtime client, not the correct home for secrets, shared provider orchestration, authoritative calculations, persistence, or recalculation. Rewriting those in Swift would discard verified Python behavior without improving the product boundary.

### 2. Can the existing STRATZ acquisition and normalization pipeline remain authoritative?

**YES.** It is already isolated, typed, versioned, cache-aware, fail-closed, and tested. It should become the provider path behind the mobile API. The operational gap is routing/authentication and the new scorecard domain—not replacement of acquisition/normalization. Add factual fields only when an approved metric proves the current deep query insufficient.

### 3. Can the existing canonical schemas/contracts be reused for Swift?

Reuse them **indirectly**. Keep provider-neutral canonical schemas internal to Python. Project a thinner, authenticated, versioned Pydantic mobile DTO; generate Swift `Codable` models and the selected API client from FastAPI OpenAPI. Reuse sanitized public JSON golden fixtures in both Python and XCTest. Do not expose or generate raw STRATZ/canonical models into the app.

### 4. Which existing code should actually be ported to Swift?

No backend or analytical module. Port only behavior/content that belongs to presentation: selected formatting/copy/accessibility and navigation ideas from `apps/web/app/report/[reportId]/v6/story/{format,copy,motion}.ts` and the request/status UX pattern from `apps/web/app/components/analysis-form.tsx`. Reimplement them idiomatically in Swift/SwiftUI; do not translate React source line by line. Generate transport types rather than porting them.

### 5. Which existing code should definitely NOT be ported to Swift?

`services/api/app/stratz/*`; `providers/*`; `storage/*`; `workers/*`; `core/config.py`, `cache.py`, `security.py`, `release.py`; `ingestion/*`; all analytical modules under `player_analysis_v6`, `player_analysis_v61`, and `player_analysis_v7`; frozen `player_analysis_v7/data/*`; corpus/probe/collector/calibration/freeze scripts; `.local` corpora; database migrations; provider tokens; Redis/Celery orchestration.

### 6. How much of our existing backend investment survives the move to iOS?

Approximately **97% survives as-is or with bounded adaptation**: about 90% unchanged and 7% adapted at the API/auth/progress boundary. Roughly 3% of existing cross-boundary behavior belongs in Swift. The new role-progress domain is additional product work, not a rewrite of provider/research infrastructure.

### 7. What is the smallest first native vertical slice we can build while exercising the real existing backend?

One authenticated “sync and show latest scorecard” flow:

```text
iOS POST /v1/mobile/players/{player}/sync
  → FastAPI validates identity/rate limit/idempotency
  → existing StratzProvider.fetch_history
  → existing cached deep acquisition for only missing needed matches
  → existing canonical normalization
  → new minimal server role-scorecard calculation
     (eligible mode, assigned role, prior-role baseline excluding current,
      support count/refusal, metric values, PB state)
  → repository saves versioned immutable scorecard
  → status/latest-scorecard endpoint returns typed mobile DTO
  → generated Swift client decodes it
  → SwiftUI renders raw values, baseline comparison, and explicit unavailable state
```

Start with one approved role and the smallest metric set fully supported by existing acquired fields; do not fake unsupported metrics. Use stored/sanitized fixtures for development and tests, then perform separately authorized production-provider validation. Role correction and multi-match progress history come next, not in the first slice.
