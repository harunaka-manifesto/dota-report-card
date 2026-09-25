# Making Personal Progress Visible in Dota 2

## 1. Executive conclusion

**There is a credible product here, but Dota has no single equivalent of running pace or weight lifted.** The strongest foundation is a personal performance journal: comparable match measurements, honest records, repeated changes, and memorable accomplishments. Its promise should be “see how your Dota is changing,” with “see where you are progressing” earned by the evidence. It should not promise that every match produces growth, that good statistics prove good decisions, or that losing players secretly deserved to win.

The product should track three distinct things:

1. **Performance:** what happened in a bounded part of a match, such as last hits by ten minutes, early deaths, or a particular item timing.
2. **Progress:** whether a useful performance pattern changes and persists across sufficiently comparable games, without an obvious harmful tradeoff.
3. **Personal history:** records, hero preferences, memorable events, and milestones that can matter without demonstrating improvement.

This distinction is the product's central measurement discipline. A personal best is a fact about recorded history. An improving trend is an estimate. Better decision-making is a substantially stronger claim, often requiring replay review or an intervention study. Neither a provider's performance score nor a correlation with winning bridges those gaps automatically. STRATZ itself has documented the difficulty of explaining its outcome-correlated IMP model; research on professional Dota performance also emphasizes role and patch context. [^1] [^2]

**Recommended initial direction:** test standard ranked Dota with players who repeatedly play one role and a small hero pool. Track three to five relevant measurements per player, chosen from the 15-concept shortlist below. Start with early-game resource checkpoints, bounded survival observations, and familiar item timings. Add verified support contributions as accomplishments rather than claiming that ward counts measure support skill. Support players must participate in discovery, even if the first quantitative pilot is carry-focused.

**The hardest unresolved problem is support progress.** Creating resources, absorbing pressure, enabling vision, choosing good sacrifices, and saving allies are central to Dota, yet their value is often counterfactual and opportunity-dependent. A support who places fewer wards may have placed better ones. A support who dies more may have protected a core. A product that solves carry measurement and disguises support activity as skill has not solved its intended market.

**Commercial conclusion: conditional go for a research pilot, not yet a broad product build.** Role-aware measurement is well motivated. Tracking and feedback have evidence from adjacent domains. Demand for this particular mobile reward loop, recurring value after novelty fades, and organic acquisition through shared progress remain unproven. The MVP should test those propositions directly.

### Evidence labels and scope

Throughout this document:

- **Evidence** means an observed product capability, repository finding, or published empirical result. It does not automatically establish effectiveness.
- **Convention** means an expert/player interpretation of useful Dota behavior, requiring contextual judgment.
- **Inference** means a conclusion drawn from evidence without direct testing of this app.
- **Hypothesis** means a product choice or numerical starting rule that needs validation.

Confidence refers to the recommendation, not a calculated probability. **High** indicates convergent evidence or a clear measurement constraint; **moderate** indicates relevant but indirect evidence; **low** indicates a plausible untested product assumption. Research is current to September 9, 2026; older Dota studies establish concepts, not current-patch thresholds. No player interviews, live STRATZ probes, new corpus analysis, or product experiments were conducted for this document. Product marketing establishes advertised features, not independently verified accuracy or traction.

## 2. A mental model of Dota improvement

### Skill is a capability; match statistics are performances

A useful working definition of improvement is **a more reliable ability to make and execute useful choices under comparable constraints**. This includes acquiring resources, using power windows, protecting valuable resources, coordinating with allies, and converting opportunities into objectives. Improvement can also mean maintaining performance against harder opposition or transferring competence to a new hero. It need not mean every tracked number rises.

Observed performance combines player capability, role, hero mechanics, teammates, opponents, draft, resources, match state, patch, mode, and chance. These factors interact. A favorable lane gives a carry more last-hit opportunities; excellent lane play can also create that favorable state. There is no simple adjustment that perfectly separates the two.

The closest Dota equivalent to a repeatable running route is **a recurring hero-role-mode context with a fixed measurement window**. Luna position 1 at ten minutes in standard ranked is more comparable to the same player's previous Luna position-1 openings than to an entire 55-minute support match. It is still less standardized than a 5K. Strava's matched-activity approach is a useful analogy precisely because it recognizes that comparison needs a recurring context. [^3]

### Four kinds of positive change

| Kind | What it means | Legitimate example | What does not follow |
|---|---|---|---|
| Higher capability | More useful output under comparable opportunity | Sustained increase in early farm in matched carry games | Every extra creep was the right choice |
| Greater reliability | Fewer weak executions while maintaining useful contribution | Fewer poor openings across separate periods | Lower variance alone is better; consistently weak play is also consistent |
| Transfer | Capability holds in a new context | A familiar opening standard becomes repeatable on a second carry | More heroes played proves adaptability |
| Maintenance under greater difficulty | Similar execution against stronger constraints | Stable early economy after a sustained bracket rise | A constant percentile proves no improvement |

**Identity is a separate axis.** A narrow hero pool, a preference for roaming, or a recurring item pattern may be personally meaningful without being better or worse. The repository's discovery research explicitly found stable behaviors that were nevertheless poor candidates for evaluative findings. That is a warning against turning reliability into a moral ranking. [R4 · Discovery screen][r4]

### What expertise research contributes

Deliberate practice is structured work on particular skills with feedback; simply accumulating matches is not equivalent. The deliberate-practice literature also disputes definitions and how much performance variation practice explains. None of it supports a guarantee that automatic match tracking improves Dota skill. [^4] [^5]

Older Dota observational research found relationships between skill tiers and movement/coordination, and between performance and play histories. These studies do not establish that an amateur should maximize movement, queue more warm-up matches, or pursue kills over assists. Team-level differences, hero/role selection, old patches, and observational designs limit individual prescriptions. [^6] [^7]

**Inference, high confidence:** track observable capabilities and their repeatability; reserve claims about decision quality for evidence that actually supports them.

## 3. Competitive and analogous product research

### Existing Dota and gaming products

| Product | Evidence of the existing approach | Useful lesson | What does not transfer or remains unproven |
|---|---|---|---|
| STRATZ | Published IMP explanation uses contextual statistics and estimated win probability; the 2021 article acknowledges interpretation difficulties | Rich temporal data and hero/role context are valuable; explanations matter | Model predictions and input perturbations do not demonstrate causal contribution or longitudinal learning; current exact model behavior was not audited [^1] |
| OpenDota | Open-source replay parsing and detailed match data; repository research documents event logs, resource curves, and important omissions | Transparent raw evidence can support an auditable journal | Parsed aggregates do not reproduce the player's information or exact decision sequence [^8] [R3][r3] |
| Dotabuff Plus | Advertises hero rankings, farm charts, vision maps, item timelines, damage/CC breakdowns, and retained history | Players already have many analysis surfaces; the opportunity is interpretation over time | A new statistics dashboard is weak differentiation; advertised analysis does not establish skill-growth validity [^9] |
| Dota Plus / Battle Report | Official product offers hero progression, challenges, relics and comparisons; Battle Report was introduced as a personalized performance retrospective in 2022 | Hero-specific recognition is native to Dota; retrospective progress is not an empty competitive space | Hero XP/relic accumulation is not necessarily mastery. Historical launch material does not prove current cadence, quality, or player satisfaction [^10] [^11] |
| Dota2ProTracker | Exposes professional builds and separates high-level pub/pro comparisons | Specific hero/build context and visible examples can make benchmarks meaningful | Professional coordination, selection and priorities are not universal pub targets [^12] |
| LaneMind and coaching tools | LaneMind advertises a desktop overlay, item/context analysis and post-match coaching plans | The coaching workflow is a real competing position | Vendor claims are not evidence of validated advice or adoption. This concept should test a lower-effort personal journal, rather than compete on volume of advice [^13] |
| Leetify | Publishes benchmark recalibration and even score changes resulting from an equipment-calculation correction | Explain benchmark revisions; preserve raw values and eras | A score moving because its reference changed must not masquerade as personal growth [^14] |
| Tracker Network | Its published Tracker Score combines selected indicators and explicitly says it is not a replacement for rank | Fast summaries are attractive and weighted scores are feasible | Feature weights embed judgments; outcome-derived components cannot prove outcome-independent improvement [^15] |

Valve’s published Dota Plus page describes challenge XP as requiring a victory. This illustrates a concrete distinction to test: recognizing a bounded personal accomplishment in a loss without changing the meaning of the match result. The page is product documentation, not a current in-client behavioral audit. [^10]

The distinction worth testing is **a credible personal progression history that is rewarding to revisit and easy to share**, not exclusive access to match statistics. Existing products cover large portions of the feature inventory. No feature comparison here proves a defensible moat.

### Fitness and recap analogues

| Analogue | Observed mechanism | Transferable principle | Boundary |
|---|---|---|---|
| Hevy | Exercise-specific records include weight, estimated 1RM, set/session volume and records at particular repetition counts | Several understandable achievements can coexist; define each record's task and units | Match duration and number of fights are not equivalent to training volume. An estimated quantity must stay labeled as estimated [^16] |
| Hevy history | A weekly workout streak, visible rest days, calendar history and yearly review connect workouts over time | History becomes meaningful when it preserves recognizable effort and moments | A gym attendance habit is not automatically a desirable Dota queueing habit [^17] |
| Strava | Matched activities compare repeated routes; best efforts identify performances over defined distances | Define a comparable task and let an activity contain a noteworthy effort | A Dota checkpoint has opposing agents and shared resources; “same hero” is not “same course” [^3] [^18] |
| Apple Fitness / Health | Fitness trends compare recent activity with a longer history; activity goals can be adjusted and rings paused | Separate near-term movement from a longer reference; permit breaks | Calendar windows appropriate to physical activity are not automatically statistically adequate for sparse hero-role cells [^19] [^20] |
| Garmin | Training status uses a history of physiological/training measures and distinguishes multiple states | Maintenance can be legitimate; insufficient data should produce no status | Dota telemetry cannot infer physiological recovery or readiness to queue [^21] |
| WHOOP | Journal and trend products connect repeated observations with reported behaviors | Repeated reflection and cautious personal associations may be useful later | Observational associations are not experiments; match logs alone cannot measure sleep, tilt or recovery. Current support materials vary in recap terminology, so exact delivery cadence is not assumed [^22] |
| Spotify Wrapped | Published experiences use identity, change over time, top preferences and easy sharing | People can share self-recognition, surprise and belonging as well as superiority | Cultural scale and established social rituals do not transfer automatically to a new Dota app [^23] |

The analogy works best at the level of **recognition, comparability, and memory**. It works poorly when “more activity,” “higher output,” or a single readiness number is assumed to be universally desirable.

### Motivation evidence and counterevidence

