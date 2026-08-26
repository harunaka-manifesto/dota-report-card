# Free DNA V6.1 story state machine

Status: implementation source of truth
Contract: `free-dna-report-6.1.0` / `free-story-6.1.0`
Purpose: define availability, fallback, ordering, depth, synthesis, and share behavior without changing analytical semantics.

## 0. Direction freeze

The governing constitution and complete storyboard were read in full on
2026-08-25. The frozen emotional order is:

> Recognition → Familiarity → Structure → Adaptability → Adversity →
> Expression → Time → Coherence → Signature → Depth → Share

The storyboard's 33 screens are reference compositions, not a mandatory page
count. The nine compatibility beats remain the API contract; screens merge,
collapse into disclosures, or disappear when their backend condition is absent.
The UI is editorial/story-first with explicit Story, Evidence, and Methodology
depths. Prompt B's Sequencing Field primitives and Prompt C's continuity,
neutral, insufficient, mixed, narrow-pool, broad-pool, no-fixed-type, and
reduced-motion states are presentation rules only.

## 1. State vocabulary

The report has two independent kinds of state:

1. **Server evidence state:** immutable report data and qualification status.
2. **Journey state:** user-reported answers, reveal/skip choices, disclosure
   depth, share selection, save/resume metadata, and optional follow-up state.

Journey state never changes server evidence. User answers remain under
`user_reported`; observed values remain server-owned.

### Server evidence states

| State | Meaning | Story behavior | Evidence behavior | Share/Deep behavior |
|---|---|---|---|---|
| `qualified` | Registered outcome and claim contract cleared all required gates. | Show the outcome headline and visual relationship. | Show comparison, denominator, alternatives, and methodology. | Eligible only if the separate share/Deep gates also pass. |
| `neutral` | The supported comparison remains compatible or no direction clears. | Show the neutral sentence as an interesting result. | Show the complete supported range and what was compared. | No finding share card or Deep question. |
| `insufficient` | Required opportunities, sessions, events, coverage, or complete history are missing. | Show “Not enough signal to call this one.” plus one factual reason. | Show the missing denominator/coverage fact. | No claim, share card, or Deep question. |
| `mixed` | A registered outcome has valid components that disagree or are context-dependent. | Show both sides; never average them into a generic middle. | Show the two component rows and alternatives. | Share only if server marks the resulting finding eligible. |
| `suppressed` | The branch is intentionally withheld, such as incomplete annual history or a shadow-only outcome. | Omit the branch; show the family neutral/boundary state. | Methodology may name suppression without exposing branch text. | Never share or offer Deep. |
| `unavailable` | Required source data or public context is absent. | Show “Not available” only when the source itself is absent. | Name the missing source/coverage plainly. | Never share or offer Deep. |

`qualified` and `mixed` are not synonyms. A mixed outcome is still qualified
when its registered evidence contract clears; “mixed” describes the shape of
the result, not a failed statistical gate.

## 2. Report-level states

```text
REPORT_LOADING
  ├─ valid V6.1 report → REPORT_READY
  ├─ 404 → REPORT_NOT_FOUND
  └─ non-404 fetch failure → REPORT_ERROR

REPORT_READY
  → BEAT_START
  → BEAT_SHAPE
  → BEAT_POOL
  → BEAT_CHANGE
  → BEAT_AFTER_LOSS
  → BEAT_MATCH
  → BEAT_SESSION
  → BEAT_SIGNATURE
  → BEAT_SHARE
  → STORY_COMPLETE

BEAT_SHARE
  ├─ eligible Deep question selected → DEEP_QUEUED / DEEP_STATUS
  └─ no Deep selection or skipped → STORY_COMPLETE
```

The API still returns the nine compatibility IDs:

```text
self-estimate
identity-reveal
pool-evolution
combat-expression
strongest-finding
secondary-finding
recommendation
hero-mirror
deep-diagnostic
```

