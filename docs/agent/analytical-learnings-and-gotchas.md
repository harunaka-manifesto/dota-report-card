# Analytical learnings and gotchas

This is mandatory reading before designing or changing a Finding. It is a
practical guardrail for the V7 STRATZ rebuild, derived from the V6/V6.1
release record and the STRATZ field research. It does not define a Finding,
threshold, estimator, or release artifact.

## Product and statistical rules

### 1. Finding reach is a product requirement

A statistically valid Finding is not automatically a useful product Finding.
Before deep calibration, estimate:

```text
STRUCTURAL REACH
INFORMATION REACH
PLAYER HETEROGENEITY
EXPECTED PUBLICATION REACH
PORTFOLIO COMPLEMENTARITY
```

The V7 portfolio design target is that roughly 80–90% of sufficiently active
eligible users can receive at least three genuinely qualified Findings. This
is a design and calibration target, not a publication quota. Never reach it by
raising alpha, dropping stability or effect requirements, selecting the best
three p-values after the fact, or forcing a result for every player. Poor
reach means the candidate or portfolio needs redesign.

### 2. Prefer information-rich estimands

When scientifically justified, prefer continuous or otherwise information-
rich estimands over unnecessarily sparse binary events. STRATZ parsed
trajectories should provide more information per match, not merely reproduce a
coarser OpenDota proxy.

### 3. The null must match the estimand

Define the estimand and its null data-generating process before coding a
p-value. Every candidate needs a simulation suite, measured Type-I behavior,
power where possible, and edge-case tests. A function returning a number in
`[0, 1]` is not statistical validation.

At minimum test constant non-null draws, boundaries, relevant sign symmetry,
repeated or duplicated branch p-values, degenerate samples, small `N`,
missingness, and no-information samples. The V6/V6.1 statistical recovery
notes are evidence of why generic or incorrectly centered bootstrap/null logic
is unsafe.

### 4. Publication plumbing is part of inference

Trace every Finding end to end:

```text
estimator → support → effect → stability → p-value → multiplicity
→ publication flag → serialization → report rendering
```

Valid analytical output can still be suppressed or mispublished by inherited
version gates. Each stage needs an explicit test; rendering is not a substitute
for publication logic.

### 5. Declarations must execute

Minimum support, effect, stability, coverage, robustness, and confidence
claims must participate in publication logic. Keep boundary tests for pass,
fail, missing, and degenerate inputs. A documented gate that is not executable
is not a gate.

### 6. Freeze the multiplicity universe first

Before sealed validation, freeze the candidate universe, registered Finding
families, multiplicity method, and `q`/alpha. Do not add, remove, or re-rank
the hypothesis universe after seeing validation outcomes.

### 7. Separate discovery, calibration, test, and sealed validation

Pre-split identities before serious exploration. Maintain distinct roles for
discovery/development, calibration, internal test, and sealed validation.
Track the split manifest and provenance with the analytical release.

### 8. Changed methods need new validation

An old holdout does not validate a materially changed estimand, null model,
qualification rule, provider, or population baseline. Change the lineage and
obtain the matching calibration and validation evidence.

### 9. Population-common behavior is not automatically identity

A large, significant, stable effect can still be a poor personal Finding if
nearly everyone behaves the same way. Measure player heterogeneity. Population-
common behavior may belong in Elements or reference context instead.

### 10. Population position is separate from significance

Keep these questions separate:

```text
Finding: is this player's individual pattern credibly present?
Population position: where does the same estimand sit among comparable players?
```

Percentile is not skill, and higher is not always better. Say “reference
population” unless representativeness is established.

## Provider and data rules

### 11. Provider field names are not semantics

The STRATZ research showed that similarly named `*PerMinute` arrays can have
different meanings, including cumulative levels, deltas, running averages, or
minute-local gain. Verify semantics from payload evidence and preserve field
provenance. Never infer meaning from a name alone.

### 12. Role, position, and lane are distinct

Preserve STRATZ `position`, `role`, and `lane` independently. Never pass
STRATZ `lane` through the legacy OpenDota `ROLE_HINTS` vocabulary. In
particular:

```text
HARD_SUPPORT + SAFE_LANE ≠ carry
LIGHT_SUPPORT + OFF_LANE ≠ offlane
```

Any V7 role vocabulary must be explicit, versioned, and semantically verified.

### 13. Parsed availability can bias the sample

Do not silently condition research on `isParsed = true`. Measure exclusions,
availability by relevant strata, and the potential selection mechanism before
using parsed-only evidence.

### 14. Keep data layers separate

