# Dota Tracker — V1 Product Documentation

This folder is the **active product documentation** for Dota Tracker V1 (native iOS).

It is organised by **product feature**. Start with the feature SSOT and design requirements, then follow any linked technical annexes. You should not have to read research history to design or build a screen.

---

## How to use this

| You want to… | Open |
|---|---|
| Design a screen | that feature's `DESIGN-REQUIREMENTS.md` |
| Know the exact product rule behind something | that feature's `SSOT.md` |
| Know a rule that applies everywhere | [`app_foundation/SSOT.md`](app_foundation/SSOT.md) |
| Know **how the system behaves** — data, providers, readiness, storage, scale | [`architecture/README.md`](architecture/README.md) |
| Know what data a screen needs before it can render | [`architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md`](architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md) |
| Understand *why* a decision was made | [`architecture/decisions/`](architecture/decisions/) for architecture · [`_archive/`](_archive/) for product |
| Run, test or operate the backend | [`operations/README.md`](operations/README.md) · [mobile API](api/README.md) · [implementation ledger](architecture/IMPLEMENTATION-LEDGER.md) |

Every feature has an `SSOT.md` and `DESIGN-REQUIREMENTS.md`. A feature may also link a narrowly scoped technical annex when an algorithm or data contract needs more detail; there are no "final-v2", "latest" or "research" documents beside active feature truth.

`architecture/` is the one non-feature folder. It answers *how the system behaves*, where the feature folders answer *what the product means*. Start at its [`README.md`](architecture/README.md).

---

## Feature map

| Feature | One sentence | SSOT | Design Requirements |
|---|---|---|---|
| **App Foundation** | The cross-product semantics every surface inherits: identity, match lifecycle, roles, metrics, baselines, context-adjusted expectation, trend, Personal Bests, Free/Pro, rebuild and versioning. | [SSOT](app_foundation/SSOT.md) | [Design](app_foundation/DESIGN-REQUIREMENTS.md) |
| **Onboarding & Cold Start** | Getting a player from first launch to a linked, tracking account — and keeping a nearly-empty app honest while history arrives. | [SSOT](onboarding/SSOT.md) | [Design](onboarding/DESIGN-REQUIREMENTS.md) |
| **Home** | The daily check-in and routing hub: today's matches or today's focus, a challenge slot, the four role progression summaries, and the last five matches. | [SSOT](home/SSOT.md) | [Design](home/DESIGN-REQUIREMENTS.md) |
| **History** | The complete chronological record of what has been played, built for scanning and navigating into individual matches. | [SSOT](history/SSOT.md) | [Design](history/DESIGN-REQUIREMENTS.md) |
| **Match Detail** | One match reviewed properly: personal performance against a fair expectation, matchup context, factual key-item timings, and 0–3 deterministic insight cards — kept strictly apart. The [item-timings backend contract](match_detail/ITEM-TIMINGS-V1.md) is ready; iOS rendering is pending. | [SSOT](match_detail/SSOT.md) | [Design](match_detail/DESIGN-REQUIREMENTS.md) |
| **Progress** | Per-role, per-mode, per-metric progression: observation series, rolling baselines, trend states and Personal Bests. | [SSOT](progress/SSOT.md) | [Design](progress/DESIGN-REQUIREMENTS.md) |
| **Profile** | Who the player is over the long term: identity line, role map, hero identity, durable claims with receipts, and what's moving right now. | [SSOT](profile/SSOT.md) | [Design](profile/DESIGN-REQUIREMENTS.md) |
| **Settings, Account & Subscription** | Ongoing account management: auth methods, Steam switching, data-access recovery, subscription lifecycle, notifications and deletion. | [SSOT](settings_account/SSOT.md) | [Design](settings_account/DESIGN-REQUIREMENTS.md) |

### Architecture

| Area | One sentence | Entry point |
|---|---|---|
| **Architecture** | How match data is acquired, stored, enriched, analysed and delivered — and the rules that keep that shape stable while providers, scale and monetisation change. | [`architecture/README.md`](architecture/README.md) |