An experimental meta-analysis of 138 studies found that interventions increasing progress monitoring improved goal attainment on average, with stronger effects when progress was recorded or reported. This supports testing a visible record, not assuming automatic analytics alone will improve play. [^24]

A sport goal-setting review found process goals more favorable than performance/outcome goals in the included studies, while noting substantial limits and heterogeneity. Dota last hits and death counts are **performance goals**, not process goals merely because they exclude wins. “Scan the map before pushing” is closer to a process goal, but cannot be resolved reliably from ordinary match aggregates. [^25]

Self-determination theory provides a rationale for competence, autonomy and relatedness: recognizable progress, chosen focuses and social connection. It is a design lens, not a validated recipe for Dota retention. Counterevidence matters: quantification experiments found that measuring enjoyable activities can increase output while making them feel more like work and reducing enjoyment. [^26] [^27]

### Player sentiment: directional, not representative

Small self-selected Reddit discussions contain appreciation for Battle Stats, requests for more timely reports, frustration about Turbo exclusion, and objections to item-specific hero challenges. They suggest topics for interviews: recognition, freshness, mode inclusion, and being pushed into unsuitable builds. They do not establish prevalence, willingness to pay, or causal retention effects. [^28] [^29]

## 4. Dota metric landscape: broad inventory before selection

The inventory below contains **60 candidate signals**, including weak and rejected ideas. It combines published analytics surfaces, the repository's parsed-data research, and explicitly proposed measurements. Inclusion means “worth evaluating,” not “validated.” Public research does not establish each signal as a causal skill measure. [^2] [^6] [R1][r1] [R3][r3] [R4][r4]

Disposition: **S** = shortlist; **D** = descriptive/context only; **V** = needs deeper validation before promotion; **X** = do not optimize or score as proposed. Shortlist IDs refer to section 5.

| Area | Candidate signals and disposition | Main interpretation problem |
|---|---|---|
| Early resources | 1. Last hits at 10 (M1); 2. net worth at 10 (M2); 3. denies at 10 (D); 4. XP/level checkpoint (M5); 5. lane-opponent resource differential (V) | Farm opportunity, lane partner, hero mechanics, matchup and lane swaps |
| Resource development | 6. Fixed-window farm rate (M3); 7. whole-match GPM (D); 8. XPM (D); 9. recovery after a weak opening (M13); 10. time with unused spendable gold (V) | Income is not resource access; gold can be intentionally saved; roles require different priorities |
| Timings | 11. Named item timing (M4); 12. time from item acquisition to first use (V); 13. useful first power-spike engagement (V); 14. first rotation timing (D); 15. first objective timing (D) | Earlier is not always better; purchase, delivery and effective availability differ |
| Survival | 16. Deaths before 10 (M6); 17. rapid repeat-death frequency (M7); 18. dead-time within a fixed phase (D); 19. isolated-death share (V); 20. buyback availability at death (V) | Valuable sacrifices and map pressure; nearby allies do not determine correctness |
| Combat contribution | 21. Credited kill involvement (M8); 22. participation in identified fights (V); 23. damage in defined engagements (M11); 24. damage to priority targets (V); 25. effective healing/saves (V) | Fight detection, target value, damage inflation, missing opportunities and counterfactuals |
| Mechanics/resources | 26. Hero-specific spell connection (M12); 27. overlapping disable waste (V); 28. unused defensive active on death (V); 29. mana efficiency (V); 30. APM (X) | Need cast opportunities, cooldowns, mana, range and intent; counts reward spam |
| Vision | 31. Observer placement (D); 32. attributed observer destruction (M9); 33. useful vision-time (V); 34. vision preceding objectives (V); 35. sentry detection efficiency (V) | Placement/lifetime is not information value; teammates and territory create opportunities |
| Resource enabling | 36. Camps stacked (M10, conditional); 37. stacked resources later secured (V); 38. pull success (V); 39. lane-equilibrium maintenance (V); 40. allied core access to safe resources (V) | Attribution, theft, contested camps, denial of own teammate XP, role opportunity |
| Objectives | 41. Tower damage (D); 42. credited objective participation (V); 43. post-fight team objective conversion (V); 44. Roshan timing/participation (V); 45. high-ground attempt outcome (V) | Objectives are team events; timing needs opportunity, buybacks, lanes and health |
| Movement/positioning | 46. Zone changes (D); 47. travel versus productive activity (V); 48. spacing relative to threats (V); 49. timely response to ally pressure (V); 50. pressure without dying (V) | Optimal movement depends on hidden information; distance is not map awareness |
| Mastery/adaptability | 51. Repeatable early performance (M14); 52. maintained performance across heroes (V); 53. matchup-specific execution (V); 54. role transfer (V); 55. build adaptation (V) | Breadth and variation can reflect experimentation or necessity, not mastery |
| Competitive/personal history | 56. MMR/rank trajectory (D); 57. win rate (D); 58. KDA (D); 59. hero/role history milestones (M15); 60. post-loss/session behavior (D) | Rank is relative, outcomes are shared, persistence is not resilience, identity is not growth |

The discovery frontier is attractive precisely where measurement is hardest: useful vision, opportunity-aware fighting, saves, safe map pressure, and conversion. Do not fill these gaps with renamed count statistics.

## 5. Recommended metric framework and top shortlist

### Organize by questions, not a universal player score

Four player-facing questions are sufficient:

- **How did my opening go?** Early resources, survival, meaningful first timings.
- **What did I contribute?** Involvement and role/hero-specific observed actions.
- **What is becoming more repeatable?** Recent distributions, fewer weak openings, sustained benchmarks.
- **What is worth remembering?** Records, accomplishments, milestones and identity.

Internally, retain evidence, eligibility, interpretation and recognition as distinct layers. There is no need for every raw field to become a contextual metric, every metric to become a dimension score, or every dimension to award a badge. Several measurements may support one story. Last hits, net worth, level and item timing are correlated witnesses to an opening, not four independent proofs of growth.

### Fifteen strongest concepts for MVP consideration

**This is a prioritized shortlist, not a recommendation to ship 15 measurements at once.** “Direct” below refers to the observable event or quantity; its relationship to skill is still a proxy. Every metric uses a valid match clock, complete required fields, a verified context, and metric-specific exclusions. Standard ranked and unranked references are separate initially; Turbo requires its own definition and reference.

**M1. Last hits by ten minutes — first pilot metric.** Count verified last-hit deltas in the horn-to-10:00 interval. Best for repeated core hero-role contexts, especially position 1; not a support grade. It indicates early resource acquisition, not last-hit accuracy because available/contested creeps are unknown. Compare the same hero, role, mode and compatible patch; use lane matchup as explanatory context. Noise and state dependence are moderate. Chasing jungle creeps or abandoning pressure can inflate it. A record remains factually meaningful after a loss. Pair it with early deaths and resource context; do not proclaim a “better lane” automatically. Personal comparison is strong; matched-rank/hero benchmarks are useful if representative. **Confidence: moderate for progress, high for bounded counting.**

**M2. Net worth at ten minutes — corroborating opening metric.** Read the verified checkpoint, in gold. Applies to every role descriptively, with core-focused progress interpretation. It reflects resources available, including effects beyond last hitting; it is not pure farming efficiency. Hero, role, patch, kills, lane pressure and item rules matter. Self-comparison is useful; peer comparison is conditional. Gold funnels, kill income and sacrificed team resources can inflate it. Useful after a loss as an opening fact; a separate PR is usually redundant with M1. **Confidence: moderate.**

**M3. Resource acquisition during a fixed later window — conditional core metric.** For example, last hits from 10:00 to 20:00 divided by ten minutes, only when the full window exists. Net-worth change is a separate measure and must not be mislabeled gold earned. Ideal measurement would evaluate the resources reasonably available while fulfilling team duties. The approximation cannot do that. Match state dependence and gameability are high: ignoring team pressure can improve the number. Compare within hero/role and annotate starting state; use as a trend with context, not a default challenge. **Confidence: moderate for description, low-to-moderate for improvement.**

**M4. Timing of a familiar named item — record candidate.** First verified completion/acquisition of an item already common in that player's comparable build path. Show the actual clock time. Purchases must be distinguished from assembly, inventory arrival and delivery. Compare the same hero, role, patch and comparable prior build commitments. Faster timings may reflect better economy, but skipping necessary defensive or lane items can make the build worse. Valid after a loss as a timing record, not proof of correct itemization. Personal records are understandable and plausibly shareable; aspirational timings are examples, not prescriptions. **Confidence: moderate; semantic verification required.**

**M5. Level/XP milestone timing — corroborating metric.** Time reaching a named level or XP at a fixed checkpoint, using a verified level-event mapping. It can reveal access to a hero's abilities; it also reflects lane sharing and teammate sacrifices. Compare within hero and role. Earlier support level six is not automatically better if obtained by taking the core's lane. Keep personal trends and milestones conditional; avoid default XP-racing challenges. Measurement is direct; “tempo” is an inference. **Confidence: moderate for facts, low-to-moderate for growth.**

**M6. Deaths before ten minutes — contextual reliability metric.** Count death events in [0, 600) seconds, with pre-horn events separately identified and death semantics verified. All roles can see the count; it has different implications for a carry and an initiating support. Zero is a floor, not an endlessly improving PR. Hiding, conceding lane resources, or refusing a valuable trade can game it. Evaluate jointly with the player's opening resources and involvement. A loss does not erase fewer early deaths, but the app cannot call them fewer mistakes. **Confidence: moderate for progress with context.**

**M7. Rapid repeat-death frequency — exploratory reliability metric.** Count deaths within a predeclared interval after the player's previous respawn; ideally distinguish tactical re-entry from an unproductive repeat death. Death-to-death gaps are not equivalent and must be labeled if used. Compare a fixed phase within hero/role; low-count uncertainty is substantial. Staying disengaged can improve the statistic. A falling rate can support a descriptive trend after losses, but cannot establish tilt control or better judgment. **Confidence: low-to-moderate; not a first-release target.**

**M8. Credited kill involvement — contribution context.** Numerator: distinct team hero kills on which the player has kill/assist credit. Denominator: valid team hero kills in the same window. Show “involved in 9 of 18,” not merely 50%. When the denominator is zero, the rate is unavailable. Global abilities, split pushing, team pace and draft affect the result; maximizing it encourages unnecessary fighting or tagging. Useful across roles when compared within hero and role, including losses, but not a standalone improvement score or challenge. **Confidence: high for verified credits, low-to-moderate for skill interpretation.**

**M9. Attributed enemy observer wards destroyed — support accomplishment.** A verified event count, ideally linked to meaningful removal opportunities and downstream information denial. Raw destruction is measurable if attribution/type semantics are sound; opportunity quality is not. Sentries and observers must be separated. Compare the same support hero/role and fixed duration window, but do not imply higher is always better. Enemies can place more wards; hunting wards can be dangerous; kill credit may omit shared detection effort. A bounded record can be proudly shared after a loss as an accomplishment. **Confidence: moderate for accomplishment, low for growth.**

