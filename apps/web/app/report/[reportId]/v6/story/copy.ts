/**
 * Editorial copy for the V6.1 story.
 *
 * House rule: the narrator never describes the report's own structure. Lines
 * like "the first receipt is simple" or "the chronology has a payoff" tell the
 * reader what the page is doing instead of telling them what their year did,
 * and they are the fastest way to drain a recap of energy. Say something about
 * the player, or say nothing and let the Endstop hold the beat.
 *
 * Branch selection reads a supplied `copy_variant`, a supplied boolean, or the
 * composed presence of another page. It never thresholds, sums, or ranks.
 */

export const CHAPTERS: Record<number, string> = {
  1: "The Year in Queue",
  2: "When It Worked",
  3: "When It Didn’t",
  4: "The Next Queue",
  5: "The Heroes That Returned",
  6: "Outside the Short List",
  7: "The Scoreboard",
  // Chapter 8 (Deaths Have Context) does not exist in Free.
  9: "The Pattern Underneath",
  10: "The Reveal",
  11: "The Year, Reassembled",
  12: "One Layer Deeper",
};

/** Which chapter owns each rendered page. */
export const PAGE_CHAPTER: Record<number, number> = {
  1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1,
  8: 2, 9: 2, 10: 2, 11: 2,
  12: 3, 13: 3,
  14: 4, 15: 4,
  16: 5, 17: 5, 18: 5, 19: 5,
  20: 6, 21: 6,
  22: 7, 23: 7, 24: 7,
  26: 9, 27: 9, 28: 9,
  29: 10, 30: 10, 31: 10,
  32: 11, 33: 11,
  34: 12,
};

