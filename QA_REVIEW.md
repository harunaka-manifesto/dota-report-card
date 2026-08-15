# Code and UX QA Review

Reviewed: 2026-08-15  
Scope: Python/FastAPI analysis pipeline, OpenDota transport and caching, insight evaluation, persistence/worker seams, Next.js UI, and automated tests.

## Executive summary

The repository is cleanly separated by responsibility and all current static checks and automated tests pass. However, the report-generation rules have a critical fail-open path: insights that require a practical effect can be published when no effect was computed, including when no cohort exists. The fixture run demonstrates this behavior. The live-request path can also multiply OpenDota traffic through duplicate in-flight jobs, up to 200 sequential match-detail calls per job, and an uncancelled browser polling loop.

Recommended release decision: **do not ship the current insight claims to users until P0 and P1 findings are fixed and regression-tested.**

### Finding count

| Priority | Count | Meaning |
|---|---:|---|
| P0 | 1 | Invalid report conclusions can be published |
| P1 | 8 | Major correctness, API-cost, reliability, or deployment risk |
| P2 | 7 | Material UX, maintainability, or future cost issue |
| P3 | 2 | Lower-impact polish/test gaps |

## P0 — Critical

### QA-001 — Effect gates fail open when an effect cannot be computed

- Category: logic error / user trust
- Evidence: `services/api/app/insights/gates.py:36-44`, `services/api/app/reports/assembly.py:19-53`
- Problem: `PRACTICAL_EFFECT_TOO_SMALL` is checked only when `observation.effect is not None`. Definitions with a non-zero minimum effect therefore pass this gate when the effect is missing. The report then assigns static `strength` or `weakness` categories and presents the item as a “Superpower” or “Work on next” conclusion.
- Reproduction: the fixture analysis completed with no cohort and published 11 insights. Published examples included `adjusted_role_fit`, `economy_to_impact_efficiency`, `hero_role_fit_residual`, `collapse_tail_performance_floor`, `comfort_vs_stretch`, `item_timing_reliability`, and `tower_first_objective_orientation` with `effect.value = null` and `selected_cohort = null`.
- Impact: a raw player metric can be promoted as a positive or negative finding without the comparison/effect required by its definition. This contradicts the product’s fail-closed promise.
- Recommendation: if `minimum_absolute_effect > 0`, suppress when `effect is None` with a reason such as `EFFECT_UNAVAILABLE`. Separately require a valid cohort for cohort-relative families, and derive report placement from the measured direction rather than static category membership.
- Regression test: assert that every published definition with a non-zero effect gate has a non-null effect meeting the threshold; assert that cohort-relative families are suppressed when `context.cohort` is absent.

## P1 — High

### QA-002 — Seven replay insight families calculate the same generic metric

- Category: logic error
- Evidence: `services/api/app/insights/evaluator.py:470-519`, `services/api/app/insights/registry.py:112-121`
- Problem: only `objective_vision_timing`, `teamfight_survival_conversion`, and `early_death_tax` have family-specific calculations. Every other replay family falls into one `else` branch that uses the same mean `impact_score` and the same situation count.
- Affected examples: advantage conversion, deaths while ahead, objective follow-through, power-spike conversion, farm-to-fight pivot, lane-loss recovery, and comeback safety.
- Impact: semantically different cards can publish identical evidence under different labels and actions. The implementation does not measure the behavior named by the insight.
- Recommendation: implement a dedicated calculator per family, or keep that family unregistered/suppressed until its required events and metric exist. Add a registry test proving each replay definition resolves to an explicit calculator.

### QA-003 — Early-death detection can never become true with the current normalized events

- Category: logic error
- Evidence: `services/api/app/features/calculators.py:59-63`, `services/api/app/ingestion/normalize.py:175-206`
- Problem: the feature calculator searches participant events for `event_type == "death"`, but normalization only creates `kill`, `buyback`, and `purchase` participant events. No code creates a `death` event.
- Impact: `early_death` is always `0.0`; `early_death_tax` cannot produce meaningful situations and will remain suppressed or misleading.
- Recommendation: derive deaths from a verified event source (for example objective kill events mapped to the victim), include a normalized death event, and test deaths before/after 600 seconds.

