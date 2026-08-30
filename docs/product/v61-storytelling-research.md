# V6.1 Storytelling and Reveal Research

- Status: research handoff for the V6.1 presentation revamp
- Research date: 2026-08-30
- Scope: editorial mechanics, narrative sequencing, recap interaction, and Dota-community expectations
- Non-goal: changing analytical estimators, thresholds, report fields, publication logic, or data sources

This document is an evidence-backed editorial brief. It is deliberately
separate from the copy/data-basis matrix and the renderer. The matrix remains
the authority for whether a sentence is allowed; this document describes how
an allowed sentence can earn attention, create momentum, and remain honest.

## Executive synthesis

The strongest recap products do not make a dashboard more colorful. They turn a
bounded dataset into a sequence of recognitions. Across eight generations of
Spotify Wrapped and the comparator products reviewed here, the durable pattern
is:

1. Establish the scope and make the first fact easy to verify.
2. Alternate receipt, interpretation, participation, and context.
3. Delay the broad identity label until several independent observations have
   accumulated.
4. Let chronology, contrast, or a surprising relationship do the dramatic work;
   do not repeat “setup → number → proof → joke” for every screen.
5. Treat a share card as a standalone artifact with one legible idea, not as a
   compressed dump of the report.
6. Make uncertainty visible as a meaningful state. Missing coverage is part of
   the report boundary, not a reason to fill the page with a guess.
7. Give the user control over pace, replay, sharing, and motion. A reveal is
   still a good reveal when a user reads it slowly or uses reduced motion.
8. Earn humor from an observable choice or sequence. Generic gamer insults are
   neither personal nor trustworthy.

The central implication for Dota Report Card is a two-voice experience:

- the evidence voice states what the report can observe, with the denominator
  and boundary available;
- the editorial voice chooses the order, contrast, and human phrasing, while
  never adding a reason, trait, causal story, or identity that the evidence did
  not qualify.

This is not a request to imitate Spotify, Steam, or any other brand. Their
mechanics are useful as precedent; their names, visual signatures, personality
taxonomies, and social comparisons are not a substitute for Dota-specific
evidence.

## Method and evidence discipline

The research combines official product announcements, product-support pages,
engineering/design write-ups, one independent news report about user response,
and public Dota community discussions. Official product materials are best for
what a recap actually shipped. Engineering and support materials are useful for
how the experience was constructed and where it is conditional. Reddit threads
are qualitative examples of language and reactions, not prevalence estimates or
representative user research.

Claims in this document use the following labels:

- **Observed** — directly described in a linked product source or visible in a
  linked community discussion.
- **Inference** — an editorial/product implication derived from one or more
  observations. It is a design hypothesis, not a measured causal result.
- **Guardrail** — a constraint imposed by the Dota report contract or by a
  failure mode in the evidence.

The source set was checked on 2026-08-30. Annual recap features, eligibility,
and URLs can change; links are included so a future release can re-check them.

## 1. Spotify Wrapped across generations

### Timeline of observed mechanics