**M10. Camps stacked, eventually resources enabled — support candidate.** Ideal: safe extra resources created and secured by the team without greater opportunity cost elsewhere. MVP approximation: verified stacks, explicitly called stacks, not gold created. Requires nonzero semantic samples; the early STRATZ specimen could not settle `campStack` semantics. Hero tools, blocked camps, timing, map control and role matter. Raw counts invite abandoning lanes or stacking for the enemy. Treat as an occasional personal accomplishment, not a universal support goal. **Confidence: conditional/low until field and behavioral validation.**

**M11. Hero damage in defined engagements — contribution descriptor.** Bound damage to validated fight windows and distinguish relevant targets when possible. This is more meaningful than whole-match damage but still depends heavily on hero, enemy durability, resources and fight length. Damage healed immediately or dealt to low-value targets may inflate the number. Use a hero-specific event highlight with engagement context; avoid cross-hero PRs and default challenges. A fight in a loss can be memorable without proving successful fighting. **Confidence: low-to-moderate; requires better event validation.**

**M12. Hero-specific spell connection — narrow mastery experiment.** Ideal: correct targeting and timing per legitimate cast opportunity. Approximation: a whitelisted ability's verified target connections divided by applicable casts, with multi-target and repeated ticks handled explicitly. Accuracy alone rewards withholding difficult but necessary casts; “targets affected” does not prove good usage. Only heroes and patches with validated semantics qualify. Useful for a small experimental mastery track; no generic spell-efficiency score. **Confidence: low for broad MVP, potentially moderate for a carefully audited ability.**

**M13. Recovery after a weak opening — research-stage progress concept.** Compare later resource development among games that were already weak at a predeclared early checkpoint. Do not define weakness after examining the whole match. Opportunities, allied space creation and regression to the mean dominate interpretation. Use “your next ten minutes” and actual values; not “mental resilience” or “comeback skill.” This can matter in a loss but requires enough weak-opening cases and independent validation. **Confidence: low-to-moderate; not a launch claim.**

**M14. Repeatable opening standard — strongest derived progression concept.** Across a fixed, predeclared set of comparable matches, report how often the player reaches a frozen personal resource target while remaining within a bounded early-death condition. The two facts remain visible separately. This records repeatability rather than inventing a score. Conditions do not prove teamwork and can still be gamed. Personal comparison is strongest; standardized cohort versions need the same target/definition across players. Good candidate for an achievement and a rolling trend; do not keep raising the target automatically. **Confidence: moderate, product thresholds unvalidated.**

**M15. Hero/role history milestones — identity and engagement, not skill.** Examples: first recorded ranked match on a hero, a familiar hero returning after a break, or an opening standard documented on a second hero. Counts are direct but not mastery. A game total should never receive “expert” or “master” status by itself. Works across modes as labeled history, with mode-specific performance records. Self-comparison is meaningful; rank benchmarking usually is not. Plausibly shareable through identity and familiarity rather than superior performance. **Confidence: high for classification as history; low for retention impact.**

## 6. Metric evaluation matrix

These are **research judgments, not measured scores**. They rank candidates by safe product usefulness, with description and growth kept separate. H/M/L mean high/moderate/low; V = validity as evidence of growth, F = feasibility from the inspected STRATZ evidence, A = actionability, U = understandability, P = personalization potential. R, N, G and State are dependencies/risks, so H is a caution. Share is a hypothesis, not observed behavior. Conditional feasibility is marked C.

| Priority | Metric | V | F | A | U | P | Role dependence | Noise | Gameability | State | Share | Recommended use |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | M1 CS10 | M | H | H | H | H | H | M | M | M | M | Core record + bounded trend |
| 2 | M14 repeatable opening | M | H* | H | H | H | H | M | M | M | H | Derived milestone; *needs M1/M6 validity |
| 3 | M6 early deaths | M | H | M | H | H | H | M | H | M | M | Context/trend; no standalone virtue badge |
| 4 | M4 named item timing | M | C | H | H | H | H | M | H | H | H | Familiar-build record |
| 5 | M2 NW10 | M | H | M | H | H | H | M | M | H | M | Corroboration, not another score |
| 6 | M8 kill involvement | L–M | H | M | H | H | H | H | H | H | M | Contribution description |
| 7 | M9 observer destruction | L | C | M | H | H | H | H | M | H | H | Support accomplishment |
| 8 | M15 history milestone | — | H | L | H | H | L | L | M | L | H | Identity, never growth by itself |
| 9 | M5 level timing | L–M | C | M | H | H | H | M | H | H | M | Conditional corroboration |
| 10 | M3 later farm window | L–M | H | M | H | H | H | H | H | H | M | Contextual trend |
| 11 | M10 stacks | L | C | M | H | H | H | H | H | H | H | Conditional support event |
| 12 | M7 repeat deaths | L–M | C | M | H | H | H | H | H | H | L | Research-stage trend |
| 13 | M13 weak-opening recovery | L–M | C | M | M | H | H | H | H | H | H | Research-stage trend |
| 14 | M12 spell connection | L–M | C | H | H | H | H | H | H | H | H | One-hero experiment |
| 15 | M11 engagement damage | L | C | M | M | H | H | H | H | H | H | Event description |

### Recognition and comparison eligibility

Y = suitable for the named purpose with the qualifications above; C = conditional; — = do not offer by default. “Loss” means still interpretable, not statistically independent of outcome. “Care” and “Share” are untested hypotheses. Every row's raw phenomenon is direct or derived; **every growth claim remains a proxy**.

| Metric | Direct/derived observable | Personal history | Matched cohort | PR | Achievement | Challenge | Trend | Loss | Casual comprehension | Likely care / share |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 | Count at checkpoint | Y | C | Y | Y | C | Y | Y, bounded | High | Core H / M |
| M2 | Resource level | Y | C | C | C | — | Y | Y, bounded | High | Core M / M |
| M3 | Window count/rate | Y | C | C | C | — | C | C | High | Core M / M |
| M4 | Acquisition timestamp | Y | C | Y | Y | — | Y | Y, bounded | High | H / H |
| M5 | Level timestamp | Y | C | C | C | — | C | C | High | M / M |
| M6 | Event count | Y | C | — | C, paired | C, paired | Y | C | High | M / M |
| M7 | Event interval/rate | Y | C | — | C | — | C | C | High | M / L |
| M8 | Credited event share | Y | C | — | C | — | Y, descriptive | C | High with denominator | M / M |
| M9 | Attributed event count | Y | C | C | Y | — | C, descriptive | Y, factual | High | Support H / H |
| M10 | Verified stack count | Y | C | C | C | — | C, descriptive | Y, factual | High | Support H / H |
| M11 | Damage in detected event | C | C | C | C | — | C | C | Moderate | H / H |
| M12 | Cast/connection ratio | Y | C | C | C | C, experimental | C | C | High if ability named | Hero specialist H / H |
| M13 | Conditional change | Y | C | — | C | — | C | C | Moderate | H / H |
| M14 | Successes / fixed attempts | Y | C | C, fixed blocks | Y | C | Y | C | High | H / H |
| M15 | Verified history event | Y | — | — | Y | C, optional exploration | Y, history | Y | High | H / H |

No row has high established validity as an outcome-independent skill measure. That is the honest result of the research, not a reason to abandon all measurement. Narrow records can be valuable without making broad causal claims.

## 7. STRATZ feasibility: ideal → approximation → MVP

### What the existing research supports

The repository is a feasibility reference, not this product's specification. Its 365-day retrospective, non-MMR policy, finding taxonomy and publication rules answer a different question. This document proposes no changes to that system.

The inspected research establishes timestamped events and resource trajectories on specimens, richer later discovery data, and important ambiguity. The early specimen's 91%/93% role-field coverage is **one account's history**, not a platform guarantee. Later corpus work expanded the evidence, but discovery-only findings are not independent validation of a consumer progression system. [R1][r1] [R2][r2] [R4][r4] [R5][r5]

| Ideal capability | Measurable approximation and inspected evidence | MVP interpretation | Remaining gate |
|---|---|---|---|
| Last-hit execution under contest | `stats.lastHitsPerMinute` deltas, optionally detailed CS events | CS by fixed time | Exact interval alignment, nonzero tail behavior, summoned-unit treatment; does not reveal missed opportunities |
| Effective early resource acquisition | `stats.networthPerMinute` | NW at fixed time | Snapshot timestamp alignment; resources are not causal skill |
| Efficient resource development | Last-hit deltas; XP deltas; NW snapshots | Fixed-window count/rate | Do not sum running-average GPM or call NW change earned income |
| Early survival without surrendering contribution | `deathEvents`, resource checkpoints | Early-death count beside resources | Death/reincarnation semantics; trade value unavailable |
| Correct itemization and power timing | `itemPurchases`; later inventory/spike research | Named timing only where assembly/acquisition is verified | Purchase ≠ delivered usable item; build suitability not inferred |
| Coordinated fight contribution | `killEvents`, `assistEvents`, ten-player credits | Credited kill involvement | Event identity, valid denominators, duplicate attribution; fight participation is different |
| Useful enemy vision removal | Ward/destruction surfaces; later vision research | Typed, attributed observer removals if audited | Removing a ward ≠ information value; detection credit may be shared |
| Resources enabled for allies | `campStack` and possible later resource events | Stack count only if semantics established | Early samples all zero; must verify attribution and actual resource benefit |
| Correct spell execution | Cast reports / ability playback surfaces | One whitelisted hero ability, later pilot | Denominators, target relevance, spell variants, repeated ticks, cast opportunity |
| Timely objective conversion | Objective events, kill/fight windows, state | Team event in history, no individual score | Window choice, opportunity, attribution, objective availability |
| Good positioning/map awareness | Position events and later spatial research | None in MVP beyond factual event location | Information available at the time, threat range, ally plans and alternatives |
| Adaptability/mental recovery | Repeated matched contexts and history | Observable changes, not personality diagnosis | Confounding, regression to mean, adequate comparable opportunities |

**Critical semantic controls from repository evidence:** last hits and denies are minute deltas; net worth is a level; parsed GPM is a running average; XP arrays contain gains; similarly named arrays must not be treated uniformly. `stats` may exist with all-null members. `roleBasic` is not a trustworthy substitute for role. Team kill arrays in the specimen counted opposing deaths, including uncredited deaths, so a kill-involvement denominator must be verified rather than copied. Level arrays are timestamps, with shape questions documented. [R1][r1]

