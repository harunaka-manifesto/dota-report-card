# Patterns

This is the retained V5.2-compatible Pattern registry and presentation
contract. It is not a V7 Finding registry; V7 Findings must be re-derived
from STRATZ-native data under a new versioned release.

Patterns are reviewed relationships among public Element results. The active
registry is `free-patterns-5.1.0` and contains exactly 11 active Patterns. A Pattern
does not mine normalized rows again: it consumes the upstream Element result,
its named zone, confidence, coverage, quality, receipts, and confounders.

## Qualification and ranking contract

Qualification is zone-first. The accepted zones below are the public contract;
numeric scores supply relationship magnitude only. For a qualified Pattern:

```text
relationship_strength = mean(reviewed zone components)
strength = relationship_strength × confidence × coverage × qualification_quality
```

That evidence-weighted `strength` is calculated once. The v5 ranking layer
does not multiply confidence or coverage into it again. Ranking adds only an
inspectable novelty adjustment, a close-Tier-A tie preference, and a small
same-family redundancy penalty. Required Elements gate qualification from
registry-owned zone clauses; every selected clause Element must be available,
scored, meet its own registry minimum coverage, and have confidence at least
0.45. Modifier Elements add context and never silently become gates. A qualified Pattern also exposes `story_eligibility` and
`story_blockers`, so a blocking confounder cannot enter the Free story merely
because its numeric strength is large.

Every Pattern is unavailable when a selected qualification Element is
unavailable or has no score, suppressed when selected coverage is below the
Element registry gate or selected confidence is below 0.45, and suppressed when
its reviewed zone relationship is not met. A blocking confounder also excludes
it; informational confounders remain visible in the receipt and limitations.
`qualification_element_keys` identifies the authoritative clause. For P06/P07,
the winning Recovery + Familiarity or Recovery + Tempo branch alone supplies
confidence, coverage, quality, receipts, blockers, and strength; ties use
confidence, coverage, relationship sum, then registry clause order.

## Owner catalog

| Public title / key | Tier · family | Human meaning and why it matters | Exact required zones | Modifier Elements | What can be claimed | What cannot be claimed / suppression | Related or opposing Patterns |
|---|---|---|---|---|---|---|---|
| Same Playbook · `same_playbook` | A · `breadth_toolkit` | Hero names change more than the kinds of Dota jobs underneath. It separates name variety from repeated toolkit shape. | `hero_pool_breadth`: Varied or Wide; `toolkit_breadth`: Compact or Focused | None | The observed pool is broad while its taxonomy toolkit remains compact/focused. | Not that the player intentionally repeats a strategy; unavailable/low-confidence/low-coverage required Elements suppress it. | Opposes Versatile Core. Related Comfort Edge and Proven Flexibility. |
| Comfort Edge · `comfort_edge` | A · `breadth_transfer` | The playable pool is wider than the range where current results reliably hold. It exposes selection/result divergence. | `hero_pool_breadth`: Varied or Wide; `off_pool_performance`: Slips or Falls off | `hero_exploration_rate`, `post_loss_familiarity_shift` | Results are weaker in the off-pool comparison despite a broad pool. | Not a claim of fear, comfort-seeking, or motive; modifiers do not gate it. Opposed by transfer-positive Proven Flexibility. | Opposes Proven Flexibility; related Partial Transfer. |
| Partial Transfer · `partial_transfer` | A · `presence_transfer` | Fight presence travels off-pool better than results do. It tests whether “disappearing” explains the result change. | `off_pool_activity_stability`: Holds or Unchanged; `off_pool_performance`: Slips or Falls off | None | Activity remains similar while the outcome proxy falls off-pool. | Not a causal explanation for results; no claim that activity is good or bad. | Related Comfort Edge; contrasts with a general transfer win. |
| Versatile Core · `versatile_core` | A · `breadth_toolkit` | A focused pool still covers meaningfully different Dota jobs. It distinguishes few names from a narrow functional toolkit. | `hero_pool_breadth`: Focused or Selective; `toolkit_breadth`: Versatile or Diverse | None | A focused hero pool has a broad taxonomy toolkit. | Not that the player is universally flexible; taxonomy coverage must clear its gate. | Opposes Same Playbook. Related Proven Flexibility. |
| Proven Flexibility · `proven_flexibility` | A · `breadth_transfer` | A broad pool is backed by observable transfer, not selection variety alone. | `hero_pool_breadth`: Varied or Wide; `off_pool_performance`: Travels or Carries over | None | The off-pool outcome proxy holds or improves relative to the familiar comparison. | Not a trait, mastery claim, or motive. | Opposes Comfort Edge; related Versatile Core and Partial Transfer. |
| Bounceback · `bounceback` | B · `post_loss_recovery` | Positive comparable post-loss Recovery combines with an observable response. | `post_loss_performance_response`: Recovers or Surges; and either Familiarity is not Unchanged or Tempo is not Same | None | A post-loss rebound coexists with a selection/activity move. | Not resilience, confidence, emotion, or intent. Recovery alone remains an Element. | Opposes Performance Slide. |
| Performance Slide · `performance_slide` | B · `post_loss_recovery` | Negative comparable post-loss Recovery combines with an observable response. | `post_loss_performance_response`: Drops or Slips; and either Familiarity is not Unchanged or Tempo is not Same | None | A post-loss decline coexists with a selection/activity move. | Not tilt, choking, weakness, emotion, cause, or intent. Recovery alone remains an Element. | Opposes Bounceback. |
| Controlled Presence · `controlled_presence` | B · `involvement_deaths` | Finds where high participation is most economical in death exposure. | `combat_involvement`: Active or Everywhere; `death_exposure`: Elusive or Safe | `finisher_orientation` | Participation and low-to-moderate death exposure coexist; supporting hero/function breakdowns may localize it. | Not positioning skill, teamfight skill, discipline, personality, or proof that a death was valuable. | Contrasts Presence Tax. |
| Presence Tax · `presence_tax` | B · `involvement_deaths` | Localizes whether high-participation death cost is job-shaped, hero-specific, cross-context, or unresolved. | `combat_involvement`: Active or Everywhere; `death_exposure`: Exposed or Frequent | `finisher_orientation` | Participation and high death exposure coexist; supporting contexts may localize the concentration. | Not feeding, recklessness, bad positioning/initiation, cause, or proof that deaths were useful/wasteful. | Contrasts Controlled Presence. |
| Session Fade · `session_fade` | B · `session_drift` | Later games in sufficiently long sessions show a repeated weaker result signal. | `session_length_tendency`: Long or Marathon; `late_session_performance`: Drops or Fades | None | Late-session outcome proxy is lower in long-session context. | Not fatigue, burnout, or a causal session effect. | Opposes Session Rise. |
| Session Rise · `session_rise` | B · `session_drift` | Later-session results improve often enough to stand out. | `session_length_tendency`: Medium, Long, or Marathon; `late_session_performance`: Warms up or Finishes strong | None | Late-session outcome proxy improves in the reviewed session context. | Not warm-up, resilience, or a causal session effect. | Opposes Session Fade. |