### QA-004 — Duplicate in-flight jobs can multiply OpenDota calls

- Category: inefficient API calls / concurrency
- Evidence: `services/api/app/analysis/service.py:38-63`, `services/api/app/analysis/service.py:119-136`, `services/api/app/storage/repository.py:75-96`
- Problem: reuse checks only completed jobs. Two requests for the same account before completion create separate jobs. Each job may request the profile, history, and every eligible match detail. The process-local cache has no single-flight/request-coalescing mechanism, so overlapping jobs can miss the cache together.
- Worst-case request shape: **1 profile + 1 history + up to 200 match-detail calls per job**, before retry traffic.
- Impact: double-clicks, multiple tabs, or concurrent users requesting one account can duplicate expensive upstream work and accelerate rate limiting.
- Recommendation: atomically reuse queued/running compatible jobs by `(account_id, model_version)`, add per-cache-key request coalescing, and make job creation idempotent.

### QA-005 — Configured analysis concurrency is unused and every job is detached

- Category: inefficient API calls / reliability
- Evidence: `services/api/app/core/config.py:30,54-57`, `services/api/app/analysis/service.py:59-63`
- Problem: `analysis_max_concurrency` is never referenced after configuration. Every accepted request calls `asyncio.create_task` without a semaphore, queue, task tracking, cancellation, or shutdown drain.
- Impact: load can start many 200-match analyses concurrently, overwhelming OpenDota and the API process. Detached tasks can be lost during restart/deploy.
- Recommendation: route production work through the worker queue or a bounded in-process task manager that uses `analysis_max_concurrency`, tracks tasks, and drains/cancels them on shutdown.

### QA-006 — The browser poller can issue requests forever

- Category: inefficient API calls / UI reliability
- Evidence: `apps/web/app/components/analysis-form.tsx:44-59`
- Problem: `for (;;)` polls every 1.2 seconds with no maximum duration, exponential backoff, `AbortController`, component-unmount cleanup, tab-visibility pause, or handling for non-2xx status responses.
- Impact: a stuck/lost job creates unbounded API traffic. Navigating away can leave requests in flight. A 404/500 body is treated like a normal status object and the loop continues unless JSON parsing throws.
- Recommendation: prefer a real SSE stream or use bounded polling with response validation, abort-on-unmount/navigation, visibility awareness, capped exponential backoff, and a user-visible timeout/retry state.

### QA-007 — “Immutable” cache entries ignore configured TTLs

- Category: cache logic error
- Evidence: `services/api/app/opendota/cache.py:30-39`, `services/api/app/opendota/client.py:165-184`
- Problem: expired entries are removed only when `immutable` is false. `get_hero_stats()` and `get_benchmarks()` set both `cache_ttl=3600` and `immutable=True`, so they never expire.
- Impact: hero statistics and benchmarks remain stale for the lifetime of the process despite the apparent one-hour policy.
- Recommendation: make expiry independent of immutability; use `ttl=None` to express permanent entries. Add clock-controlled tests for expiring and permanent values.

### QA-008 — Runtime still uses process-local storage despite database/worker scaffolding

- Category: correctness / deployment reliability
- Evidence: `services/api/app/main.py:21-40`, `services/api/app/storage/repository.py:65-72`, `services/api/app/workers/tasks.py:21-28`
- Problem: the app always constructs `InMemoryRepository`. PostgreSQL models and Alembic exist but are not connected to the analysis service. Celery expects a process-global configured service, yet `create_app()` never calls `configure_service()` and a separate worker cannot share the API process’s in-memory jobs.
- Impact: reports and job state disappear on restart; multi-worker API instances return inconsistent 404s; the included Celery task cannot find API-created jobs in a real separate worker.
- Recommendation: implement a persistent repository and dependency-select it by environment. Enqueue a durable job containing stable identifiers; have workers load/update job state from the database.