The overview and field inventory differ in how they describe access tier versus replay provenance for some match-level context. Therefore, availability in a history request must not be equated with availability on every unparsed match. Query-path coverage and semantic correctness are separate gates.

### Later repository evidence changes the interpretation, not the promise

The September 5 pipeline reports reliable between-player differences in several richer dimensions, including vision coverage and death clustering. It also reports low reliability for fight conversion and zero estimated between-player signal for some attractive concepts under its estimator. These are useful prioritization warnings, not universal declarations that a skill does not exist. Cross-player trait reliability is not within-player change sensitivity; hundreds of historical observations do not establish that ten new matches reveal improvement. [R5][r5]

The repository's discovery screen pooled modes with adjustment and used normalized game progress in some analyses. **Do not reuse that choice for clock-time PRs.** It may be defensible for a specific descriptive research question; it does not make minute ten of Turbo comparable to minute ten of standard Dota. It also does not validate pooling for this new product. [R4][r4]

### Capability gates, independent of API cost

For each promoted metric, require: field presence; semantic agreement with replay/scoreboard evidence; coverage by hero/role/mode/patch; error and missingness analysis; contextual validity; player comprehension; and resistance to harmful optimization. A successful GraphQL response proves only transport. No API-cost assumption should decide what meaningful progress is, but unavailable information must still limit claims.

The ideal positioning/vision problem genuinely needs information-state evidence. A 2026 Dota visibility paper uses both team perspectives and annotated minimap video to study this missing layer. This is promising research, not a reason to assume ordinary aggregate telemetry already measures awareness. [^30]

## 8. Baseline and personalization model

### A year is an archive, not a universal statistical baseline

Use approximately 365 days to establish history, recurring heroes/roles, mode mix, available measurements and previous records. Then derive **metric-specific recent references** from comparable games. A hundred old support matches should not make a five-game current carry baseline look mature.

Maintain three references:

1. **Historical record book:** all observed eligible matches in the available archive, grouped into comparable eras. Label records “since tracking began” or with explicit dates; do not claim lifetime coverage from 365 days.
2. **Starting reference:** a frozen snapshot at enrollment or at the start of a chosen focus. This prevents moving the goalposts and allows an honest before/after story.
3. **Current form:** a rolling recent distribution, updated after new games, with its own count and uncertainty. This helps choose an achievable next focus without erasing the starting point.

The repository's historical methodology uses recency and session-balanced weighting; its provider contract also records truncation rather than presenting incomplete history as complete. Those are valuable principles, not a reason to copy an old estimator or hidden weight system. [R6][r6] [R7][r7]

### Baseline contents

For every active measurement, retain units, clock window, eligible count, date coverage, current context, missing count, median, middle range, relevant tail/record, and evidence status. Describe the middle 50% as “your usual range” only after testing comprehension; it is not a confidence interval. Record rare and outlier performances separately.

Hero-role frequency and mode mix determine which tracks are relevant. They do not determine strengths. A strength should mean a reliably favorable measurement within a defined reference, not “you play this hero often.” A weakness should remain a possible focus, not a negative identity label.

### Sparse data and fallback

Start with hero × role × mode × compatible patch era. When this is too sparse, broaden only if the metric's semantics permit it, and label the changed comparison. It may be reasonable to show role-level early deaths descriptively; it is usually not reasonable to compare a hero-specific item timing with every hero in that role. Cohort shrinkage can stabilize an estimate internally, but the product must not present a cohort-influenced estimate as purely the user's own baseline.

**Provisional operational starting rules, not validated thresholds:** fewer than five comparable matches means history only; five to nineteen means provisional descriptive ranges; twenty or more may support a personal benchmark after stability checks. A strong growth claim requires an effect large enough to matter and uncertainty appropriate to that specific metric, not merely reaching twenty games. Rare spells, weak-lane recovery and observer removal opportunities may require much more history.

A recent reference might start with up to 30 comparable games within 90 days. Test alternatives rather than hard-code this as science. Do not borrow old-patch matches to reach a count when mechanics materially changed. If the reference is stale, say so. A new or returning player should still receive an activity journal while benchmarks accumulate.

### Change estimation and false discoveries

Compare predeclared, non-overlapping blocks for growth claims. Resample at an appropriate dependence level, such as play-day or contiguous match blocks, rather than treating every minute or spell as independent. The product's activity unit remains one match; dependence grouping is an analytical property, not an extra activity type.

Separate an observed delta from a supported change. Look for persistence across a later block, robustness to context mix, and stable metric definitions. If many metrics, windows and hero combinations are searched, attractive deltas will occur by chance. Predeclare primary metric families and evaluation times; use multiplicity-aware inference for promoted growth claims, or keep the copy purely descriptive. Repeatedly peeking at a rolling trend and stopping at the first favorable p-value is not valid confirmation.

Records do not need a significance test to be records. They do need correct coverage and scope. Under an idealized continuous, independent, unchanged distribution, the next observation is a record with probability 1/(n+1). Real Dota violates those assumptions, but the implication survives: records are frequent in short histories and scarce in long ones. Record count cannot itself be the growth metric.

## 9. Benchmarking and mode model

### Self versus cohorts

| Reference | Best use | Main risk | Recommendation |
|---|---|---|---|
| Frozen personal starting reference | “What changed for me?” | Old context becomes obsolete | Default for progression; retain era/context |
| Recent personal history | “What is normal for me now?” | Moving target can hide real improvement | Default for match interpretation; separate from starting reference |
| Same hero + role + mode | Meaningful task comparison | Sparse samples and remaining matchup differences | Minimum conceptual matching for many metrics |
| Same rank plus hero/role | Locating a measurement among comparable peers | Selection bias, changing rank, weak coverage | Optional, explicit sampling frame and period |
| One rank above | A reachable reference/example | Implies that matching one statistic causes promotion | Optional aspiration, no promotion claim |
| High-skill pubs | Learning possibilities, build/timing examples | Different opposition and opportunity | Exploration reference, not default goal generator |
| Professional matches | Coordinated strategic examples | Severe transfer and selection limits | Context library, not ordinary pub target |
| Friends/stack | Shared memories and social relevance | Shaming, incompatible roles, tiny samples | Opt-in factual comparison; no support-vs-carry leaderboard |

**Self-comparison is a sensible default, not proven universally more motivating.** Some players want rank and peers; others experience such comparison as discouraging. Test which reference players choose and understand. A low-ranked player can set a meaningful personal best even when it is below a peer median. A high-ranked player can improve while raw output stays flat because opposition improves.

For cohort percentiles, specify whether the unit is **matches** or **players**. “Higher than 70% of eligible matches” is not “better than 70% of players.” Player-level estimates require comparable aggregation and adequate data per player. Use unique-player accounting or weighting so prolific accounts do not silently dominate a player comparison. Record contemporaneous rank when available; current profile rank is not historical rank. The existing repository deliberately excluded rank, so it cannot automatically supply these cohort benchmarks. [R7][r7]

Keep raw units visible and version peer references. Leetify's published benchmark change illustrates how a rating can move even when the player has not changed. Do not award a breakthrough solely because the cohort was recalibrated. [^14]

### Modes

| Mode/context | Shared tracking | Baseline/record decision | Reason |
|---|---|---|---|
| Standard ranked | Matches, heroes, raw events, outcomes | Initial performance pilot; dedicated ranked references | Competitive context is explicit |
| Standard unranked | Same event vocabulary when rules match | Separate starting references; test pooling empirically later | Player goals, compositions and experimentation can differ |
| Turbo | History and compatible event types | Dedicated records and definitions; exclude from standard PRs | Accelerated resources and altered game structure break simple timing comparison |
| Ability Draft / custom / event modes | Labeled history if supported | Exclude from ordinary hero mastery/role baselines | Hero name may no longer define the same task |
| Bots / practice / private lobbies | Optional separate practice history | No public-match PR pooling | Difficulty and coordination differ; easy to manipulate |
| Abandons / incomplete data | Preserve labeled match entry | Exclude affected measurements, not necessarily all history | Valid partial facts can remain; never impute missing outcomes |

Valve's original Turbo description explicitly changes gold/XP, towers and respawn conditions. Exact modern parameters should be patch-versioned later; a universal multiplier is not adequate. Fixed fractions of final match duration also leak future context and compare different strategic phases. [^31]

Event definitions such as “observer destroyed” can work across modes while their **performance comparisons remain mode-specific**. Eventually, pooling ranked/unranked should depend on invariance tests and user expectations, not just a failed significance test in a small sample.

## 10. Personal records

### A record must name the contest

A useful record has a metric, unit, direction, hero/role, mode, compatible era, observation window, previous mark, eligible history size, and coverage label. “66 last hits by ten minutes — your best recorded Luna carry opening in ranked this patch” is verifiable. “Best Dota ever” is not.

| Record type | Decision | Example |
|---|---|---|
| Best within one match | Use as event highlight, not automatically personal progress | Largest verified multi-target connection in that game |
| Hero + role + mode best | Strongest default | Fastest familiar item acquisition in comparable games |
| Role-wide best | Conditional on metric comparability | A bounded resource checkpoint, with hero shown prominently |
| Recent-period best | Useful for mature accounts, label the period | Best recorded opening in the last 90 days |
| Lifetime best | Only with lifetime coverage | Otherwise say “best in recorded history” |
| Fixed-block consistency record | Promising, fewer weak games can matter | Best predeclared ten-game opening block |
| Improvement milestone | Separate from extreme record | Sustained higher median confirmed in a later block |
| Percentile breakthrough | Conditional, frozen reference | First supported movement above a stated cohort threshold |
| Unusual accomplishment | Valuable as history, not growth | Verified multi-kill, observer-removal event, rare hero action |

Do not create endless slices until every match wins something. Consolidate correlated records into one opening story. A tied floor, such as another zero-death opening, is a repeat achievement at most, not a new PR. Avoid maximum survival time and maximum match damage as flagship records: time exposure and passive play can dominate them.

For timing records, rounds and ties must respect provider resolution. Missing the target item is not “infinite time” and not failure: the build may correctly omit it. Preserve previous marks when a patch starts a new era. If late data revises a record, explain the correction and update dependent recognitions consistently.

**Hypothesis, moderate confidence:** scoped PRs can provide a rewarding match-level moment. Their frequency, credibility and longevity need a replay-history simulation before product commitments.

## 11. Achievement system

Achievements should recognize one of four things, with distinct language:

1. **A verified accomplishment:** “You removed four enemy observer wards in the first 30 minutes.” Factual event, not support mastery.
2. **A repeated personal standard:** “Three comparable openings at 55+ last hits and no more than one early death.” The conditions are the achievement.
3. **A supported improvement milestone:** “Your recent opening benchmark moved from 52 to 58 and held in the next block.” Requires actual validation and a useful effect, not just an attractive delta.
4. **Personal history or exploration:** “Your first recorded ranked game on this hero.” No skill implication.