## Modifiers and confounders

Modifiers are visible ingredients when available, but a missing modifier does
not invalidate a Pattern. Informational confounders explain what the summary
data cannot control. Blocking confounders are explicit public fields and are
the only confounders that suppress an otherwise zone-qualified result.

The Pattern story leads with the human meaning, then shows the required
Element labels and zones, receipts, and a keyboard-accessible methodology
disclosure. Tier, family, relationship strength, coverage, and quality remain
inspectable transparency details rather than the headline discovery.

## Story selection and reviewed actions

Free selects up to five qualified, story-eligible Patterns. The deterministic
selector uses strength, confidence, novelty, family diversity, and a close
Tier-A tie preference. If fewer than five Patterns clear the gates, the story
keeps the shorter set.

Reviewed action modules cover the active P01–P11 set:

- **Same Playbook** offers up to three `deepen` and three `stretch` heroes from
  the versioned relationship/expression layer. Both directions preserve named
  anchors, and the action may abstain.
- **Comfort Edge** ranks the player's top five sufficiently sampled heroes by
  confidence-adjusted, recency-weighted player-relative reliability. Ranks 1–2
  are the reference core; ranks 3–5 receive typed “why learn this hero?”
  reasons with situations and only supported aggregate examples.
- **Partial Transfer** separates a direct summary difference, a narrow
  capability-expression lead, and an unresolved gap; it never turns summary
  history into replay-level causality.
- **Versatile Core** maps each core hero to reviewed jobs, classifies coverage
  as strong, single-point, thin, or missing, and recommends at most one next
  tool plus two alternatives when a real gap clears the gates.
- **Proven Flexibility** selects the strongest active rolling seven-day window
  or reports distributed flexibility with the actual roster, functional jobs,
  repeated proof, and distribution evidence.
- **Bounceback** and **Performance Slide** use same-session, comparable-context
  Recovery evidence plus a Familiarity or Tempo movement. Their baselines leave
  the target session out; Recovery alone does not become a Pattern or an action.
- **Controlled Presence** and **Presence Tax** use confidence-gated hero,
  function, role, and overall fallback levels. They describe observable
  involvement/death relationships without claims about positioning, intent,
  discipline, or personality; localized Presence Tax results may hand off to
  deeper evidence.
- **Session Fade** and **Session Rise** expose a session-balanced G1/G2/G3/G4/G5+
  curve with context-relative proxy units, earliest persistent breakpoint,
  gradual/unresolved states, and explicit limits against fatigue or warm-up claims.

Actions are server-owned immutable report data. React renders them and never
recomputes hero rankings from taxonomy fields.

Every action also exposes an additive `evidence_summary` envelope with
resolution status, sample/effective sample, coverage, confidence, independent
group count where relevant, limitations, evidence keys, and provenance
versions. A qualified Pattern remains qualified when its action falls back or
is unresolved.

## Additive V6 finding families

This page remains authoritative for the V5.2 11-Pattern registry. V6.0 and
V6.1 do not reinterpret those Patterns: they use five finding-family roots.
V6.1 freezes 28 nested semantic outcomes, corrects the five roots before
correcting branches inside a surviving family, and publishes no more than
three. Lifecycle, era, and loop outcomes remain shadow-only. See the
[V6.1 feature graph](free-dna-v6.1-feature-graph.md).