The UI maps those IDs to the production labels and emotional jobs below. It
does not rename the API IDs or add a tenth page.

## 3. Beat availability and fallback matrix

| Production state | Compatibility beat | Unconditional? | Entry condition | Primary content | If no qualified finding | If source unavailable | Skip rule |
|---|---|---:|---|---|---|---|---|
| `BEAT_START` / Start | `self-estimate` | Yes | Valid report. | “We sequenced your Dota.” Optional self-read. | Report-level neutral copy. | Report-level error only if report invalid. | Always skippable; answers remain user-reported. |
| `BEAT_SHAPE` / Shape | `identity-reveal` | Yes | Report identity and seven Element records. | “Yep. This is you.” Optional display name/avatar specimen, then a 2–3 Element teaser; full seven-signal scan in Evidence. | Descriptive identity and Element states. | “Your identity is still forming from this sample.” | Reveal gate may be skipped; observed result remains locked until reveal for pacing. |
| `BEAT_POOL` / Pool | `pool-evolution` | Conditional content | Human-labeled hero rows, pool shape, or timeline. | Heroes → Breadth/Toolkit → core/stretch → chronological field/timeline. Show match count/share only; never invent hero win rate. | Pool descriptive cards; no semantic family claim. | “Not enough usable hero history to map the pool.” | If no hero/timeline payload exists, show a short unavailable card and allow skip. |
| `BEAT_CHANGE` / Change | `combat-expression` | Family shell yes; qualified result no | Transfer family record or Element exists. | Transfer question and qualified outcome. | Neutral/insufficient Transfer state. | “The transfer comparison is not available here.” | Always skippable; no branch text when not published. |
| `BEAT_AFTER_LOSS` / After loss | `strongest-finding` | Family shell yes; strongest claim no | Result-response evidence exists. | Post-loss question and qualified outcome. | Neutral/insufficient Post-Loss state. | “Same-session result transitions are not available here.” | If no family record, omit content and mark page unavailable; no fake strongest finding. |
| `BEAT_MATCH` / Match | `secondary-finding` | Family shell yes; qualified result no | Combat Elements/family evidence exists. | Combat question and qualified outcome. | Neutral/insufficient Combat state. | “Context-resolved match expression is not available here.” | If no combat evidence, omit content and allow skip. |
| `BEAT_SESSION` / Session | `recommendation` | Family shell yes; recommendation no | Session curve/family evidence exists. | Session question and qualified outcome; optional five-game aftercare. | Neutral/insufficient Session state. | “Completed-session positions are not available here.” | Recommendation aftercare is never a blocking beat. |
| `BEAT_SIGNATURE` / Signature | `hero-mirror` | Yes after report | At least three public Element records; slots may be partial. | Coherence, Signature, Why Signature, Hero Mirror. | Descriptive/partial Signature. | “Your Signature is still taking shape.” | User may skip individual disclosures, but final Signature shell remains available. |
| `BEAT_SHARE` / Share | `deep-diagnostic` | Share shell yes; cards/Deep no | Valid report and share section. | Eligible server share candidates, three depths, optional Deep. | No-card copy; no fake card. | Methodology-only boundary and finish. | Deep and share are optional; story can finish without either. |

The compatibility beat names are retained because the strict V6.1 schema
requires nine page IDs. The presentation may provide chapter and reference-
screen composition metadata, but it may not change the schema's ordered beat
tuple. A beat may render fewer screens when there are fewer qualifying findings;
it must not add placeholder drama to preserve the reference count.

## 4. Journey transitions

### Start

1. Enter `BEAT_START` after `REPORT_READY`.
2. Optionally collect one of the server-provided self-estimate options.
3. Store the selection only at `journey.user_reported.identity_estimate`.
4. `Reveal your shape` marks the beat complete; it does not score or alter the
   report.
5. `Skip` marks the beat skipped and leaves the self-estimate absent.

### Shape