A mastery milestone should combine repeated role/hero-relevant evidence, adequate opportunities and persistence. Until validated, call it a benchmark milestone or hero journey. Do not issue mastery levels purely for game counts.

Rarity requires a denominator: percent of eligible observed matches, or percent of eligible players within a stated period. A small convenience sample cannot support “only 1% of Dota players.” For rare achievements, uncertainty in the rarity estimate matters especially. Absence from collected data is not proof of uniqueness.

Avoid currencies, escalating daily tasks and dozens of achievement tiers in the pilot. Recognition itself must first demonstrate value. If the measurement is boring or misleading, a badge does not fix it.

## 12. Personalized challenges

### Challenge generation is a measurement decision

Offer one optional focus at a time, with two or three choices when enough valid options exist. Let users decline, pause or choose “just track.” The app should explain why the challenge appeared, the comparison set, what counts, and how many **eligible matches** it covers. Do not require a calendar deadline that pressures additional play.

A bounded generator can select from a small reviewed catalog using the player's frozen baseline. Do not ask a language model to invent unrestricted targets. Automatic resolution needs verified fields and eligibility, not a confident narrative.

### Initial challenge candidates

| Focus | Example | Conditions and risk |
|---|---|---|
| Personal opening performance | “Your recent Luna carry median is 52. Reach 57 by ten minutes in one of your next three comparable ranked games.” | Experimental: farm can be prioritized badly; pair with early survival context and do not call completion proof of better play |
| Repeatability | “In three of your next five comparable games, reach your 55-CS opening standard with at most one death before ten.” | A compound measured standard, still not full teamwork validation |
| Maintaining a strength | “Keep your established opening standard across your next small set.” | Optional; do not punish exploratory games outside eligibility |
| Hero exploration | “If you choose to play another familiar carry, track an opening benchmark there.” | No forced pick, no claim of transfer from one match |
| Support focus | Initially prefer recognition after the fact | Raw ward/stack quotas are too easy to optimize badly; develop opportunity-aware candidates with replay review |

An early-death challenge on its own is too easy to misunderstand as “avoid all risk.” Pairing it with resource performance reduces one failure mode but does not prove good Dota. If testing shows players divert farm, avoid necessary fights or resent the goal, remove the challenge rather than add an opaque correction score.

### Difficulty calibration

Choose attainable targets from the observed personal distribution, with a minimum meaningful step and rounding in familiar units. Do not assume “10% higher” has the same difficulty on every metric. A target historically reached in 25% of comparable games has, **under an independence assumption**, about a 58% chance of at least one success in three attempts: 1 − 0.75³. Dota attempts are dependent, so empirical sequence replay is required. This illustrates why a single-game percentile cannot be called challenge completion probability.

Do not target an anomalously bad recent game; regression to the mean would manufacture “success.” Freeze target, eligibility and attempt count before the first attempt. Reassess after completion or cancellation, not mid-challenge. Give users a choice of stretch, consistency or maintenance when feasible; no evidence supports an automatic weakness-only policy.

### Resolution and failure handling

States should include completed, in progress, paused, canceled, and not assessable. Unparsed data should wait or become not assessable according to a declared policy; it must not secretly count as success or failure. Valid eligible attempts should be included regardless of W/L, with abnormal-match exclusions fixed in advance. A deliberately avoided eligible match cannot be erased merely because its result was inconvenient.

If a target is missed: “Not reached in this set. Your results were 51, 54 and 53; your starting median was 52.” Do not describe this as regression. Offer retry, a different focus or no challenge. After success, acknowledge it without automatically ratcheting difficulty. Strength maintenance and ordinary play must remain legitimate.

**Boundary:** performance challenges are a form of light guidance, even without an AI coach. Their behavioral effects must be owned and evaluated; calling them “not coaching” does not remove responsibility for bad incentives.

## 13. Growth in losses: what can and cannot be claimed

### Three different meanings of “independent of winning”

1. **Outcome-independent calculation:** the formula does not use final W/L. Many metrics satisfy this.
2. **Outcome-independent distribution:** the metric behaves similarly in wins and losses. Many do not, because both reflect shared match state and capability.
3. **Outcome-independent value:** the observation is still meaningful and worth recognizing after a loss. This is the achievable product goal.

A runner's 5K time has a relatively stable task definition. A Dota carry's 66 CS at ten is a narrower fact under varying opposition. It can be a legitimate recorded best in a lost match; it does not establish that the player's overall game was better, or that those creeps were acquired through better decisions.

### Interpretation by class

| Signal | Meaningful in a loss? | Required interpretation |
|---|---|---|
| Fixed early resource checkpoint | Yes, often | Opening performance record; favorable lane/opportunity remains possible |
| Familiar item timing | Yes | Timing fact; build correctness and item use remain separate |
| Repeated early performance across blocks | Potentially strong | Comparable contexts, effect size, persistence and tradeoff checks |
| Observer destruction / stacks | Yes as accomplishments | Not proof of useful vision or support growth |
| Spell event | Yes if verified | Connection/event quality is narrower than good spell decisions |
| Kill involvement | Descriptively | Team pace, hero function and denominator remain visible |
| Whole-game GPM / damage / KDA | Weak alone | Strongly state- and duration-dependent, with obvious padding routes |
| Low deaths | Conditional | Could mean effective survival or refusal to contribute |
| Team objective conversion | Cannot remove outcome context | Whether the opportunity produced an objective is part of what is being measured |
| MMR / win rate | No for a single-loss “growth” claim | Valuable longer-horizon competitive result, not replaced by the journal |

### Outcome must remain visible without controlling every comparison

Display the actual match result. Do not use celebratory copy to imply an undeserved loss or teammate blame. “A new opening best in a loss” is honest. “You carried; your team failed” is not supported.

Do not simply compare losing games with losing games as the universal fix. Final outcome happens after early performance and depends on all players. Conditioning on it can create selection bias. Likewise, adjusting away the team's entire net-worth trajectory can remove part of the player's actual contribution. Duration is also affected by gameplay; a duration-adjusted statistic answers a different question from a fixed early checkpoint.

Use pre-window context where possible, show game-state annotations, and test sensitivity to alternative reasonable comparison sets. Treat win/loss-stratified results as diagnostics rather than the sole baseline. Retain W/L as an external reality check: if optimizing a metric consistently accompanies harmful choices or worse outcomes under a credible evaluation, reconsider the metric. Conversely, no detectable win-rate change in a small pilot does not disprove a modest local skill improvement.

### Validation required for a stronger growth claim

Compare model claims with blinded expert replay judgments focused on the named skill, ideally hiding final results for early-phase judgments. Examine disagreements, not just aggregate agreement. Test within-player longitudinal changes, temporal holdouts, patch changes and whether improvements survive a later block. Ultimately, a randomized focus intervention can test whether pursuing the target improves the intended behavior without harmful substitution.

**Conclusion, high confidence:** players can record worthwhile performances in losses. **Conclusion, moderate confidence:** repeated contextual performance can provide evidence consistent with skill growth. **Not established:** telemetry alone can reliably certify better decision-making or total contribution independently of outcomes.

## 14. Retention and streaks

The desirable loop is returning to understand play the user already chose to undertake. It is not increasing matches at any cost.

Logged-streak research finds that a streak can become a goal in itself, and a broken streak can reduce subsequent engagement. This supports caution about compulsion and discontinuation, but does not quantify Dota-specific harm. [^32]

| Mechanism | Value | Risk | Decision |
|---|---|---|---|
| Daily play streak | Easy to understand | Queuing to preserve a counter; penalizes breaks | Exclude from MVP |
| Consecutive wins | Familiar excitement | Outcome pressure and tilt-driven queueing | Historical fact only, no retention task |
| Consecutive improvement | Sounds aligned with progress | Statistically implausible expectation; punishes variance | Reject |
| Eligible-game consistency run | Shows repeatability | Can reward risk avoidance and cherry-picking | Use a bounded set; freeze criteria |
| Challenge completion streak | Acknowledges focus | Escalating pressure and goal substitution | Prefer completed sets, no unbroken chain |
| Weekly activity | Broad rhythm without daily pressure | Still treats more play as desirable | Neutral history, optional personal preference |
| Weekly review habit | Creates reflection | Checking can become obligation | Optional, no lost rewards for absence |
| Hero journey | Identity and accumulated memories | Repeated picks for points | Celebrate events without required game volume |

Retention should be measured among people who continue playing Dota, and separately among those who pause. Useful measures include return after an eligible match, voluntary recap revisits, challenge opt-out, perceived pressure, and whether players say the app made them queue when they otherwise would have stopped. Avoid optimizing notification opens or match volume as the sole success metric.

Do not infer tilt, fatigue, sleep or mental health from requeue speed or losses. The repository's post-loss behaviors are observations; they are not psychological diagnoses. Breaks should preserve the record book and suspend active expectations without penalty. [R4][r4]

## 15. Shareability model

### What a player is sharing

The share object should answer a social question: **what does this say about me, and why would this recipient care?** It can express pride, recognition, surprise, humor or shared memory. A technically valid metric with no social meaning may be useful privately but weak for acquisition.

Spotify demonstrates identity-oriented data storytelling and sharing mechanisms. Research on online transmission links sharing to emotion and other content properties, but its news/content settings do not establish a Dota referral engine. These sources support creative hypotheses, not viral-growth forecasts. [^23] [^33]

| Object | Likely audience/emotion | Honest content | Integrity requirement |
|---|---|---|---|
| Scoped PR | Friends who know the hero; pride | New mark, old mark, hero/role/mode/window | Record scope and result visible |
| Repeatability milestone | Stack; recognition | A formerly occasional opening became repeatable | Fixed criteria and denominator |
| Improvement delta | Self and friends; surprise | 52 → 58 CS, with comparison periods | Observed change vs supported growth distinguished |
| Support accomplishment | Stack; appreciation | Verified observer removals or enabling actions | Do not convert counts into “best support” |
| Hero journey | Hero specialists; identity | Familiar heroes, meaningful returns, verified milestones | No invented personality diagnosis |
| Unusual event | Friends; amusement | A genuine rare-looking moment | Call it unusual unless population rarity is established |
| Weekly/monthly recap | Friends who played together; memory | A small number of specific moments | No fabricated highlights to fill a template |
| Rank progression | Competitive peers; pride | Verified rank change over time | No claim that one metric caused it |
| Cohort comparison | Competitive peers; status | Named sample and statistic | Never “top 1% of Dota” from a biased sample |

**Initial content hypothesis:** concrete hero-specific records and recognizable repeated changes will outperform abstract percentile or composite-score cards. Identity may share more easily than honest small deltas; that is acceptable if it is labeled history rather than skill.

