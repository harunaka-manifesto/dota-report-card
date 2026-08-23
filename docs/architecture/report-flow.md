# Report flow

The Free v5 report is a one-viewport story: each section has one discovery,
one evidence boundary, and one deliberate interaction. The strict API schema,
server content catalog, web story, share SVG, and analytics contract are
versioned together.

## Public contract

The top-level shape is:

`identity`, `metadata`, `versions`, `quality`, `elements`, `patterns`,
`highlights`, `hero_portfolio`, `story`, `pages`, `shares`, `deep_dive`,
`methodology`, `cost`, and `reproducibility`.

The public report contains exactly 18 Elements and 11 active Patterns. It contains no
account ID, raw match ID, raw normalized row, private scorer metric, or detail-
analysis payload. Cost is a validated summary-only ledger: Free has one history
request and zero detail, parse, and parse-status requests. The actual ledger is
serialized; a nonzero forbidden request fails assembly rather than being
masked by a hand-written zero.

The current public schema is `free-dna-report-5.2.0`; `free-dna-report-5.0.0`
and `free-dna-report-5.1.0` snapshots remain readable. Each current Pattern
also carries a `pattern-presentation-5.2.0` payload with a finite outcome ID,
visual variant, structured proof facts, interpretation/recommendation IDs,
semantic outcome and recommendation IDs with their registry versions,
auditable evidence references, and raw metrics kept separate from the primary
story.

Current Pattern pages repeat that payload and add catalog-backed
`presentation_copy` for the five Wrapped + Depth layers. The active semantic
copy catalog is `free-dna-semantic-copy-5.3.0`; the legacy
`free-dna-copy-5.5.0` catalog remains only for compatibility reads of older
snapshots. The web app chooses this renderer only when the payload exists;
historical pages use the legacy body/action renderer. See the
[v5.2 SSOT](dota-dna-ssot.md) for the outcome, recommendation, hero snapshot,
manifest, copy, and fixture compatibility map.

## Exact story structure

The normal completed flow is:

1. Element scan with all 18 tiles.
2. Three Element highlight pages, selected from display-eligible Elements.
3. Up to five Pattern highlight pages, selected only from qualified,
   story-eligible Patterns.
4. Common Thread question.
5. Exception question.
6. Pool Evolution question.
7. Hero Mirror reveal.
8. Final card with share controls.
9. Deep Dive teaser.

The API semantic validator derives the expected page kinds from the highlight
counts, verifies stable IDs and order, verifies selected highlight keys, and
requires exactly four Common Thread options and four Exception options only
when a clear result exists. A current no-clear Exception exposes zero options
and no guessing interaction; historical `free-story-5.2.0` snapshots keep
their recorded four-choice payload. Story page content comes from the server catalog;
the client may keep old snapshots readable with a body fallback, but active
reports do not maintain a second narrative catalog in the web bundle.

## Interaction gates and accessible alternatives

| Surface | Gate | Accessible alternative | Announcement / state |
|---|---|---|---|
| Element scan | Tiles enter a short staged scan before strongest tiles are emphasized. | All tiles remain in the DOM and are readable without animation. | `data-scan-state` exposes `scanning` or `ready`; reduced motion starts ready. |
| Element highlight | None; evidence and guardrail are visible. | Keyboard focus reaches methodology control and the modal traps focus. | Evidence receipts name the measured fields and sample. |
| Pattern highlight | None; discovery leads, ingredients remain inspectable. | Required/modifier ingredients are visible; methodology details use native keyboard disclosure. | `report.pattern_element_expanded.v1` fires once per open transition. |
| Common Thread / clear Exception | Reveal disabled until a choice is selected; reveal is one-way. A no-clear Exception skips the controls and presents the insight directly. | Buttons expose `role="radio"`, `aria-checked`, visible focus, and keyboard selection. | Selection status, feedback, and the no-clear insight use live regions. |
| Pool Evolution | Same-page result is locked until self-assessment and Reveal. The self-assessment is not scored. | Radio semantics and keyboard reveal; historical 5.2 duplicate pages are filtered by the client. | One revealed payoff is announced; raw variant keys are not headline copy. |
| Hero Mirror | Closed until button, Enter/Space, or horizontal drag. | Button and keyboard reveal are equivalent to drag. Vertical movement remains page scroll. | Start and completion events are deduplicated; result is announced in a live region. |
| Share | No identity or raw IDs in the generated card. | Native share, clipboard fallback, and download controls are buttons. | Share open/completion/failure events use the canonical names below. |

