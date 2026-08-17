# Architecture

~~~mermaid
flowchart LR
    S[Summary history] --> N[Normalized rows]
    N --> F[Sessions and features]
    F --> E[17 Elements]
    E --> P[14 Patterns]
    F --> H[Hero Portfolio]
    E --> R[Report assembly]
    P --> R
    H --> R
    R --> V[Strict v4 validation]
    V --> W[Interactive story and share]
~~~

Free reads one bounded summary-history window. It never hydrates match details
or requests replay parsing. The browser receives an immutable snapshot and
does not recompute scores.

Elements are atomic reviewed measurements. Patterns consume required Elements
and may include separate modifier Elements. Hero Portfolio is independent of
Pattern qualification and uses established hero history plus a versioned
taxonomy. Assembly creates the only public story and share projection.

The public contract is free-dna-report-4.0.0 with exactly 17 Elements and 14
Patterns, quality metadata, zero detail/parse requests, and privacy-safe share
data.