1. Enter locked if the user has not requested the observed reveal.
2. `Reveal observed shape` exposes the optional display name/avatar specimen,
   identity headline/slots, and a 2–3 Element teaser; the full seven-Element
   scan is an Evidence disclosure.
3. Use the server's `identity`, `identity_summary`, and `elements`; the client
   does not rank Elements or findings from raw values.
4. If PRIMARY is absent, use the descriptive identity state. Do not invent a
   PRIMARY from the strongest-looking numeric Element.

### Pool

1. Render human hero names before pool metrics.
2. If `hero_portfolio.prediction.options` exists, the user may make a pool
   prediction; the answer is stored under `user_reported`.
3. Reveal uses only `hero_portfolio.prediction`, `evolution`, `timeline`, and
   supporting portfolio fields.
4. The pool field may show three chronological thirds, core/stretch/outer edge,
   and hero/job layers only when their fields exist. It uses the timeline and an
   accessible table; it does not invent a spatial map or pan/zoom behavior.
5. Hero cards show only server fields that exist (`match_count`, `share`, and
   reviewed display labels). Hero win rate is not available in the current
   portfolio output and must not be added by the client.
6. Missing timeline does not prevent the hero introduction; missing all hero
   rows makes the pool surface unavailable and skippable.

### Change / Transfer

1. Show the human question before any outcome line.
2. If `findings[family=transfer].published=true`, render the registered
   `semantic_outcome_key` row from the copy matrix.
3. If `published=false`, redact branch/claim/interaction fields exactly as the
   strict schema requires. Render only the family neutral/insufficient/
   unavailable sentence derived from public evidence state.
4. `interaction.enabled` controls the finite visual. If false, use the textual
   evidence fallback; the client never enables it from raw fields.
5. Alternatives appear in Depth 2; the opaque `deep_handoff` appears only as a
   protected server handoff and is never displayed.

### After loss

1. Use same-session chronological transitions only.
2. Display states in this order: `win`, `one_loss`, `two_plus_losses`,
   `win_streak`; do not call a state “tilt,” “recovery,” or “streak mentality.”
3. A qualified outcome maps to one of the five registered Post-Loss keys.
4. A neutral state uses the complete supported range, not “not significant.”
5. An insufficient state names missing transitions/sessions and offers a skip.

### Match

1. Keep Involvement, Finishing, and Death Exposure visually distinct.
2. A Combat finding is published only when the server says so.
3. Use `two_versions` or `variance_decomposition` only when the server's
   interaction is enabled; otherwise use the table/disclosure fallback.
4. Do not derive a combat family claim from Element zones in the client.

### Session

1. Use completed sessions only; display `G1`, `G2`, `G3`, `G4`, `G5+`.
2. Do not reinterpret `result_rate` or hero counts as fatigue, warm-up, or
   focus.
3. Censored sessions are a methodology/evidence note, not a Story headline.
4. Show optional Recommendation after the Session evidence, not as a required
   page transition. It is available only when a published finding contains a
   server-authored recommendation and both verification metric keys.

### Signature

1. Build only from server `identity_summary.slots`, Elements, published
   findings, and human hero portfolio anchor.
2. Render the public title `Your Dota Signature` and `PRIMARY`, `TWIST`, and
   `ANCHOR` in that order. A missing slot is an
   empty slot, not a generated substitute.
3. If the anchor is not a human display name, omit it and mark the presentation
   payload for assembly correction; never show a numeric hero ID.
4. The `Why this signature?` view opens the three-part evidence map.

### Share / Deep

1. The share shell always appears after Signature, even with zero candidates.
2. The client filters only `eligible=true` candidates already supplied by the
   server; it does not infer eligibility.
3. A share gallery may render only the actual eligible identity, finding, and
   hero-mirror candidates already returned by the server; it never creates a
   card for a merely possible storyboard surface.
4. Deep questions are shown only when `available=true`, `offered=true`,
   confidence is moderate/high, evidence refs exist, and no blocking
   confounder is present.
