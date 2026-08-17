export const PORTFOLIO_COPY_V4 = {
  version: "free-dna-copy-4.0.0",
  common_thread: {
    correct: "You got it.",
    incorrect: "Not quite.",
    reveal: (trait: string, heroCount: number) => `${trait} is the strongest recurring functional trait across ${heroCount} established heroes.`,
    unavailable: "No clear common thread"
  },
  exception: {
    correct: "Yep.",
    incorrect: "Good guess — but not this one.",
    reveal: (hero: string) => `${hero} is the clearest functional outlier in the established pool.`,
    unavailable: "No clear exception"
  },
  evolution: {
    check: "Let’s check.",
    variants: {
      new_heroes_new_toolkit: "New heroes arrived with a meaningfully different toolkit.",
      new_heroes_same_toolkit: "New hero names arrived, while the toolkit stayed familiar.",
      stable_core_new_branch: "A stable core remains, with a newer branch growing beside it.",
      broadly_stable: "The hero distribution and toolkit stayed broadly stable."
    }
  },
  hero_mirror: {
    closed: "One last comparison: your observable behavior against a hero-shaped reference.",
    available: (hero: string) => `The closest sufficiently sampled match is ${hero}.`,
    qualifier: "Not your best hero. Not necessarily your most played.",
    guardrail: "This is a behavior comparison, not a claim about identity."
  }
} as const;
