# Provider operations

Routing policy and provider semantics are defined in
[PROVIDER-CAPABILITIES-AND-ROUTING](../architecture/PROVIDER-CAPABILITIES-AND-ROUTING.md) and the
ADRs. This page covers operating the adapters that implement them.

## Who does what

| Work | Provider | Code |
|---|---|---|
| Foreground discovery (`significant=0`, Turbo included) | OpenDota history | `tracker/sync.py` |
| Stage-1 summary (all ten players) | OpenDota `GET /matches/{id}` | `tracker/acquisition.py` |
| Replay processing and parsed payload | OpenDota `POST /request/{id}`, `GET /matches/{id}` | `tracker/replay_acquisition.py` |
| Bootstrap, Pro backfill and access-recovery scans | OpenDota history (enumeration only) | `tracker/bootstrap.py`, `tracker/backfill.py` |
| Historical replay-class evidence | STRATZ deep batches (≤ 50 IDs) with OpenDota summary fallback | `tracker/historical.py`, `tracker/historical_summary.py` |
| Population parameters | STRATZ `heroStats` (offline P3 job, validated artifact) | `tracker/population_parameters.py` |

STRATZ is never on the fresh path. A mobile read never reaches any provider; this is
enforced by `tests/tracker/test_architecture_boundaries.py`.

## Admission and accounting

Every provider request goes through `ControlledTransport` and the shared Redis
`ProviderGate`:

- Capacity comes only from named response-header windows (`x-rate-limit-*`). Until a window
  is observed, one shared discovery read per probe interval is admitted and processing waits.
  Observed remaining-only headers are treated as a lower bound, never as the plan ceiling.
- Reads and replay processing use separate lanes. A processing request costs 10 rate units and
  1 billing unit; the two are stored separately in `tracker_provider_calls`.
- A reserve share is held for P2 recovery work. Repeated failures open a shared breaker;
  401/403 or an IP-binding 403 disables the provider until an operator resets it.
- Every call, its units, latency, owning job and response snapshot commit together. The
  operations readout (`/internal/tracker/summary`) attributes calls and units by operation,
  job type and priority, and reports breaker state and P3 pause.

All replicas that share a credential must share `TRACKER_NAMESPACE`; separate namespaces
would double the real request rate.

## STRATZ IP binding

A STRATZ token is bound to the source IP. A request from a second IP, or two concurrent jobs
sharing the token, returns 403 naming different addresses. The adapter single-flights every
STRATZ call through one IPv4 client, treats an IP-binding 403 as a disable (no retry storm),
and records it. Before any live STRATZ call from a developer machine, establish that no
deployed service uses the same token, or use a separate development token. Production needs a
stable static egress IP (see [deployment notes](deployment-notes.md)).

## Budgets and the live call ledger

The implementation goal's budgets and every live call made are recorded in the
[ledger](../architecture/IMPLEMENTATION-LEDGER.md) (provider, operation, purpose, units,
outcome). Do not make provider calls to validate UI, fixtures or presentation.