5. A selected Deep question sends only the question ID and interaction-session
   reference. The client never sends a predicate assembled from UI text.
6. After submission, show `Your deeper question is queued.` plus factual status.
   No Deep result is implied by acceptance.

## 5. Finding-count state machine

`quality.published_findings` is the authoritative count, constrained to 0–3.

| Published findings | Strongest/After loss | Secondary/Match | Signature | Recommendation | Deep | Share candidates |
|---:|---|---|---|---|---|---|
| 0 | No strongest claim. Show family neutral/insufficient cards where evidence exists. | No secondary claim; skip the branch. | Descriptive or partial Signature from Elements/anchor only. | Hidden. | No questions. | Identity and Hero Mirror only if independently eligible; often zero. |
| 1 | Show the one qualified family in its chapter; do not force it into a generic “strongest” label. | Skip/empty secondary branch. | PRIMARY plus one TWIST if slot gates pass; anchor separately. | Show only if this finding has a recommendation and verification contract; after Signature/share. | At most one offered question from the published family. | Identity, Hero Mirror, or finding only if each candidate is independently eligible. |
| 2 | Show both qualified family chapters in their natural order. | No third finding. | Primary/twist/anchor map may use both; evidence map names both. | Only server-authored recommendation. | At most two offered questions, max three by schema. | Maximum three candidates; never one card per finding automatically. |
| 3 | Show the top two in the two compatibility finding beats; retain the third in Signature/Evidence. | Third is a synthesis/evidence item, not a fourth beat. | Signature evidence map may include all three, ordered by server selection. | Only registered recommendation. | Up to three offered questions. | Maximum three server-eligible cards. |

The renderer must never synthesize a “strongest finding” from a family that is
not published, reorder findings based on client confidence, or fill a missing
secondary finding with the next raw family record.

## 6. Finding-state handling

### Qualified

Render the outcome headline, its relationship visual, evidence cue, alternatives,
and optional recommendation/verification. In Story, show only the headline and
visual; in Evidence, show the denominator and comparison; in Methodology, show
the estimator and release details.

### Neutral

Render the family question and a sentence such as “Your covered expression stays
compatible across completed session positions.” Show the supported range and
why the result is interesting. Do not use “no statistically significant
difference.” No share/deep branch is created from neutral family state.

### Insufficient

Render “Not enough signal to call this one.” followed by exactly one factual
reason, such as “The comparison has fewer than the required supported
opportunities.” Keep the family question so the user understands what could
not be answered. No branch claim or interaction appears.

### Mixed

Render the tension directly: “One signal holds while another moves,” or the
registered outcome-specific line. Show both component rows. Do not average,
rank, or call the result “typical.”

### Visual state rules

- Neutral keeps the sequence deliberate and interesting even when it barely
  changes.
- Insufficient uses “Not enough signal to call this one.” plus one factual
  reason; it is incomplete, not an error treatment.
- Narrow pools use fewer, larger samples; broad pools use aggregation/clusters.
- A Signature remains an evidence-derived artifact with no fixed player type.
- Every scan, bridge, fork, drift, and recombination has a static equivalent:
  crossfade, before/after, stepped reveal, or discrete chronology.

### Suppressed or shadow-only

Do not render the semantic key, hypothesis, claim, interpretation, or
interaction. Use the family boundary sentence and methodology explanation.
`hero_lifecycle`, `identity_eras`, and `behavioral_loop` never appear in Story,
Signature, share, or Deep.

## 7. Recommendation and five-game aftercare

Recommendation is a server-authored optional drawer. It appears only when a
published outcome contains:

- a registered recommendation key;
- `verification.eligibility_games=5`;
- `primary_metric` and `guardrail_metric`;
- `causal=false`; and
- `abstention="too early to tell"`.

Use these exact labels:

- Entry: `Try this next`;
- action: server-authored recommendation label;
- commitment: `Set a five-game check-in`;
- progress: `X / 5 context-matching games`;
- guardrail: `This compares the next five matching games. It does not claim
  causality or change your Signature.`;
