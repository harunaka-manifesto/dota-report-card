# Graph Report - dota-report-card  (2026-08-15)

## Corpus Check
- Corpus is ~21,826 words - fits in a single context window. You may not need a graph.

## Summary
- 525 nodes · 1123 edges · 42 communities (28 shown, 14 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 136 edges (avg confidence: 0.54)
- Token cost: 10,800 input · 6,900 output

## Community Hubs (Navigation)
- Insight Statistics
- Rate Limiting Cache
- Feature Calculation
- Web Dependencies
- Cohort Aggregation
- TypeScript Configuration
- API Routes Schemas
- Runtime Configuration
- Database Migrations
- Evidence Models Ranking
- Analysis Data Sources
- System Architecture Docs
- OpenDota Client
- Insight Design Docs
- Application Errors
- Analysis Orchestration
- Match Eligibility
- Logging Security
- API App Tests
- Analysis Form UX
- Report Page UI
- Public Match Collection
- API Client Package
- Generated API Client
- Web Layout Metadata
- ESLint Configuration
- OpenDota Schemas
- Next Build Config
- Next Type Stubs
- Migration Package
- OpenAPI Metadata
- Analysis Package
- API Package
- Core Package
- Ingestion Package
- Application Package
- Worker Integration
- Project Root

## God Nodes (most connected - your core abstractions)
1. `MatchFeature` - 37 edges
2. `InsightContext` - 31 edges
3. `OpenDotaClient` - 26 edges
4. `Settings` - 24 edges
5. `AnalysisService` - 23 edges
6. `InMemoryRepository` - 23 edges
7. `MetricObservation` - 22 edges
8. `_observation()` - 18 edges
9. `create_app()` - 18 edges
10. `EvidenceObject` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Catalogued MVP-B Replay Families` --semantically_similar_to--> `MVP-B Replay-Dependent Insight Families`  [INFERRED] [semantically similar]
  docs/insight-catalog.md → PLAN.md
- `Dota Report Card` --semantically_similar_to--> `OpenDota Insight System`  [INFERRED] [semantically similar]
  README.md → PLAN.md
- `Catalogued MVP-A Summary Families` --semantically_similar_to--> `MVP-A Summary Insight Families`  [INFERRED] [semantically similar]
  docs/insight-catalog.md → PLAN.md
- `Evidence Contract` --semantically_similar_to--> `Evidence Object`  [INFERRED] [semantically similar]
  docs/evidence-contract.md → PLAN.md
- `Published Card as Evidence Projection` --semantically_similar_to--> `Evidence-Backed Report UI`  [INFERRED] [semantically similar]
  docs/evidence-contract.md → PLAN.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Analysis-to-Evidence Pipeline** — plan_opendota_integration, plan_eligible_match_corpus, plan_parse_coverage_ledger, plan_role_inference, plan_cohort_fallback_system, plan_insight_registry, plan_publication_gates, plan_evidence_object, plan_report_ui [EXTRACTED 1.00]
- **22-Family MVP Insight Program** — plan_insight_registry, plan_mvp_a_summary_families, plan_mvp_b_replay_families, plan_publication_gates, plan_insight_value_score [EXTRACTED 1.00]
- **Local Containerized Application Stack** — infra_compose_api_service, infra_compose_web_service, infra_compose_postgres_service, infra_compose_redis_service [EXTRACTED 1.00]

## Communities (42 total, 14 thin omitted)

### Community 0 - "Insight Statistics"
Cohesion: 0.16
Nodes (39): normal_interval(), wilson_interval(), MatchFeature, Any, _base(), _cohort_metric(), _collapse_tail(), _comfort_vs_stretch() (+31 more)

### Community 1 - "Rate Limiting Cache"
Cohesion: 0.08
Nodes (14): datetime, RateLimiter, Small process-local limiter; production can replace it with Redis counters., CacheEntry, MemoryCache, payload_hash(), Any, Small local cache with the same semantics used by the production adapter. (+6 more)

### Community 2 - "Feature Calculation"
Cohesion: 0.14
Nodes (24): calculate_match_feature(), calculate_match_features(), Reusable match and player feature calculators., _economy_rank(), _economy_score(), infer_role(), RoleInference, coverage_for_match() (+16 more)

### Community 3 - "Web Dependencies"
Cohesion: 0.06
Nodes (30): dependencies, next, react, react-dom, devDependencies, eslint, eslint-config-next, @playwright/test (+22 more)

### Community 4 - "Cohort Aggregation"
Cohesion: 0.13
Nodes (16): aggregate_by_dimensions(), CohortAggregate, Any, Cohort selection and aggregation., aggregate_metrics(), _as_mapping(), CohortSelection, _impact() (+8 more)

### Community 5 - "TypeScript Configuration"
Cohesion: 0.08
Nodes (25): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+17 more)

### Community 6 - "API Routes Schemas"
Cohesion: 0.19
Nodes (23): BaseModel, CreateAnalysisRequest, CreateAnalysisResponse, get, post, Request, analysis_events(), create_analysis() (+15 more)

### Community 7 - "Runtime Configuration"
Cohesion: 0.14
Nodes (14): AsyncClient, asyncio, Engine, get_settings(), Path, Settings, create_database_engine(), create_session_factory() (+6 more)

### Community 8 - "Database Migrations"
Cohesion: 0.14
Nodes (17): DeclarativeBase, AnalysisJobRecord, Base, CohortAggregateRecord, ConstantSnapshotRecord, DerivedFeatureRecord, EvidenceObjectRecord, MatchEventRecord (+9 more)

### Community 9 - "Evidence Models Ranking"
Cohesion: 0.21
Nodes (16): EvidenceObject, Any, rank_evidence(), _format_value(), render_action(), render_statement(), assemble_report(), _card() (+8 more)

### Community 10 - "Analysis Data Sources"
Cohesion: 0.16
Nodes (9): Protocol, AnalysisSource, FixtureOpenDotaSource, MappingSource, Any, Path, Recorded source adapter used by tests and the local demo., Tiny injected source for unit and contract tests. (+1 more)

### Community 11 - "System Architecture Docs"
Cohesion: 0.12
Nodes (21): Evidence Contract, Provenance Map, Published Card as Evidence Projection, OpenDota Insight System Implementation Reference, API Service, Dota PostgreSQL Persistent Volume, PostgreSQL Service, Redis Service (+13 more)

### Community 12 - "OpenDota Client"
Cohesion: 0.18
Nodes (6): OpenDotaClient, Any, Authenticated server-side OpenDota client. The API key is deliberately only…, OpenDota transport adapters and source schemas., test_api_key_is_sent_only_as_a_bearer_header(), test_transport_has_no_replay_parse_method()

### Community 13 - "Insight Design Docs"
Cohesion: 0.13
Nodes (19): Deferred Insight Features, Insight Catalog, Catalogued MVP-A Summary Families, Catalogued MVP-B Replay Families, Behavioral-Vector Archetype Clustering, Cohort Fallback System, Eligible Match Corpus, Fail-Closed Insight Publication (+11 more)

### Community 14 - "Application Errors"
Cohesion: 0.18
Nodes (13): Exception, parametrize, AnalysisRateLimited, AppError, InvalidPlayerIdentifier, OpenDotaRateLimited, OpenDotaUnavailable, Stable client-facing domain error. (+5 more)

### Community 15 - "Analysis Orchestration"
Cohesion: 0.23
Nodes (12): AnalysisService, _normalized_record(), _profile_account_id(), _profile_for_report(), Any, _select_cohort(), InsufficientMatchHistory, parse_player_identifier() (+4 more)

### Community 16 - "Match Eligibility"
Cohesion: 0.31
Nodes (11): _as_int(), assess_match(), EligibilityResult, ExclusionReason, Any, _target_player(), StrEnum, base_match() (+3 more)

### Community 17 - "Logging Security"
Cohesion: 0.21
Nodes (9): FastAPI, LogRecord, configure_logging(), log_fields(), Any, SecretRedactionFilter, Any, Recursively remove known credentials from logs and exception payloads. (+1 more)

### Community 18 - "API App Tests"
Cohesion: 0.31
Nodes (7): main(), create_app(), Any, test_create_analysis_returns_job_contract(), test_health_contract(), test_malformed_identifier_is_rejected_before_source_request(), test_private_profile_returns_stable_empty_state()

### Community 19 - "Analysis Form UX"
Cohesion: 0.38
Nodes (4): AnalysisForm(), poll(), submit(), AnalysisStatus

### Community 20 - "Report Page UI"
Cohesion: 0.33
Nodes (5): Card, dynamic, getReport(), Report, ReportPage()

### Community 21 - "Public Match Collection"
Cohesion: 0.38
Nodes (4): CollectorPolicy, PublicMatchCollector, Any, Quota-aware boundary for future warehouse population. The collector…

### Community 22 - "API Client Package"
Cohesion: 0.33
Nodes (5): main, name, private, types, version

### Community 23 - "Generated API Client"
Cohesion: 0.40
Nodes (3): AnalysisStatus, CreateAnalysisRequest, CreateAnalysisResponse

## Knowledge Gaps
- **62 isolated node(s):** `next/core-web-vitals`, `AnalysisStatus`, `metadata`, `dynamic`, `Card` (+57 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MatchFeature` connect `Insight Statistics` to `Feature Calculation`, `Cohort Aggregation`, `Runtime Configuration`, `Analysis Orchestration`, `Logging Security`, `API App Tests`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `OpenDotaClient` connect `OpenDota Client` to `Rate Limiting Cache`, `Runtime Configuration`, `Analysis Data Sources`, `Application Errors`, `Logging Security`, `API App Tests`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `InMemoryRepository` connect `Rate Limiting Cache` to `Logging Security`, `API App Tests`, `Runtime Configuration`, `Analysis Orchestration`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 27 inferred relationships involving `MatchFeature` (e.g. with `AnalysisService` and `_select_cohort()`) actually correct?**
  _`MatchFeature` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `InsightContext` (e.g. with `AnalysisService` and `CohortSelection`) actually correct?**
  _`InsightContext` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `OpenDotaClient` (e.g. with `create_app()` and `Settings`) actually correct?**
  _`OpenDotaClient` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Settings` (e.g. with `AnalysisService` and `create_app()`) actually correct?**
  _`Settings` has 14 INFERRED edges - model-reasoned connections that need verification._