| Generation | Observed product mechanic | Editorial job | V6.1 implication |
|---|---|---|---|
| 2018 | Spotify presented a rediscovery/share experience with interactive prompts, including a guess-then-check moment for total listening time, then lists of songs, artists, and genres. [Spotify, 2018](https://newsroom.spotify.com/2018-12-06/relive-your-year-in-music-with-spotify-wrapped/) | Let the user participate before receiving a familiar receipt. | A small prediction or choice can make an existing metric feel discovered. It must have a skip and a deterministic reveal path. |
| 2019 | The recap added a decade lens to the annual review. Spotify’s engineering account describes the target as simple, intuitive, shareable, and native to the app, with a static minimum viable version before animation was layered in. [Spotify, 2019](https://newsroom.spotify.com/2019-12-05/spotify-wrapped-2019-reveals-your-streaming-trends-from-2010-to-now/), [engineering notes](https://engineering.atspotify.com/2020/09/spotify-unwrapped-2019-how-we-built-an-in-app-experience-just-for-you) | Turn one year into a personal time horizon and establish a readable product grammar before decoration. | Dota can use a within-year chronology (eras, streaks, first/last occurrence) without claiming lifetime history. Build the static reading path first; motion should clarify the transition. |
| 2020 | “Story of Your 2020” traced a top song through milestones such as the first stream and later notable listens. Quizzes, behavior-based badges, playlists, and customizable share cards added participation and artifacts. [Spotify, 2020 features](https://newsroom.spotify.com/2020-12-01/6-new-features-to-unwrap-in-your-spotify-2020-wrapped/), [share mechanics](https://newsroom.spotify.com/2020-12-09/3-tips-tricks-to-enhance-your-2020-wrapped-experience/) | Make a static count feel like a lived sequence; convert a result into something the user can test and share. | Prefer “what happened next?” and “how the shape changed” where the report has chronology. Do not invent a song-like milestone when only annual aggregates exist. |
| 2021 | The experience used a movie framing for top songs, an Audio Aura built from two mood categories, a true/false Playing Cards interaction, friend Blend, and creator messages. [Spotify, 2021](https://newsroom.spotify.com/2021-12-01/the-wait-is-over-your-spotify-2021-wrapped-is-here/), [Audio Aura explanation](https://newsroom.spotify.com/2021-12-01/learn-more-about-the-audio-aura-in-your-spotify-2021-wrapped-with-aura-reader-mystic-michaela/) | Give different facts different narrative containers and make identity feel assembled from behavior. | Vary the reveal grammar: card, timeline, comparison, question, and quiet evidence panel. Do not import an aura/personality metaphor unless the Dota contract independently qualifies it. |
| 2022 | Listening Personality named one of 16 types, while Audio Day placed descriptors across morning, afternoon, and evening. The product also expanded share surfaces. [Spotify, 2022](https://newsroom.spotify.com/2022-11-30/everything-you-need-to-know-about-2022-wrapped/) | Translate a collection of facts into a memorable label, then anchor it in time-of-day context. | An identity reveal should be the end of an evidence arc, not an opening classification. Dota has hero eras and session positions that can supply context without a new personality taxonomy. |
| 2023 | “Me in 2023” used a flip-card reveal for a listening character; Sound Town matched listeners to a city using artist affinity and how those artists streamed in other cities; top genres and browser parity broadened the experience. [Spotify, 2023 UX](https://newsroom.spotify.com/2023-11-29/wrapped-user-experience-2023/), [Sound Town](https://newsroom.spotify.com/2023-12-01/wrapped-sound-town-berkeley-burlington-cambridge/) | Make a label feel like a reveal and add social context around a personal pattern. | A Dota “Signature” can use a delayed card reveal, but a cohort comparison is only legitimate when a supported cohort, denominator, and privacy contract already exist. |
| 2024 | Music Evolution showed up to three listening phases with descriptors, genres, and artists. Spotify also placed AI features and smaller insights throughout the flow rather than relying on one final card. [Spotify, 2024 UX](https://newsroom.spotify.com/2024-12-04/wrapped-user-experience-2024/), [art and science](https://newsroom.spotify.com/2024-12-04/the-art-and-science-behind-spotify-wrapped/) | Use phases and distributed callbacks to make a year feel changeable, while editorial experts contextualize raw data. | Hero eras are a natural Dota analogue. Place a small number of reliable observations across the arc and let the final synthesis point back to them. Avoid generic generated copy that outruns evidence. |
| 2025 | Spotify explicitly iterated from audience feedback and described the experience as more layered. It added a Top Song Quiz, Listening Age, monthly Top Artist Sprint, Fan Leaderboard, Clubs with roles, Listening Archive, and controls to adjust speed/revisit moments. [Spotify, 2025 UX](https://newsroom.spotify.com/2025-12-03/2025-wrapped-user-experience/), [methodology](https://newsroom.spotify.com/2025-12-05/wrapped-methodology-explained/), [Clubs](https://newsroom.spotify.com/2025-12-03/wrapped-clubs-overview/) | Combine familiar receipts with optional participation, temporal movement, social comparison, and replay. Explain the metric choice and boundary. | Layered does not mean crowded. Give Dota a primary reading path plus optional Evidence/Methodology and Share actions. A quiz, percentile, or “club” needs a real data basis and an explicit privacy/eligibility decision. |

### What persisted, despite the changes

**Observed:** Spotify kept returning to a few structural moves: annual scope,
top-list receipts, a moment of participation or surprise, one or more temporal
views, a memorable identity frame, and a shareable artifact. Its own 2025
methodology says the snapshot selects metrics appropriate to the story—streams
for one question, minutes for another—and documents exclusions such as private
mode. [Spotify methodology, 2025](https://newsroom.spotify.com/2025-12-05/wrapped-methodology-explained/)

**Inference:** Metric variety works when each metric answers a different
narrative question. Repeating counts with different typography does not create
variety. For Dota, match count, time, dates, streaks, hero concentration, and
qualified families should each have a distinct job in the story.

**Observed:** Spotify’s engineering write-up says the 2019 team started with a
static minimum viable experience and added animation after the reading path was
clear; it also reports that personalized share cards were more expensive than
expected. [Spotify engineering, 2019](https://engineering.atspotify.com/2020/09/spotify-unwrapped-2019-how-we-built-an-in-app-experience-just-for-you)

**Inference:** The Dota reveal system should have a stable text-and-evidence
fallback. Animation, gradients, and particle effects are enhancement layers,
not dependencies for comprehension or shareability.

**Observed:** Spotify’s animation write-up describes parameters driven by
localized text, images, and listening data; examples include color intensity
based on frequency and a coordinate derived from Sound Town. [Spotify
engineering, 2023](https://engineering.atspotify.com/2024/01/exploring-the-animation-landscape-of-2023-wrapped)

**Inference:** Data-bound motion is meaningful when the parameter is legible: a
timeline moves because time changes, a stack grows because a count accumulates,
and a card flips because the label is being disclosed. Decorative motion should
not imply a magnitude, direction, or confidence that is not present.

**Observed:** An academic study of Wrapped describes it as an “algorithmic
event” in which participants both celebrate and question how the product claims
to know them. [AoIR study](https://spir.aoir.org/ojs/index.php/spir/article/view/14038)

**Inference:** Delight and skepticism coexist. A Dota user should be able to
ask “where did this come from?” without leaving the story, and should never be
forced to accept an archetype as a psychological truth.

## 2. Comparator scan

The comparators below were selected because the plan names them or because they
exercise a different recap mechanic. “Transferable” means an editorial pattern,
not a feature request.

| Product | Observed mechanics | Transferable editorial lesson | Guardrail for Dota |
|---|---|---|---|
| Steam Replay 2024 | A playful “memory lane” journey includes year-over-year comparison, achievements, longest streak, monthly/platform/Steam Family breakdowns, spider graphs, and sharing on and off Steam. [Steam Replay](https://store.steampowered.com/news/posts/?enddate=1734653759&feed=steam_clientAny) | Mix a few familiar receipts with a change-over-time comparison and a closing artifact. | Only compare what the report actually stores. Do not imply MMR/rank history or platform context that is absent. |
| Dota Plus Battle Report | Valve’s 2022 season update added a report for the previous season, included Turbo, offered a calendar view, and added Aghanim filters. [Valve update](https://store.steampowered.com/news/posts/?appids=620%2C550%2C240%2C220%2C70%2C440%2C420%2C400%2C500%2C10%2C380%2C4000%2C300%2C30%2C5952%2C80%2C5489%2C5268%2C219%2C40%2C60%2C360%2C340%2C320%2C280%2C130%2C50%2C20%2C80822%2C80788%2C80762%2C80752%2C80747%2C80739%2C80633%2C5739%2C410%2C630%2C570%2C1800%2C80923%2C5734%2C5724%2C5260%2C5149%2C5150%2C5141%2C5139%2C5138%2C5073%2C5051%2C5032%2C997%2C987%2C985%2C960%2C937%2C936%2C934%2C933%2C932%2C931%2C930%2C916%2C923%2C922%2C915%2C914%2C913%2C912%2C905%2C904%2C918%2C917%2C901%2C81061%2C81026%2C5825%2C5722%2C995%2C906%2C1003&enddate=1663275332&feed=steam_community_announcements) | Dota players already understand seasonal review and calendar context; the opportunity is a more authored sequence around existing evidence. | Do not blur Battle Report semantics with this product. Treat mode, date window, and source differences as visible boundaries. |
| STRATZ and Dotabuff | STRATZ positions player profiles as a drilldown with match history, historical rank progression, hero/position statistics, comparisons, and replay-style match views. [STRATZ](https://stratz.com/) Dotabuff’s TI 2025 recap turns professional-match data into contextualized meta trends rather than a personal report. [Dotabuff](https://www.dotabuff.com/blog/2025-09-16-the-international-2025-meta-recap) | Dota users already have dense analytical destinations. The recap’s job is to select a few relationships and make the path to the underlying receipt obvious. | Do not reproduce a stats portal in the story, and do not imply that a personal report has replay, position, rank-history, or global-meta data unless the current contract supplies it. |
| PlayStation Wrap-Up 2024 | The flow includes most-played games, monthly activity, a gaming style, account-history stats, trophy milestones, recommendations, eligibility conditions, and an earned avatar/digital collectible/share card. [PlayStation](https://blog.playstation.com/2024/12/10/celebrate-30-years-of-playstation-with-playstation-2024-wrap-up-launching-today/) | A completion reward and a historical lens can make the end feel earned. | The Dota close can offer a share artifact, but should not promise a collectible, all-time history, or recommendation unless it exists in the contract. |
| YouTube Music Recap 2024 | Animated cards use personalized text, a listening description, a timeline with an adventurous month, a music-film character, a photo album, and podcast cards. [YouTube Music](https://blog.youtube/news-and-events/2024-music-recap-youtube/) | A timeline and small “album” of moments can support memory better than one aggregate score. | Dota can use hero eras, busiest days, and longest match as memory anchors; do not call a match a “moment” unless its evidence is actually available. |
| Apple Replay | Replay uses listening history, play counts, and time; it offers monthly/year views, a highlight reel, shareable milestones/comparisons, top-listener badges, weekly playlists, all-time views, and prior years. [Apple support](https://support.apple.com/en-ie/109356) | Ongoing monthly and prior-year views support self-comparison rather than a one-time spectacle. | A persisted report is a snapshot. Do not imply live updating or lifetime trend data; state the report window. |
| Reddit Recap 2022 | The recap combined time, content, communities, downloadable/shareable cards, avatar and community moments, and a final “Superpower” card. Users could hide their username/avatar; the data window and SFW boundary were explicit. [Reddit](https://redditinc.com/news/reddit-recap-2022-product) | Privacy control and a final, self-contained card matter as much as the headline. | Make identity/avatar optional, and keep share candidates eligible only when their evidence refs and privacy rules pass. |
| Duolingo Year in Review | Duolingo evolved from an email into an in-app story; learner “styles” were designed to be fun, clever, and legible on small screens. It reports that a percentile card over-indexed toward its most active users, while styles created another sharing opportunity. [Duolingo behind the scenes](https://blog.duolingo.com/year-in-review-behind-the-scenes/) The 2020 edition omitted unstable stats and used a compact share card. [Duolingo 2020](https://blog.duolingo.com/duolingo-2020-year-in-review/) | A label is useful when it is short, specific, and supported by an evidence path. Omission can be better than an unstable number. | No percentile or archetype by default. If a Dota label is used, require qualified slots and keep neutral/insufficient variants. |
| Strava Year in Sport | Strava describes unique insights, social engagements, and standout moments; cards are conditional on activity amount and available features. It requires a minimum activity level, is mobile-only, and supports sharing individual scenes and a final summary image. [Strava support](https://support.strava.com/en-us/articles/15401959-your-year-in-sport) | Conditional scenes keep the recap personal without pretending every user has every data type. | A missing finding, chronology, or identity slot should remove that scene, not be replaced by invented filler. |

### Fragile or failed patterns

These are not claims that a whole product failed. They are observed warning
signals that should influence the Dota release gate.

**Minimalism without enough substance.** An Associated Press report on the 2025
Wrapped launch records complaints and memes about the prior year feeling too
minimal, followed by Spotify adding more familiar stats and interaction in
response. [AP coverage](https://apnews.com/article/spotify-wrapped-2025-release-music-tracking-8a7a7f08150eefd3a26020a4a9d046e1)

- **Observed:** A sparse interface can be perceived as missing value when the
  recognizable receipts are absent.
- **Inference:** A clean Dota screen still needs an immediate, checkable anchor
  before a more abstract synthesis. Whitespace is not a replacement for
  substance.

**A final label without enough personal evidence.** Reddit’s 2022 recap framed
communities and karma as a “Superpower,” but a 2023 user thread contains
complaints about missing preferred stats, inaccurate top-comment/karma details,
and absent avatars. [Community reaction](https://www.reddit.com/r/recap/comments/18c85p8)

- **Observed:** Some users judge a recap by whether its chosen “special” facts
  match their own memory of the product.
- **Inference:** Dota’s final Signature should not compensate for weak evidence
  with a louder label. The report should say when the identity gate is not met.

**Inconsistent receipts.** A Valve Dota gameplay issue documents a user finding
that Battle Report streak values disagreed across tabs and hero views; the issue
was closed as not planned. [Dota report issue](https://github.com/ValveSoftware/Dota2-Gameplay/issues/9629)

- **Observed:** A single inconsistent stat can undermine trust in the whole
  recap, even when the surrounding presentation is polished.
- **Guardrail:** Any Dota story card must have one canonical source path and
  denominator. Cross-view values should be tested against the same fixture.

**Third-party recap coverage and mode ambiguity.** Dota Rewind discussions praise
the concept and interface while questioning estimated rank, ranked/unranked
boundaries, Turbo coverage, and privacy. A newer Dota Rewind discussion also
notes that parsed-only Ability Draft matches made the summary less fun and that
some estimates were explicitly rough. [Dota Rewind, 2020](https://www.reddit.com/r/DotA2/comments/kzp438),
[Dota Rewind, 2025](https://www.reddit.com/r/DotA2/comments/1psy4ns/i_made_a_dota_2_rewind_-_personal_recap_for_2025)

- **Observed:** Players notice data-set boundaries and question a metric that
  appears more precise than its source.
- **Guardrail:** Show the eligible window, mode/coverage note, and precision
  appropriate to the source. Never make a rough estimate look like an exact
  analytical result.

**Static charts as ceremony.** Steam, PlayStation, and Apple all use charts or
  monthly views, but their useful role is to support a comparison or milestone,
  not merely to add a visualization.

- **Inference:** Every chart in Dota should answer a question the preceding
  sentence creates. If the user cannot say what changed, accumulated, or held,
  the chart is probably decoration.

## 3. Dota community research

The community material is intentionally read as qualitative language research.
Upvotes and comment threads show that a topic can be emotionally resonant; they
do not establish that most Dota players feel the same way. The practical use is
to learn which hooks sound personal and which claims invite immediate dispute.

| Community hook | Observed reaction or language | Editorial inference | V6.1 guardrail |
|---|---|---|---|
| Hero pool as negotiated identity | `r/TrueDoTA2` discussions repeatedly weigh comfort heroes against counters, team fit, the current meta, and the size of a practical pool. Learning threads recommend a small core plus backups while acknowledging boredom and patch change. [Comfort vs team fit](https://www.reddit.com/r/TrueDoTA2/comments/1g75d87/to_climb_mmr_should_i_select_a_hero_im_most_comfortable_with_or_something_that_will_work_in_the_particular_game), [pool balance](https://www.reddit.com/r/TrueDoTA2/comments/y67xfn/tools_to_tell_you_how_to_balance_out_your_hero_pool), [six heroes](https://www.reddit.com/r/TrueDoTA2/comments/1aqkzu9/is_6_heroes_for_your_main_role_really_enough), [learning pool](https://www.reddit.com/r/learndota2/comments/1gspbli/help_with_picking_hero_pool) | “Your hero pool says something” is compelling because players already debate it, but the meaning is contextual and contested. | Describe observed concentration, movement, and mapped jobs. Do not turn most-played into comfort, skill, lane, intent, or personality. |
| Loss streaks and the next queue | DotA, TrueDoTA2, and LearnDota2 discussions describe brutal streaks, repeated queueing, tilt concerns, and advice to take a break or stop after a small number of losses. [DotA2 streak](https://www.reddit.com/r/DotA2/comments/1nech4f/how_do_you_guys_wind_down_after_a_brutal_losing_streak), [TrueDoTA2 streak](https://www.reddit.com/r/TrueDoTA2/comments/rxg76d/why_do_loss_streaks_feel_so_rigged), [LearnDota2 advice](https://www.reddit.com/r/learndota2/comments/vdiel4/any_tips_on_dealing_with_losing_streaks), [streak discussion](https://www.reddit.com/r/learndota2/comments/16l91cd/lose_streaks_instead_of_win_streaks) | Result-response is emotionally legible. A next-choice sequence can create recognition without asserting that a loss caused a decision or that a player was tilted. | Use neutral verbs such as “followed,” “shifted,” and “stayed near.” Keep “tilt,” “frustration,” “recovery,” and “intent” out unless separately evidenced—which the current report does not do. |
| Memorable sequence over a single result | Threads about unforgettable games emphasize comebacks, base holds, long close matches, personal hero moments, and even memorable losses. Satisfaction threads likewise mention a cohesive team, a turned fight, or everyone trying despite a loss. [Memorable game](https://www.reddit.com/r/DotA2/comments/1m68xxt/what_is_that_one_dota_game_you_played_that_still_lives_rent_free_in_your_head), [satisfying feeling](https://www.reddit.com/r/DotA2/comments/17o9dxs/what_is_the_most_satisfying_feeling_in_dota) | A result alone is a weak emotional story. Time, order, contrast, and persistence are better memory scaffolds when the dataset supports them. | Use longest match, busiest day/week, streak order, and hero eras as memory anchors. Do not call a match a comeback, throw, or clutch without event evidence. |
| Players audit their recaps | Dota Rewind and Leetify recap threads contain users comparing totals, win rates, dates, and missing games against Dotabuff or their own memory; comments also ask about public-profile visibility and account coverage. [Leetify recap](https://www.reddit.com/r/DotA2/comments/1qavt53/we_built_a_recap_of_your_dota_2_stats_for_2025), [Dota Rewind](https://www.reddit.com/r/DotA2/comments/1psy4ns/i_made_a_dota_2_rewind_-_personal_recap_for_2025) | Dota players are unusually likely to challenge an impressive sentence if its receipt is not easy to find. | Make Evidence one tap away, preserve the exact window/denominator, and expose “not enough context” as a valid state. |
| Precision and mode boundaries are social issues | Threads question ranked vs unranked, Turbo, parsed matches, estimated rank, and public profiles showing zero or partial data. | A limitation statement is not bureaucratic copy; it protects the user’s trust and the share card’s reputation. | Never silently merge incompatible modes or sources. If a field is absent in a persisted report, omit the corresponding story surface. |
| Peer roast can be affectionate, but generic roast is cheap | A “what does my hero pool tell you?” thread invites playful stereotypes alongside serious pool discussion. [Hero-pool reactions](https://www.reddit.com/r/DotA2/comments/1huy4uq/what_does_my_hero_pool_tell_you_about_me) | A roast lands when it points to a specific, recognizable sequence and leaves the user room to disagree. | Roast the pattern, not the player. Prefer reversible lines (“you kept returning to…”) over identity judgments (“you are…”). |

### Community-derived emotional hooks

The safest hooks are those that can be written as a question before the answer
is known:

- **Return:** Which hero or behavior kept coming back after the pool appeared to
  move?
- **Pressure:** What changed after one loss versus two or more, if the supported
  transitions are sufficient?
- **Persistence:** Which signal held while names, dates, or contexts changed?
- **Boundary:** Where does the report stop knowing what happened, and can that
  boundary itself be stated clearly?
- **Memory:** Which date, week, era, or unusually long match gives the year a
  concrete handle?

These questions are deliberately narrower than “what kind of player are you?”
They create room for recognition without fabricating motivation.

## 4. Editorial system for V6.1

### Narrator and voice

Use a quietly observant analyst with dry restraint. The narrator notices a
pattern, gives the user the receipt, and lets the user decide how much meaning
to attach to it. The narrator is not a coach, therapist, teammate, referee, or
omniscient storyteller.

The voice has four operating modes:

1. **Receipt:** plain statement of a count, date, range, or observed category.
2. **Pattern:** bounded comparison or qualified finding, with its evidence path.
3. **Tension:** two supported facts that do not collapse into one conclusion.
4. **Boundary:** an explicit “this report cannot tell us” or “not enough history”
   state.

Do not use the same mode on every page. A receipt followed by another receipt
feels like a spreadsheet; a pattern followed by another pattern feels like a
lecture. Alternate modes to create rhythm.

### Claim ladder

The copy catalog and the report contract determine which rung is available:

| Rung | Permitted language | Example shape | Forbidden leap |
|---|---|---|---|
| 1. Fact | “You played `{count}` eligible matches.” | Exact value + scope. | “You live in Dota.” |
| 2. Description | “Your hero pool has a stable core and a moving edge.” | Existing portfolio shape. | “You are a comfort player.” |
| 3. Qualified pattern | “After the registered result state, the next choice moved differently.” | Published finding + evidence. | “The loss caused the switch.” |
| 4. Synthesis | “These signals share a shape.” | Existing identity slot with refs. | “This is your personality.” |
| 5. Unknown | “The report cannot separate the covered contexts.” | Neutral/insufficient/mixed state. | Fill the gap with a joke or invented archetype. |

The editorial layer may make a sentence warmer or shorter, but it cannot move a
claim up the ladder. A missing slot, chronology, comparison, or evidence ref is
an omission state, not a writing challenge.

### Number and evidence order

Use this sequence when a number is the emotional anchor:

1. **Orient:** name the unit and window (“in this report,” “across eligible
   matches,” “during the year”).
2. **Reveal:** show the number, range, date, or category at readable size.
3. **Interpret:** give one sentence about the supported relationship.
4. **Receipt:** make Evidence or Methodology available without interrupting the
   main arc.
5. **Release:** optional dry line, only after the fact is understood.

The order can be inverted when the question itself is the hook, but every
foreground interpretation should still have an obvious receipt. Never hide the
denominator inside a tooltip that is unavailable to keyboard or reduced-motion
users.

### Praise, negative framing, and uncertainty

- **Praise:** praise persistence, range, return, or a verified sequence—not
  skill, value, or character. “You kept showing up” is safer than “you carried.”
- **Negative framing:** keep it specific, bounded, and reversible. “The second
  loss is where the next choice moves” is useful; “you tilt” is unsupported.
- **Uncertainty:** state what is unresolved, not merely that confidence is low.
  “The covered signals disagree” gives the user a real shape to inspect.
- **Mixed outcomes:** keep both sides visible. Mixed is not a failure state and
  should not be forced into positive or negative sentiment.

### Humor policy

Humor should pass all four tests:

1. It points to a visible fact, sequence, or choice.
2. It remains true when the user opens Evidence.
3. It does not imply motive, mental state, skill, or blame.
4. It still reads as affectionate if the user had a bad year.

Good source material includes a very long match, repeated returns to a hero,
an unusually narrow or wide observed pool, or a date that recurs. Avoid generic
“touch grass,” “NPC,” “copium,” and “skill issue” lines. These are portable
insults, not editorial observations, and they become especially damaging when
the underlying report is incomplete.

### Bridges and callbacks

Bridges should change the question, not merely announce the next data type.
Useful bridge forms include:

- **Scale shift:** “The year is one thing. The next choice is smaller.”
- **Contrast:** “The names moved. Did the shape move with them?”
- **Reversal:** “That was the result. Here is what followed it.”
- **Depth:** “The visible numbers are done. The relationship is next.”
- **Callback:** “The center we saw earlier is still here—just farther out.”

Use a callback only when the earlier fact is still visible or available in
Evidence. A callback that appears to remember a fact not present in an older
persisted report is a compatibility bug in prose form.

### Interaction and motion

Interaction should disclose meaning, not gate it. Every quiz, flip, chart, or
carousel needs a direct read path, a keyboard path, and a reduced-motion state.
Use semantic motion:

- count-up or stacking = accumulation;
- left-to-right timeline = chronology;
- side-by-side movement = contrast;
- flip or mask = a label being disclosed;
- pause = an explicit uncertainty or transition.

Do not use motion to imply confidence, causality, or a value being “won” unless
the report actually measures those things. An animation that cannot be paused,
replayed, or understood as a static frame is a production risk, not a reveal.

## 5. Reveal grammar library

The following grammars are reusable shapes for the existing 33-screen arc. They
are editorial patterns, not new analytical outputs. The examples use current
surfaces such as match count, busiest day, hero eras, post-loss response, and
identity slots; placeholders indicate existing fields rather than proposed
values.

| Grammar | Structure | Suitable V6.1 surface | Static fallback and motion | Risk / guardrail |
|---|---|---|---|---|
| **Receipt first** | Scope → one unmistakable fact → optional dry release. | Opening scope, match count, hours, longest match. | Render the fact immediately; a number may count up, but the final value must be present in the DOM. | A run of receipt-first screens becomes a dashboard. Follow with a question, contrast, or chronology. |
| **Question → answer** | Ask a narrow question → let the user choose/guess or continue → reveal → show receipt. | “What happened after a loss?”; hero-pool center; most-played hero. | The question remains readable without interaction; reveal on Next, Enter, or tap; reduced motion uses a crossfade. | Never require a guess to access the report. Do not suggest the user’s answer was predicted if no prediction was computed. |
| **Accumulation ladder** | Add one item at a time → threshold/shape becomes visible → name the observed pattern. | Losing-streak sequence; top hero stack; repeated hero eras. | Bars/cards build in source order; static view shows all items and the total. | An animation must not imply a threshold or qualification that the analytical contract does not define. |
| **Chronology / era** | Early state → change or hold → later state → one sentence about movement. | Busiest week/day, hero eras, chronological thirds, session positions. | Timeline is linear and scroll-safe; reduced motion shows connected stops with dates. | Do not attribute a change to a patch, mood, or decision without evidence. |
| **Contrast / split screen** | A vs B → each side gets its own receipt → relationship sentence. | Familiar vs stretch heroes; one-loss vs two-plus-loss; involvement vs exposure. | Side-by-side desktop becomes stacked mobile; no overlap; screen reader gets ordered labels. | Never collapse disagreement into a winner. Mixed components stay mixed. |
| **Boundary / reversal** | Expected story → supported exception or unresolved boundary → evidence invitation. | Post-loss result chain, transfer boundary, “not enough context” state. | The boundary appears as a deliberate pause, not an error; static text says what remains unknown. | “Unexpected” is editorial framing only if the expectation was actually established. Avoid causal language. |
| **Callback / return** | Earlier anchor → later echo → changed context or confirmation. | Hero pool center returning in transfer; early hero returning in final Signature. | Reuse a small visual token or label; static fallback repeats the earlier name and source. | Only callback to values present in the current payload; old reports may omit optional anchors. |
| **Quiet evidence** | Minimal setup → one careful statement → Evidence/Methodology affordance. | Mixed/neutral findings; methodology bridge; insufficient history. | No celebratory motion; preserve generous reading time and focus order. | Do not treat neutral as boring. A quiet page can build trust before a bigger reveal. |
| **Evidence mosaic** | Three independently supported signals → relationship sentence → identity candidate. | Identity Signature and “why this describes your Dota.” | Cards appear as a static three-part map; motion highlights refs one at a time. | Only use qualified slot refs. A mosaic is not permission to invent a global score or causal through-line. |
| **Artifact close** | Best standalone line → two supporting receipts → share/deeper action. | Final identity card, share candidates, deeper layer. | Server-rendered card remains legible when copied or downloaded; motion is optional. | A share card must stand alone and preserve scope/limitations where needed; never share private identifiers. |

### Recommended distribution across the current arc

This is a sequencing recommendation, not a page-count change:

- **Opening recognition:** use Receipt first for scope, match count, time, rank
  direction, and busiest moments. End the run with Chronology so the year has
  shape rather than only volume.
- **Good news:** use Question → answer for the wins bridge, then Accumulation
  for streaks and a compact Contrast for winning heroes. One positive section
  should have one tonal turn, not three jokes.
- **Adversity:** use Accumulation for the losing streak, then Boundary / reversal
  for what followed. Give the user a neutral path when post-loss evidence is
  absent or mixed.
- **Hero portfolio:** use Chronology for eras, Contrast for pool layers, and
  Callback when a familiar pattern returns across a hero change. This is the
  strongest place to make the report feel specifically Dota without claiming
  psychology.
- **Combat and session:** use Contrast for signals that disagree and Quiet
  evidence for session limitations. The visual should not imply a quadrant is a
  skill rating.
- **Synthesis:** use Evidence mosaic only after the source signals have appeared
  in the story. A Signature card should feel like recognition, not assignment.
- **Close:** use Callback to return to scope and time, then Artifact close for
  Share. Keep deeper diagnostics an invitation, not a promise.

## 6. Compatibility and release guardrails

This research supports presentation work only. It does not authorize a backend,
analytical, schema, or OpenDota change. The following constraints are part of
the editorial system:

1. Runtime JSON remains authoritative. A TypeScript type or a current fixture
   cannot justify copy for a missing persisted field.
2. Missing `story_band`, chronology, identity slots, comparison rows, optional
   copy, or a finding must degrade by omission or its truthful neutral/
   insufficient/mixed state.
3. No prose may fabricate findings, confidence, evidence refs, identity slots,
   cohort membership, causal explanations, or semantic outcomes.
4. The report window and eligible denominator belong near the first relevant
   receipt and remain available in Evidence/Methodology.
5. A direct story path must work for current and historical persisted fixtures.
   Conditional scenes are a feature: Strava’s recap is a useful external
   precedent for showing only scenes the available data can support.
6. A share card must use only eligible candidates with valid refs and must not
   expose account, Steam, report, match, or session identifiers.
7. “Compared with others,” percentiles, rank-style labels, and social matching
   are separate data products. They are not implied by a personal annual
   report.
8. Test the editorial grammar on a newest fixture and a sanitized historical
   production-shaped fixture. Verify first-to-last, backward, Next, Back,
   keyboard, Evidence, Methodology, Share, End, Read Again, 375px mobile,
   desktop, reduced motion, no horizontal overflow, and no pageerror/
   console/hydration error.

### Research questions still open

These should be answered by product/analytics owners before implementation, not
by copy:

- Which existing finding and Element records are guaranteed to be public and
  available to the story renderer?
- Which chronology fields survive in persisted reports from each supported
  version?
- Which share-card candidates have stable evidence refs and privacy-safe
  display labels?
- Is there a sanctioned cohort source for any future social comparison? If not,
  remove comparative wording rather than deriving it client-side.
- Which interaction affordances are allowed on mobile and in reduced motion?

## Source index

### Spotify and recap mechanics

- [2018 Wrapped](https://newsroom.spotify.com/2018-12-06/relive-your-year-in-music-with-spotify-wrapped/) — interactive rediscovery, guess-then-check, core lists, sharing.
- [2019 Wrapped](https://newsroom.spotify.com/2019-12-05/spotify-wrapped-2019-reveals-your-streaming-trends-from-2010-to-now/) — annual plus decade framing.
- [Spotify engineering: 2019 build](https://engineering.atspotify.com/2020/09/spotify-unwrapped-2019-how-we-built-an-in-app-experience-just-for-you) — simple/native/shareable goals, static-first build, share-card cost.
- [2020 Wrapped features](https://newsroom.spotify.com/2020-12-01/6-new-features-to-unwrap-in-your-spotify-2020-wrapped/) — quizzes, top-song story milestones, badges, playlists, sharing.
- [2020 share tips](https://newsroom.spotify.com/2020-12-09/3-tips-tricks-to-enhance-your-2020-wrapped-experience/) — interaction and customizable share cards.
- [2021 Wrapped](https://newsroom.spotify.com/2021-12-01/the-wait-is-over-your-spotify-2021-wrapped-is-here/) — film framing, Audio Aura, Playing Cards, Blend, social sharing.
- [2021 Audio Aura](https://newsroom.spotify.com/2021-12-01/learn-more-about-the-audio-aura-in-your-spotify-2021-wrapped-with-aura-reader-mystic-michaela/) — mood categories and weighted top-two composition.
- [2022 Wrapped](https://newsroom.spotify.com/2022-11-30/everything-you-need-to-know-about-2022-wrapped/) — Listening Personality, Audio Day, sharing surfaces.
- [2023 UX](https://newsroom.spotify.com/2023-11-29/wrapped-user-experience-2023/) — flip-card character, Sound Town, top genres, browser parity.
- [2023 Sound Town](https://newsroom.spotify.com/2023-12-01/wrapped-sound-town-berkeley-burlington-cambridge/) — cohort/contextual matching mechanics.
- [2024 UX](https://newsroom.spotify.com/2024-12-04/wrapped-user-experience-2024/) — up-to-three-phase evolution, distributed insights, AI features.
- [2024 art and science](https://newsroom.spotify.com/2024-12-04/the-art-and-science-behind-spotify-wrapped/) — editorial context layered over technology and data.
- [2025 UX](https://newsroom.spotify.com/2025-12-03/2025-wrapped-user-experience/) — feedback-led layering, quizzes, temporal movement, Clubs, Archive, replay controls.
- [2025 methodology](https://newsroom.spotify.com/2025-12-05/wrapped-methodology-explained/) — metric choice, exclusions, cutoff, and data boundaries.
- [2025 Clubs](https://newsroom.spotify.com/2025-12-03/wrapped-clubs-overview/) — descriptor/stream scoring and behavior-based roles.
- [Spotify animation engineering](https://engineering.atspotify.com/2024/01/exploring-the-animation-landscape-of-2023-wrapped) — data-bound animation parameters and web parity.
- [AoIR Wrapped study](https://spir.aoir.org/ojs/index.php/spir/article/view/14038) — celebration and skepticism around algorithmic identity.
- [Associated Press, 2025](https://apnews.com/article/spotify-wrapped-2025-release-music-tracking-8a7a7f08150eefd3a26020a4a9d046e1) — reported audience reaction and iteration after a sparse prior edition.

### Comparator products

- [Steam Replay 2024](https://store.steampowered.com/news/posts/?enddate=1734653759&feed=steam_clientAny)
- [Valve Dota Battle Report update](https://store.steampowered.com/news/posts/?appids=620%2C550%2C240%2C220%2C70%2C440%2C420%2C400%2C500%2C10%2C380%2C4000%2C300%2C30%2C5952%2C80%2C5489%2C5268%2C219%2C40%2C60%2C360%2C340%2C320%2C280%2C130%2C50%2C20%2C80822%2C80788%2C80762%2C80752%2C80747%2C80739%2C80633%2C5739%2C410%2C630%2C570%2C1800%2C80923%2C5734%2C5724%2C5260%2C5149%2C5150%2C5141%2C5139%2C5138%2C5073%2C5051%2C5032%2C997%2C987%2C985%2C960%2C937%2C936%2C934%2C933%2C932%2C931%2C930%2C916%2C923%2C922%2C915%2C914%2C913%2C912%2C905%2C904%2C918%2C917%2C901%2C81061%2C81026%2C5825%2C5722%2C995%2C906%2C1003&enddate=1663275332&feed=steam_community_announcements)
- [STRATZ](https://stratz.com/) — dense player profile, comparison, and replay-oriented analytical destination.
- [Dotabuff TI 2025 meta recap](https://www.dotabuff.com/blog/2025-09-16-the-international-2025-meta-recap) — contextualized Dota trend editorial, not a personal recap.
- [PlayStation 2024 Wrap-Up](https://blog.playstation.com/2024/12/10/celebrate-30-years-of-playstation-with-playstation-2024-wrap-up-launching-today/)
- [YouTube Music Recap 2024](https://blog.youtube/news-and-events/2024-music-recap-youtube/)
- [Apple Replay support](https://support.apple.com/en-ie/109356)
- [Reddit Recap 2022](https://redditinc.com/news/reddit-recap-2022-product)
- [Duolingo Year in Review](https://blog.duolingo.com/year-in-review-behind-the-scenes/)
- [Duolingo 2020](https://blog.duolingo.com/duolingo-2020-year-in-review/)
- [Strava Year in Sport](https://support.strava.com/en-us/articles/15401959-your-year-in-sport)

### Dota community and trust signals

- [Dota gameplay issue: conflicting Battle Report values](https://github.com/ValveSoftware/Dota2-Gameplay/issues/9629)
- [Dota Rewind discussion, 2020](https://www.reddit.com/r/DotA2/comments/kzp438)
- [Dota Rewind discussion, 2025](https://www.reddit.com/r/DotA2/comments/1psy4ns/i_made_a_dota_2_rewind_-_personal_recap_for_2025)
- [Leetify Dota recap discussion](https://www.reddit.com/r/DotA2/comments/1qavt53/we_built_a_recap_of_your_dota_2_stats_for_2025)
- [Hero-pool role/comfort discussion](https://www.reddit.com/r/TrueDoTA2/comments/1g75d87/to_climb_mmr_should_i_select_a_hero_im_most_comfortable_with_or_something_that_will_work_in_the_particular_game)
- [Hero-pool balance discussion](https://www.reddit.com/r/TrueDoTA2/comments/y67xfn/tools_to_tell_you_how_to_balance_out_your_hero_pool)
- [Hero-pool size discussion](https://www.reddit.com/r/TrueDoTA2/comments/1aqkzu9/is_6_heroes_for_your_main_role_really_enough)
- [Learning a hero pool](https://www.reddit.com/r/learndota2/comments/1gspbli/help_with_picking_hero_pool)
- [Loss-streak reset discussion](https://www.reddit.com/r/DotA2/comments/1nech4f/how_do_you_guys_wind_down_after_a_brutal_losing_streak)
- [TrueDoTA2 loss-streak discussion](https://www.reddit.com/r/TrueDoTA2/comments/rxg76d/why_do_loss_streaks_feel_so_rigged)
- [LearnDota2 loss-streak advice](https://www.reddit.com/r/learndota2/comments/vdiel4/any_tips_on_dealing_with_losing_streaks)
- [Memorable Dota games](https://www.reddit.com/r/DotA2/comments/1m68xxt/what_is_that_one_dota_game_you_played_that_still_lives_rent_free_in_your_head)
- [Satisfying Dota moments](https://www.reddit.com/r/DotA2/comments/17o9dxs/what_is_the_most_satisfying_feeling_in_dota)
- [Hero-pool roast prompt](https://www.reddit.com/r/DotA2/comments/1huy4uq/what_does_my_hero_pool_tell_you_about_me)
- [Reddit Recap community reaction](https://www.reddit.com/r/recap/comments/18c85p8)
