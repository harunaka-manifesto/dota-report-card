# V6.1 Story — reinvention pass

- Date: 2026-08-31
- Base: `c3b9acd` (main, after the storytelling/reveal revamp on `8d12c48`)
- Scope: presentation only. No backend, analytical, ingestion, or threshold change.

This document covers the creative thesis, the architecture change, and the
before/after mapping for this pass. It builds on, and does not replace,
`v61-storytelling-research.md`, `v61-story-audit-and-narrative.md`, and
`v6.1-backend-storytelling-opportunities.md` from the previous pass.

---

## 1. What the previous pass fixed, and what it did not

The revamp on `8d12c48` was an editorial pass, and a good one: it replaced the
generic chapter spine, curated the humor down from a per-page reflex to five
evidence-gated closes, and gave pages semantic rhythms. Pacing improved.

It did not change the *shape* of the experience. After it, the report was still:

- 31 pages of one fact per page, in fixed order;
- read-only, with one interaction in the entire story (the hero-era slider);
- ending on a constant shown to every player.

## 2. The diagnosis: the narrator was describing the report

Reading the full traversal end to end, the same failure appears on almost every
page. The narrator talks about the document instead of the year:

> "The first receipt is simple: how much Dota happened here."
> "The next receipt: time spent inside those matches."
> "The scale is set. Now the result column gives wins the first word."
> "The chronology has a payoff."
> "This report checks the signals it could support."

Every one of those sentences is *stage direction*. It tells the reader what the
page is about to do. It is the written equivalent of a presenter reading their
own slide titles aloud, and it is the single largest drain on the experience —
because it spends the reader's attention on structure at exactly the moments
where a recap should be spending it on recognition.

A recap earns attention by making the reader do a small amount of work:
remember, guess, brace, recognise. Announcing the next beat removes all of it.

**Second diagnosis: the ending had nothing in it.** The report closed on the
title `THE YEAR IN QUEUE` — a constant string, identical for every player —
followed by a sentence describing the report's own methodology. This is
precisely the failure mode that got Spotify Wrapped 2024 mocked: the year they
removed the identity features (Sound Town, Listening Personality) and replaced
them with generic AI commentary, users called the result "empty observations."
The features people mourned were the ones that *named them something*.

## 3. Creative thesis

**The report is a friend who watched all your games, telling you what they
noticed — in order, with timing.**

Not a lawyer, not a compliance officer, not a brand. Someone who was there. That
narrator is allowed to be dry, to pause, to be a little unkind about the hero
that kept losing, to withhold a name because you already know it, and to be
sincere exactly once, at the end.

The emotional spine is **you kept showing up**. Wins and losses vary between
players; returning does not. It is the one thing every number in this payload
supports, and it is what Dota players actually recognise about themselves — the
queue is the habit.

Three rules follow from that:

1. **Never describe the report.** Say something about the year, or say nothing
   and let the Endstop hold the beat. Silence is cheaper than stage direction.
2. **Make the reader do the last step.** Where the reader can supply the answer,
   let them, and confirm it. Recognition beats presentation.
3. **The ending is a name, not a disclaimer.** It must be *their* name, drawn
   from a fact the backend already asserted.

## 4. What changed

### 4.1 The ending now names the year after the player's own hero

`year-shape.ts` selects a title from a supplied `copy_variant` and a supplied
hero name. The full fixture supplies `hero_era_payoff.copy_variant = "takeover"`
with a named hero, so the card resolves to **"The Hero Zeta Year"** — in
production, "The Pudge Year", "The Invoker Year".

**The analytical boundary, precisely.** This is copy selection, which the
presentation contract already permits, not new analysis:

- every branch is chosen by a supplied `copy_variant` or a supplied enum;
- nothing is summed, ranked, compared, or thresholded in the frontend;
- every hero name comes from the module that already named that hero;
- no branch asserts anything its source variant does not already assert;
- if no qualifying variant is supplied, the title is `null` and the neutral
  constant is used. **Absence is never filled in.**

It is deliberately *not* an archetype. The archetype module remains `not_ready`,
the narrow exception is unchanged, and nothing here claims a type, a
personality, a tier, or a trait. It names a year after a hero the backend
already said led it. Eight unit tests pin this boundary, including that a
`neutral` concentration band produces no shape at all.

### 4.2 The reader calls the top hero before it resolves

Page 17 previously printed all five names in rank order. It now shows ranks 2–5,
then a concealed first slot: **"You already know who's first."** → *Tap to
confirm*.