### QA-009 — Production browser origins are rejected by hard-coded CORS

- Category: deployment bug / UX
- Evidence: `services/api/app/main.py:49-54`, `apps/web/app/components/analysis-form.tsx:6`
- Problem: the browser can be configured to call a separate API through `NEXT_PUBLIC_API_BASE_URL`, but the API allows only localhost origins.
- Impact: a separately hosted production frontend fails at the browser’s CORS boundary even when both services are healthy.
- Recommendation: configure an explicit environment-specific allowlist and test the intended production web origin. If web and API are same-origin through a reverse proxy, use relative browser URLs.

## P2 — Medium

### QA-010 — Progress SSE endpoint is a snapshot, not a stream

- Category: API logic / UX / inefficient calls
- Evidence: `services/api/app/api/routes.py:52-63`
- Problem: the endpoint iterates events that already exist, emits `event: end`, and closes. It never waits for later job events. Although clients receive an `events_url`, the endpoint cannot provide live progress; the web app ignores it and polls instead.
- Impact: the advertised streaming path is misleading and cannot replace repeated polling.
- Recommendation: implement a proper subscription/queue with heartbeat and disconnect handling, or remove the SSE contract until it is live.

### QA-011 — Configurable thresholds are applied inconsistently

- Category: logic error
- Evidence: `services/api/app/core/config.py:27,32`, `services/api/app/insights/gates.py:34`, `services/api/app/insights/registry.py:71`, `services/api/app/reports/assembly.py:98-116`
- Problem: role gating hard-codes `0.60` instead of using `role_confidence_threshold`. Replay definitions hard-code `0.60`, while the report status uses `replay_coverage_threshold`. Missing-family display also hard-codes `0.60`.
- Impact: after configuration changes, a card may publish while the report says evidence is unavailable, or the displayed role status can disagree with the publication gate.
- Recommendation: pass effective thresholds into the gate and use one source of truth for publication and display.

### QA-012 — Cohort selection depends on input ordering

- Category: logic error
- Evidence: `services/api/app/analysis/service.py:195-201`
- Problem: `_select_cohort()` uses `features[-1]` without sorting. If OpenDota returns newest-first history (the usual shape), this selects dimensions from the oldest hydrated match, not the current/latest player state.
- Impact: cohort patch, rank, hero, and role can be anchored to the wrong match; any reordering changes conclusions.
- Recommendation: select explicitly by maximum `start_time` (with a deterministic fallback) or derive cohort dimensions from a documented recent-window policy.

### QA-013 — Failure responses discard the actionable message

- Category: UI/UX error
- Evidence: `services/api/app/storage/repository.py:113-120`, `services/api/app/api/schemas.py:20-32`, `apps/web/app/components/analysis-form.tsx:52-54`
- Problem: the repository stores `failure_detail`, but `AnalysisJob.as_dict()` and `AnalysisStatusResponse` omit it. The UI shows only an internal code such as `PROFILE_PRIVATE_OR_UNAVAILABLE`.
- Impact: users receive technical codes rather than guidance on privacy, invalid history, or upstream availability.
- Recommendation: expose a safe `message`, map codes to user-centered copy, and provide an obvious retry/edit action.

### QA-014 — The form is prefilled with another player’s ID

- Category: UI/UX / avoidable API calls
- Evidence: `apps/web/app/components/analysis-form.tsx:19`
- Problem: the default state is `193875165`, not an empty value. A user can submit the demo account accidentally, and the required-field validation no longer protects against an omitted identifier.
- Impact: confusing reports and unnecessary analysis/OpenDota calls.
- Recommendation: leave the field empty; put the sample in placeholder/help text and provide a clearly labeled “View demo report” path that does not trigger a fresh analysis.

### QA-015 — Report UI does not expose the audit trail promised on the home page

