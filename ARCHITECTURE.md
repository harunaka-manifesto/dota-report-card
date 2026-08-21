# Architecture

~~~mermaid
flowchart LR
    S[Summary history] --> N[Normalized rows]
    N --> F[Sessions and features]
    F --> E[18 Elements]
    E --> P[11 Patterns]
    F --> H[Hero Portfolio]
    E --> R[Report assembly]
    P --> R
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

The public contract is free-dna-report-5.0.0 with exactly 18 Elements and 11
active Patterns, reproducibility metadata, zero detail/parse requests, and
privacy-safe share data. Historical v4 snapshots remain readable under their
original registry meanings.
