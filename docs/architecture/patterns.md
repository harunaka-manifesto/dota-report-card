# Patterns

Patterns are reviewed relationships among public Element results. The active
registry is `free-patterns-4.0.0` and contains exactly 14 Patterns. A Pattern
does not mine normalized rows again: it consumes the upstream Element result,
its named zone, confidence, coverage, quality, receipts, and confounders.

## Qualification and ranking contract

Qualification is zone-first. The accepted zones below are the public contract;
numeric scores supply relationship magnitude only. For a qualified Pattern:

```text
relationship_strength = mean(reviewed zone components)
strength = relationship_strength × confidence × coverage × qualification_quality
```

That evidence-weighted `strength` is calculated once. The v4.1 ranking layer
does not multiply confidence or coverage into it again. Ranking adds only an
inspectable novelty adjustment, a close-Tier-A tie preference, and a small
same-family redundancy penalty. Required Elements gate qualification;
modifier Elements add context and never silently become gates.

Every Pattern is unavailable when a required Element is unavailable or has no
score, suppressed when a required Element is below the 0.45 confidence gate,
and suppressed when its reviewed zone relationship is not met. A blocking
confounder also excludes it; informational confounders remain visible in the
receipt and limitations. `qualification_quality` is the mean quality of the
required Elements and `evidence_coverage` is the weakest required coverage.

## Owner catalog