Maintain this boundary:

```text
immutable raw provider response
        ↓
provider-native normalized projection
        ↓
versioned V7 canonical analytical data
        ↓
derived feature
        ↓
Finding estimator
```

Raw responses are immutable research evidence. Normalization may repair
structure, but it must not invent analytical meaning.

### 15. Do not use opaque scores as analytical truth

Do not build a Finding on proprietary performance scores, rank/MMR, behavior
labels, smurf labels, or model outputs when transparent gameplay fields exist.
Such values may be retained as provider provenance when explicitly allowed,
but are not a reproducible V7 estimand.

### 16. Measure provider economics before corpus design

Measure requests per player-year, batch sizes, GraphQL complexity, response
bytes, parsed availability, latency, rate limits, and storage footprint before
locking a corpus size. A feasible query is not necessarily an economical
research design.

### 17. Fixtures are not semantic validation

Fixtures test parser and application behavior. They do not establish live
provider coverage, field semantics, or schema stability. Label live captures,
sanitized fixtures, dry-run stubs, and derived reports separately.

### 18. Unknown semantics fail closed

For an unknown field or enum, retain the provider-native value, mark the
canonical mapping unavailable, and exclude dependent eligibility or analysis.
Do not guess an OpenDota integer or a friendly role word to make a test pass.

### 19. V7 candidates are not inherited truths

Transfer, Post-Loss, Session Drift, Lane Recovery, and any future fifth family
are research candidates. Re-derive and revalidate them from STRATZ-native data;
do not port V6/V6.1 implementations line-for-line.

### 20. Judge the portfolio jointly

Evaluate candidate families together for Dota relevance, personal meaning,
structural and information reach, heterogeneity, identifiability, stability,
presentation quality, and complementarity. A locally strong candidate can make
the portfolio worse through redundancy or low reach.

## Engineering and release rules

### 21. Production and experimentation are different branches

`main` is the stable production line. V7 experimentation belongs on isolated
branches/worktrees and integrates into `staging` only after validation.
Implementation permission is not deployment permission.

### 22. Worktree state is evidence

Use an isolated worktree, preserve other agents' changes, and report branch,
base, head, ancestry, and integration state explicitly. Never reset, stash,
clean, delete, or rewrite another agent's worktree.

### 23. Frozen release artifacts must not drift

Keep deployed code SHA, analytical source SHA, and frozen artifact digest
separate. Do not regenerate V6.1 artifacts, inspect sealed validation data, or
silently change a release binding during V7 research or presentation work.

### 24. Cache identity includes provenance

Cache and raw-storage keys must include provider, schema, operation, and other
identity needed to prevent OpenDota and STRATZ data from colliding. A matching
account ID is not enough to reuse a completed analysis.

### 25. Secrets stay local or in secret stores

Put local credentials in ignored `.env` files or approved secret stores.
`.env.example` contains empty placeholders only. Never track, print, snapshot,
or include authorization headers, cookies, raw identities, or tokens in
fixtures, documentation, CI YAML, or error messages.

### 26. CI is credential-free by default

Ordinary CI must use fixtures and mocks, require no live STRATZ token, and make
no provider calls. Live probes are explicit, bounded, separately labeled, and
never hidden inside an offline test.

### 27. Readiness and provenance strings must be truthful

Provider/source labels, release metadata, cache keys, and deployment checks
must describe the actual lineage. Do not call STRATZ data OpenDota, call a
fixture production evidence, or report a deployment/validation event that did
not happen.

### 28. Old documents do not override current decisions

Use the current canonical contract and release manuals first. Mark historical
research as historical, migrate useful lessons into this document, and remove
superseded task prompts when they would misdirect future work.

### 29. Branch integration is part of the release record

Before staging integration, fetch again, compare the current staging tip with
the audited base, confirm ancestry, use normal non-force history, and record
the resulting staging SHA. Never make `main` the V7 integration target.

## Before opening a Finding change

The agent should be able to answer, with links to evidence:

1. What is the exact estimand and unit?
2. What data-generating process is the null?
3. Which identities belong to discovery, calibration, test, and sealed validation?
4. What are the executable support, effect, stability, coverage, and multiplicity gates?
5. What is the player heterogeneity and expected publication reach?
6. What provider semantics and provenance are established versus unresolved?
7. Which current V7 canonical data layer supplies each field?
8. How are publication, serialization, rendering, rollback, and persisted-report compatibility tested?

If any answer depends on a guessed provider semantic, an old holdout after a
material method change, an opaque score, or a live credential in ordinary CI,
stop and resolve that boundary first.
