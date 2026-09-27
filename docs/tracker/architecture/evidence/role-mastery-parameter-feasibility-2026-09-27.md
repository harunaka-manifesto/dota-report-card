# Role Mastery context parameter feasibility — 2026-09-27

**Decision: keep public Role Mastery gated.** Eight-week population acquisition and opponent coverage succeeded. The available independent replay does not yet support a complete, owner-approved 16-metric context parameter artifact. This study publishes no parameter set or awards.

## Acquisition and provenance

- The pre-existing private STRATZ corpus had tracked-player histories and deep responses, but no retained `heroStats.stats` or `heroStats.laneOutcome` population aggregate for the required window.
- With owner authorization, the offline collector requested eight full STRATZ weeks, **2026-07-30 through 2026-09-24 UTC** (weeks 2952–2959): 10- and 20-minute `stats` for five positions and opponent `laneOutcome` for 127 heroes in each core position. Requests used the tracker `ControlledTransport` and `ProviderGate` against local PostgreSQL/Redis. The local audit records **160 collection plus 8 exploratory STRATZ calls, all HTTP 200, no recorded failures**. OpenDota calls: **0**. No production service or flag changed.
- The 160 aggregate responses and SHA-256 manifest are retained only at `.local/tracker-context-calibration-2026-09-27/` in the primary checkout. Manifest SHA-256: `d0fdef3c96fb7ca3b23867c9c8bd132cddf35ba75c94079d1f23cda9caf4ff0f`. No player identifiers or raw responses are committed.
- STRATZ accepts a Unix timestamp for the `week` input and returns the week number in each row. The `laneOutcome.position` response reported `POSITION_1` even when a P2/P3 filter materially changed cohort counts. The requested filter was retained as the cohort key; every row's week and own hero ID was checked. Sampled summed pair counts were about twice `stats` match counts at P1/P3 and equal at P2, consistent with 2v2 and 1v1 lanes. The response-position discrepancy needs a provider regression check before publication.

## Population and independent coverage

| Measure | Result |
|---|---:|
| Hero-position checkpoint cells | 635/635 (127 heroes × 5 positions) |
| Hero-position cells meeting the ≥300-match gate | 635/635 |
| Weekly opponent pair rows | 367,587 |
| Eight-week pooled opponent pairs | 47,894 |
| Opponent effects after 3,000/20/500-match gates | 127/127 in each of P1, P2 and P3 |
| Independent recent Standard drafts with valid core lane shape | 4,937 |
| Drafts with all lane opponents covered | Carry 1,657/1,657; Mid 2,060/2,060; Offlane 1,220/1,220 |

The independent drafts came from the private V7 tracked-player replay corpus, not the STRATZ aggregate pool. Observed 100% coverage clears the 97% gate **for this sample**; the sample is concentrated in tracked accounts, so it is not proof of launch-cohort representativeness.

## Slope check

The engineering reference slopes are Carry **0.748**, Mid **0.778**, Offlane **0.722**. A direct regression of raw CS on the opponent score confounds player and hero mix. This diagnostic instead uses each player's 20 prior same-role Standard matches (at least five), subtracts median CS and the own-hero population-level change, then regresses that residual on the current opponent score minus its prior median. It mirrors the runtime window-relative adjustment, but does **not** replace the independent per-opponent partial-effect regression used to lock the reference slopes. The repository has no owner-approved maximum drift bound.

| Role | Recent observations | Estimated slope | Approximate 95% interval | Full retained-year slope (observations) |
|---|---:|---:|---:|---:|
| Carry | 1,627 | 0.813 | 0.629–0.997 | 0.838 (7,141) |
| Mid | 1,977 | 0.768 | 0.640–0.896 | 0.851 (7,923) |
| Offlane | 1,197 | 0.990 | 0.781–1.199 | 0.767 (5,649) |

Intervals use an independent-observation standard error and do not account for repeated accounts; they are not a release gate. Recent Offlane is materially above the frozen reference while full-year Offlane is closer. The owner must approve the regression method, drift bound and any changed slope before artifact validation. More aggregate calls cannot settle that choice.

## Metric parameter gap

The builder requires finite `sigma_pop`, `tau`, `floor` and `floor_tolerance` for **all 16 active** tracker metrics (four per role). Running the tracker's normalization, replay and metric functions on 7,435 recent Standard viewer rows yielded usable *provisional* distributions for 12 active metrics. Four lack a usable scale:

| Metric | Valid measurements | Main reason |
|---|---:|---|
| `mid.early_fight_presence.v1` | 0/2,048 | Other players' event streams absent |
| `mid.lane_net_worth_advantage_at_10.v1` | 0/2,048 | Opposing player's checkpoint absent |
| `offlane.lane_net_worth_advantage_at_10.v1` | 0/1,277 | Opposing player's checkpoint absent |
| `offlane.objective_involvement.v1` | 0/1,277 | Tower-damage report absent |

The private parsed OpenDota corpus has 960 Standard matches with ten players. Under the tracker's existing evidence translation, tested lane net-worth comparisons still yielded zero valid measurements. The 12 provisional distributions come from a tracked-player cohort, not an approved population sample. STRATZ `stats` supplies useful checkpoint means for active metrics. The acquired aggregate fields cannot establish damage-share and event hero levels. The four retired metrics are excluded from this release assessment.

`tau = 0.35` is the V1 engineering default, not an approved binding for every metric. Per-metric floor tolerances and representative population scales are also unapproved. Arbitrary positive placeholders for scored metrics would pass shape checks while changing `ABOVE`/`BELOW` states and mastery bonuses. Offlane Objective Involvement is diagnostic-only, but the current artifact contract still requires its parameter entry. The release gate remains closed.

## Owner decision and next data work

Approve a documented 16-metric calibration protocol and resulting versioned artifact: representative source/cohort for each active metric scale and hero level, per-metric `tau` and floor tolerance, independent opponent partial-effect regression, and its maximum permitted slope drift. Missing replay fields may require a separately scoped ten-player sample after that protocol is chosen. Once approved, register the artifact and backfill mastery from retained data without provider calls. Public enablement and deployment still require an explicit owner request.
