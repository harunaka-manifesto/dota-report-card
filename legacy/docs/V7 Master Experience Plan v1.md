> **Legacy report-card documentation — non-authoritative for Dota Tracker.**
> For current product and architecture rules, start at [Dota Tracker](../../docs/tracker/README.md).
> Retained for the live report product, compatibility and historical evidence.

# Dota Report Card V7 — Master Experience Plan

7 September 2026 · Experience specification v1 · Planning deliverable, not production certification

Internal source boundary: the supplied V7 backend capability manifest, V7 design content catalog, and V6.1 main script. The manifest governs data truth; this document specifies experience decisions. External research informs the choices, not capability availability. No implementation audit, production code, Figma work, analytical changes, provider acquisition, or deployment forms part of this deliverable.

The source prompt requests a planning document. “Implement the master plan prompt” is therefore fulfilled here as that complete planning exercise, not as permission to build or deploy the future product. Initial administrative reads of the repository contract and working-tree status preceded discovery of the prompt’s context boundary; no implementation was inspected or used as evidence.

## 1. Executive recommendation

Build **a short Dota yearbook with a private next-game note**. Start with something the player recognizes, find one moment worth remembering, show the habits behind the games, offer one experiment, then give the player a playful calling card.

The emotional sequence is **recognition → memory → discovery → agency → identity → choice of what to share**. Annual facts supply recognition. Findings supply surprise. The recommendation supplies one useful action. The archetype supplies a name friends can react to. None needs to impersonate the others.

Use manually paginated scenes, with optional detail inside each scene. The ideal report normally takes 2–3 minutes and about 8–10 scenes; its ceiling is 11. The measured-capability version normally takes 60–120 seconds and 5–7 scenes; its ceiling is 7. These are design targets, not measured completion times. Sparse reports should be honestly shorter. No introductory chapter gets three slides before the first personal fact.

Make annual context, a familiar hero, and one remembered period the first descriptive investment. Do not rebuild the 34-page V6.1 script or add a scoreboard chapter. Identity and scene order should vary substantially with available content; navigation, content density, and endings should remain predictable.

**Release reality:** Tier A means measured development capability, not a working consumer report. The manifest explicitly says no assembled V7 `ReportPayload` producer exists; persistence wiring is also missing, and sealed validation is untouched. “Ship-now” below means the strongest content sequence requiring no new analytical or descriptive capability, after assembly, persistence, contract/version work, and authorized release validation. It does not mean V7 can be deployed today.

## 2. Research synthesis

Research was conducted on 7 September 2026 using public product documentation and selected community discussions. Product pages establish documented mechanics; community posts establish individual reactions, not their prevalence. Historical release pages do not prove every current-client detail. The decisions in the final column are product judgments, not measured causal effects.

### Annual recap mechanics worth borrowing