| Public title / key | Tier · family | Human meaning and why it matters | Exact required zones | Modifier Elements | What can be claimed | What cannot be claimed / suppression | Related or opposing Patterns |
|---|---|---|---|---|---|---|---|
| Same Playbook · `same_playbook` | A · `breadth_toolkit` | Hero names change more than the kinds of Dota jobs underneath. It separates name variety from repeated toolkit shape. | `hero_pool_breadth`: Varied or Wide; `toolkit_breadth`: Compact or Focused | None | The observed pool is broad while its taxonomy toolkit remains compact/focused. | Not that the player intentionally repeats a strategy; unavailable/low-confidence/low-coverage required Elements suppress it. | Opposes Versatile Core. Related Comfort Edge and Proven Flexibility. |
| Comfort Edge · `comfort_edge` | A · `breadth_transfer` | The playable pool is wider than the range where current results reliably hold. It exposes selection/result divergence. | `hero_pool_breadth`: Varied or Wide; `off_pool_performance`: Slips or Falls off | `hero_exploration_rate`, `post_loss_familiarity_shift` | Results are weaker in the off-pool comparison despite a broad pool. | Not a claim of fear, comfort-seeking, or motive; modifiers do not gate it. Opposed by transfer-positive Proven Flexibility. | Opposes Proven Flexibility; related Partial Transfer. |
| Partial Transfer · `partial_transfer` | A · `presence_transfer` | Fight presence travels off-pool better than results do. It tests whether “disappearing” explains the result change. | `off_pool_activity_stability`: Holds or Unchanged; `off_pool_performance`: Slips or Falls off | None | Activity remains similar while the outcome proxy falls off-pool. | Not a causal explanation for results; no claim that activity is good or bad. | Related Comfort Edge; contrasts with a general transfer win. |
| Stable Style · `stable_style` | A · `form_stability` | Recent results changed more than visible hero-pool shape and fight pace. It separates form movement from a broad style change. | `recent_form_shift`: Rising, Surging, Sliding, or Cooling; `hero_pool_stability`: Settled or Steady; `recent_activity_shift`: Calmer, Same, or Busier | None | Form moved while pool stability and recent activity stayed in reviewed zones. Direction is rising-style or sliding-style. | Not that the player’s style is fixed, nor why form changed. | Related Form and Pace Elements; no direct Pattern opponent. |
| Versatile Core · `versatile_core` | A · `breadth_toolkit` | A focused pool still covers meaningfully different Dota jobs. It distinguishes few names from a narrow functional toolkit. | `hero_pool_breadth`: Focused or Selective; `toolkit_breadth`: Versatile or Diverse | None | A focused hero pool has a broad taxonomy toolkit. | Not that the player is universally flexible; taxonomy coverage must clear its gate. | Opposes Same Playbook. Related Proven Flexibility. |
| Proven Flexibility · `proven_flexibility` | A · `breadth_transfer` | A broad pool is backed by observable transfer, not selection variety alone. | `hero_pool_breadth`: Varied or Wide; `off_pool_performance`: Travels or Carries over | None | The off-pool outcome proxy holds or improves relative to the familiar comparison. | Not a trait, mastery claim, or motive. | Opposes Comfort Edge; related Versatile Core and Partial Transfer. |
| Selective Closer · `selective_closer` | B · `involvement_finishing` | The player is not everywhere, but appearances skew toward final kill credit. | `combat_involvement`: Quiet, Selective, or Present; `finisher_orientation`: Closer or Cleanup | `death_exposure` | Involvement is selective while the kill/assist split leans toward final credit. | Not that kills are always more valuable; death modifier is context only. | Contrasts Assist Presence; shares ingredients with Controlled/Heavy Exposure. |
| Loss Response · `loss_response` | B · `post_loss` | After a loss, hero familiarity and next-game activity can move together or separately. | `post_loss_familiarity_shift`: anything except Unchanged; `post_loss_activity_shift`: anything except Same. A single moved Element qualifies. | None | Direction is `pick_reset`, `pace_reset`, or `full_reset`. | Unchanged + Same is explicitly not qualified; not a claim about emotion or intent. | Uses the two post-loss Elements; no single opposite Pattern. |
| Controlled Presence · `controlled_presence` | B · `involvement_deaths` | High involvement appears without a similarly high death-exposure signal. | `combat_involvement`: Active or Everywhere; `death_exposure`: Elusive or Safe | `finisher_orientation` | Frequent participation coexists with low-to-moderate deaths per time. | Not “safe play,” discipline, or causality; finisher modifier is descriptive only. | Opposes Heavy Exposure. Related Selective Closer and Assist Presence. |
| Heavy Exposure · `heavy_exposure` | B · `involvement_deaths` | High presence currently carries a visible death cost. | `combat_involvement`: Active or Everywhere; `death_exposure`: Exposed or Frequent | `finisher_orientation` | Frequent participation coexists with high deaths per time. | Not recklessness, aggression, or motive. | Opposes Controlled Presence. Related Selective Closer and Assist Presence. |
| Session Fade · `session_fade` | B · `session_drift` | Later games in sufficiently long sessions show a repeated weaker result signal. | `session_length_tendency`: Long or Marathon; `late_session_performance`: Drops or Fades | None | Late-session outcome proxy is lower in long-session context. | Not fatigue, burnout, or a causal session effect. | Opposes Session Rise; neutral counterpart Session Hold. |
| Session Rise · `session_rise` | B · `session_drift` | Later-session results improve often enough to stand out. | `session_length_tendency`: Medium, Long, or Marathon; `late_session_performance`: Warms up or Finishes strong | None | Late-session outcome proxy improves in the reviewed session context. | Not warm-up, resilience, or a causal session effect. | Opposes Session Fade; related Session Hold. |
| Session Hold · `session_hold` | B · `session_drift` | Long sessions exist without a meaningful late-session result decline. | `session_length_tendency`: Long or Marathon; `late_session_performance`: Holds | None | Long-session late results remain in the reviewed hold zone. | Not fatigue resistance or proof that session length has no effect. | Neutral counterpart to Session Fade and Session Rise. |
| Assist Presence · `assist_presence` | B · `involvement_finishing` | Meaningful fight involvement is expressed more through assists than final kill credit. | `combat_involvement`: Present, Active, or Everywhere; `finisher_orientation`: Setup or Support | `death_exposure` | The kill/assist split leans toward assists at meaningful activity volume. | Not a support-role assignment or a value judgment about assists. | Contrasts Selective Closer; shares Controlled/Heavy Exposure context. |

## Modifiers and confounders

Modifiers are visible ingredients when available, but a missing modifier does
not invalidate a Pattern. Informational confounders explain what the summary
data cannot control. Blocking confounders are explicit public fields and are
the only confounders that suppress an otherwise zone-qualified result.

The Pattern story leads with the human meaning, then shows the required
Element labels and zones, receipts, and a keyboard-accessible methodology
disclosure. Tier, family, relationship strength, coverage, and quality remain
inspectable transparency details rather than the headline discovery.