Offer optional captions such as “The throne fell. The opening record didn't.” Keep the factual statement attached: “66 CS at 10:00, Luna carry, ranked, best in 27 recorded comparable matches this patch.” Avoid implying the entire loss was progress. Give users control over rank visibility, profile identity and destination; never auto-post or expose teammates' identities or blame narratives.

Sharing must be measured beyond button taps. Distinguish intent, export/share-sheet activation, actual attributable visits, connected accounts and retained referred players. External share completion may not be fully observable. Compare private usefulness and sharing performance separately: deleting useful low-share metrics would make the product worse.

## 16. Product loop and calendar/history

**Baseline → play → ingest → verify → interpret → recognize when earned → optional focus → history → recap → repeat.**

The verification step belongs before interpretation. Partial ingestion produces a pending or limited record, not a confident summary. Recognition is conditional; a normal match can simply be recorded as normal.

The calendar should answer more than “did I play?” It should recover:

- what was played, in which mode/role, and with what result;
- which moment changed a record or completed a focus;
- which evidence contributed to a later trend;
- when a new hero, role, patch or return from a break began;
- whether missing analysis explains a quiet period;
- what mattered in a week without a rank increase.

Use the date a match happened for its historical entry, with a separate recognition/analysis timestamp when data arrive later. Let a recap point back to the actual matches that support it. A correction should not create a second achievement. The weekly grouping should use a user-chosen/local timezone, not infer it from the game server.

A useful week can contain five ordinary matches, one memorable event and no supported trend. It is better to say “no clear benchmark change yet” than turn calendar density into progress. Over months, annotations make the record legible: changed main hero, entered a new patch, returned after time away, completed a focus, or sustained an opening standard.

## 17. High-level experience and information architecture

This is a conceptual content structure, not screen design:

| Area | User question | Core content |
|---|---|---|
| Recent activity | What changed after my match? | Result, two or three relevant facts, earned recognition, analysis availability |
| Personal progress | What is becoming different or more repeatable? | Starting/current references, raw units, scope and evidence status |
| Hero/role journeys | Where is my history developing? | Relevant records, repeated standards, exploration and context changes |
| Focus | What am I choosing to track next? | One optional challenge, fixed conditions, attempts, pause/decline |
| History and recaps | What is worth remembering? | Calendar, match evidence, milestones, weekly/monthly summaries |

Sharing is available from an appropriate factual object rather than requiring a separate social network. Benchmark context and methodology must be available without making the main experience read like a statistical paper. Players should always be able to discover why a comparison was made and why a match did not count.

## 18. Smallest MVP that can test the thesis

### Narrow the measurement population, not the ambition

**First measurement pilot:** standard ranked players who repeatedly play position 1 on a small hero pool. Use M1, M2 and M6 as one opening interpretation, with M4 only for verified familiar builds. Derive M14 from those observations and add M15 as identity/history. Show at most three primary facts after a match, with no overall player score.

**Parallel research cohort, not a second product build:** include position-4/5 players in interviews and replay labeling. Test M8/M9 and, if semantics support it, M10 as factual contributions. If supports find those facts shallow, acknowledge the limit and keep the initial positioning narrow. Do not launch as a complete five-role growth system until support value is established.

The prototype needs automatic recognition, one optional reviewed challenge type, a history, one recap, and an exportable share object. It does not need a full social feed, AI conversation, real-time overlay, generalized recommendation engine, composite ratings or elaborate reward economy.

### High-level plan

| Stage | Deliverable | Exit question |
|---|---|---|
| Measurement audit | Operational definitions and replay-checked measurements | Are counts/timings correct and interpretations bounded? |
| Retrospective simulation | Replay existing histories in temporal order | How often do true, non-redundant records/trends appear, and for whom? |
| Content and player research | Real-history examples, comprehension interviews, share choices | Do players recognize themselves and distinguish records from improvement? |
| Longitudinal pilot | Several weeks of personal tracking with optional focus | Does value persist through ordinary games, losses and plateaus? |
| Product decision | Evidence-based scope and metric selection | Build, narrow, pivot to history, or stop? |

A suggested discovery sample is 20–30 varied players; a suggested longitudinal feasibility pilot is 40–60 players over roughly six weeks. These are planning hypotheses for qualitative and usage learning, **not powered sample sizes for proving a retention or skill effect**. An efficacy or acquisition experiment needs its own power analysis and predefined endpoints.

The primary success outcome should be **players can identify a specific, credible change or accomplishment they value and return for another summary without feeling pressured to play**. Track comprehension, usefulness after losses, voluntary revisits and unwanted behavioral substitution. Referral conversion is a separate commercial endpoint. Record novelty must not be mistaken for long-term retention.

## 19. Later opportunities and “do not build” list

### Later, if the measurement earns it

Opportunity-aware support tracks; a small number of audited hero mechanics; replay-supported save/positioning events; context-specific objective conversion; careful transfer milestones; aspirational cohort libraries; user annotations; and other games with more repeatable tasks. Each game needs its own constructs and feasibility assessment. A universal cross-game score is not the natural next step.

### Do not build

| Seductive idea | Why it fails |
|---|---|
| Universal “Dota fitness” score | Unclear construct and hidden tradeoffs; confuses precision with validity |
| IMP as personal growth | Outcome-correlated model behavior is not longitudinal skill validation |
| GPM/XPM/CS leaderboard across roles | Rewards role/resource access more than comparable execution |
| “Death quality” from nearest-ally distance | Cannot establish sacrifice, information or alternatives |
| Ward count = vision skill | Counts inputs, not information value |
| Damage dealt = fight impact | Targets, regeneration, fights and duration dominate interpretation |
| APM = mechanics | Spam can raise the metric without better execution |
| Item-use count = efficiency | Encourages waste and ignores legitimate hold decisions |
| Always-earlier BKB or Blink challenge | Correct builds and timing depend on the match |
| One custom PR per match | Slice mining makes recognition arbitrary |
| “You deserved to win” cards | Unsupported counterfactual and invitation to blame |
| Win/loss-free objective score | Removes the very result the objective measures |
| Daily queue streak / “one more game” push | Retention through additional play pressure |
| Zero-death worship | Rewards disengagement and penalizes useful risk |
| Hero game count = mastery | Exposure is not demonstrated capability |
| “Tilt-proof” or “resilient” personality labels | Psychological claims unsupported by match logs |
| Universal Turbo normalization | Mode changes are structural, not a simple multiplier |
| Global rarity from a convenience sample | False population claim |
| “90% chance to improve” from a percentile | Confuses a distribution rank with a predictive probability |
| Automatic diagnosis of weak decision-making | Data lack the required information/counterfactuals |

## 20. Open questions, experiments and hypothesis verdicts

### Explicit verdict on the ten product hypotheses

| Hypothesis | Verdict | Confidence and missing evidence |
|---|---|---|
| 1. Progress can be meaningful independently of MMR | Supported in a bounded sense | Moderate: specific capability/performance changes can matter; not a replacement for competitive outcomes |
| 2. Players can improve meaningfully in losses | Supported conceptually; telemetry claim conditional | High for records surviving losses; moderate for repeated growth; weak for single-match decision-quality claims |
| 3. Personal baseline is more motivating than global benchmarks | Not established as a universal claim | Moderate rationale for default, low Dota-specific comparative evidence |
| 4. Role-aware metrics are necessary | Strongly supported | High: both game structure and analytics research support different expectations |
| 5. Understandable collection is better than one score | Recommended, not empirically proven | Moderate: clear interpretability benefit; test cognitive load and preference |
| 6. Automatic PRs create a Strava-like reward loop | Plausible but unvalidated | Low-to-moderate: analogues exist; mature-history reward scarcity and Dota legitimacy remain |
| 7. Challenges encourage improvement without coaching | Qualified disagreement | Goals are guidance; automatic safe resolution is possible only for narrow metrics; efficacy unproven |
| 8. Shareable progress drives organic acquisition | Unproven | Low: need attributable activation and retention, not analogy or stated sharing intent |
| 9. A 365-day baseline provides enough context | Disagree as a blanket statement | High: sample size, patch compatibility, missingness and context coverage matter more than elapsed days |
| 10. Match tracking creates engaging long-term history | Plausible | Moderate analogue support; low direct evidence for this proposition in Dota |

### Experiment program

| Question | Smallest credible test | What would change the recommendation? |
|---|---|---|
| Are measurements correct? | Replay audit stratified by heroes, roles, modes, patches and unusual mechanics | Material semantic errors or unresolved attribution remove the metric |
| Do improvements reflect the named skill? | Blinded expert judgments on early segments, with inter-rater disagreement recorded | Frequent “metric up, execution worse” cases downgrade to description |
| Can players understand the claims? | Have players explain the comparison and what it does not prove | Confusing “record” with “better player” requires copy/scope change |
| Is the loss story welcome? | Compare neutral factual recap, bounded achievement and upbeat framing after real losses | Perceived consolation, blame or irritation argues for a quieter default |
| Which benchmark motivates? | Randomize self-only vs optional peers; allow subsequent preference choice | Strong segments may require different defaults |
| Does a challenge distort play? | Randomized reviewed target vs tracking-only; replay inspect tradeoffs | Increased selfish play or pressure removes that target even if completion rises |
| Do records last beyond novelty? | Time-ordered simulation plus longitudinal follow-up, split by history depth | Sparse mature-player value shifts emphasis to trends and identity |
| Is support value credible? | Support-specific replay interviews and factual accomplishment prototypes | Rejection of raw contributions requires better opportunity data or narrower launch |
| Does sharing acquire users? | Track consented exports, attributable visits, account connections and retained referrals | Shares without retained referrals invalidate the acquisition premise |
| Does the app become work? | Enjoyment and pressure measures alongside actual usage | High checking with reduced enjoyment is not success |
| Can modes be pooled? | Contextual distribution/invariance checks plus user comprehension | Material differences retain separate definitions; small samples do not justify pooling |
| Do trend claims survive? | Temporal holdout, negative controls and later-block confirmation | High false-positive or retraction rates require stronger abstention |

Before running experiments, predeclare acceptable semantic error, false-recognition, comprehension and harmful-substitution criteria. Exact thresholds should be chosen from error consequences and pilot variability, not invented as evidence in a strategy document. Preserve all tested candidates and failed hypotheses so later agents cannot quietly select only flattering results.

## 21. Worked example: baseline and ten new matches

**Entirely hypothetical.** The player, matches, values, cohort distribution and content below are invented to demonstrate system behavior, not calibrated thresholds or research results. The example assumes field semantics, match eligibility and patch compatibility have already passed the measurement gates.

### Starting point