| Product | What the source documents | What to borrow, and what not to copy |
|---|---|---|
| Spotify Wrapped | Its 2025 experience combines familiar favorites with personalized stories, varies with available listening data, and supports revisiting moments and playback-speed control. [Spotify 2025 experience](https://newsroom.spotify.com/2025-12-03/2025-wrapped-user-experience/) | Open with recognition, then earn a less-obvious observation; support return visits. Do not imitate Spotify’s visual identity or assume timed playback is right for reading a Dota claim. |
| Spotify Archive / remarkable days | Archive selects up to five days using narrative potential and statistical strength, grounds narrative in logs and computed facts, and avoids repetition. Its engineering account describes a timezone bug that produced incorrect discovery-day stories despite fluent copy. [Inside the Archive](https://engineering.atspotify.com/2026/3/inside-the-archive-2025-wrapped) | A specific date turns behavior into memory; selection matters more than displaying every date. Use deterministic candidates and grounded copy. Do not add an unconstrained narrator or assume the busiest day was psychologically important. |
| YouTube Music Recap | The 2024 recap uses animated personal cards, a listening description, a timeline of important months, a movie-character framing, and optional personal photos/podcast material. [YouTube Music Recap 2024](https://blog.youtube/news-and-events/2024-music-recap-youtube/) | Alternate summary and episodes; a hero portrait can be a memory cue. Do not invent a personality or personal photo/match record the backend does not provide. |
| Apple Music Replay | Monthly and yearly insights, milestones, an audiovisual highlight reel, shareable insights, and previous-year playlists sit alongside an updating current-year playlist. [Apple Replay support](https://support.apple.com/en-us/109356) | Treat the short recap as an entrance to something revisitable. Do not copy leaderboard achievements or percentile claims into a product without those outputs. |
| Steam Replay | Valve’s 2024 announcement describes games, achievements, streaks, comparisons, monthly playtime, genres and device splits, with sharing. [Valve Steam Replay announcement](https://store.steampowered.com/news/posts/?enddate=1734653759&feed=steam_clientAny) | Familiar games and chronological activity are natural gaming memories. In Dota, familiar heroes serve that role. Do not inherit a dashboard’s full metric inventory or radar chart. |
| PlayStation Wrap-Up | The 2025 release describes games/genres, playtime, trophies, and a closing summary card plus completion avatar. [PlayStation Wrap-Up 2025](https://blog.playstation.com/2025/12/09/playstation-2025-wrap-up-launches-starting-today-explore-your-personalized-gaming-recap-for-2025/) | Give the sequence a concrete keepsake destination. Do not add an unrelated reward economy just to force completion. |
| Nintendo Year in Review | Nintendo’s 2025 experience invites users to revisit play activity, choose their own favorite game, and share. [Nintendo Year in Review 2025](https://www.nintendo.com/us/whatsnew/rediscover-your-playful-past-with-the-nintendo-switch-2025-year-in-review/) | “Most played” and “favorite” are different. Let the player choose the card they identify with; never label an inferred most-played hero their favorite. |
| Strava Year in Sport | Personalized scenes depend on available data and include activities, social connections, and standout moments. Individual scenes and a customizable summary are shareable; the full experience remains private. [Strava Year in Sport](https://support.strava.com/en-us/articles/15401959-your-year-in-sport) | Omit unavailable scenes and select public output separately. Do not export the private report wholesale or invent team/social data. |
| Duolingo Year in Review | Duolingo reports that its top 10% of XP earners generated over half of shares in 2020; behavioral styles created another reason to share. It also describes adapting copy to language and screen constraints. [Duolingo behind the scenes](https://blog.duolingo.com/year-in-review-behind-the-scenes/) | Ordinary players need a recognizable identity surface. This supports investing in a factual hero fallback when an archetype refuses. Do not manufacture a label or positive Finding to make everyone exceptional. |

These sources do not establish a universally best opening screen or optimal length. My decision is to reveal the first actual personal fact on the first scene, use at most one main memory, and keep label explanations optional. A story-worthy statistic answers a recognizable question and changes what the reader thinks: a hero replacing another in a particular month does more work than another annual total.

### Positive and negative recap reactions

One public Wrapped discussion praises richer album information and playful group identity, while other commenters report unexpected rankings or confusing minute totals; another asks what its group name means. These are reported experiences, not independently verified defects. They suggest two useful design checks: can the player recognize the underlying observation, and can the label be explained immediately? [Mixed reactions to Wrapped 2025](https://www.reddit.com/r/spotifywrapped/comments/1pd33t1/this_years_wrapped_mightve_been_the_best_one_yet/).

A separate discussion includes a participant who misses the previous year’s quirky evolution names. The implication is not “more jokes always win”; delight and irritation can coexist. Use specific language sparingly and preserve the factual meaning. [Wrapped naming discussion](https://www.reddit.com/r/spotifywrapped/comments/1pd95u7/what_are_your_thoughts_on_this_years_spotify/).

Duolingo’s retrospective says unstable statistics were omitted and share images were chosen so friends could understand a result without traversing a whole page. Its selected learner testimonials celebrate recognition, but are company-curated rather than independent satisfaction evidence. [Duolingo 2020 retrospective](https://blog.duolingo.com/duolingo-2020-year-in-review/).

The research supports accuracy, specificity, explainable labels and standalone cards. It does **not** establish how many Dota users find recap experiences too short, generic, basic, or overdesigned. Those remain risks to test, not invented research findings. The design response is a short authored route with optional evidence and exploration, not maximal animation or maximal statistics.

### Dota Plus Battle Report: territory it already occupies

Valve’s launch documentation describes prior-season hero, role and overall comparisons with similarly skilled players; personalized trends, records and match highlights; deeper sorting/filtering by hero, role and match; seasonal delivery; and achievement medals with Shard rewards. Its highlight example includes a comeback. This is a documented summary/highlights/exploration product. Calendar functionality and exact current-client controls were not verified, so this plan does not claim them. [Valve Battle Report Update](https://www.dota2.com/battlereport).

Our distinction is editorial: a limited sequence about the player’s recognizable habits, a single private action, and a self-contained keepsake. V7 cannot copy rank-matched comparisons, medals, or rich comeback records merely because Valve has them. The dashboard-like sorting/filtering belongs in optional exploration, not the main emotional arc.

### What the Dota community evidence suggests

| Observed reaction | Product implication, explicitly our judgment |
|---|---|
| Hero-spam discussions describe affection, familiarity and understanding, alongside boredom and fatigue. [Spamming one hero](https://www.reddit.com/r/DotA2/comments/tj9u5f), [Hero-spammer fatigue](https://www.reddit.com/r/DotA2/comments/1fpaoop) | Repetition can be warm recognition rather than a deficiency. Use actual usage, not “lack of versatility.” A broad pool is not automatically superior either. |
| Turbo players objected to being absent from reports; others wanted separation rather than mixed statistics. Later discussion also objects to blended Turbo highlights while recognizing that exclusion leaves some players with nothing. [Turbo recognition](https://www.reddit.com/r/DotA2/comments/v8b6kn), [Separate mode requests](https://www.reddit.com/r/DotA2/comments/v8dihq), [Mixed highlights complaint](https://www.reddit.com/r/DotA2/comments/1l6wnnu) | Recognize Turbo as legitimate play and print the mode on identity cards. These posts do not independently establish current client behavior. |
| Session discussions include both continuing until a win and being satisfied after one game; “one more game” appears alongside burnout and taking breaks. [Session endings](https://www.reddit.com/r/DotA2/comments/z1q40j), [One-more-game discussion](https://www.reddit.com/r/DotA2/comments/1rfeii3/is_it_even_possible_to_love_dota_again/) | The observable next-match behavior is interesting; assigning anger, addiction or resilience is unnecessary and unsupported. |
| Carry discussions distinguish farming, fighting, survival, and hero/item timing; learners find the decisions context-dependent. [Farming versus fighting](https://www.reddit.com/r/learndota2/comments/1frewzk), [PA timing question](https://www.reddit.com/r/learndota2/comments/1gqltez) | “Item done, what next?” is understandable vocabulary. Do not equate more fights or less jungle with universally better play, and do not turn these anecdotes into current build advice. |
| A support learner reports feeling more useful after changing behavior despite another loss; the discussion spans wards, objectives, farm and teammate timings. [Position-five midgame discussion](https://www.reddit.com/r/learndota2/comments/1cxc190) | Usefulness need not be narrated as winning. Ward uptime is an observable behavior, not a complete support grade. |
| A comeback discussion asks how a defensive fight becomes progress, with replies mentioning lanes and map control. [Coming back discussion](https://www.reddit.com/r/learndota2/comments/15r5oow) | A win flag is not enough to narrate a personal rescue or comeback. A bounded run-to-win memory is more defensible than an invented comeback story. |
| Rank/improvement discussions include feeling overwhelmed and asking for one or two priorities, as well as disagreement that rank captures the whole experience. [Conscious improvement](https://www.reddit.com/r/learndota2/comments/135adx4), [Rank versus improvement](https://www.reddit.com/r/learndota2/comments/18wce5y) | One next-game note suits the audience better than a plan of corrective tasks. Rank stays optional and descriptive. |
| A Battle Report post about Dire results attracts speculative explanations and a sample-size question. [Dire/Radiant discussion](https://www.reddit.com/r/DotA2/comments/1ha85kr) | Surprise creates conversation, but speculation is not permission to publish V7’s rejected side-sensitivity dimension. |

This is a purposive sample of public conversations, not a survey of casual players. It establishes useful vocabulary and tensions, not consensus, causal effect, or conversion forecasts. The final architecture deliberately uses the strongest recurring material—familiar heroes, real moments, bounded behavior, optional depth—without importing the communities’ coaching claims or memes as analytical truth.


## 3. Experience principles

1. **Recognition precedes interpretation.** In the ideal report, show a real hero or date before asking the player to accept a behavioral story. In the measured-only report, open on a concrete supplied Finding, not a faux annual total.
2. **One scene, one new thought.** A number, its meaning, and one supporting image are enough. Additional evidence belongs behind a labeled control.
3. **Show the observable Dota situation.** A ward’s lifetime can be pictured. “Map awareness” cannot be inferred from it. Kill involvement timing is not a judgment of impact.
4. **The slate is material, not a slide order.** Choose a recognizable lead, group related patterns, and keep criticism to one main-story scene. All supplied Findings remain reachable.
5. **Ordinary is a valid year.** Familiar heroes and a real date do not need a record, a percentile, or a dramatic comeback to deserve attention.
6. **Make the action smaller than the analysis.** One canonical recommendation, one observation to watch. No runner-up checklist, task streak, or implied win-rate promise.
7. **Earn the label without pretending it summarizes everything.** Explain the actual archetype axes. Do not claim hero loyalty, rank movement, or the recommendation caused the label.
8. **Public content is selected afresh.** Export only approved ingredients, not the DOM of the private report. The player previews the exact card.
9. **Omission must read as editing.** No empty chapters, missing-axis badges, apology bridges, or substitute archetypes. Acquisition failure gets a clear separate state.
10. **The player controls time.** No auto-advance, forced suspense, mandatory dragging, or reduced-motion penalty.

Humor rule: factual line first; at most two dry lines per complete report, never consecutive, never on a recommendation, adverse Finding, rank display, or acquisition failure. Fixed candidates are the hero-cast line “Some familiar faces in the draft.” and the closing line “The Ancient had a busy year.” The latter requires actual annual-window metadata; otherwise omit it. No joke is mandatory, and no joke implies addiction, tilt, laziness, or skill.

### Source conflicts resolved

| Conflict or ambiguity | Decision |
|---|---|
| Catalog calls metadata always available and concludes everything catalogued is computed; manifest marks window/counts/rank/provenance B | Treat these as B, requiring producers. No year label or total in measured-only mocks without an explicit supplied, trustworthy value. |
| Manifest says 265/276 get a recommendation, then “none receive zero” | Use conditional refusal rules; the intended coverage is 265 recipients, not a promise for every player. |
| V6.1 requires an archetype for valid reports | Superseded. V7 refuses the entire archetype when any axis is unavailable. |
| Catalog describes map coverage; actual ward measure is minutes with own observer alive | Say ward uptime, never area revealed, vision placement quality, or map-awareness skill. |
| Catalog calls deaths “away from your team”; measure is absence of team kill activity in that minute | Name the event condition. Never depict literal teammate distance as measured evidence. |
| “Build comes online” vs eighth item-purchase progress | Name purchase pace and the eighth purchase, not a power spike or finished build. |
| `direction = sign(z)` but some example language implies sign of a player’s win/loss contrast | Separate population position from the sign of the player’s own estimate; rules below. |
| Catalog calls verification proof the recommendation worked | Watching a behavior change is not proof it caused better results. Use “What to watch,” not “How you’ll know you win more.” |
| Specials use an internal provisional 98th-percentile cut; catalog mentions top 2% | Display the returned Special label, with no rarity number or top-X% badge. |

## 4. Story architectures explored

| Architecture | Sequence | Strength | Weakness / breaking case |
|---|---|---|---|
| Scoreboard to coaching | Volume → wins → losses → problems → advice → identity | Immediately legible outcome structure | Loss-heavy players receive a review, ordinary years repeat familiar stats, and absent history breaks the opening. Reject. |
| Mystery identity | Locked label → clues → axes → reveal → advice | Strong anticipation and potential sharing | Refusal makes the promised payoff disappear; axes become an artificial personality quiz. Reject. |
| Calendar documentary | Month-by-month heroes → dates → streaks → annual synthesis | Recognition and temporal specificity | Twelve periods become repetitive; stable pools and sparse months fail; too much new production work. Retain one memory, not the structure. |
| **Yearbook with a next-game note** | Familiar cast → one memory → selected habits → one experiment → identity or keepsake | Supports both mundane and dramatic histories; recommendation stays private; optional capabilities can disappear cleanly | Measured-only version lacks dates and heroes. Admit that gap and fund the minimum memory layer. **Choose this.** |

## 5. Final recommended story map

All copy below is working product copy. Braced values are actual payload substitutions, not invitations to invent metrics. Where an example profile is used, its data are illustrative. Scene IDs are stable; page numbers are assembled afterward. “A” means AVAILABLE NOW — TIER A. “B” means ASSEMBLY / PRODUCER NEEDED — TIER B. “D” means NEW DESCRIPTIVE DERIVATION PROPOSED. Static editorial text is not a measured capability.

Every scene inherits visible Back/Next, progress, End, and optional Methodology. Evidence appears only for supplied supporting data. No dedicated bridge screens. The transition is the next scene’s opening line, selected from §6.

### O — The year, already recognizable

- **Job / feeling / question:** Establish personal scope and scale: “Yes, this is my Dota.” What history is this about?
- **Atoms / status:** Window and eligible recorded count **B**; optional display name is a **proposed presentation input**, not established by the manifest. Dominant mode **A**, optional. This scene is ideal-only unless context is genuinely supplied.
- **Headline:** “{N} games. Your kind of Dota.” Singular: “1 game. Your kind of Dota.”
- **Support / display:** “Recorded between {start_date} and {end_date}.” Name, if supplied and safe, above the number. Never “all your games.” No separate hours page.
- **Visual / interaction:** A large count with a compact date strip; Next immediately available. Motion opportunity: recorded game marks gathering into the number. No one-dot-per-game requirement.
- **Conditionality / omission:** Require a valid positive count and a trustworthy interval. If absent, omit O and begin with the first substantive scene using the opening wrapper below. If count is zero but analytical atoms exist, treat the payload as inconsistent rather than silently fabricating a report.
- **Transition:** To H: “These were your regulars.” Otherwise use the destination’s standalone headline.
- **Sharing / justification:** Yes, as context or alternate factual card. Earns one scene by grounding the scope; scale does not need to be exceptional.

### H — Your regulars

- **Job / feeling / question:** Introduce the familiar cast. “Of course that hero is here.” Who did I keep picking?
- **Atoms / status:** Ordered hero IDs/names/assets and eligible counts **D**, within the broader B history gap. No performance interpretation.
- **Headline:** “You kept coming back to {Hero}.” If the lead is tied: “These were your regulars.” If only one hero: “One hero. {N} games.”
- **Support / display:** Lead portrait and “{n} recorded games”; up to two smaller runners-up with counts. Never “best hero.” Optional fixed dry line from §3.
- **Visual / interaction:** Portrait-led scene, not a leaderboard table. Tap “All heroes” for the full supplied distribution; it is optional, not a new scene. Motion opportunity: repeated picks settling into three portraits.
- **Conditionality / omission:** Require valid hero attribution. Missing hero names omit the affected portrait; no raw IDs. If the highest-count hero cannot be labeled, use “Your familiar picks” and show only named heroes without claiming global rank. If no usable heroes, omit.
- **Transition:** M: “One part of the year worth revisiting.” Otherwise first Finding: “And there was a pattern in the games.”
- **Sharing / justification:** Yes, positive factual choice-of-hero material. Gives an ordinary player an identity moment without inventing a classification.

### M — One thing to remember

- **Job / feeling / question:** Trade an aggregate for a memory. “I remember that stretch.” What moment is worth revisiting?
- **Atoms / status:** One deterministic memory candidate **D**: monthly hero change, a completed losing-run-to-win sequence, or busiest recorded seven-day stretch. Use at most one main memory.
- **Working variants:**
  - Hero change: “{Hero A} in {month A}. {Hero B} in {month B}.” Support: “Your most-played hero changed.” Two counts with their periods. No invented “obsession.”
  - Completed sequence: “Then came a win on {Hero}.” Support: “After {L} recorded losses in a row.” Show the sequence and date. Never credit the hero with causing the win.
  - Familiar stretch: “{start}–{end}: {N} games.” Support: “Your busiest recorded seven-day stretch.” Optional leading hero only if supplied.
- **Visual / interaction:** One before/after, one run, or one seven-day strip. “Explore the dates” opens a detail sheet. Motion opportunity: hero replacement, a win interrupting a run, or a year narrowing to seven dates. Illustrations must not invent a match timeline.
- **Conditionality / omission:** Rules in §13. No qualifying candidate → omit. Stable hero pools can still use a real busy stretch; no unsupported “your pool changed.” An unresolved loss run never gets a recovery story.
- **Transition:** “The dates tell one part. Here’s a pattern in the games.” If no Finding, jump to the standalone recommendation or identity headline.
- **Sharing / justification:** Hero change and factual stretch: yes, opt-in. Loss-run variant: private. This is the ideal experience’s essential memory beat, not a requirement that every year be dramatic.

### D1 — A recognizable habit

- **Job / feeling / question:** Deliver the first surprising but understandable observation. “I didn’t know I did that.” What shows up in my play?
- **Atoms / status:** Lead Finding **A**, selected by §6; exact copy from §7. Backend section is not a chapter title.
- **Example headline:** “Your wards tend to stay on duty.” Support: “You tend to spend a larger share of the match with an observer ward alive than the comparison players.” If a directly interpretable point is supplied: “About {p}% of match minutes with your observer alive.”
- **Visual / interaction:** One metaphor plus one line of interpretation. In this example, a ward lifetime strip, never a map heatmap. “Evidence” opens supplied units, estimate, interval, and sample. Motion opportunity: the measured concept resolving into the headline.
- **Conditionality / omission:** Require at least one safe-to-render Finding. If all are adverse, this slot becomes the single compact D3 scene instead. Unknown dimensions go to an unsupported-content state in details; never guessed copy.
- **Transition:** D2: “Another part of the pattern.” D3: “One pattern worth noticing.” R: “For the next queue, one thing to try.” I: “A playful name for how you play.”
- **Sharing / justification:** Only approved favorable variants, rendered as tendencies. It deserves prominence because its meaning is concrete, not because the score is a public achievement.

### D2 — The other side of your habits

- **Job / feeling / question:** Add a different recognizable behavior without repeating the reveal format. “That too.” What else do I tend to do?
- **Atoms / status:** One or two remaining non-adverse Findings **A**, ideally a common topic such as after-match behavior.
- **Example:** “After the result, what happens next?” Rows use exact directional variants, such as “After a loss, your next match tends to come sooner” only when the within-player estimate supports that sentence. Pair a hero-switch observation without claiming tilt.
- **Visual / interaction:** Maximum two compact observations with different small illustrations; additional supplied Findings accessible via “{n} more patterns.” Motion opportunity: a result becoming a next-match arrow. No simulated actual match chain.
- **Conditionality / omission:** Only when at least one non-adverse Finding remains after D1. Never repeat the same atom or turn five Findings into five clones.
- **Transition:** D3 if present; otherwise the next substantive scene’s standalone line.
- **Sharing / justification:** Per-row favorable whitelist only; the whole mixed scene is not shareable. Earns its slot through breadth, not exhaustive analytics.

### D3 — One rough edge, kept in proportion

- **Job / feeling / question:** Recognize a difficult habit without an accusation. “Fair enough.” Is there something worth noticing?
- **Atoms / status:** Remaining adverse Findings **A**. At most one such scene in the main story, regardless of count.
- **Example headline:** “Your deaths tend to come closer together.” Support: “A larger share of the gaps between your deaths falls within 90 seconds than in the comparison group.”
- **Display / visual:** Highest-scoring adverse Finding receives the headline. Other adverse Findings appear under a clearly counted “{n} more patterns” expansion, each with its own explanation and Evidence. They are not discarded. One neutral death-gap strip, no blame-red grade.
- **Interaction / motion:** Expansion is user-controlled. No repeated-death animation or accumulating failure sounds; a static interval image is sufficient.
- **Conditionality / omission:** Require adverse material. If this is the only Finding scene, its opening wrapper is “A pattern in your games.” If point uncertainty makes a claim tentative, retain tendency wording; do not add a new reliability threshold.
- **Transition:** R: “If you want one thing to try next game…” I: “There’s also a playful way to describe your games.” C: “That’s the report. The next queue is yours.”
- **Sharing / justification:** No. Makes room for honest negative material once, then releases the player from it. It never asserts that the recommendation fixes this Finding.

### R — One thing for the next queue

- **Job / feeling / question:** Give agency. “I can remember that.” What is the one thing to try?
- **Atoms / status:** Returned primary recommendation, canonical instruction and verification, optional own-win/loss observation **A**.
- **Headline:** “One thing for the next queue.” Support: the dimension-specific setup in §8, then the canonical instruction verbatim.
- **Display / visual:** Instruction is the dominant content. Below: “What to watch” and a short human-readable label tied to canonical verification. The exact verification string remains in Evidence. No priority, gap, or runner-up on the main face.
- **Interaction:** “Why this?” and “What to watch” expand inline or in the detail sheet. No public Share. Copying the instruction is private utility, explicitly labeled “Copy for myself.” No automatic reminder or experiment enrollment.
- **Motion opportunity:** Several visual possibilities clearing away to leave one instruction; no animated improvement forecast.
- **Conditionality / omission:** Missing recommendation → omit R and all setup. Unknown canonical dimension or missing instruction → do not synthesize advice.
- **Transition:** I: “One suggestion for next time. A name for this time.” Without I: “Keep the part that sounds like you.”
- **Sharing / justification:** No. This is the only coaching-shaped moment and stays small enough to remember.

### I — Your calling card

- **Job / feeling / question:** Playful identity payoff. “That sounds like me.” What name fits these measured tendencies?
- **Atoms / status:** Complete returned archetype label, axes, stratum, and optional Special **A**. No inferred/default axis.
- **Headline:** “{returned_label}.” Eyebrow: “Your {Standard/Turbo} calling card.” Support from §9. Normal example: “The Early Bird.” / “Your kill involvement leans a little earlier for Turbo.”
- **Visual / interaction:** Bespoke art slot inside the common focus template. Label first; “Why this name?” opens the three measured axes. No seven-signal chart. Native visible “Reveal” is optional for first view; Next never waits. Read Again shows the settled state.
- **Motion opportunity:** A name resolves from three subtle motifs. A Special replaces the normal reveal at the outset; never show two competing winning labels.
- **Conditionality / omission:** All axes and valid stratum required. If absent, no teaser anywhere. No “unclassified,” “balanced,” or default label.
- **Transition:** C: “Keep the part that sounds like you.”
- **Sharing / justification:** Yes, with mode context baked into the card. Converts explainable observations into a social object, not a scientific personality type.

### C — Choose what leaves the report

- **Job / feeling / question:** Finish on the player’s terms. “That’s the bit I’d send.” What do I want to keep or share?
- **Atoms / status:** Whitelisted ingredients from prior scenes **A**, optional B/D facts. Share artifact generation is **proposed presentation derivation**; the B share-card model has no producer. Closing copy is static, not a claimed backend output.
- **Headline:** “Keep the part that sounds like you.” Card default from §10. No-asset branch: “That’s the report. The next queue is yours.”
- **Support / display:** One full-size preview; “Choose a different card” when alternatives exist. Never an auto-collage of private content. With no safe public ingredient: Read Again and Done, no empty share surface.
- **Visual / interaction:** Share, Save image when supported, Read Again, Done. Optional Methodology remains accessible. Motion opportunity: only previously eligible public ingredients arranging into one card.
- **Conditionality / omission:** Always closes a substantive report, except in the one-scene compact case where these actions attach to the only substantive scene. No upsell chapter.
- **Transition:** End. Read Again returns to first assembled scene; Done exits to the report’s entry point without regeneration.
- **Sharing / justification:** The preview is the precise public output, and a meaningful ending still exists without a label or a share card.

### Measured-only opening wrapper

If O is absent, the first substantive scene gets a small “Your Dota, in a few patterns” eyebrow. No stand-alone hello screen. For identity-only output use “Your Dota calling card”; for recommendation-only output use “One thing to try.” Do not write “your year,” “2026,” “365 days,” or a match count without reliable corresponding metadata. A recommendation-only result is explicitly a short private note, not a full annual recap.

## 6. Dynamic story engine

### Inputs and boundaries

Consume normalized, persisted capability objects, not raw matches. The downstream implementation must version this editorial rule set and persist or reproducibly derive the ordered scene IDs from a versioned report. No frontend re-ranking of the population, confidence gates, tier escalation, or analytical recomputation.

The manifest and catalog disagree on some field aliases (`dimension`/`dimension_key`, `dominant_mode`/`stratum`). Those are schema questions for the assembly boundary; they are not permission for scattered component fallbacks. Missing optional capabilities remove scenes. Malformed known capabilities fail closed individually; an unrecognizable report contract gets an explicit unsupported-report state rather than a fake empty report.

### Finding selection and polarity

1. Start with the supplied slate, at most five. Preserve every supplied Finding in the accessible pattern inventory; do not pull excluded dimensions back from deeper analysis.
2. Sort reproducibly by descending score, then canonical dimension key. Score stays private. No extra numerical quality cutoff or strength band.
3. A zero population direction is neutral for ordering and is not eligible for a favorable share variant; use the actual estimate and its supported meaning rather than inventing an opposite. Assign **editorial valence**, separate from `section` and `direction`: favorable, neutral, adverse. Favorable candidates: higher ward uptime; lower clustered-death share; lower no-team-kill death share; shorter first-item-to-involvement delay; higher tower-after-won-fight rate. Their opposites are adverse. Treat all other dimensions as neutral, including high/low novelty, duration, flexibility, purchases, post-loss habits, and the two lead contrasts. This conservative whitelist makes no performance grade.
4. `direction` indicates population-relative high/low, not whether an event happened more after losses than wins. Within-player contrast copy requires the estimate and interval in that contrast’s own frame. If `z > 0` but the point contrast is negative, use the negative own-contrast variant, not the positive-z interpretation. Never let section choose good/bad copy.
5. D1 lead pool: non-adverse concrete concepts first—hero novelty, ward uptime, farming split, item-to-involvement, game duration, post-loss continuation/switch/requeue. Choose highest score within that pool; if empty choose highest-score other non-adverse Finding. If none, omit D1 and use D3. This is a presentation preference, not an analytical significance ranking.
6. D2 receives all remaining non-adverse Findings. Choose first two visible by topic matching, then score/key: prefer two sharing `after-result`, `in-match rhythm`, or `resource habits`; if no shared pair, top two. Additional rows use a counted expansion. Groups: after-result = three post-loss dimensions; resource habits = vision, farming, purchase, spike; rhythm = duration, flexibility, fight centroid, novelty; outcomes = two lead contrasts and tower conversion. All rows retain independent claims.
7. D3 receives all adverse Findings. Highest score/key visible; the rest in a counted expansion. This keeps a five-adverse slate to one main-story beat without claiming only one Finding exists. The pattern inventory says “5 patterns” and provides every row, never “your only pattern.”
8. No Finding is repeated across D1/D2/D3. One non-adverse Finding = D1 only. Two non-adverse Findings = D1+D2. Mixed favorable/adverse pair = D1+D3. No Findings = no D scenes.

Grouping does not imply joint evidence or causation. A high neutral score cannot make a neutral behavior share-safe. A favorable Finding in `what_is_costing_you` belongs in D1/D2, never in an automatically negative chapter.

### Assemble, then write transitions

Ideal order: **O → H → M → D1 → D2 → D3 → R → I → C**. Up to two optional context-detail scenes may be inserted only in the ideal version: **E** after H for hero-period exploration and **K** after the last available history scene (M, otherwise H, otherwise O) for user-requested rank history. These are detailed below. Neither is inserted by default; their inclusion is an explicit player choice made from the local detail control, and progress expands deterministically. They are the only additions allowed to the 9-scene base ceiling.

Measured-only: **D1 → D2 → D3 → R → I → C**, with at most one context opener O only if a trustworthy metadata producer has actually supplied it. Under strict Tier-A-only conditions, O is absent: maximum **6** scenes; **7** with genuinely available context metadata. Nothing calls B metadata “measured.”

A substantive report has at least one nonempty analytical, identity, recommendation, or eligible descriptive scene. For exactly one substantive scene, merge C actions into it: minimum **1**. For two or more, append C: minimum **3**. There is intentionally no padded two-scene one-atom report. No usable personal content → separate insufficient-history state, not a one-scene “report.” Mode metadata alone is context, not enough to launch the report.

**Expanded ideal ceiling 11; default ideal ceiling 9; strict measured-only ceiling 6; measured plus supplied context ceiling 7.** Typical ideal includes 8–9, with one optional exploration sometimes making 10. Counts exclude sheets, share previews, and error/loading states. Early executive length refers to this actual default and opt-in range, not eleven mandatory scenes.

Transitions are destination-based, with only the explicit variants in §5. Never refer to a skipped predecessor. Do not promise a future archetype unless I is already assembled. Use only the immediate-predecessor-to-I transition specified in §5, followed by I’s label reveal; do not add a separate teaser line or a buildup scene. This is the complete suspense treatment. Label explainers refer only to axes, not every preceding Finding.

H exposes “Explore months” when E is eligible. The last available history scene (M, otherwise H, otherwise O) exposes “Recorded rank labels” when K is eligible. Its insertion anchor is that scene, and Next from K continues to the anchor’s original successor. If no history scene exists, rank stays in a history detail sheet reached from the report menu; it does not create a main-story scene. Rank K uses no joke or causal bridge to advice and does not influence any analytical assembly choice. E and K never create further scenes recursively.

### Missing states and caps

- No recommendation: omit, do not turn the last Finding into advice.
- No archetype: C defaults to a safe Finding or factual hero/memory card; never draw an empty badge.
- No safe share atom: finish privately with Read Again/Done. This is a legitimate constraint, not a reason to share an adverse Finding.
- Pass-2 unavailable: keep supplied history-only Findings; do not assume all Pass-1 families work, because several require parsed data too.
- Mixed/no dominant mode: do not invent a “Mixed” archetype. Omit mode-specific label; other supplied atoms remain usable. A mixture that still receives a returned dominant stratum uses that returned frame.
- Ordinary/low volume: no volume jokes, record badges, or “balanced” identity. Same precise factual narration.
- Five adverse Findings: one D3 with four expanded rows; maximum one adverse main scene. Full expanded content may be heavy, but the player chooses it.
- Duplicated unknown keys or inconsistent polarity metadata: no guessed merging; downstream normalization must surface the structural problem for diagnosis. This plan does not authorize new analytical eligibility rules.

### Optional E and K scenes (complete specifications)

**E — Your heroes through the months.** Job: optional discovery, “I remember that phase”; question: who did I pick then? Atoms: supplied monthly hero counts **D**. Copy: “Your heroes, month by month.” Support: “Choose a month.” Show a discrete month selector, one lead portrait, two secondary names/counts; empty period says “No recorded games here.” Native buttons supplement the slider. Motion opportunity: portraits swap at actual period boundaries. Require two populated periods; otherwise stay in H’s detail sheet. Return to M or the next available scene; share only an explicitly selected positive factual month card. No interpolated eras or “takeover” unless the proposed rule qualified it. Earns a scene only when the user asks to explore.

**K — Where the labels moved.** Job: requested factual history; question: what rank labels were recorded? Atoms: `rank_display` **B**. Headline: “{start_rank} → {end_rank}.” Support: “Recorded rank labels for this report period.” Equal labels: “{rank} at both ends.” Visual: two labels, neutral treatment, no graph between unobserved dates. No motion needed. Require complete supplied display labels and user request; otherwise omit. Next returns to main sequence via standalone copy. Share is a separate explicit rank opt-in. No MMR, modeled points, assessment, celebration, consolation, or explanation of Findings. It deserves only optional space because the player may care while the main arc should not become a rank evaluation.

## 7. Finding content system — all 16 dimensions

### How to read and apply the copy

The internal key appears here for implementation mapping only. User-facing screens use the headline and explanation. **H/L means higher/lower on the measured dimension relative to its comparison frame; it does not mean better/worse.** Every statement is a tendency. Avoid “most players” because being above a population mean does not establish being above a majority.

For raw level measures, the headline and comparative explanation travel together. A standalone shorter headline must never quietly convert a population comparison into an absolute behavioral claim. For context-adjusted measures, do not turn a residual/log/progress estimate into raw minutes, a percent, or an observed match count. Leave the main numeric slot empty unless the supplied estimate’s units and baseline make that conversion valid. Evidence can retain technical units backstage.

For the post-loss and lead contrasts, the player's own point estimate determines the within-player direction, not `direction = sign(z)`. When the interval includes zero, use the explicitly tentative alternative: “There’s a hint of {pattern} here.” Supporting line: “The difference could also be small.” No public share card from these contrast rows in v1. If point is exactly zero, say “There isn’t a clear lean in this comparison.” This is still a supplied Finding, not a fabricated neutral Finding. Missing units or an unresolved estimand frame → show the supported comparison question in details without making a directional claim; flag the copy binding for backend confirmation.

The following explanations are the full working text. “Higher/lower than the comparison players” refers to the actual model reference, not rank-matched players or an invented percentile. §3’s valence whitelist governs sharing even when an illustrative phrase sounds flattering.

| # / internal dimension | Plain concept and higher-direction treatment | Lower-direction treatment | Visual / tone / prominence / favorable sharing | Wording traps |
|---|---|---|---|---|
| 1 `vision_coverage` | Own observer uptime. **“Your wards tend to stay on duty.”** “You tend to spend a larger share of the match with an observer ward alive than the comparison players.” Optional valid number: “About {p}% of match minutes.” | **“Your wards tend to leave longer gaps.”** “You tend to spend a smaller share of the match with an observer ward alive than the comparison players.” | Ward lifetime ribbon, not illuminated map area. H warm, L matter-of-fact. Hero-scene eligible. H share yes as tendency. | No placement quality, vision area, support quality, or “never warded” when absent. Multiple wards do not multiply covered time. |
| 2 `duration_tempo` | Game length. **“Your games tend to take the longer route.”** “Compared with similar game contexts, your matches lean longer.” | **“Your games tend to wrap up sooner.”** “Compared with similar game contexts, your matches lean shorter.” | An Ancient and an unnumbered time ribbon. Neutral both ways; hero eligible. No v1 Finding share. | Long is not close, epic, inefficient, or late-game skill. Do not exponentiate an adjusted log estimate into a claimed average duration. |
| 3 `death_clustering` | Repeated deaths close in time. **“Your deaths tend to come closer together.”** “A larger share of the gaps between your deaths falls within 90 seconds than in the comparison group.” | **“Your deaths tend to be more spread out.”** “A smaller share of the gaps between your deaths falls within 90 seconds than in the comparison group.” | Two marks separated by a labeled 90-second span; no fake match sequence. H adverse, L favorable; hero eligible for L, D3 for H. L share yes. | It is death-to-death time, not time after respawn; no feeding, second-death inevitability, or advice to fix it. Never recommendation material. |
| 4 `lane_vs_jungle_share` | Creep-gold source. **“More of your creep gold tends to come from neutrals.”** “Your neutral-creep share leans higher than the comparison players.” | **“More of your creep gold tends to come from lanes.”** “Your neutral-creep share leans lower than the comparison players.” | Lane/neutral icons with a supplied valid share, otherwise no proportional bar. Neutral; hero eligible. Neither v1 share. | Gold share is not time spent jungling, camp frequency, safe farming, selfishness, or wasted map space. |
| 5 `purchase_tempo` | Timing of eighth purchase. **“Your eighth purchase tends to arrive later.”** “It tends to fall later in the match’s progress than in similar game contexts.” | **“Your eighth purchase tends to arrive earlier.”** “It tends to fall earlier in the match’s progress than in similar game contexts.” | Eight purchase ticks; final tick emphasized. Neutral; compact preferred. Neither v1 share. | Not first major item, full build, item quality, inventory slot eight, or power-spike timing. Preserve the actual purchase definition. |
| 6 `deaths_alone_share` | Deaths during minutes without a team kill. **“More of your deaths tend to come in quiet kill minutes.”** “A larger share happens in minutes when your team records no kills, compared with the reference players.” | **“Fewer of your deaths tend to come in quiet kill minutes.”** “A smaller share happens in minutes when your team records no kills, compared with the reference players.” | One minute strip with death marker and team-kill row; not teammate positions. H adverse, L favorable; compact preferred because proxy needs a sentence. L share yes only with explanatory line intact. | No physical isolation, nearby teammate claim, trading a death, sacrifice, or positioning diagnosis. |
| 7 `spike_usage` | First item to next kill/assist. **“Your next involvement tends to come later after that first item.”** “The wait from your first real item to your next kill or assist tends to be longer than in the comparison group.” | **“Your next involvement tends to follow that first item sooner.”** “The wait from your first real item to your next kill or assist tends to be shorter than in the comparison group.” | Item icon → kill/assist icon, optional supplied mean seconds. H adverse, L favorable; hero eligible. L share yes. | A kill/assist is not every fight; no proof the item was used, item causality, or “wasted power spike.” Finding uses mean, not the census median. |
| 8 `position_flexibility` | Position change within sessions. **“You tend to change position between games.”** “Your chance of changing position between consecutive games in a session leans higher than the comparison players.” | **“You tend to stay with a position.”** “Your chance of changing position between consecutive games in a session leans lower than the comparison players.” | Two position markers, not skill badges. Neutral, compact. Neither v1 share. | Position is not unrestricted role mastery, versatility, intentional queue choice, or guaranteed role accuracy. No forbidden provider `roleBasic` surface. |
| 9 `fight_timing_centroid` | Timing of kills and assists. **“Your kill involvement tends to lean later.”** “Your kills and assists tend to fall later in the match’s progress than in similar game contexts.” | **“Your kill involvement tends to lean earlier.”** “Your kills and assists tend to fall earlier in the match’s progress than in similar game contexts.” | Unnumbered progress ribbon with a center marker. Neutral, compact. Neither v1 share. | Not first rotation, all fighting, decisive impact, or a minute-15 boundary. Distinct from archetype’s mode-relative tempo label. |
| 10 `hero_novelty` | Heroes not seen in the prior 30 days. **“A less-familiar pick tends to enter the draft.”** “You tend to pick heroes absent from your previous 30 days more often than the comparison players.” | **“Familiar picks tend to return.”** “You tend to pick heroes absent from your previous 30 days less often than the comparison players.” | Generic repeated/new portrait slots unless actual hero facts supplied separately. Warm-neutral both ways; hero eligible. Neither v1 Finding share; actual factual hero cast can share. | Not lifetime first-time heroes, mastery, curiosity as psychology, adventurousness, or proof of a narrow lifetime pool. |
| 11 `closer_vs_comeback` | Own win-rate contrast at a 10k lead versus deficit. **“Your recorded leads tend to end in more wins than your deficits.”** “In the games behind this comparison, your win rate from a 10k lead is higher than from a 10k deficit.” | **“Your recorded deficits tend to end in more wins than your leads.”** “In the games behind this comparison, your win rate from a 10k deficit is higher than from a 10k lead.” | Paired lead/deficit labels; no claimed comeback match. Neutral, compact; both tentative if interval crosses zero. Neither share. | Use own estimate sign for these lines. Positive z alone does not prove the first. No “comeback specialist,” skill, rescued team, or recommendation. A small contrast does not prove good comebacks. |
| 12 `post_loss_session_continuation` | Next game after loss versus win. **“After a loss, another game tends to follow.”** “You tend to continue the session more often after a loss than after a win.” | **“After a loss, you tend to stop sooner.”** “You tend to continue the session less often after a loss than after a win.” | Result → next-game/session-end fork; schematic, not actual logs. Neutral; hero eligible if own contrast interpretable. Neither share. | Use point contrast sign. No inability to stop, addiction, tilt, healthy behavior, or certainty it was the last game of the calendar day. |
| 13 `lead_retention` | Own decided-ahead/decided-behind win contrast. **“Ahead tends to end differently from behind.”** “Your decided-ahead games tend to end in wins more often than your decided-behind games.” | **“The comparison leans toward your behind games.”** “Your decided-behind games tend to end in wins more often than your decided-ahead games.” | Two supplied outcome labels, compact and neutral. Neither share. | Never call it literal lead survival over time. Backend must confirm plain-language meaning of “decided-ahead”; retain this in details until bound. No “you throw leads,” hidden 10k definition, or advice. |
| 14 `post_loss_hero_switch` | Next hero after loss versus win. **“After a loss, the next pick tends to change.”** “You tend to change hero more often after a loss than after a win.” | **“After a loss, the same pick tends to return.”** “You tend to change hero less often after a loss than after a win.” | Generic same/different draft portraits. Neutral; hero eligible if contrast clear. Neither share. | Use point contrast sign, not z. Not blame on hero, mental reset, loyalty diagnosis, or a specific hero without supporting history. |
| 15 `post_loss_requeue_latency` | Gap to next recorded match. **“After a loss, the next game tends to wait.”** “The gap to your next match tends to be longer after losses than after wins.” | **“After a loss, the next game tends to come sooner.”** “The gap to your next match tends to be shorter after losses than after wins.” | Result → clock → match. Neutral; hero eligible if contrast clear. Neither share. | This is a match gap, not observed click-to-queue latency, queue duration, a therapeutic break, or impatience. Do not convert adjusted log gap into minutes without baseline. |
| 16 `fight_conversion` | Team tower after a won-fight minute. **“Won fights tend to be followed by towers.”** “An enemy tower tends to fall within two minutes of a won-fight minute more often than in the comparison group.” | **“Fewer won fights tend to be followed by towers.”** “An enemy tower tends to fall within two minutes of a won-fight minute less often than in the comparison group.” | Fight-minute marker → two-minute window → tower. H favorable, L adverse; compact preferred. H share yes with team-event context. | No player tower damage claim, secured objective, proof of decision quality, caused wins, or recommendation. Never amplify low reliability into a settled claim. |

**Copy binding gate:** Dimensions 11–15 illustrate a real distinction between population-relative ranking and the player’s own contrast. Their table headlines are within-player variants. The main screen must choose them using the own-contrast point/interval, not mechanically the H/L label. A source-confirmed formatter is required before showing numeric adjusted comparisons. This is a content/assembly requirement, not a request to change the estimator.

Uncertain copy should still describe a recognizable situation. If the only honest wording for a particular estimate is too technical, keep that Finding in the accessible pattern inventory with its plain-English question and evidence; it is ineligible for D1’s hero slot. Do not invent a simpler metric or silently suppress the whole report.

## 8. Recommendation experience

Use the returned instruction verbatim, even when its editorial wording feels awkward. The seven supplied lines are fixed, not alternatives the FE chooses. All surrounding copy is private. The backend’s selected recommendation may concern a dimension absent from the five Findings; R therefore never says “to fix what we just saw.”

Common setup: **“If you want one thing to try next game…”** Canonical instruction follows. Below it, **“What to watch”** opens a single observation, with the exact backend verification visible under “Measurement.” Avoid “How you’ll know it worked.” The question is whether the behavior changes; improvement in win rate is not established.

| Selected recommendation | Setup and canonical instruction | Relevance / verification / next-game memory aid |
|---|---|---|
| `last_hits_at_ten` | “Give the first ten minutes one clear focus.” **“For five games, care about nothing but last hits until minute 10.”** | Why this: “Your first-ten-minute last hits differ between your wins and losses.” Watch: “Your last-hit count at minute 10.” Preserve `last_hits_per_minute cumulated to minute 10` if that is the returned canonical field. Five games is in the instruction; memory aid: “Minute 10: last hits.” |
| `deaths_alone_share` | “A simple cue before crossing.” **“Do not cross the river without a teammate on screen.”** | Why: “The share of deaths in minutes without a team kill differs between your wins and losses.” Watch: “Deaths in minutes without a team kill.” Exact verification: “share of death minutes with no team kill activity.” Memory aid: “River. Teammate on screen.” This verification is a proxy, not proof the river instruction was obeyed; do not show an invented compliance tick. |
| `first_real_item_time` | “One purchase-order note for the next game.” **“Buy your first big item before your damage item.”** | Why: “Your first real-item timing differs between your wins and losses.” Watch: “When your first real item arrives.” Exact verification: “time of first real-item purchase.” Memory aid is the full canonical sentence; no hero-specific shopping list. The distinction between “big” and “damage” is underspecified in the sources; flag explanatory taxonomy as a P0 content clarification. Do not silently reinterpret or substitute an item. |
| `first_ward_time` | “One thing to do before the clock starts.” **“Place your first ward before the horn.”** | Why: “Your first observer-ward timing differs between your wins and losses.” Watch: “When you place your first observer.” Exact verification: “time of first observer ward.” Memory aid: “Before the horn.” No invented ward location. |
| `lane_vs_jungle_share` | “A reminder when the wave is available.” **“Take the lane creeps when they are there.”** | Why: “The source of your creep gold differs between your wins and losses.” Watch: “How much creep gold comes from neutrals.” Exact verification: “share of creep gold from neutrals.” Memory aid: “Wave available? Lane creeps.” Not a guarantee the lane is safe or a command to steal farm. |
| `vision_coverage` | “Keep one ward cycle in mind.” **“Replace your ward the moment the old one expires.”** | Why: “Your observer uptime differs between your wins and losses.” Watch: “How much of the match has your observer alive.” Exact verification: “share of minutes with a ward alive.” Memory aid: “Ward expires → replace.” No assumption of shop stock, map access, or observed notification. |
| `spike_usage` | “Let the item be the reminder.” **“When your item finishes, go and use it.”** | Why: “The wait from your first item to your next kill or assist differs between your wins and losses.” Watch: “The wait until your next kill or assist.” Exact verification: “seconds from first item to next kill/assist.” Memory aid: “Item done → use it.” Do not prescribe an unsafe fight or claim the next kill proves item use. |

For the six instructions without an explicit duration, the surrounding invitation is **“Try it in your next game.”** No invented validated five-game protocol. “Want to keep watching it?” may explain that the player can observe future games themselves, but v1 does not promise tracking, a refresh, a dashboard, statistical confirmation, or provider-funded follow-up.

Why-this detail uses the actual own win/loss values only when units are valid, with neutral labels “In your wins” / “In your losses.” The direction need not match a presumed unfavorable gap; never hardcode “you did less in losses.” A gap spanning zero remains tentative. No automatic claims that this is the player’s biggest weakness.

If verification is missing, keep the canonical instruction if valid but omit the unsupported measurement promise and flag the payload for assembly QA. If the recommendation itself is absent, omit the entire beat. Runners-up are excluded from the v1 story and export; a later authenticated deeper-analysis product may use them with a clear subordinate role.

## 9. Archetype experience

The label is a playful naming of three axes, not a summary of the hero chapter, all Findings, recommendation, or rank. Reveal it late, but never lock it behind a timer. The main face shows mode and one restrained tempo sentence. “Why this name?” exposes all three axes using these fixed patterns:

| Axis value | Working explanation |
|---|---|
| early | “Your kills and assists tend to land a little earlier in the game for a {mode} player.” |
| mid | “Your kills and assists tend to land around the middle of the timing range for {mode} players.” |
| late | “Your kills and assists tend to land a little later in the game for a {mode} player.” |
| frontliner | “You appear in fight minutes, with deaths in those minutes on the higher side for {mode}.” |
| opportunist | “You appear in fight minutes, with fewer deaths in those minutes for {mode}.” |
| ghost | “You appear in fewer fight minutes for {mode}.” |
| metronome | “Your session results sit on the steadier side of this playful label.” Detail: “This does not establish unusually consistent play.” |
| streaky | “Your session results tend to bunch into more up-and-down stretches.” |

Fight-minute explanation includes “A kill, assist, or death counts as appearing.” No inference of initiating, tanking, being brave, waiting for kills, avoiding effort, or contributing little. “Ghost” stays out of the main face and share caption; the canonical grid label remains unchanged. If raw dispersion is near the boundary, do not invent a new threshold or relabel; use restrained modifier copy for everyone. The modifier describes sessions across modes, while tempo and fight style use the supplied dominant mode; explain this distinction in details.

### All 18 normal labels

Use the canonical spelling. One-line copy below is the main tempo clause; the paired fight/session descriptors belong in the explainer, with the fixed wording above. This intentionally resists writing eighteen unsupported personalities.

| Tempo / fight / modifier | Canonical label | Main working copy and explainer binding |
|---|---|---|
| early / frontliner / metronome | The Alarm Clock | “Your involvement leans a little earlier for {mode}.” Early + frontliner + metronome explanations. |
| early / frontliner / streaky | The Opening Act | “A slightly earlier lean for {mode}; more up-and-down sessions.” Early + frontliner + streaky. |
| early / opportunist / metronome | The Early Bird | “Your involvement leans a little earlier for {mode}.” Early + opportunist + metronome. |
| early / opportunist / streaky | The Ambusher | “A slightly earlier lean for {mode}; sessions with more swings.” Early + opportunist + streaky. |
| early / ghost / metronome | The Quiet Start | “A slightly earlier lean in the fight minutes you appear in.” Caption “For {mode}.” Early + ghost + metronome. |
| early / ghost / streaky | The Slow Burn | “A slightly earlier lean for {mode}; an up-and-down session pattern.” Early + ghost + streaky. Do not reinterpret the evocative label as late tempo. |
| mid / frontliner / metronome | The Engine Room | “Your involvement sits around the middle of the {mode} timing range.” Mid + frontliner + metronome. |
| mid / frontliner / streaky | The Brawler | “A middle timing lean for {mode}; sessions with more swings.” Mid + frontliner + streaky. |
| mid / opportunist / metronome | The Timekeeper | “Your involvement sits around the middle of the {mode} timing range.” Mid + opportunist + metronome. |
| mid / opportunist / streaky | The Pickpocket | “A middle timing lean for {mode}; an up-and-down session pattern.” Mid + opportunist + streaky. |
| mid / ghost / metronome | The Understudy | “A middle timing lean in the fight minutes you appear in.” Caption “For {mode}.” Mid + ghost + metronome. |
| mid / ghost / streaky | The Wildcard | “A middle timing lean for {mode}; sessions with more swings.” Mid + ghost + streaky. |
| late / frontliner / metronome | The Last Word | “Your involvement leans a little later for {mode}.” Late + frontliner + metronome. |
| late / frontliner / streaky | The Overtime | “A slightly later lean for {mode}; more up-and-down sessions.” Late + frontliner + streaky. |
| late / opportunist / metronome | The Long Game | “Your involvement leans a little later for {mode}.” Late + opportunist + metronome. |
| late / opportunist / streaky | The Closer's Apprentice | “A slightly later lean for {mode}; sessions with more swings.” Late + opportunist + streaky. No implication the Special Closer rule fired. |
| late / ghost / metronome | The Patient One | “A slightly later lean in the fight minutes you appear in.” Caption “For {mode}.” Late + ghost + metronome. |
| late / ghost / streaky | The Late Bloomer | “A slightly later lean for {mode}; an up-and-down session pattern.” Late + ghost + streaky. |

Here “involvement” is shorthand for kills and assists; the accessible description and explainer use the full phrase. An art direction may distinguish labels, but imagery must not pretend to show actual positioning or intent. No personality biography, rarity meter, stat radar, axis score, or type compatibility game.

### Special interruption

When `is_special` is true and a recognized `special_label` exists, reveal it instead of the grid label. Eyebrow: “A different calling card.”

- **The Lighthouse.** “Your observer uptime stood out for {mode}.” Optional detail: “This playful label comes from the time your own observers stayed alive.” Never show map area or top 2%.
- **The Closer.** “Your results from a 10k lead stood out for {mode}.” Optional detail: “This playful label comes from recorded wins when your team had that lead.” Never “you never throw” or personal causal credit.

Trust the backend’s Special selection and Lighthouse precedence; do not compare scores or fire an override in FE. Special explanations require the returned label, not a fabricated extra Finding. If Special metadata is malformed but the complete normal grid object is valid, omit the unrecognized Special and show the already supplied valid grid label; this is structural degradation, not a newly assigned archetype.

Without archetype, do not mention the missing name. Use a favorite factual hero cast or favorable Finding on C. With no safe card, the private closing line still finishes the report. Identity art is never a required asset for basic navigation.

## 10. Share system

### Default, in strict priority order

1. Recognized returned Special, with its mode caption.
2. Returned normal archetype, with its mode caption.
3. Highest-score favorable, renderable Finding from the supplied slate, with the full tendency and necessary measurement context.
4. Named most-played hero / supplied positive factual hero card.
5. Share-safe selected memory (hero change or recorded activity stretch, never a losing sequence).
6. Supplied count plus actual window.
7. No card. Read Again and Done still work.

Mode alone does not earn a public card. Recommendation-only and adverse-only reports can finish without sharing. Do not manufacture an achievement to satisfy a sharing metric. The ideal descriptive layer materially reduces this case; the measured-only plan cannot guarantee it away.

### Card formats and intended conversation

| Card | Hierarchy and working copy | Intended reaction |
|---|---|---|
| Calling card, default when eligible | Optional user-chosen display name → “The Timekeeper” → “A {mode} Dota calling card” → one supported restrained clause → actual window if present → Dota Report Card attribution | “That name fits you. What did I get?” No cross-mode comparison interface. |
| Favorable habit | “My wards tend to stay on duty.” → full observer-uptime meaning → actual window if present → attribution | “Yes, you are always replacing those.” It must remain interpretable without the private report. |
| Familiar hero | “Back to {Hero}.” → “{n} recorded games” → actual window → attribution | “Of course it was {Hero}.” Frequency, never strongest/best. |
| Memory | Date pair / hero pair → exact recorded event → actual scope → attribution | “I remember that phase.” No match IDs, other-player names, or private loss run. |
| Factual fallback | “{N} recorded Dota games” → actual dates → attribution | “That was a lot of Dota together.” A useful fallback, not the product’s primary ambition. |

Public first-person copy is a deterministic grammatical transformation of an approved claim, not a new interpretation. No technical numerical claim is necessary on a Calling card. Use portrait art only with rights/asset approval in the downstream design pass; placeholder silhouette is acceptable during Figma mocks.

Per-scene Share opens a separate preview with that scene’s eligible atom selected. C offers a selector only when at least two safe alternatives exist. Selecting a rank addition requires an explicit unchecked **“Include my recorded rank labels”** control in the preview, available only with B rank data; the default remains off each new export session. Labels are factual and separate from the insight. No rank affects automatic selection, art, or headline.

Share artifacts contain no recommendation, gap, adverse Finding, score, z, reliability, interval, internal identifier, pseudonym, access token, private report link, or automatic rank. A player may elect a normal public display name; omit names by default if provenance is unclear. User-supplied display text is escaped and layout-bounded, never executed as markup.

Generate a deterministic static card from the safe projection, not a screenshot of the reading scene. Freeze fonts/assets and the settled state before export; previews and saved output must agree. Public-link generation is not assumed available. Default is image sharing or saving via supported platform capabilities; cancellation returns to the exact scene without a success toast. If image export fails, keep preview and offer retry; never claim sharing succeeded. No tracking pixels, QR codes into private reports, or referral mechanics are needed for v1.

## 11. Mobile FE blueprint

### Navigation and state

Choose **manual paginated scenes with native vertical scrolling inside a scene when content needs it**. This preserves a deliberate reveal order without making someone race an autoplay story or fight scroll-snap. Main navigation is visible Back/Next; horizontal swipe is an optional shortcut on noninteractive content. Swiping is never the only path. Do not hijack vertical scroll, browser edge gestures, text selection, sliders, or sheet interactions.

W3C’s carousel guidance supports keyboard access, explicit controls, communicated slide changes, and sensible focus; its APG warns that automatic rotation can disrupt a screen reader’s current context. We borrow those control principles, not a mandate to implement the entire report as an ARIA carousel. [W3C carousel tutorial](https://www.w3.org/WAI/tutorials/carousels/), [W3C carousel pattern](https://www.w3.org/WAI/ARIA/apg/patterns/carousel/).

- Top: chapter label, “{current} of {total},” End menu. Bottom: Back / Next, with safe-area padding. Chapter labels are **Your games**, **Your patterns**, **Next queue**, **Calling card**, **Keep it**; omit empty chapters.
- “End” jumps to C, or exposes merged closing actions in the one-scene case. It does not delete the report or regenerate it. “Skip chapter” goes to the first scene in the next assembled chapter.
- Progress reflects actual scenes, not potential slots. Optional E/K add one at the moment the user asks; returning does not insert it twice. Prefer marking optional exploration separately in the chapter menu to avoid surprise.
- Back reverses scene navigation; browser Back first closes an open sheet/preview, then returns through scene history, then to entry. No loops created by Read Again. Reload restores the same persisted report and compatible scene ID; if an old ID no longer exists, use the first valid scene.
- Left/Right can navigate when focus is outside editable/interactive controls. Tab/Shift-Tab follow native control order; Enter/Space activate buttons. Escape closes the top sheet/preview and returns focus to its invoker. No key handler intercepts a range input or text field.
- Navigation buttons retain focus for repeated activation, with a concise polite announcement of the new scene title and count. Chapter-menu jumps can focus the destination heading. Off-screen scenes do not remain in the tab order or accessibility tree.
- Evidence shows the current atom’s plain definition first, then supplied sample, estimate/units and interval. Methodology is separate and optional. Both return to the same scene, scroll position, and settled reveal state. No drawer-of-drawers.

### Six scene templates

| Template | Purpose / hierarchy | Comfortable maximum | Visual form | Interaction / mobile constraint | Reuse |
|---|---|---|---|---|---|
| Focus | O, D1, I: one fact or label → one meaning → optional context | Headline ≤12 words; support ≤32; one principal number or label; one illustration | Count, ward strip, identity art | One optional detail action. Wrap long labels; no shrinking below readable size. | Shared layout; illustrations differ by concept. |
| Cast | H: one lead hero → up to two supporting picks | Three portraits/counts; lead name two lines | Portrait group, no performance chart | All heroes in detail. Missing portrait gets accessible text/fallback art. | Reusable for annual or selected period. |
| Memory | M, E: one date/period event → supporting actual values | One before/after or up to seven date cells; three hero names maximum | Discrete timeline or result run | Native period controls; no mandatory drag. Overflow moves vertically. | Three bounded visual variants; no universal chart builder. |
| Pattern group | D2, D3: one headline → up to two visible observations → counted expansion | D3 only one adverse observation visible; D2 two. Each row ≤28 words plus optional detail. | Small concept glyphs / comparison labels | More rows expand normally; each has Evidence. | Common row grammar, fixed per-dimension copy. |
| Next-game note | R: setup → canonical instruction → observation to watch | Entire canonical text untruncated; one setup ≤12 words; one verification label | Text-led with one timing/item/ward cue | Private copy utility, one detail surface; no checklist. | Seven content variants, one layout. |
| Keepsake | C: single export preview → choice → action | One card; two primary actions; alternatives behind selector | Static artifact | Preview fits width; text remains readable; rank checkbox separate. | Same safe renderer for preview and export. |

K reuses Focus with two rank labels. Evidence, Methodology, Share preview, chapter menu, and loading/error are support surfaces, not extra scene templates. No generic dashboard grid, full charting library, or bespoke page for every dimension is warranted by this specification.

### Text, layout, and visual limits

Design baseline: 375px width, then 320px reflow and desktop. Main body target at least 18px; secondary information at least 14px. Interactive targets target 44×44 CSS px. These are product design choices, not a claim every number is a WCAG requirement. Respect text zoom, OS text settings, contrast, focus visibility, and non-color meaning.

Use a minimum-height scene, not a fixed-height text cage. Sticky controls must never obscure the last line or a focused element. At 200% zoom or short landscape height, the page scrolls. Names wrap naturally; no essential hero/archetype title is ellipsized. Long usernames can wrap to two lines then be omitted from the decorative hero treatment while remaining available in account context; never replace them with a private ID. Export must use a bounded name field or omit the optional name, not clip the claim.

Desktop keeps a focused reading column (roughly 560–680px as a design target), with art beside it only when reading order remains clear. It does not become a 12-column analytics dashboard. Legends explain concepts with words and icons, not green/red alone. Do not render numerical scales where the payload supplies only a category; decorative marks must be visibly schematic.

### Motion opportunities, not animation specifications

Counts can gather; one date strip can narrow; heroes can swap at actual period boundaries; an item can become an involvement marker; the returned name can resolve; safe keepsake elements can assemble. No timing, easing, choreography, or implementation library is mandated here. Content is readable immediately and never waits for animation completion.

Reduced motion uses the settled state with no count-up, zoom, parallax, spinning wards, shaking failures, or automatic transitions. All meaning survives in text and static visual order. Sound is unnecessary; never autoplay audio. Screen-reader output reads final values once, not every animation frame.

### Loading, failure, and insufficient history

| State | Working copy / behavior |
|---|---|
| Initial request | “Preparing your report.” Show only real pipeline status, if available. No invented match counter, timer, hero, or guaranteed completion time. |
| Stored report ready | Open it directly. No ceremonial fake analysis and no provider calls for viewing or sharing. |
| Slow request | “This is taking longer than usual.” Allow leaving and reopening only if persistence supports that promise. Otherwise do not claim background completion. |
| Acquisition failed | “We couldn’t load your match history.” Supported retry and account-check action; no report scenes. |
| Private/anonymous or no parsed matches, some usable atoms | Show the reduced story. Explain coverage only in optional details when a supplied reason supports it. |
| No usable personal content | “There isn’t enough recorded history for a report yet.” Done / supported retry. No sample archetype presented as personal. |
| Optional capability absent | Omit scene and adjust progress/bridges. No red missing-data badge. |
| Malformed/unsupported report version | “This saved report can’t be displayed here yet.” Preserve data, provide supported recovery route; never regenerate automatically. |
| Image export fails | “The image couldn’t be saved. Try again.” Keep preview and reading state. |

A generation service, retry policy, durable background jobs, authenticated sharing, and state persistence are not claimed to exist. They are implementation prerequisites to these UI behaviors. The pilot’s full-depth policy applies to free and paid equally; do not sell deeper evidence or imply the free report is deliberately less informed.

## 12. Ideal versus ship-now

The following are complete illustrative sequences for a player receiving five Findings, a recommendation, and an archetype. They are not claims that any real user has these values. Ideal assumes the proposed producers exist; measured-only explicitly does not.

| Beat | Ideal V7 | Strict measured-capability V7 | What is lost without the addition |
|---|---|---|---|
| Opening | O: “428 games. Your kind of Dota.” Actual recorded interval below. **B** | First Finding carries “Your Dota, in a few patterns.” No count/year claim. | Scope and instantly recognizable scale. |
| Familiar cast | H: “You kept coming back to Jakiro.” Supplied usage counts. **D** | Omitted. | Familiar faces and a factual identity fallback. |
| Memory | M: “Jakiro in March. Lich in April.” Supplied counts and valid periods. **D** | Omitted. | The feeling of remembering a particular part of the year. |
| Recognition in behavior | D1: favorable ward-uptime Finding. **A** | D1: same Finding and full correct meaning. **A** | Analytical meaning survives; fewer personal anchors precede it. |
| Other habits | D2: novelty and next-hero contrast, with another neutral Finding under counted expansion. **A** | D2: same grouped material. **A** | No invented hero identity can accompany novelty. |
| Difficult pattern | D3: one adverse Finding. **A** | D3: same bounded scene. **A** | No additional loss chapter in either version. |
| One action | R: returned ward instruction. **A** | R: same private note. **A** | No loss in action quality; still not causal advice. |
| Identity | I: returned archetype and mode. **A** | I: same returned label. **A** | Label still works, but does not feel as much like an annual yearbook. |
| Ending | C: label default; hero and memory alternatives. **A + D** | C: label default; favorable Finding alternative. **A-derived presentation** | Less variety and a weaker no-archetype fallback. |
| Optional exploration | E monthly hero view and K opt-in rank labels; only if requested. **D / B** | Neither promised. | Optional depth, not core completion. |

Default sequences: **Ideal O–H–M–D1–D2–D3–R–I–C (9)**. **Strict measured D1–D2–D3–R–I–C (6)**. In this example five Findings are three scene units, not five identical screens. With supplied real context, measured capability plus B assembly can add O for seven scenes; that is explicitly no longer Tier-A-only metadata.

For an ordinary player with one neutral Finding and no archetype: **Ideal O–H–M–D1–R–C**, defaulting to the hero card. **Measured D1–R–C**, finishing privately because that neutral Finding is not an approved public atom. If the Finding were favorable instead, both versions would select it ahead of the hero card under §10. For adverse-only output, **D3 with closing actions**, not a manufactured recap. This is complete as a bounded report but cannot honestly deliver an annual memory experience. The gap is the reason to prioritize descriptive history.

### Production readiness is separate from content feasibility

Before any consumer V7 release, the future implementation must assemble/persist capabilities, bind canonical copy and units, version the contract and presentation rules, handle historical reports, and complete authorized validation and release gates. Existing V6.1 persisted reports keep their renderer/compatibility path; they must not be relabeled as V7 or regenerated merely to satisfy the new UI. This plan does not alter the frozen V6.1 analytical source or artifact identity.

## 13. Backend and content priority list

Priorities are narrative value, not estimates derived from code inspection. **No repository implementation cost was investigated.** “Source exists” below means the supplied documents mention the necessary type of data; it does not guarantee complete coverage for every user. Anything less explicit is marked **NEEDS BACKEND CONFIRMATION**.

### P0 — Make a personal recap possible

| Addition | Exact purpose / data | Source and work type | Provider implications / conditionality / sharing | Narrative value |
|---|---|---|---|---|
| Assembly, persistence, versioned projection | Deliver the measured capabilities coherently and reopen without recomputation. Need returned slate, primary rec, complete archetype/refusals; manifest §8 provenance additions including window, depth, versions, parsed count, validation status. | B wiring; A research outputs exist. Plumbing and deterministic projection, not new modeling. Contract field aliases and version migration need explicit binding. | Storage wiring absent. Initial acquisition requirements governed by existing policy; no new acquisition solely for UI. Reopen/export must use stored data. Private provenance never exported. | Release prerequisite. Without it, neither sequence is a consumer product. |
| Honest window and recorded count | O and all public scope captions. Need start/end, eligible count, count definition, coverage boundary, generated time. | B. Manifest names Pass-1 window/history rows and context filters. Deterministic assembly. | No new provider category appears necessary for stored history; coverage completeness **NEEDS BACKEND CONFIRMATION**. Valid positive count and window required. Share-safe. | First scope anchor; prevents a 500-match slice being labeled an entire year. |
| Familiar hero cast | H and no-archetype public ending. Need eligible hero counts, names/art mapping, tie metadata, actual window. | D. History and hero novelty imply hero observations; complete display metadata/rights **NEEDS BACKEND CONFIRMATION**. Deterministic aggregation, not a “best hero” model. | Reuse stored history when available; whether missing historical hero metadata needs a provider request **NEEDS BACKEND CONFIRMATION**. At least one named hero; share-safe counts. | Highest recognition per new scene. |
| Minimum date memory | M’s factual seven-day candidate. Need eligible match timestamps, coverage bounds, count per UTC date, most recent tied stretch. | D. Timestamped history/window exists per manifest; complete chronology **NEEDS BACKEND CONFIRMATION**. Deterministic rolling aggregation. | No new provider category apparent; never fetch solely for presentation QA. Require enough dated history under rules below. Share-safe factual activity. | Makes this feel like a yearbook even when no records or labels exist. |
| Semantic/canonical copy binding | Prevent wrong stories while keeping them simple. Need unit/baseline metadata for adjusted estimates; own-contrast direction mapping; plain definition of decided-ahead; exact canonical strings; explanation of first-big-item versus damage-item distinction. | Content/contract clarification around A, not estimator changes. Manifest supplies enough to identify the ambiguities, not settle every term. | No provider calls. Undefined numeric conversions omitted. Preserve canonical instruction; no invented item examples. Private details except approved Finding copy. | Required to avoid confident but false simplification. |
| Safe artifact renderer | C and per-scene image preview/export. Need only the allowlisted projection, editorial version, approved art/fonts, layout dimensions. | B share shape / proposed presentation producer. Deterministic formatting. | No provider calls. At least one approved ingredient. Never a screenshot of authenticated report. | Converts story into a social object; required before enabling Share. |

The minimal ideal increment is therefore **window/count + hero cast + one date memory**, all from existing history where coverage permits. Do not hold that increment hostage to every P1 idea.

### P1 — Recognition and variety

| Addition | Exact purpose / data | Source / work | Provider / conditionality / sharing | Narrative value |
|---|---|---|---|---|
| Monthly hero contrast and optional E | Replace a generic busy stretch with a personal change. Need per-month hero counts, period boundaries, lead counts/shares, valid names. | D from timestamped hero history. Deterministic. No inference about preference or mastery. | Stored rows should suffice; display metadata and complete periods **NEEDS BACKEND CONFIRMATION**. Two qualifying months; factual card share-safe. | More specific than total games; optional interaction earns its place. |
| Completed loss-run interruption | M alternative when there is a bounded, completed story. Need chronological eligible outcomes, immediate following win, hero/date, and missing-history boundary indicators. | D; outcomes are implied by Findings/recommendation sources. Complete chronological coverage **NEEDS BACKEND CONFIRMATION**. Deterministic, no comeback model. | Reuse stored history; no extra calls presumed. No missing entries inside sequence. Private, not exported. | A remembered event with a release, without a whole negative chapter. |

### P2 — Optional, after the recap works

| Addition | Exact purpose / data | Source / work | Provider / conditionality / sharing | Narrative value |
|---|---|---|---|---|
| Rank display K | Respond to explicit interest in history. Start/end recorded rank labels and direction only. | B. Historical availability not established; **NEEDS BACKEND CONFIRMATION**. Descriptive display, permanently outside analysis. | Additional collection may be needed; do not assume present or reconstruct from wins. Require both labels and user request. Share only explicit opt-in. | Some players care strongly; it should not govern the main report. |
| Longest recorded match, optional memory detail | A concrete match someone may remember. Duration, hero, date, outcome, duration-coverage metadata. | D, with duration known as a context input. Complete coverage/metadata **NEEDS BACKEND CONFIRMATION**. Deterministic. | No new calls if stored rows suffice; otherwise confirm. Detail-only in v1, not an extra main scene. Public only a positive factual non-adverse treatment. | Flavor, but less universally relatable than familiar heroes. |
| Optional deeper interpretation | Let interested players inspect existing evidence after finishing. Supplied estimates, intervals, samples and retained material. | B interpretation surface over A. No promise of new evidence or stronger analysis for paid users. | No provider calls for stored output. Private and capability-dependent. | Retention for curious users, not needed to finish the story. |

### Proposed deterministic descriptive rules

These are **new product proposals for producers**, not claims about present implementation, statistical eligibility, or frozen V6.1 behavior. Persist their version with output; FE receives selected candidates, not raw history to recompute them.

- **Scope:** use the supplied report interval and eligible history. If coverage is truncated, caption “recorded” and never assert a full-year maximum. A date period is not silently expanded to 365 days.
- **Calendar:** UTC date buckets until a reliable user-local historical timezone is explicitly supplied. Show dates; no “your Saturday night” or inferred sleep/work schedule. Seven-day stretch means seven consecutive UTC dates, not calendar week. Most recent ending date wins ties.
- **Hero cast:** descending eligible match count; equal counts remain visibly tied. Stable hero identifier orders tied cards internally but does not turn a tie into a sole leader. Actual named heroes only.
- **Monthly hero candidate:** calendar months intersected with the report window; caption partial months as partial. Need two adjacent fully covered months with at least 10 eligible games each; each leader must be unique and account for at least 30% of that month’s eligible games, and leaders must differ. These are editorial clutter controls, not analytical qualification or confidence. Select the pair with the largest smaller-month count, then most recent pair, then stable hero IDs. Headline states only the changed most-played hero and dates.
- **Completed loss-run candidate:** at least three consecutive eligible recorded losses followed immediately by a recorded win, with no known data gap. Choose longest qualifying run, then most recent following win. If the selected run is unresolved, it is not a candidate; do not search backward to pretend the unresolved run recovered. A different completed run may be shown only with its explicit dates and no claim it ended the year’s longest run.
- **Activity candidate:** at least two populated seven-day stretches and at least three games in the selected busiest stretch; otherwise omit as too thin for a distinct memory scene. No comparison to other players and no hours/addiction punchline. Complete time coverage is required for “busiest”; otherwise “A recorded seven-day stretch” and selection remains factual but is not a maximum claim.
- **Memory selection:** qualifying hero-month change first; completed loss-run second; activity stretch third. If an adverse Finding will be in the report, prefer a qualifying activity stretch over the loss-run to avoid stacking setbacks. If no alternative exists, omit the loss-run rather than add a second main adverse beat. One main memory only; E provides optional monthly exploration.
- **Unsupported maximum:** do not claim longest or busiest from uncertain coverage. A labeled actual date is still usable without a record badge, but no invented superlative.

### Do not build merely because V6.1 had it

Drop modeled ±25 rank points permanently; use only actual display labels when available. Drop full-page annual deaths, loss-hero rankings, three separate K/D/A chapters, the seven-element radar/shape, transfer claims, strength bands, percentile badges, hero matchup/draft advice, provider awards, APM, and side-sensitivity surprises. Rejected dimensions are not a P2 backlog. Rich B death profiles, team-in-wins projections, telling-sign minute, and good/bad hero contrasts have not earned a place in this chosen story; do not implement them for completeness.

## 14. Stress-test results

These are **synthetic editorial simulations**, not production fixtures, model validation, browser QA, or observed user reactions. The engine was applied to 14 deliberately different capability profiles. Counts exclude detail expansions; C* means closing controls merged into the sole substantive scene. E/K only appear when explicitly requested. A “pass” below means the specified story stays coherent under those inputs, not that the product has been tested with real players.

| Profile and supplied content | Assembled path | Opening / recognition / pacing / repetition | Identity, recommendation, ending and share | Result / design repair |
|---|---|---|---|---|
| 1. Regular Standard; hero cast, hero-change memory; five mixed Findings; R and normal I | O H M D1 D2 D3 R I C (9) | Count and heroes ground the year; three different Finding treatments, only one adverse scene. | Axes explain I, R stands alone; label default with hero alternate. | Pass. Replaced five identical Finding slides with three scene units. |
| 2. Turbo main; ordinary cast/activity; three non-adverse Findings; R and normal I | O H M D1 D2 R I C (8) | No ranked assumption or inflated Turbo totals; ordinary activity is still a real date. | Every label includes Turbo. R private; calling card share. | Pass. Made mode visible on the exported artifact, not only report footer. |
| 3. Mixed, no dominant stratum; three history-only neutral Findings; no R/I | D1 D2 C (3) | Specific post-result behavior supplies recognition; no false year/hero opening. | No label teased. Private ending, no share unless an approved atom exists (none assumed here). | Pass within measured-only limits. Removed requirement for a public card for every report. |
| 4. Five adverse Findings; R present; no I/history | D3 R C (3) | One visible difficulty, four labeled expansions; not five accusations. | R never claims to fix D3; no safe card, private finish. | Pass. Consolidated adverse material and retained discoverability. |
| 5. One favorable ward Finding; no R/I/history | D1+C* (1) | Direct personal observation, no filler hello or reveal promise. | Favorable ward card with exact uptime meaning; Done/Read Again. | Pass. Merged ending actions for a one-atom report. |
| 6. Two neutral Findings; R; no I/history | D1 D2 R C (4) | Two different concepts, no demand to reach three or five. | Useful private note, then private close; no invented positive share. | Pass. Honesty outranks universal sharing. |
| 7. No Findings; complete normal I only | I+C* (1) | “Your Dota calling card”; no pretense of preceding evidence. | Three-axis explainer earns the label; share exists. R omitted. | Pass. Removed generic buildup claiming “everything we saw.” |
| 8. No Findings/I; R only | R+C* (1) | “One thing to try”; framed as a short private note, not an annual recap. | Exact instruction, no public export, Done. | Pass as bounded result. Explicitly named the limit in ship-now plan. |
| 9. Stable one-hero player; window/count and busy stretch; one low-novelty Finding; no R/I | O H M D1 C (5) | “One hero. {N} games.” No fake hero change or mastery claim. | H is an excellent factual share; no consolation for missing label. | Pass. Stable cast gets its own truthful recognition rather than forced novelty. |
| 10. High novelty; valid hero-month change; five non-adverse Findings; R/I | O H M D1 D2 R I C (8); E opt-in makes 9 | Hero dates and novelty answer distinct questions; D1 cannot name a hero from novelty alone. | Explain axes independently of adventurous-sounding copy; factual hero card available. | Pass. Kept era evidence separate from novelty inference. |
| 11. Large recorded rank climb, neutral three Findings, R/I; user requests rank | O H M K D1 D2 R I C (9) | Rank is a neutral history excursion; never an explanation of later patterns. | Default share I; rank off until explicit preview selection. | Pass. Removed automatic celebration and rank-driven sequencing. |
| 12. Recorded rank fall; adverse Findings; no I; cast/activity present | O H M D3 R C (6); K only if requested | Activity memory replaces any losing-run memory; only one main adverse scene. | Hero card ending; no consolation badge, public rank absent. | Pass. Negative history no longer piles onto negative Findings. |
| 13. Lighthouse Special; five non-adverse Findings; history absent | D1 D2 R I C (5) | No year claim. Vision Finding and label explain different outputs without repeating a giant percentage. | Special replaces grid label; no rarity number. Share Lighthouse with mode. | Pass. Special is a replacement reveal, not bonus identity slides. |
| 14. Acquisition failed / no personal atoms | No report; failure/insufficient-history state | No generic report opening, no fabricated hero or balanced identity. | No R/I/share; supported retry only. | Pass as non-report state. Kept operational failure separate from editorial refusal. |

Document checks passed: all 16 required sections, all 16 Finding mappings, all seven exact canonical instructions, and all 18 normal labels are present. A small local editorial simulation checked the 14 path counts and the six-scene strict measured-only ceiling across all 0–5 Finding-count combinations with recommendation/archetype present or absent. These are document/assembly checks, not application tests.

Additional adversarial checks applied during review:

- **Positive z, negative own post-loss contrast:** must use the point-contrast copy, never assume more requeue after losses. This prompted the explicit two-direction rule in §7.
- **Zero-spanning interval:** tendency/“hint” wording, no settled headline or invented significance band.
- **No-ward player:** missing ward Finding is omitted, never “your map stayed dark.”
- **Ghost + metronome:** label explanation avoids effort/skill and proven consistency. No insult in share captions.
- **All-zero or all-one session win rate:** trust archetype refusal; do not supply a modifier.
- **Unknown hero art / long username / long canonical label:** text remains usable without art and without horizontal overflow; actual browser proof remains future work.
- **Two equally most-played heroes:** tied headline, stable rendering, no invented unique favorite.
- **Missing chronology or observed history boundary:** no longest/busiest claim and no invented streak ending.
- **Same dimension rec and Finding with apparently different direction:** render each in its own comparison frame; no contradiction invented by a bridging causal sentence.
- **Back, End, Read Again after omission:** use assembled IDs; no empty scene indexes or new analysis on revisit.

The resulting architecture is shorter for sparse players, specific for familiar heroes, exploratory for real hero changes, restrained for rough years, and complete without an archetype. Actual enjoyment and recognition remain user-research hypotheses. A future moderated test should ask people what exact game/period a scene recalls and what they think the claim means, not merely whether they like the art.

## 15. V6.1 disposition

| V6.1 idea | Disposition | V7 decision |
|---|---|---|
| Name-first hello and scope | **REWORK** | Merge scope and first factual reveal. No separate preamble or “all of it” completeness claim. |
| Annual volume | **KEEP THE PRINCIPLE** | One bounded recorded-count/context scene when B producer exists. |
| Hours page | **DROP** | Repeats scale; not needed before recognition. Could be a later detail, not a new main producer priority. |
| Modeled rank points | **DROP** | Never reconstruct rating from ±25 wins/losses. |
| Actual rank history | **RETURN ONLY IF BACKEND SUPPORT IS ADDED** | Optional B display K, with private-by-default sharing and no analytical role. |
| Year → week → day → match zoom | **REWORK** | One memory scene. Dates must relate literally; no four-page ladder of unrelated maxima. |
| Busiest week/day | **REWORK** | Single seven-day memory fallback with explicit calendar/coverage rule. No extra busiest-day page. |
| Longest match | **RETURN ONLY IF BACKEND SUPPORT IS ADDED** | P2 detail; a match need not be an epic or comeback. |
| Win/loss chapter separation | **DROP** | Outcomes do not dictate emotional chapters. No long negative corridor. |
| Win totals / winningest day | **DROP** | Not required main-story beats; familiar facts already establish the year. |
| Streak storytelling | **REWORK** | One completed dated interruption, conditional and private; never dramatize unresolved losses. |
| Most-loss hero list | **DROP** | Usage-driven embarrassment, weak recognition value, repetitive with cast. |
| Most-win hero ranking | **REWORK** | Most-played cast is enough for v1; no “best hero” leap from raw wins. |
| Hero ranking / hero pool | **KEEP THE PRINCIPLE** | Recognizable cast, bounded to three visible heroes and exact counts. |
| Hero-era interaction | **RETURN ONLY IF BACKEND SUPPORT IS ADDED** | One optional discrete period view E, not mandatory dragging or multiple payoff pages. |
| Generic bridge pages | **DROP** | Destination-aware transition lines inside substantive scenes. |
| Inferential chapters | **REWORK** | Story-oriented D1/D2/D3, not backend topic headings or jargon. |
| Post-loss beat | **KEEP THE PRINCIPLE** | Three actual V7 behaviors; no psychological/causal “next game changed” blanket claim. |
| Transfer / outside comfort zone | **DROP** | Rejected V7 dimensions stay absent; novelty/flexibility are not substitutes for transfer. |
| Kills/assists/deaths chapter | **DROP** | Repetitive raw totals; does not justify three scenes or nine match lists. |
| Death-context placeholder | **REWORK** | Use only actual death-gap/no-team-kill Findings with exact proxy meaning. Do not revive B profiles automatically. |
| Seven Elements / distinctive shape | **DROP** | Not the V7 identity model. No radar or neutral fallback shape. |
| Build-up to identity | **REWORK** | One immediate transition into the label only when the complete archetype exists; no separate teaser. |
| Archetype explanation | **KEEP THE PRINCIPLE** | Actual three axes plus mode, after label. No “patterns we proved” framing. |
| Archetype guaranteed for everyone | **DROP** | Refusal is not a type. |
| Card collage | **REWORK** | A selectable public projection with one preview, not a private-data collage. |
| Final identity card | **KEEP THE PRINCIPLE** | Label when available; factual hero/Finding keepsake otherwise; private close when no safe atom. |
| Deeper-analysis bridge | **DROP** | No upsell scene in v1. Optional supported details accessible after or during story. |
| Dry-humor cadence | **KEEP THE PRINCIPLE** | Fewer jokes, after facts, never a requirement or repetition. |
| Deterministic omission and persisted reproducibility | **KEEP THE PRINCIPLE** | Versioned assembly, static export, old-report support; never require regeneration. |

## 16. Final implementation handoff

### What the next Figma pass should create

Create a coherent set of **six reusable scene templates** from §11, five support surfaces (Evidence, Methodology, chapter menu, Share preview, operational states), and a complete 375px ideal flow. Add a compact desktop interpretation and 320px/reduced-motion/text-zoom frames for the hardest cases. These are design tasks for the next pass; no Figma implementation is part of this document.

Required scene frames: O, H, all three M variants, D1 favorable/neutral, D2 paired/expanded, D3 single/expanded, all seven canonical R variants, normal I, Special I, no-I C, no-share private C, and one-scene closing controls. Optional E/K should be drawn as explicit excursions, not required chapters.

Archetype art can begin with three representative normal labels spanning early/mid/late and ghost/frontliner/opportunist, plus both Specials; the component must accept all 18 exact names and explainers. Do not invent eighteen new copy personas. Test “The Closer's Apprentice” at phone width before polishing shorter labels.

### Mock content to supply explicitly

- Mark every invented player profile **SYNTHETIC DESIGN DATA** in the Figma annotation layer, outside exported product cards.
- One current-shaped V7 mock with five mixed Findings; one five-adverse mock; one zero-Finding mock; no-R, no-I, both absent; one recognized Special; Standard, Turbo, and missing stratum.
- Raw-level Finding with interpretable units; adjusted log/progress Finding with no fake raw number; contrast with positive z but negative estimate; interval crossing zero; zero point.
- Ideal-only producer mocks for window/count, one hero, tied heroes, hero-change months, stable months, empty month, activity memory, completed run, unresolved run, unknown artwork, and optional recorded rank labels.
- Long username, long hero/label, singular count, short viewport, 200% text zoom, failed export, and operational failure.
- Actual downstream compatibility QA must use a sanitized persisted-production report from a previous implementation as well as a current report fixture. These synthetic planning profiles are **not** a substitute, and historical fixtures must not be overwritten.

### Future engineering acceptance criteria

Implement only after the intended layer is authorized. A presentation-only phase must not silently add producers or analytical work. Separate deliverables are: (1) assembly/content binding and storage/version prerequisites; (2) minimum descriptive producers; (3) renderer and safe exports; (4) optional P1/P2 work. No retraining, recalibration, reserved-data opening, threshold changes, or production deployment is authorized here.

For a material renderer change, require current and historical persisted-production-shaped fixtures, first-to-last and reverse traversal, Next/Back, keyboard navigation, Evidence, Methodology, Share, End, Read Again, 375px/mobile and desktop, reduced motion, overflow, browser pageerrors, unexpected console errors, hydration errors, and project-required typecheck/lint/build. Preview and existing-report smoke test precede owner review and any authorized merge/production release. Presentation QA must not trigger provider acquisition or report regeneration.

Content acceptance is exact: all 16 mappings reviewed in both directions; seven instructions unchanged; all 18 labels preserved; no percentiles/strength bands/causal copy; mode attached to identity; no private atoms in exports; no references to omitted scenes; no counts or year scope fabricated from samples. Audit actual rendered text, not only the nominal input schema.

### Decisions made and genuinely unresolved facts

**Decided:** yearbook arc; manual pagination; one memory; at most three Finding scene units; one adverse main scene; all Findings reachable; one private recommendation; axes after label; no default identity; separate public projection; six scene templates; honest sparse endings; minimal descriptive priority.

**Needs backend confirmation before dependent rendering:** exact adjusted-estimate display binding and decided-ahead terminology; full-history coverage versus acquisition depth; hero/date metadata coverage; first-big-item/damage-item explanatory taxonomy; actual persistence/assembly contract/version mapping. None is resolved by guessing or reading the repository during this task. Until confirmed, omit unsupported numeric/explanatory details and do not claim a consumer-ready pipeline.

**Needs future user testing, not a specification choice:** whether the chosen lead makes players recall a real moment; whether the private recommendation is memorable and correctly understood; whether ghost-related labels feel fair; whether the no-archetype ending is satisfying; whether optional expansion makes all five Findings discoverable. The specified architecture is the starting decision, not a menu awaiting selection.

### Delivery status

TASK TYPE: DOCUMENTATION / EXPERIENCE PLANNING
BASE SHA: NOT APPLICABLE — three supplied documents are the planning base; no implementation base assessed
NEW SHA: NOT APPLICABLE — standalone planning artifact, no repository changes or commit
CHANGED FILES: dota-report-card-v7-master-experience-plan.md (Downloads)
BACKEND FILES CHANGED: NO
ANALYTICAL FILES CHANGED: NO
PUBLIC REPORT CONTRACT CHANGED: NO
PERSISTED REPORT COMPATIBILITY TESTED: NO — future implementation gate
PRODUCTION-SHAPED FIXTURE: NOT APPLICABLE to this planning artifact
BROWSER E2E: NOT APPLICABLE
TYPECHECK: NOT APPLICABLE
LINT: NOT APPLICABLE
BUILD: NOT APPLICABLE
ANALYTICAL BEHAVIOR CHANGED: NO
HOLDOUT RERUN: NO
RECALIBRATION: NO
OPENDOTA QA CALLS: 0
DEPLOYED: NO
SAFE TO MERGE: NOT APPLICABLE — no code change; no release approval claimed
