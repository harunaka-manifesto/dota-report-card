/**
 * Contracted copy from `docs/dota-v6.1-main-script.md`.
 *
 * Every string here is quoted, not paraphrased.  Curly quotation marks and
 * ellipses are reproduced as written; Page 7's loss outcome deliberately keeps
 * a STRAIGHT apostrophe because the script writes it that way.
 *
 * Branch selection reads a supplied `copy_variant`, a supplied boolean, or the
 * composed presence of another page.  It never thresholds, sums, or ranks.
 */

export const CHAPTERS: Record<number, string> = {
  1: "Your Year",
  2: "The Good News",
  3: "And Then There Was This",
  4: "What Happened Next?",
  5: "Your Heroes",
  6: "Outside the Comfort Zone",
  7: "The Body Count",
  // Chapter 8 (Deaths Have Context) does not exist in Free.
  9: "The Seven Signals",
  10: "Your Archetype",
  11: "Your Dota DNA",
  12: "There's More Down There",
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

/**
 * Bridge pages carry no dry line, and these four always close silently
 * (script, Content Safety and Tone Rules).  The cadence rule is frozen, not a
 * frontend judgement call.
 */
export const ALWAYS_SILENT_PAGES: ReadonlySet<number> = new Set([4, 9, 22, 30]);
export const BRIDGE_PAGES: ReadonlySet<number> = new Set([8, 14, 16, 20, 26, 34]);

export const COPY = {
  page1: {
    greetingNamed: (name: string) => `Hey, ${name}.`,
    greetingAnonymous: "Hey.",
    scopeFull: "We looked back at 365 days of your Dota.",
    scopeShort: "We looked back through your Dota from the last 365 days.",
    // Suppressed on the short-history branch: "All of it" would claim a
    // completeness the short-history copy has just declined to claim.
    dry: "Yes. All of it.",
  },
  page2: {
    headline: (formatted: string, count: number) => (count === 1 ? "1 match." : `${formatted} matches.`),
    support: "That’s how much Dota happened this year.",
    dryNormal: "That’s a lot of Ancient exploding.",
    dryLimited: "Enough to leave a trail.",
  },
  page3: {
    headline: (value: string, unit: "hours" | "minutes") => `${value} ${unit}.`,
    support: "Spent inside those matches.",
    dry: "We’ll let you decide whether that sounds impressive or concerning.",
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
    lead: "But one week stood above the rest.",
    range: (start: string, end: string) => `${start} — ${end}.`,
    withHours: (matches: string, hours: string, unit: string) => `${matches} matches · ${hours} ${unit}.`,
    matchesOnly: (matches: string) => `${matches} matches.`,
    dry: "Apparently, plans were optional that week.",
  },
  page6: {
    leadInside: "Inside that week, one day did most of the work.",
    leadOutside: "And one single day outplayed all of them.",
    withHours: (matches: string, hours: string, unit: string) => `${matches} matches · ${hours} ${unit}.`,
    matchesOnly: (matches: string) => `${matches} matches.`,
    dry: "A full shift, essentially.",
  },
  page7: {
    leadRefused: "And one match refused to end.",
    leadOnBusiestDay: "That day also held the longest match of your year.",
    leadNeutral: "Your longest match of the year.",
    match: (hero: string, date: string) => `${hero} · ${date}.`,
    win: "You won that one.",
    // Straight apostrophe, exactly as the script writes it.
    loss: "That one didn't go your way.",
    detail: (kills: number, deaths: number, assists: number) => `${kills} / ${deaths} / ${assists}`,
    dry: "Nobody was calling GG in that one.",
  },
  page8: {
    leadWins: "Alright. Let’s start with the good news.",
    leadZero: "Alright. Let’s start with what the year gave us.",
    dry: "You did, in fact, win some Dota.",
  },
  page9: {
    zero: "No wins made it into this year’s recorded history.",
    headline: (wins: string, count: number) => (count === 1 ? "1 win." : `${wins} wins.`),
    support: (matches: string) => `Out of ${matches} matches this year.`,
    winningestDay: (date: string, wins: string) => `Your winningest day: ${date} · ${wins} wins.`,
  },
  page10: {
    lead: "And at one point, you simply refused to lose.",
    headline: (length: string) => `${length} wins in a row.`,
    range: (start: string, end: string) => `${start} → ${end}.`,
    dry: (length: string) => `For ${length} games, matchmaking behaved itself.`,
    singleLead: "No giant streak this year, but every run starts somewhere.",
    singleHeadline: "Longest run: 1 win.",
  },
  page11: {
    headlineThree: "These heroes showed up for the most wins.",
    // Script: "If fewer than three heroes have wins ... use this."
    headlineFew: "These heroes showed up for your wins.",
    headlineOne: "This hero showed up for more wins than anyone else.",
    dry: "Keep them close.",
  },
  page12: {
    lead: "Unfortunately, Dota does believe in balance.",
    headline: (length: string) => ["You lost ", length, " matches in a row."] as const,
    range: (start: string, end: string) => `${start} → ${end}.`,
    singleLead: "You never let the losses pile up very far.",
    singleHeadline: "Longest slide: 1 match.",
    // Positional reveal choreography, tied to the second and third revealed
    // loss block.  The third scripted line ("And… yeah.") is conditional on
    // streak length, which is a threshold the frontend may not evaluate, so it
    // ships when the payload supplies the condition.  See plan Risk 5.
    microcopy: ["One more.", "And another."],
    brokenLead: (hero: string) => `Until ${hero} finally put a stop to it.`,
    brokenSupport: (length: string) => `After ${length} straight losses, you won this one.`,
    brokenDry: (hero: string) => `Thank you for your service, ${hero}.`,
    observationEnded: "And that’s where the recorded year ends.",
    historyBoundary: "That streak ends at the edge of the history we can see.",
  },
  page13: {
    breakerLead: (hero: string) => `${hero} got you out of that mess.`,
    breakerSecond: "Your other heroes had… mixed results.",
    neutralLead: "Some heroes spent more time on the wrong side of the Ancient.",
    headlineThree: "These three accompanied you through the most losses this year.",
    // Script: show only the remaining heroes, and remove plural wording when
    // there is a single losing hero.
    headlineFew: "These accompanied you through the most losses this year.",
    headlineOne: "This hero accompanied you through the most losses this year.",
    roughestDay: (date: string, losses: string) => `Your roughest day: ${date} · ${losses} losses.`,
    dry: "They were there for you. Technically.",
  },
  page14: {
    lead: "Losing is one thing.",
    second: "What you did next is more interesting.",
  },
  page15: {
    question: "After a loss, did your next game change?",
    sample: (count: string) => `Based on ${count} comparable loss → next-game moments.`,
  },
  page16: {
    lead: "Wins, losses, streaks, questionable decisions…",
    second: "Some heroes kept showing up through all of it.",
    // Fixed combined transition used when Post-Loss did not render.
    combined:
      "Wins, losses, streaks, questionable decisions… some heroes kept showing up through all of it.",
  },
  page17: {
    headlineFull: "These were your heroes.",
    headlineFew: "These were the heroes you kept coming back to.",
    share: (percent: string) => `Together, they made up ${percent} of your matches.`,
    dryConcentrated: "Some people call it a hero pool. Sometimes it’s more of a hero puddle.",
    dryBroad: "Plenty of room in that pool.",
  },
  page18: {
    lead: "But your hero pool didn’t stay still.",
    prompt: "Drag through your year.",
    dry: "Different month. Different obsession.",
    sparseLead: "Your hero pool changed through the year.",
    emptyPeriod: "No recorded matches in this period.",
    control: "Hero era period",
  },
  page19: {
    lead: "Some heroes stayed all year. Others had their moment.",
    persistence: (hero: string, periods: string) => `${hero} stayed in your top five for ${periods} periods.`,
    takeover: (hero: string, period: string) => `${hero} really took over around ${period}.`,
    steady: "Your top heroes were remarkably steady.",
    dry: "It was a phase. A very well-documented phase.",
  },
  page20: {
    lead: "Knowing your favorite heroes is easy.",
    second: "The interesting part is what happens when you leave them.",
    // Fixed direct transition used when Transfer did not render.
    directToCombat: "However the hero names changed, the scoreboard kept keeping count.",
  },
  page21: {
    question: "How much of your game travels with you?",
    dryTravelled: "Different hero. Same player. Mostly.",
    dryChanged: "Different hero. Different-looking game.",
  },
  page22: {
    headline: (total: string) => ["You collected ", total, " kills this year."] as const,
    zero: "No kills made it into this recorded year.",
    leading: (hero: string, total: string) => `${hero} contributed more than any other hero: ${total}.`,
    rowsThree: (hero: string) => `The three games where ${hero} really got involved:`,
    rowsFew: (hero: string) => `Your biggest ${hero} kill games.`,
  },
  page23: {
    headline: (total: string) => ["You also recorded ", total, " assists."] as const,
    zero: "No assists made it into this recorded year.",
    leading: (hero: string, total: string) => `${hero} led the way with ${total}.`,
    rowsThree: (hero: string) => `The three games where ${hero} led the way:`,
    rowsFew: (hero: string) => `Your biggest ${hero} assist games.`,
    dry: "Proof that clicking the same person together can occasionally be called teamwork.",
  },
  page24: {
    headline: (total: string) => ["Dota collected ", total, " deaths in return."] as const,
    zero: "Zero recorded deaths.",
    leading: (hero: string, total: string) => `${hero} was there for ${total} of them.`,
    rowsThree: (hero: string) => `The three bloodiest ${hero} games:`,
    rowsFew: (hero: string) => `The games where that number climbed highest.`,
    dry: "We said we looked at everything.",
  },
  page26: {
    // Death Context is permanently absent, so the Dynamic Chapter Assembly
    // transition copy replaces Page 26's default opening.
    lead: "Kills, assists, deaths—that’s the visible part.",
    second: "Underneath all of it, we were measuring something else.",
  },
  page27: {
    headline: "Your Dota, measured seven ways.",
    support: "Seven different ways of asking: ‘What kind of Dota do you keep playing?’",
  },
  page29: {
    lines: {
      played: "We looked at what you played.",
      won: "How you won.",
      losses: "What happened after losses.",
      stayed: "Which heroes stayed.",
      changed: "And what followed you when they changed.",
    },
    close: "Put it all together…",
  },
  page30: {
    reveal: "Reveal your archetype",
    revealed: "Archetype revealed.",
    // The scripted optional line "Built from your heroes, your Elements, and
    // the patterns we could actually prove." asserts a provenance the
    // placeholder does not have.  Restored with the archetype engine.
  },
  page31: {
    heading: (archetype: string) => `Why ${archetype}?`,
  },
  page32: {
    close: "Well. That was your year.",
    dry: "Some wins. Some losses. Several thousand clicks.",
  },
  page33: {
    matches: (count: string) => `${count} matches sequenced.`,
    lookback: "365 days of Dota.",
    share: "Share your Dota DNA.",
    runItBack: "Run it back.",
    shareCopied: "Report link copied.",
    shareCopyFailed: "The link is below. Select it to copy.",
    shareUrlLabel: "Report link",
  },
  page34: {
    lead: "Your match history tells us this much.",
    second: "Inside the matches, there’s another layer.",
    cta: "Go deeper.",
    dry: "Because apparently 365 days still wasn’t enough.",
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