Mira is an Archon player who mostly plays Luna position 1 and sometimes Crystal Maiden position 5. The 365-day archive contains 180 visible matches: 120 standard ranked, 36 standard unranked and 24 Turbo. Ranked contains 84 carry and 36 support matches. These counts describe activity, not a fitness score.

The **recent comparable reference** contains 24 ranked Luna carry matches in one compatible patch era. CS10 median is 52, middle 50% is 46–58, and the best recorded opening is 65. There are 36 early deaths across those 24 games, or 1.5 per game. A familiar item-path reference has 12 eligible Manta timings, median 20:40 and recorded best 18:10. These are not population norms.

The archive also contains 12 comparable Crystal Maiden ranked support games with complete observer-removal data; the best recorded first-30-minute count is three. Turbo history stays separate. Historical rank availability is insufficient for a real peer percentile; the cohort movement below is a labeled prototype illustration only.

Baseline content: **“Luna carry is your main track. Your usual ten-minute opening is 46–58 last hits, with a median of 52. We have 24 comparable games for this benchmark.”** This identifies neither a strength nor a weakness without another defensible reference.

Mira chooses an opening focus: reach 57 CS10 in one of the next three eligible Luna carry ranked games. The standard is frozen. It has no daily deadline. New support/Turbo games do not consume attempts.

### Ten-match sequence

| Match | Timing | Context/result | CS10 / early deaths | What changes |
|---|---|---|---|---|
| 1 | Week 1, Mon | Luna carry ranked, win | 51 / 1 | Normal opening; attempt 1 does not meet 57. No forced celebration |
| 2 | Week 1, Wed | Luna carry ranked, loss | 59 / 0 | Focus completed on attempt 2; exceeds starting median by 7, within existing record. A positive opening fact in a loss |
| 3 | Week 1, Fri | Crystal Maiden support ranked, win | Not compared to carry | Four verified observer removals by 30 minutes; support accomplishment beats previous observed three; does not prove better vision |
| 4 | Week 1, Sat | Luna carry ranked, win | 66 / 1 | CS10 PR: 66 beats 65. Manta acquired at 17:55 in comparable build path, 15 seconds faster than prior 18:10 |
| 5 | Week 1, Sun | Luna carry ranked, loss | 55 / 1 | Ordinary matched performance; second success in a chosen repeatability set |
| 6 | Week 2, Tue | Luna Turbo, win | 88 / 0 | Separate Turbo activity; does not break the standard-ranked record or advance the ranked focus |
| 7 | Week 2, Thu | Luna carry ranked, win | 58 / 0 | Completes three qualifying openings in the repeatability set; benchmark achievement |
| 8 | Week 2, Fri | Luna carry ranked, loss | 53 / 2 | A weaker opening; no automatic tilt label, no deletion of prior achievement |
| 9 | Week 2, Sat | Luna carry ranked, win | 61 / 0 | Strong familiar opening, no new record; contributes to recent distribution |
| 10 | Week 2, Sun | Luna carry ranked, loss | 57 / 1 | Meets the repeated opening standard; later trend remains provisional |

After match 2, Mira opts into a second focus: **55+ CS and at most one death before ten in three of the next five eligible Luna carry ranked games**. Matches 4, 5 and 7 meet it; match 3 is support and match 6 is Turbo, so neither counts. Completion after three eligible attempts is allowed by the declared three-of-five rule. This is a repeatability achievement, not a scientifically confirmed change.

### What the system knows after ten matches

Eight new games are comparable Luna carry ranked games. Their CS10 values are **51, 59, 66, 55, 58, 53, 61, 57**. The median is **57.5**, versus the frozen starting median of 52: an observed increase of 5.5. Their early-death counts total **6**, or **0.75 per game**, versus the starting 1.5. Ranked carry results are **4 wins and 4 losses**; all ten activities are **6 wins and 4 losses**.

Those deltas are encouraging but insufficient on their own to certify skill improvement. No confidence interval can be honestly calculated from only the summarized baseline supplied here; the actual 24 observations and dependence structure would be needed. The app says “your recent openings are higher,” not “you are 10.6% better at Dota.” Rounded user-facing copy should preserve the exact underlying values.

**Loss with meaningful improvement:** match 2 legitimately beats Mira's personal starting benchmark and completes her chosen target despite a loss. The repeated eight-game pattern is evidence worth watching. Neither licenses a claim that match 2 alone demonstrates learning. The user can reasonably value it as progress toward a personal standard while the system stays precise.

**Personal benchmark movement:** current median 52 → 57.5, frozen starting reference unchanged. **Illustrative cohort movement only:** if a frozen, representative distribution of comparable player-level medians mapped those values to the 45th and 60th percentiles, the prototype could show that movement with provisional status. No actual percentile is supplied by this research, and comparing an eight-game median to a single-match cohort would be invalid.

### Calendar and recap examples

Match 4's calendar entry reads: **“Ranked win · Luna carry · new opening best 66 · familiar-build timing best 17:55.”** One match receives one consolidated recognition object, with both supporting facts. The two correlated marks are not presented as independent evidence of growth.

Week 1 recap: **“Five matches: three wins, two losses. Your Luna opening target was reached in a loss. Saturday brought a new recorded opening best; Friday added a Crystal Maiden observer-removal accomplishment. No confirmed trend yet.”**

Week 2 recap: **“Five more matches, including one Turbo game kept in its own track. Across your eight new comparable Luna ranked games, your ten-minute median is 57.5, against 52 at the start. You completed your opening consistency focus. We are still gathering evidence that the change will hold.”**

Shareable moment after match 4: **“66 by 10. My new Luna opening best.”** Supporting line: **“Ranked carry · this patch · previous best 65 · 27 recorded comparable games including this one · won.”** The 27 equals 24 baseline games plus new comparable matches 1, 2 and 4. A timing record is available as an alternative share rather than adding clutter.

Shareable moment after match 2: **“Lost the match. Hit the target.”** Supporting line: **“Luna carry · ranked · 59 last hits at 10:00 · starting median 52 · personal focus completed.”** This reports the accomplishment without claiming superiority over teammates.

## 22. Example content and editorial boundaries

| Situation | Appropriate content | Avoid |
|---|---|---|
| Normal game | “Your opening was within your usual range. This game has been added to your history.” | Inventing a tiny achievement |
| New record | “Your fastest recorded Manta timing on this Luna build: 17:55. Previous best: 18:10.” | “Perfect itemization” |
| Loss with a strong checkpoint | “A stronger-than-usual opening in a loss: 59 CS at ten, against your median of 52.” | “You deserved the win” |
| Low deaths, lower resources | “Fewer early deaths today, alongside lower early farm. This is a different opening, not a clear improvement.” | “Flawless survival” |
| Support contribution | “Four enemy observers removed before 30 minutes—your highest recorded count in this track.” | “Your vision was elite” |
| Sparse data | “Three comparable games so far. Your personal range is still taking shape.” | A precise percentile or grade |
| Pending parse | “Match recorded. Timing and event analysis are not available yet.” | Zero-filled metrics |
| Changed patch | “A new comparison period starts here. Your earlier records are preserved.” | “You regressed” after a mechanical change |
| Plateau | “Your opening benchmark is holding steady.” | Treating maintenance as failure |
| Goal not reached | “Not reached in this set. You can retry, choose another focus, or keep tracking.” | Urging another queue immediately |
| Role uncertainty | “This match is in your history; role-specific comparisons are unavailable.” | Guessing carry from safe lane |
| Identity | “Luna appeared in 8 of your last 10 games.” | “You are loyal, stubborn or risk-averse” |

## 23. Research confidence and handoff

| Recommendation | Confidence | Evidence quality / limiting assumption |
|---|---|---|
| Separate performance, progress and identity | High | Clear construct distinction; supported by limitations in provider and repository research |
| Use hero/role/mode/patch context | High | Dota structure, primary analytics research and observed schema behavior converge |
| Begin with bounded early checkpoints | Moderate | Strong measurability and understandable units; causal skill validity remains conditional |
| Recognize scoped records in losses | High for factual legitimacy; moderate for desirability | A record survives match outcome; player reception not established |
| Prioritize self-comparison | Moderate | Adjacent motivation evidence; individual differences and Dota-specific effects unresolved |
| Treat a year as historical context | High | Sparse cells, nonstationarity and missingness undermine a universal one-year baseline |
| Avoid one composite score | Moderate | Strong interpretability rationale, no direct comparative product experiment |
| Use optional bounded challenges | Moderate for autonomy; low for effectiveness | Adjacent goal research; automatic goals may distort Dota decisions |
| Support contribution counts prove growth | Low / reject | Counts omit opportunity and team value |
| Social recognition will acquire users | Low | Analogue evidence and sharing mechanisms, no causal evidence for this product |
| No daily play streak | Moderate | Known goal-substitution risk; Dota-specific magnitude unmeasured |
| Carry-first measurement pilot | Moderate | Cleaner observables; may narrow appeal too far and must be tested |

**For future agents:** product research owns player meaning and motivation; analytics owns operational definitions, measurement validity and uncertainty; data research owns field semantics and coverage; content owns bounded language; UX owns comprehension and optionality; engineering begins only after those contracts are explicit. The most valuable next artifact is a replay-validated metric specification and a set of real-history content examples—not a polished dashboard.

The central decision is whether players value a truthful personal journal enough to return and share it when progress is modest, ambiguous or absent. If the answer is no, stronger gamification would conceal the failure rather than solve it.

## Sources and evidence register

External sources were consulted September 9, 2026. Undated product help pages describe capabilities as retrieved, not independently verified performance. Publication years are provided where established. Some publisher full-text pages were inaccessible; indexed abstracts, author manuscripts or accessible product documentation support the bounded claims above. No interview findings or market-size estimates are asserted.