Reduced motion disables scan and cover transitions, but never removes content,
focus states, gates, or keyboard functionality. The CSS uses `prefers-reduced-
motion: reduce`; browser QA also checks narrow viewports and 200% zoom.

## Progress and analytics contract

The fixed progress bar reports the currently intersecting story page and links
to Hero Mirror. Intersection impressions are deduplicated by page ID. Event
payloads contain page/question keys, section, schema/model versions, selected
option keys, match status, interaction type, card type, channel, and result
status as appropriate. They do not contain account ID, report ID, player name,
or raw match ID.

Canonical event names:

```text
report.page_viewed.v1
report.element_scan_viewed.v1
report.element_highlight_viewed.v1
report.pattern_viewed.v1
report.pattern_element_expanded.v1
hero_portfolio.question_viewed.v1
hero_portfolio.answer_selected.v1
hero_portfolio.reveal_viewed.v1
hero_mirror.reveal_started.v1
hero_mirror.reveal_completed.v1
report.share_opened.v1
report.share_completed.v1
report.share_failed.v1
deep_dive.cta_clicked.v1
```

The analytics helper strips identity-shaped keys at the client boundary. A
collector is optional and vendor-neutral; the report story remains usable when
no collector is attached.

## Final share hierarchy

The privacy-safe 4:5 SVG is a deliberate hierarchy, not a flattened list:

1. DOTA DNA title and optional display name/avatar.
2. TOP SIGNALS: strongest Element labels with their reviewed zones.
3. PATTERNS: strongest Pattern titles.
4. HERO PORTFOLIO: human Common Thread, Exception, and Pool Evolution copy.
5. HERO MIRROR: the available hero or a clear unavailable state.
6. Summary-history footer and deterministic renderer version in the cache key.

The renderer is `share-svg-5.0.0`. Avatar URLs are HTTPS-only and allowlisted;
query strings and fragments are rejected. Name and avatar preferences are
explicit share controls. The SVG has a title/description for assistive tools,
escapes all interpolated text, and keeps raw enum values out of the human
Evolution line.

## Ownership rules

Server content is the source of truth for public narrative. `dna_assembly`
owns report-page composition, presentation payloads, and semantic validation;
the web app owns
interaction state and accessible rendering; `share/service.py` owns the final
card hierarchy; `analytics.ts` owns event sanitization. Any version change to
one of these contracts must update the API client, model catalog/docs, tests,
and the version fingerprint in the same change.

## v6 opt-in flow

The v6 renderer is selected only for `free-dna-report-6.0.0` snapshots. Its
server-owned flow is:

```text
365-day summary history
→ normalization and literal lane context
→ 90-minute sessionization and frozen non-MMR baseline resolution
→ seven Elements and five finding families
→ clustered intervals, finite-family p-values, BH q-values, and max-three ranking
→ deterministic identity, nine skippable beats, diagnostic specs, and share candidates
```

The browser renders the supplied payload; it does not recompute scores, choose
suppressed findings, create recommendation text, or synthesize Deep predicates.
Self-estimates are stored only under `user_reported`; server observations remain
server-owned. Recommendation commitments resolve a report-authored structured
recommendation, lock its one follow-up metric and baseline, and compare the
first five qualifying post-cutoff games without changing stable identity.

Deep v2 receives only the offered diagnostic-question ID. The API retrieves the
immutable serialized question specification, persists it in job metadata, and
the worker executes the two-stage detail/parse acquisition path under 25-detail,
25-parse, and 160-relative-unit ceilings. Missing parse transport produces an
explicit abstention rather than a successful-looking parse result.