This is the cheapest available "I knew it" moment, and it costs no new analysis
— the list is merely split for presentation, in the supplied order.

Accessibility: concealment is visual only. The hidden name is in the DOM and in
the accessibility tree from mount, so a screen reader is never made to play a
guessing game. Reduced motion renders it already resolved with no trigger. Once
resolved, the fact receives focus and a polite live announcement, and it stays
resolved after Back; Run It Back resets it. A generic forward action may reveal
the fact, but it cannot reveal and leave the page in the same action. The mask
is striped rather than blank so it reads as withheld rather than broken.

### 4.3 The hero that ended the losing streak gets its own beat

The streak-breaker is the most emotionally loaded fact in the payload and it was
a clause inside a sentence. It is now a beat of its own: a line of silence
("Then it stopped."), then the hero name at chapter size with that match's
K/D/A and date.

### 4.4 The seven signals page carries its supplied zones

Page 27 was seven uppercase labels and nothing else — the emptiest screen in the
report. Each channel now renders the `zone` the backend already computed for it.
A channel the backend left unzoned stays blank rather than being given a value.

### 4.5 Copy: stage direction removed throughout

Fourteen pages had their framing rewritten. Representative:

| Page | Before | After |
|---|---|---|
| 1 | "The obvious receipts come first. The pattern comes later." | "One year of queueing. Let's go through it." |
| 2 | "The first receipt is simple: how much Dota happened here." | "That's how much Dota you actually played." |
| 3 | "The next receipt: time spent inside those matches." | "Spent inside those matches." + "Queue time, drafts and loading screens not included." |
| 8 | "The scale is set. Now the result column gives wins the first word." | "Good news first." |
| 10 | "The wins kept going here." | "And then, briefly, the result screen had no bad news." |
| 16 | "The result column is clear enough. Now for the hero names…" | "Wins, losses, streaks — and the heroes you picked again anyway." |
| 19 | "The chronology has a payoff." | "Some names stayed. Others had a moment." |
| 27 | "This report checks the signals it could support." | "Seven ways of asking the same question." |

### 4.6 The duplicate win card is gone

`wins_bridge` carries only `{wins}` — the same number `win_summary` already
shows — so the collage rendered the identical card twice.

**This reverses a deliberate decision from the previous pass**, which added a
test asserting the wins-bridge card is mirrored. The manifest is still the
source of card membership; this is the one module whose card is dropped, and
only because it duplicates another card's value verbatim. The test now asserts
that rule rather than the specific inclusion.

## 5. Before / after mapping — no analytical content lost

| Finding / module | Before | After |
|---|---|---|
| hello, match_count, hours, rank_points | Pages 1–4, each with stage direction | Same pages, same values; framing rewritten, page 3 gains an exclusions line |
| busiest_week / busiest_day / longest_match | Pages 5–7 | Unchanged |
| wins_bridge | Page 8 + a duplicate collage card | Page 8 unchanged; duplicate card dropped |
| win_summary, winning_streak, top_win_heroes | Pages 9–11 | Unchanged values; page 10 close rewritten |
| losing_streak | Page 12, breaker as a clause | Page 12, **breaker promoted to its own beat with K/D/A and date** |
| top_loss_heroes | Page 13 | Unchanged values; framing rewritten |
| post_loss finding | Pages 14–15 | Unchanged |
| hero_pool | Page 17, all five printed | Page 17, **ranks 2–5 printed, rank 1 concealed and called** |
| hero_eras, hero_era_payoff | Pages 18–19 | Unchanged values; page 19 framing rewritten |
| transfer finding | Pages 20–21 | Unchanged |
| kills / assists / deaths | Pages 22–24 | Unchanged |
| elements | Page 27, labels only | Page 27, labels **plus supplied zone** |
| archetype (`not_ready`) | Pages 29–30, constant title | Pages 29–30, **title from supplied variant**, neutral constant as fallback |
| card_collage | Page 32 | Same minus the duplicate |
| final_identity_card | Page 33 | Same, carrying the resolved title |

Every value rendered before is still rendered. Nothing was recomputed.

## 6. Risks

- **The shape title is the most boundary-sensitive change in this pass.** It is
  covered by six unit tests, but a reviewer should read `year-shape.ts` in full
  before release; it is short and deliberately so.
- **Two reveal gestures now exist** where the design plan specified one. They
  are different gestures with different jobs (call-it on 17, turn-it on 30) and
  a test enumerates the allowed set so a third cannot be added silently.
- The fixture's degenerate hero data (every hero 11 matches / 17%) makes the
  hero-pool call less dramatic in QA than it will be against real data.