- Category: UI/UX error
- Evidence: `apps/web/app/page.tsx:18-21`, `services/api/app/reports/assembly.py:133-149`, `apps/web/app/report/[reportId]/page.tsx:104-122`
- Problem: cards contain source match IDs, player/cohort metrics, and provenance, but the UI renders only counts, coverage, action, and limitations. There is no evidence/details link.
- Impact: users cannot audit the claim even though “Every card keeps its denominator, source matches, cohort, and limitations” is a core promise.
- Recommendation: add an accessible evidence disclosure showing player and cohort values, source matches linked to OpenDota, confidence rationale, and provenance.

### QA-016 — Report fetch errors fall through to a generic server error

- Category: UI/UX error
- Evidence: `apps/web/app/report/[reportId]/page.tsx:42-49`
- Problem: every non-2xx response throws `Error("Report not found")`; there is no route-level `not-found.tsx`/`error.tsx`, retry action, or distinction between 404 and temporary API failure.
- Impact: expired in-memory reports and transient API failures produce a generic Next.js error experience.
- Recommendation: call `notFound()` for 404, add an error boundary with retry for 5xx/network failures, and explain when a report expired.

## P3 — Low

### QA-017 — OpenDota HTTP client has no application shutdown lifecycle

- Category: resource management
- Evidence: `services/api/app/opendota/client.py:44-52,73-75`, `services/api/app/main.py:30-35`
- Problem: live mode creates a long-lived `httpx.AsyncClient` lazily, but the FastAPI app never enters the client context or closes it during lifespan shutdown.
- Impact: development reloads/tests can report unclosed transports; graceful resource cleanup is not guaranteed.
- Recommendation: create/close the client in FastAPI lifespan and inject it into the service.

### QA-018 — UX automation covers only two elements on the home page

- Category: test gap
- Evidence: `apps/web/tests/e2e/home.spec.ts:1-7`
- Problem: there is no automated coverage for submit, progress, completion redirect, failures, cancellation, mobile layout, report empty states, accessibility announcements, or report-not-found handling.
- Recommendation: mock the API and add end-to-end scenarios for completed, failed, stalled, non-2xx, and mobile flows. Add an accessibility pass with status/error regions announced via `aria-live` or `role="alert"`.

## Additional API-cost notes

- `PublicMatchCollector` declares `batch_size` and `max_requests_per_minute`, but `collect_page()` does not enforce either (`services/api/app/cohorts/collector.py:7-31`). This is not currently wired into the report path, but it will become a quota bug when cohort collection is enabled.
- `persist_raw_payload()` scans the entire in-memory payload list for every insert (`services/api/app/storage/repository.py:139-156`). A 200-match job therefore performs a growing linear deduplication scan; use an indexed key/hash in persistent storage.
- The report page opts into `force-dynamic` and `cache: "no-store"` (`apps/web/app/report/[reportId]/page.tsx:3,42-45`), so every navigation/refresh calls the API. This is defensible for mutable reports, but completed reports appear immutable and could use safe revalidation or an application cache.

## Verification performed

| Check | Result |
|---|---|
| Python tests (`make test`) | 22 passed, 2 skipped; 1 Starlette/httpx deprecation warning |
| Python lint (`ruff`) | Passed |
| Python typing (`mypy`) | Passed |
| Next.js lint | Passed |
| TypeScript (`tsc --noEmit`) | Passed |
| Next.js production build | Passed |
| Existing browser tests | Only home-label/button visibility is covered |
| Graph structure | 525 nodes, 1,123 built edges, 42 communities |

Graph health note: extraction reported 119 dangling-endpoint edges and 119 undirected endpoint-collapsed edges. The graph was used as a navigation aid, while every finding above was verified directly against source and/or runtime output.

## Suggested fix order

1. Close the effect/cohort gate and add regression invariants (QA-001).
2. Disable or implement replay families whose named metric is not calculated (QA-002, QA-003).
3. Add in-flight job idempotency and bounded durable execution (QA-004, QA-005, QA-008).
4. Replace unbounded polling with a reliable progress mechanism (QA-006, QA-010).
5. Correct cache expiration, thresholds, and latest-match cohort selection (QA-007, QA-011, QA-012).
6. Repair production CORS and the user-facing failure/evidence flows (QA-009, QA-013 through QA-016).
