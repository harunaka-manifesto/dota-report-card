# Architecture

~~~mermaid
flowchart LR
    S[Summary history] --> N[Normalized rows]
    N --> F[Sessions and features]
    F --> E[18 Elements]
    E --> P[11 Patterns]
    F --> H[Hero Portfolio]
    E --> R[Report assembly]
    P --> PP[Pattern presentation]
    PP --> R
    H --> R
    R --> V[Strict v5 validation]
    V --> W[Interactive story and share]
~~~

Free reads one previous-365-day summary-history window. It never hydrates match details
or requests replay parsing. The browser receives an immutable snapshot and
does not recompute scores.

Elements are atomic reviewed measurements. Patterns consume required Elements
and may include separate modifier Elements. The story selects the strongest
three Elements and up to five story-eligible Patterns. Reviewed Patterns may
carry typed, server-owned actions backed by versioned hero relationship and
expression artifacts. Hero Portfolio is independent of Pattern
qualification and uses established hero history plus a versioned taxonomy.
Assembly creates the only public story and share projection.

The public contract is free-dna-report-5.2.0 with exactly 18 Elements and 11
active Patterns, reproducibility metadata, zero detail/parse requests, and
privacy-safe share data. Pattern stories carry deterministic visual proof,
interpretation, action, and Deep Dive IDs. Historical v4, v5.0, and v5.1
snapshots remain readable under their original registry meanings.

Pattern qualification consumes reviewed Element zones and applies the selected
clause's registry coverage and confidence gates. Actions run after
qualification and expose a common evidence summary without demoting a
qualified Pattern. Drift, Recovery, session curves, and Recovery actions share
the versioned leave-group-out comparable-baseline resolver.

## Additive generations

V5.2 remains the default contract. V6.0 is separately selected and validated.
V6.1 is another immutable generation behind `FREE_DNA_V61_ENABLED`; it never
changes a V6.0 snapshot or validator. V6.1 uses one physical history request,
seven Elements, five family roots, a private typed signal graph, hierarchical
semantic outcomes, and at most three published findings. Its browser path
renders server-owned identity, claims, interactions, and evidence.

See the [V6.1 feature graph](docs/architecture/free-dna-v6.1-feature-graph.md).
