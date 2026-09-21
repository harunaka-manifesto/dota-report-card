# ADR 0005: The post-match analysis pipeline is deterministic; no runtime LLM

Date: 2026-09-20
Status: **Accepted**
Binds: [`../SYSTEM-ARCHITECTURE.md`](../SYSTEM-ARCHITECTURE.md) §7 · [`../DATA-CONTRACTS-AND-VERSIONING.md`](../DATA-CONTRACTS-AND-VERSIONING.md) §7

## Context

This decision records, at the architecture level, a constraint the product had already locked in several places — because it is an *architectural* constraint, and recording it only as product copy leaves it easy to violate by accident.

The product requires:

- **Reproducibility.** A historical result must be explainable from its source data, its feature-extraction version, its analysis version and its baseline version ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §14).
- **Retroactive methodology changes.** When a baseline definition changes, it applies to the whole history rather than leaving a seam. That requires replaying stored inputs and getting the same answer for the same inputs.
- **No opaque verdicts.** The product forbids composite scores, grades and "opaque AI verdicts" ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §2.1, §16).
- **Bounded claims with receipts.** Every Profile claim must be able to produce its evidence panel, and every insight card must trace to observed facts within stated sample gates ([`../../profile/SSOT.md`](../../profile/SSOT.md) §2.5, [`../../match_detail/SSOT.md`](../../match_detail/SSOT.md) §5.5–§5.6).
- **Explicit rejection of generative analysis.** "No LLM analyses any production match" ([`../../match_detail/SSOT.md`](../../match_detail/SSOT.md) §5.1); "no ML and no LLM run at any time" in the context model ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §10.1); "an LLM that reads a year of matches and writes who the player is" is listed as rejected content ([`../../profile/SSOT.md`](../../profile/SSOT.md) §10).

A non-deterministic component anywhere in the runtime path breaks all of these at once. A retroactive rebuild would produce different output from identical inputs, which means a user's history would silently change on every recompute, and no result could be explained from its recorded versions.

The provider architecture does not change this — but it does make the boundary worth stating precisely, because the provider layer is now explicitly an **evidence** layer and it would be easy for a future agent to read "the analysis connects evidence into findings" as an invitation to generate that connection.

## Decision

1. **The provider layer supplies evidence. The deterministic analysis system connects that evidence into findings.** These are different responsibilities and the boundary between them is load-bearing.

2. **No LLM runs in the runtime post-match pipeline.** Not for analysis, not for feature extraction, not for candidate selection, not for ranking, not for copy generation at request time.

3. **No model is fitted at runtime.** Population parameters are read from versioned, cached reference snapshots ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §10.1).

4. **Identical inputs and identical versions MUST produce identical output.** This is checkable via the inputs digest ([`../DATA-CONTRACTS-AND-VERSIONING.md`](../DATA-CONTRACTS-AND-VERSIONING.md) §7.1), not merely asserted.

5. **Every user-visible finding traces to structured inputs and a recorded version triple** — `feature_version`, `analysis_version`, `baseline_version`.

6. **Copy and insight rules are structured-input rules**, versioned and auditable — not generated prose. Semantic templates are part of the versioned contract.

7. **This does not prohibit LLM use outside the runtime pipeline.** Research, evidence analysis, documentation, calibration exploration, tooling and this repository's own agent-assisted workflow are unaffected. The boundary is the **runtime post-match pipeline**, and anything whose output reaches a user as a finding.

## Consequences

**Accepted costs**

- Insight coverage is bounded by what deterministic rules can defensibly say. The product already accepts this: roughly 57–61% of eligible viewpoints show no insight card at all, and that sparsity is a locked, deliberate outcome rather than an engine failure ([`../../match_detail/SSOT.md`](../../match_detail/SSOT.md) §5.2).
- Narrative richness must come from better rules and better evidence, not from generation.
- New card and claim types require validation work rather than prompt iteration.

**Gains**

- Retroactive methodology changes are possible at all.
- A result can be explained, audited and reproduced years later from recorded versions.
- The product's honesty invariants — no fabricated certainty, no opaque verdict, no causal claim, claims within sample gates — are enforceable by construction rather than by review.
- No per-match inference cost, no inference latency in the post-match path, and no third-party dependency on the critical path.

**Obligations this creates**

- A future proposal to generate user-facing findings at runtime requires superseding this ADR, and must first answer how reproducibility and retroactive rebuilds survive it.
- "The analysis engine connects evidence into findings" is a statement about deterministic rules. It is not licence to generate the connection.