export const COPY = {
  page1: {
    greetingNamed: (name: string) => `Hey, ${name}.`,
    greetingAnonymous: "Hey.",
    scopeFull: "We looked back at 365 days of your Dota.",
    scopeShort: "We looked back through your Dota from the last 365 days.",
    promise: "One year of queueing. Let\u2019s go through it.",
  },
  page2: {
    headline: (formatted: string, count: number) => (count === 1 ? "1 match." : `${formatted} matches.`),
    support: "That\u2019s how much Dota you actually played.",
  },
  page3: {
    headline: (value: string, unit: "hours" | "minutes") => `${value} ${unit}.`,
    support: "Spent inside those matches.",
    dry: "Queue time, drafts and loading screens not included.",
  },
  page4: {
    // Sentence parts keep the contracted wording intact while the numeral
    // still takes the dominant optical size.
    positive: (points: string) => ["You climbed ", points, " rank points."] as const,
    negative: (points: string) => ["You finished ", points, " rank points below where you started."] as const,
    zero: "You ended the year exactly where you started.",
    scope: (ranked: string) => `Across ${ranked} ranked matches.`,
    split: (wins: string, losses: string) => `${wins} ranked wins · ${losses} ranked losses.`,
  },
  page5: {
    question: "Which week held the most Dota?",
    range: (start: string, end: string) => `${start} — ${end}.`,
    withHours: (matches: string, hours: string, unit: string) => `${matches} matches · ${hours} ${unit}.`,
    matchesOnly: (matches: string) => `${matches} matches.`,
  },
  page6: {
    leadInside: "Inside that week, one day held the most Dota.",
    leadOutside: "Outside that week, another day held the most Dota.",
    withHours: (matches: string, hours: string, unit: string) => `${matches} matches · ${hours} ${unit}.`,
    matchesOnly: (matches: string) => `${matches} matches.`,
  },
  page7: {
    question: "Which match kept going?",
    match: (hero: string, date: string) => `${hero} · ${date}.`,
    win: "You won that one.",
    loss: "That one didn't go your way.",
    detail: (kills: number, deaths: number, assists: number) => `${kills} / ${deaths} / ${assists}`,
    dry: "That match earned its own line in the report.",
  },
  page8: {
    leadWins: "Good news first.",
    leadZero: "Let\u2019s start with what the year gave you.",
  },
  page9: {
    zero: "No wins made it into this year’s recorded history.",
    headline: (wins: string, count: number) => (count === 1 ? "1 win." : `${wins} wins.`),
    support: (matches: string) => `Out of ${matches} matches in this report.`,
    winningestDay: (date: string, wins: string) => `Your winningest day: ${date} · ${wins} wins.`,
  },
  page10: {
    lead: "And then, briefly, nothing went wrong.",
    headline: (length: string) => `${length} wins in a row.`,
    range: (start: string, end: string) => `${start} → ${end}.`,
    dry: (length: string) => `${length} in a row. Matchmaking looked away for a while.`,
    singleLead: "No long run appeared here. Every run starts somewhere.",
    singleHeadline: "Longest run: 1 win.",
  },
  page11: {
    headlineThree: "These heroes appeared in the most wins.",
    headlineFew: "These heroes appeared in the most wins.",
    headlineOne: "This hero appeared in more wins than anyone else.",
  },
  page12: {
    lead: "Then came the losses.",
    headline: (length: string) => ["You lost ", length, " matches in a row."] as const,
    range: (start: string, end: string) => `${start} → ${end}.`,
    singleLead: "The longest recorded loss run stopped at one.",
    singleHeadline: "Longest slide: 1 match.",
    // Reveal choreography.  The first two lines are positional, tied to the
    // second and third revealed loss block.  The third is conditional on
    // streak length; the owner froze that minimum at three on 2026-08-30, so
    // it is a supplied rule rather than a frontend judgement.
    microcopy: {
      positional: ["One more.", "And another."],
      long: "And… yeah.",
      longMinimumLength: 3,
    },
    brokenLead: "Then it stopped.",
    brokenSupport: (length: string) => `After ${length} straight, this one went your way.`,
    brokenDry: (hero: string) => `${hero} gets the last word.`,
    breakerLabel: "The one that ended it",
    observationEnded: "The recorded year ends here.",
    historyBoundary: "The streak reaches the edge of the history we can see.",
  },
  page13: {
    breakerLead: (hero: string) => `${hero} got you out of that.`,
    breakerSecond: "These ones were less helpful.",
    neutralLead: "Some names kept turning up on the wrong side.",
    headlineThree: "These three appeared in the most losses this year.",
    headlineFew: "These heroes appeared in the most losses this year.",
    headlineOne: "This hero appeared in the most losses this year.",
    roughestDay: (date: string, losses: string) => `Your roughest day: ${date} · ${losses} losses.`,
  },
  page14: {
    lead: "The result is one line.",
    second: "The next queue is another.",
  },
  page15: {
    question: "After a loss, did your next game change?",
    sample: (count: string) => `Based on ${count} comparable loss → next-game moments.`,
  },
  page16: {
    lead: "Wins, losses, streaks, questionable picks.",
    second: "Some names were there for all of it.",
    combined: "Wins, losses, streaks, questionable picks \u2014 some names were there for all of it.",
  },
  page17: {
    headlineFull: "These were the heroes your year kept returning to.",
    headlineFew: "These were the heroes you kept returning to.",
    // The call-it-before-it-resolves moment. The reader almost always knows.
    guessLead: "You already know who\u2019s first.",
    guessPrompt: "Tap to confirm",
    share: (percent: string) => `Together, they made up ${percent} of your matches.`,
  },
  page18: {
    lead: "But your hero pool didn’t stay still.",
    prompt: "Move through your year.",
    dry: "Different month. Different obsession.",
    sparseLead: "Your hero pool changed through the year.",
    emptyPeriod: "No recorded matches in this period.",
    control: "Hero era period",
  },
  page19: {
    lead: "Some names stayed. Others had a moment.",
    persistence: (hero: string, periods: string) => `${hero} stayed in your top five for ${periods} periods.`,
    takeover: (hero: string, period: string) => `${hero} became the leading name around ${period}.`,
    steady: "The top of the list barely moved all year.",
  },
  page20: {
    lead: "Knowing the names was the easy part.",
    second: "What followed when the names changed?",
    directToCombat: "The names changed. The scoreboard kept the count.",
  },
  page21: {
    question: "How much of your game travels with you?",
    dryTravelled: "Different hero. Same player. Mostly.",
    dryChanged: "Different hero. Different-looking game.",
  },
  page22: {
    headline: (total: string) => ["You collected ", total, " kills this year."] as const,
    zero: "No kills made it into this recorded year.",
    leading: (hero: string, total: string) => `${hero} led the kill total: ${total}.`,
    rowsThree: (hero: string) => `The three ${hero} games with the highest kill count:`,
    rowsFew: (hero: string) => `The ${hero} games with the highest kill count.`,
  },
  page23: {
    headline: (total: string) => ["You also recorded ", total, " assists."] as const,
    zero: "No assists made it into this recorded year.",
    leading: (hero: string, total: string) => `${hero} led the way with ${total}.`,
    rowsThree: (hero: string) => `The three ${hero} games with the highest assist count:`,
    rowsFew: (hero: string) => `The ${hero} games with the highest assist count.`,
  },
  page24: {
    headline: (total: string) => ["The year recorded ", total, " deaths."] as const,
    zero: "Zero recorded deaths.",
    leading: (hero: string, total: string) => `${hero} was there for ${total} of them.`,
    rowsThree: (hero: string) => `The three ${hero} games with the highest death count:`,
    rowsFew: (hero: string) => `The ${hero} games with the highest death count.`,
  },
  page26: {
    lead: "Kills, assists, deaths \u2014 that\u2019s the visible part.",
    second: "Underneath it, we were measuring something else.",
  },
  page27: {
    headline: "Seven ways of asking the same question.",
    support: (count: number) =>
      count === 1 ? "One signal. It is not the whole story." : `${count} signals. None of them is the whole story.`,
  },
  page29: {
    lines: {
      played: "We looked at what you played.",
      won: "How you won.",
      losses: "What happened after losses.",
      stayed: "Which heroes stayed.",
      changed: "And what followed you when they changed.",
    },
    close: "Put it together\u2026",
  },
  page30: {
    reveal: "Turn the card",
    revealed: "Card turned.",
    /** Used when no supplied variant can name the year's shape. */
    neutralTitle: "The Year in Queue",
    neutralLine: "Assembled from the matches, results and hero choices this history could support.",
    // The scripted optional line "Built from your heroes, your Elements, and
    // the patterns we could actually prove." asserts a provenance the
    // placeholder does not have.  Restored with the archetype engine.
  },
  page32: {
    close: "Your year, reassembled.",
  },
  page33: {
    matches: (count: string) => `${count} matches sequenced.`,
    lookback: (days: string, historyComplete: boolean) =>
      historyComplete ? `${days} days of Dota.` : "From the history this report could see.",
    share: "Share the receipts.",
    runItBack: "Read it again.",
    shareCopied: "Report link copied.",
    shareCopyFailed: "The link is below. Select it to copy.",
    shareUrlLabel: "Report link",
  },
  page34: {
    lead: "Your match history tells us this much.",
    second: "Inside the matches, there’s another layer.",
    cta: "Go deeper.",
  },
  shell: {
    exit: "Exit",
    back: "Back",
    next: "Next",
    evidence: "Why this?",
    methodology: "How this was measured",
    progress: (current: number, total: number) => `Page ${current} of ${total}`,
  },
} as const;

/**
 * Page 21's optional close is branch-accurate only.  The direction comes from
 * the supplied `semantic_outcome_key`; an unrecognised key drops the joke
 * rather than guessing at the direction.
 */
export function transferClosingLine(semanticOutcomeKey: string | null | undefined): string | null {
  switch (semanticOutcomeKey) {
    case "clean_transfer":
      return COPY.page21.dryTravelled;
    case "results_stop_first":
    case "expression_stops_first":
    case "involvement_boundary":
    case "exposure_boundary":
    case "localized_function_bottleneck":
      return COPY.page21.dryChanged;
    default:
      return null;
  }
}