Read it before changing ingestion, analysis, Match Lifecycle, Home, History, Match Detail, Profile, Progress, role resolution, social/following, or subscription behaviour. It carries a short **rules-for-agents** section that is worth reading in full.

### Not a feature folder

**Challenges / Achievements** have no locked V1 contract. Home reserves a Challenge slot by owner direction, but no challenge mechanics, eligibility, progress model or reward model exists in any document here. A folder was deliberately **not** created, because doing so would manufacture a contract that does not exist. See [`home/SSOT.md` §5](home/SSOT.md).

---

## Authority rule

When two documents disagree, resolve in this order:

1. **Owner decisions** recorded in a feature SSOT's owner-direction section.
2. **`app_foundation/SSOT.md`** — the single authoritative definition of every cross-product rule.
3. The relevant **feature `SSOT.md`**.
4. The feature's **`DESIGN-REQUIREMENTS.md`** (a projection of its SSOT — never an independent source of truth).
5. Anything in **`_archive/`** — evidence only, never active product truth.

**`architecture/` is not in that ladder**, because it answers a different question. On *product meaning* the SSOTs win; on *system behaviour* the architecture documents win. If architecture appears to make a locked product rule technically impossible, do not silently pick one — see [`architecture/README.md`](architecture/README.md) §5.

A feature SSOT may **summarise** a foundation rule for readability and link to it. It may **never** define a competing version. If it does, that is a defect: fix it, don't pick one silently.

Design Requirements are derived from the SSOT. Every content item, state and flow in a design brief traces to its feature SSOT, to explicit owner direction, or to a clearly labelled open question.

### One deliberate exception

Two archived documents remain **engineering-normative for algorithms only**:

- [`_archive/engine_specs/POST-MATCH-INSIGHTS-SSOT.md`](_archive/engine_specs/POST-MATCH-INSIGHTS-SSOT.md) — the insight-card engine: card specifications, thresholds, severity ladders, the match-shape classifier, ranking, and the machine-readable contract.
- [`_archive/engine_specs/CONTEXT-ADJUSTED-PERFORMANCE-V1.md`](_archive/engine_specs/CONTEXT-ADJUSTED-PERFORMANCE-V1.md) — the context-adjustment parameter derivation, coefficients, caps and validation evidence.

They live in `_archive/` because a designer never needs them and because their product meaning is fully captured in [`match_detail/SSOT.md`](match_detail/SSOT.md) and [`app_foundation/SSOT.md`](app_foundation/SSOT.md) §10. **Those two active documents win on product meaning; the annexes win on algorithmic detail.**

---

## Where the history lives

Architecture rationale lives in [`architecture/decisions/`](architecture/decisions/) (immutable ADRs) and architecture evidence in [`architecture/evidence/`](architecture/evidence/). Product history lives here:

```text
_archive/
├── superseded_ssots/   the seven original V1 SSOTs, consolidated into the feature folders
├── engine_specs/       insight engine + context-adjustment algorithmic annexes (see above)
├── decision_history/   how owner calls were reached
├── research/           feasibility studies, deep research, architecture audit
├── validation/         validation reports and audits with their evidence
├── generated_data/     JSON/CSV/HTML outputs and the research code that produced them
└── scripts/            standalone research code
```

See [`_archive/README.md`](_archive/README.md) for what each document is and which active document replaced it.

> ⚠️ **`_archive/` is evidence and history, not active product truth.**
>
> Everything in it is superseded, non-normative, or exploratory — with the single, explicitly scoped exception of the two `engine_specs/` annexes above. Numbers, candidate tables, thresholds and open questions in archived documents are **not** the current product. Do not implement from them, do not design from them, and do not cite them to overrule an active SSOT. Use them to trace *why* a decision was made.

---

## What V1 does not promise

Stated once, here, because it constrains everything:

The app is **not** promising "this will make you win." It helps players improve and understand the parts of Dota reasonably under their control. **Personal performance is distinct from match outcome.** MMR, win/loss and universal composite scores are never the definition of progression.
