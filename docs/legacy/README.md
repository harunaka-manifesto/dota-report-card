# Live legacy product and historical material

Dota Tracker is the current product. Its [SSOTs and architecture](../tracker/README.md) define new work.
The report-card frontend and API remain live and must retain persisted-report compatibility.
The [agent contract](../../AGENTS.md) and [production safety rules](../agent/production-safety.md) still apply.

| Boundary | Disposition and reason |
|---|---|
| `apps/web/`, legacy `/v1` API | Keep production paths; preserve report rendering and API contracts. |
| `migrations/`, `infra/runtime-artifacts/`, Dockerfiles | Keep deployment-coupled paths and frozen release identity. |
| `docs/architecture/`, `docs/product/`, `docs/qa/`, `docs/ui-revamp/`, `docs/prompts/` | Report-era references, fenced in place so tooling and historical links survive. User-owned untracked prompts remain untouched. |
| `docs/progression/` | Superseded by Tracker App Foundation; retain historical text. |
| `docs/decisions/` | Legacy ADR namespace, separate from `docs/tracker/architecture/decisions/`. |
| `graphify-out/` | Generated legacy knowledge graph, non-authoritative for tracker work. |
| `api.json` | OpenDota vendor OpenAPI, not the application API contract. |
| `dota-news-scraper/` | Unrelated tool; not a tracker backend dependency. |
| `output/` | Generated historical artifacts, not product truth. |
| `V7 Master Experience Plan v1.md`, `tone_of_voice.md` | Legacy experience/voice references, not the tracker contract. |
| `.local/`, `.env`, `apps/web/.local` | Private local data; protected and never moved or cleaned by this goal. |

Runtime research imports must be inventoried and tested before any code relocation. See the
[implementation ledger](../tracker/architecture/IMPLEMENTATION-LEDGER.md) for actual progress.