[^1]: STRATZ. [“IMP: Decoding Your Performance”](https://medium.com/stratz/imp-decoding-your-performance-c251dcb42b93), January 16, 2021. Primary provider explanation; historical model description, not a current validation study.
[^2]: Demediuk, S., et al. [“Performance Index: A New Way To Compare Players”](https://ben.kirman.org/papers/Demediuk2021PerformanceIndex.pdf), 2021. Author-hosted paper; professional Dota, 1,000 matches from patch 7.26. Role-sensitive performance modeling, not longitudinal amateur intervention evidence.
[^3]: Strava. [“Matched Activities”](https://support.strava.com/en-us/articles/15401955-matched-activities), current help page. Repeated-context self-comparison.
[^4]: Macnamara, B. N., Hambrick, D. Z., and Oswald, F. L. [“Deliberate Practice and Performance in Music, Games, Sports, Education, and Professions: A Meta-Analysis”](https://journals.sagepub.com/doi/abs/10.1177/0956797614535810), 2014. Broad-domain meta-analysis; “games” is not a Dota-specific estimate.
[^5]: Ericsson and Harwell. [“Deliberate Practice and Proposed Limits on the Effects of Practice on the Acquisition of Expert Performance”](https://pmc.ncbi.nlm.nih.gov/articles/PMC6824411/), 2019. Definition dispute and methodological limitations.
[^6]: Drachen, A., et al. [“Skill-Based Differences in Spatio-Temporal Team Behavior in Defence of The Ancients 2”](https://arxiv.org/abs/1603.07738), conference reference 2014, arXiv 2016. Observational team behavior; old game context.
[^7]: Sapienza, A., Peng, H., and Ferrara, E. [“Performance Dynamics and Success in Online Games”](https://arxiv.org/html/1801.09783), conference 2017, arXiv 2018. Observational Dota histories; prescriptions are not experimentally established.
[^8]: OpenDota. [OpenDota core repository](https://github.com/odota/core). Primary project description and parsing provenance. [API documentation](https://docs.opendota.com/) is a reference endpoint; no live data calls were made.
[^9]: Dotabuff. [Dotabuff Plus](https://www.dotabuff.com/plus), current product page. Advertised analytics capabilities.
[^10]: Valve. [Dota Plus](https://www.dota2.com/plus), current product page. Hero progression, challenges, relics and comparison features.
[^11]: Valve. [The Battle Report Update](https://steamcommunity.com/games/dota2/announcements/detail/3351254920150914113), June 2022; announcement text retrieved through [SteamDB's attributed reproduction](https://steamdb.info/patchnotes/8899448/). The linked official [Battle Report page](https://www.dota2.com/battlereport) yielded no extractable body; detailed current UI/cadence is not asserted.
[^12]: Dota2ProTracker. [Pro Builds](https://dota2protracker.com/builds) and [Pages](https://dota2protracker.com/pages), current product references. Professional-build and high-level comparison context.
[^13]: LaneMind. [Dota analytics, match review and coaching](https://www.lanemind.com/), current vendor page. Advertised workflow, not audited efficacy or adoption.
[^14]: Anderson, J., Leetify. [“Aim and Utility Benchmarks Recalculated”](https://leetify.com/blog/benchmarks-season-3/), August 1, 2025. Primary account of reference/bug-driven score movement.
[^15]: Wansbrough, L., Tracker Network. [“Tracker Score, Our New Performance Rating”](https://tracker.gg/valorant/articles/tracker-score-our-new-performance-rating), February 3, 2023. Published rationale and components, not assumed unchanged implementation.
[^16]: Hevy. [“Personal Records (PRs) and Set Records Explained”](https://help.hevyapp.com/hc/en-us/articles/35649367857175-Personal-Records-PRs-and-Set-Records-Explained-How-They-Work-in-the-Hevy-App), current help page. Record types and exercise specificity.
[^17]: Hevy. [“Calendar and Streak Features”](https://help.hevyapp.com/hc/en-us/articles/35380117933207-Track-Your-Workout-Consistency-with-the-Calendar-and-Streak-Features) and [“Yearly Review”](https://help.hevyapp.com/hc/en-us/articles/35700454899991-Discover-Your-Hevy-Training-Stats-with-the-Yearly-Review), current help pages. History/recap mechanisms.
[^18]: Strava. [“Track Your Run PRs”](https://stories.strava.com/pb/articles/track-your-run-prs), 2023. Defined-distance best efforts; product mechanism, not Dota efficacy evidence.
[^19]: Apple. [“Track daily activity with Apple Watch”](https://support.apple.com/en-ie/guide/watch/apd3bf6d85a6/watchos), current guide. Recent versus annual trend reference.
[^20]: Apple. [“Adjust your Activity ring goals”](https://support.apple.com/en-mt/guide/watch/apd29b30023c/watchos), current guide. Adjustable/pausable activity goals.
[^21]: Garmin. [Enduro owner's manual: Training Status](https://www8.garmin.com/manuals/webhelp/GUID-BD965919-30AA-4EB5-95D7-A899658C50EB/EN-US/GUID-44C7BB4B-EFF7-4A42-AC03-8A6AABB94807.html). Model-specific primary documentation; not a claim about every Garmin device.
[^22]: WHOOP. [“Guide to Self-Experimentation”](https://www.whoop.com/us/en/thelocker/guide-to-self-experimentation-whoop-journal/), [“Viewing Trends”](https://support.whoop.com/s/article/Viewing-Trends), and [“WHOOP Journal Overview”](https://support.whoop.com/s/article/WHOOP-Journal-Overview?language=en_US). Vendor methods/help; behavior associations and recap terminology require caution.
[^23]: Spotify. [“2024 Wrapped Is Here!”](https://newsroom.spotify.com/2024-12-04/wrapped-user-experience-2024/), December 4, 2024. Primary description of identity/evolution stories and sharing integrations.
[^24]: Harkin, B., et al. [“Does monitoring goal progress promote goal attainment? A meta-analysis of the experimental evidence”](https://pubmed.ncbi.nlm.nih.gov/26479070/), 2016; DOI 10.1037/bul0000025. 138 studies, 19,951 participants; indirect domain transfer.
[^25]: Williamson and colleagues. [“The performance and psychological effects of goal setting in sport: A systematic review and meta-analysis”](https://doi.org/10.1080/1750984X.2022.2116723), published online 2022. 27 included studies; process/performance distinction, heterogeneous sport evidence.
[^26]: Przybylski, A. K., Rigby, C. S., and Ryan, R. M. [“A Motivational Model of Video Game Engagement”](https://selfdeterminationtheory.org/SDT/documents/2010_PrzybylskiRigbyRyan_ROGP.pdf), 2010. Theory/review; competence, autonomy, relatedness.
[^27]: Etkin, J. [“The Hidden Cost of Personal Quantification”](https://marketing.wharton.upenn.edu/wp-content/uploads/2016/10/Etkin-Jordan-11-12-15-Hidden-Cost.pdf), author manuscript; published 2016, DOI 10.1093/jcr/ucv095. Experimental evidence of possible enjoyment costs, not Dota-specific harm estimates.
[^28]: Reddit, r/DotA2. [Battle Stats appreciation](https://www.reddit.com/r/DotA2/comments/11kmxlh/), 2023; [request for weekly Battle Report](https://www.reddit.com/r/DotA2/comments/vm61lk/), 2022; [Turbo inclusion response](https://www.reddit.com/r/DotA2/comments/x41qdz/), 2022. Self-selected player sentiment only.
[^29]: Reddit, r/DotA2. [“Dota Plus Hero Challenges”](https://www.reddit.com/r/DotA2/comments/17v9j36/), 2023. Objection to item-specific challenges; anecdotal, not prevalence evidence.
[^30]: Carvalho, R. R., et al. [“Computer Vision for MOBA Analytics: A Dataset and Baseline for Visibility Analysis in Dota 2”](https://arxiv.org/abs/2606.26970), June 25, 2026; listed as accepted for SBGames 2026. Emerging visibility research, professional tournament data.
[^31]: Valve. [Dueling Fates: The 7.07 Update](https://www.dota2.com/duelingfates?l=english), 2017. Original Turbo rule differences; current exact values not inferred.
[^32]: Silverman, J., and Barasch, A. [“On or Off Track: How (Broken) Streaks Affect Consumer Decisions”](https://academic.oup.com/jcr/article/49/6/1095/6623414?guestAccessKey=1bb91501-7f0d-4dcc-806d-8124e533be13), online 2022, journal volume 2023; DOI 10.1093/jcr/ucac029. Logged-streak behavior, not Dota clinical outcomes.
[^33]: Berger, J., and Milkman, K. L. [“What Makes Online Content Viral?”](https://doi.org/10.1509/JMR.10.0353), 2012. Content-transmission research; application to Dota share objects is inference.

### Repository references

These are scoped research/methodology references at inspected HEAD `e7d93186cec9745640dbf96386f70239ac040c88`, not an audit of production behavior. Raw account/match specimens, frontend, assets and unrelated implementation were not inspected. Historical research conclusions are attributed to their stated phase and are not promoted into release evidence.

- **R1.** [STRATZ field inventory](../research/stratz-enrichment/01-field-inventory.md), August 27 with September 1 superseding note. Specimen semantics, null behavior, role and time-series caveats. Selected sections of the companion [research overview](../research/stratz-enrichment/00-research-report.md) and [candidate catalog](../research/stratz-enrichment/03-candidate-catalog.md) supplied candidate context; no exhaustive repository audit is implied.
- **R2.** [Offline specimen recovery/gap audit](../legacy/docs/evidence/free-dna-v7-stratz-specimen-recovery-gap-audit-2026-09-01.md), [live microprobe](../legacy/docs/evidence/free-dna-v7-stratz-live-microprobe-2026-09-01.md), and [corpus QA atlas](../legacy/docs/evidence/free-dna-v7-stratz-corpus-qa-atlas-2026-09-02.md). Dated capability observations and unresolved semantics; the atlas is an acquisition checkpoint, not the final corpus state.
- **R3.** [Beyond the scoreboard: parsed OpenDota research](../research/opendota-parsed-match-insight-research.md), inspected opening/schema and relevant targeted passages. One professional specimen supports shape and omissions, not pub benchmarks.
- **R4.** [V7 discovery and early screen](../legacy/docs/evidence/v7-finding-discovery-and-early-screen-2026-09-03.md), September 3, 2026. Discovery-only signal/stability results and rejected interpretations.
- **R5.** [V7 Finding pipeline](../legacy/docs/evidence/v7-finding-pipeline-2026-09-05.md), September 5, 2026. Dependence-sensitive reliability, discovery-only and explicitly not certified publication thresholds. The opening of [September 8 fit metadata](../legacy/docs/evidence/v7-new-lineage-finding-fit-2026-09-08.json) was also checked; it does not supply longitudinal validation here.
- **R6.** [System behavior baseline](../legacy/docs/system-behavior-baseline.md). Historical 365-day, recency/session-weighting and versioned-methodology context; not assumed current production state.
- **R7.** [STRATZ V7 provider contract](../legacy/docs/architecture/stratz-v7-provider-contract.md), September 1, 2026. History window, truncation provenance, native role/mode boundaries and deliberately excluded rank fields.

[r1]: ../research/stratz-enrichment/01-field-inventory.md
[r2]: ../legacy/docs/evidence/free-dna-v7-stratz-specimen-recovery-gap-audit-2026-09-01.md
[r3]: ../research/opendota-parsed-match-insight-research.md
[r4]: ../legacy/docs/evidence/v7-finding-discovery-and-early-screen-2026-09-03.md
[r5]: ../legacy/docs/evidence/v7-finding-pipeline-2026-09-05.md
[r6]: ../legacy/docs/system-behavior-baseline.md
[r7]: ../legacy/docs/architecture/stratz-v7-provider-contract.md