- incomplete: `The check-in is not ready yet.`;
- ready: `The five-game comparison is ready.`

The follow-up response must not return or render raw `match_ids` to the user.
The current route's private response shape is a privacy implementation gap to
resolve before State C approval.

## 8. Share state machine

| Candidate kind | Server eligibility | Story placement | Allowed content | Not allowed |
|---|---|---|---|---|
| `dynamic_identity` / `identity` | High confidence, refs, no blocking confounder, no early-sign/“still forming” copy. | Screen 33 Signature share. | Signature/identity headline, reviewed supporting line, optional display name if user chooses. | Self-estimate, raw metrics, IDs, rank/MMR, personality label. |
| `strongest_finding` / `finding` | Published, high confidence, refs, no blocker, no recommendation attached, no forbidden inference. | Screen 33 finding share. | Registered finding headline, compact reason/evidence cue, identity headline. | Unpublished/neutral/insufficient branch, recommendation, p/q/interval, raw IDs. |
| `hero_mirror` | Server `eligible=true`, high confidence, refs, human hero name. | Screen 33 mirror share. | Human hero name, reviewed mirror headline/body, compact comparison. | Raw player-behavior keys, hero IDs, eligibility internals, self-report. |

Maximum three candidates are shown. A report with zero eligible candidates
still gets the exact no-card state and a finish action. The server's
`share-svg-6.1.0` renderer is the source for image cards; the frontend may
provide native share, download, clipboard, and link actions around it.

## 9. Loading, error, save, and resume states

| State | Exact primary copy | Exact secondary copy | Action | Data/privacy rule |
|---|---|---|---|---|
| Loading | “We’re sequencing your Dota.” | “Your report is being arranged into a shape.” | No action; preserve user context. | Do not show request counts, IDs, or backend errors. |
| 404 | “This report is no longer available.” | “Start a new Free DNA report to sequence a fresh year.” | `Start a new report`. | No report/profile details. |
| Fetch error | “Your Dota sequence is taking a break.” | “Try again, or start a new report.” | `Try again`, `Start a new report`. | Log sanitized status only. |
| Save idle | “Save your place” | “Your answers stay under your saved journey.” | `Save your place`. | Bearer token stays in the fragment/header flow; never analytics. |
| Saved | “Your place is saved.” | “You can come back to this story.” | `Continue`. | No token/account/report ID in visible text or events. |
| Resumed | “Your saved journey is back.” | “Your observed report has not changed.” | `Continue`. | User-reported state is separate from evidence. |
| Conflict | “Your saved journey has a newer chapter.” | “Use the latest version or keep this one.” | `Use latest`, `Keep this version`. | Never merge observed fields from client state. |
| Expired | “That saved place has expired.” | “The report is still available; you can start again.” | `Start again`. | Delete expired token/session state. |
| Deep queued | “Your deeper question is queued.” | “We’ll test the question this report can support.” | `Return to Signature`, `View status`. | Do not show cohort reference or raw selection plan. |

## 10. Analytics and privacy state

Allowed event dimensions are page key, chapter, question key, interaction kind,
status (`qualified`, `neutral`, `insufficient`, `mixed`, `unavailable`), share
kind, channel, and result status. Do not send account ID, report ID, player
name, identity text, outcome direction, Element zone, raw match ID, access
token, hero ID, or cohort reference.

The strict public report validator already rejects nested `match_ids`,
`account_id`, `rank_tier`, `average_rank`, and `mmr`. The interaction follow-up
route needs the same public response posture before release readiness is
complete.

## 11. Implementation stop lines

The following changes stop at the presentation boundary:

- frontend composition/copy placement: safe next implementation;
- copy-catalog strings: source-binding review required;
- report assembly presentation fields: source-binding review required;
- backend semantic behavior: zero changes allowed;
- analytical/model behavior: zero changes allowed; no holdout can validate a
  changed model in this batch.
