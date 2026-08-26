import type {
  V6ComparisonRow,
  V6Element,
  V6Finding,
  V6HeroRow,
  V6TimelinePoint,
  V61IdentitySlot,
  V61Report,
} from "./types";

export const SIGNAL_LABELS = [
  "Breadth",
  "Toolkit",
  "Involvement",
  "Finishing",
  "Death Exposure",
  "Transfer",
  "Consistency",
] as const;

export type EvidenceModel = {
  headline: string;
  statement?: string;
  sampleSize?: number;
  sessions?: number;
  rows: string[];
  alternatives: string[];
  limitations: string[];
};

export type StoryBand = "regular" | "rotating" | "occasional";

export type StoryPage = {
  id: string;
  chapter: string;
  layout: "center" | "split";
  bridge?: string;
  eyebrow?: string;
  headline: string;
  subtitle?: string;
  description?: string[];
  evidence?: EvidenceModel;
  evidenceRefs: string[];
  heroRows?: V6HeroRow[];
  bands?: Array<{ label: string; rows: V6HeroRow[] }>;
  timeline?: V6TimelinePoint[];
  slots?: V61IdentitySlot[];
  scope?: { matches: number; heroCount: number };
  share?: {
    displayName: string;
    signature?: string;
    heroes: string[];
    findings: string[];
  };
  kind?: "scope" | "share" | "end";
};

const FAMILY_ORDER = ["transfer", "post_loss_response", "combat_expression", "session_drift"] as const;

const FAMILY_COPY = {
  transfer: {
    id: "finding-transfer",
    chapter: "Adaptability",
    bridge: "Your pool says where you returned. Now: what survived when the hero changed?",
    eyebrow: "ADAPTABILITY",
    subtitle: "When the hero changed, what came with you?",
  },
  post_loss_response: {
    id: "finding-post-loss",
    chapter: "Adversity",
    bridge: "A different hero can move the script. A loss can do it too.",
    eyebrow: "ADVERSITY",
    subtitle: "One loss. Two or more. What happened to the next choice?",
  },
  combat_expression: {
    id: "finding-combat",
    chapter: "Expression",
    bridge: "The pick is only the start of the match.",
    eyebrow: "EXPRESSION",
    subtitle: "Involvement and death exposure stay separate here.",
  },
  session_drift: {
    id: "finding-session",
    chapter: "Time",
    bridge: "One match speaks once. A session gets a second opinion.",
    eyebrow: "TIME",
    subtitle: "Game 1 through Game 5+.",
  },
} as const;

export function buildStoryPages(report: V61Report): StoryPage[] {
  const pages: StoryPage[] = [];
  const heroes = safeHeroes(report.hero_portfolio.heroes ?? []);
  const findings = report.findings.filter(isPublishedFinding);
  const poolFinding = findings.find((finding) => finding.family === "pool_shape");
  const breadth = report.elements.find((element) => element.key === "breadth");
  const slots = availableSlots(report);
  const identityRefs = unique([
    ...(report.identity_summary.evidence_refs ?? []),
    ...slots.flatMap((slot) => slot.evidence_refs ?? []),
  ]);

  pages.push({
    id: "arrival",
    chapter: "Recognition",
    layout: "center",
    eyebrow: "DOTA DNA",
    headline: `${report.identity.display_name?.trim() || "Your Dota"}, a year of Dota left receipts.`,
    subtitle: "Let’s see what kept showing up.",
    evidenceRefs: [],
  });

  pages.push({
    id: "scope-receipt",
    chapter: "Recognition",
    layout: "center",
    headline: "365 days",
    scope: {
      matches: report.metadata?.eligible_matches ?? report.metadata?.processed_matches ?? 0,
      heroCount: Math.min(5, heroes.length),
    },
    evidenceRefs: [],
    kind: "scope",
  });

  if (heroes[0]) {
    const lead = heroes[0];
    pages.push({
      id: "lead-hero",
      chapter: "Familiarity",
      layout: "split",
      bridge: "FIRST, THE FAMILIAR PART",
      headline: `${heroName(lead)} leads your year.`,
      subtitle: `${lead.match_count} matches · ${percent(lead.share)} of the year`,
      description: ["Most-played is a starting point. One hero still doesn’t describe your Dota."],
      heroRows: [lead],
      evidenceRefs: [],
    });
  }

  if (heroes.length >= 2) {
    const supporting = heroes.slice(1, 5);
    pages.push({
      id: "hero-front-row",
      chapter: "Familiarity",
      layout: "split",
      headline: "One hero doesn’t describe your Dota.",
      subtitle: heroes.length >= 5 ? "These four kept coming back too." : "These kept coming back too.",
      heroRows: supporting,
      evidenceRefs: [],
    });
  }

  if (breadth && ["available", "descriptive"].includes(breadth.status ?? "")) {
    pages.push({
      id: "pool-width",
      chapter: "Structure",
      layout: "split",
      bridge: "Now the names become a shape.",
      headline: breadthHeadline(breadth.zone),
      subtitle: "Breadth tracks where your matches gather, not how many heroes appeared once.",
      evidence: elementEvidence(breadth, breadthHeadline(breadth.zone)),
      evidenceRefs: breadth.evidence_refs ?? [],
    });
  }

  const bands = ([
    ["Regular", "regular"],
    ["Rotating", "rotating"],
    ["Occasional", "occasional"],
  ] as const).map(([label, band]) => ({ label, rows: heroes.filter((hero) => hero.story_band === band) }));
  if (bands.filter((band) => band.rows.length > 0).length >= 2) {
    const ownsPoolFinding = poolFinding && poolFinding.semantic_outcome_key !== "names_changed_jobs_held";
    pages.push({
      id: "pool-layers",
      chapter: "Structure",
      layout: "split",
      headline: ownsPoolFinding ? poolFinding.claim! : "Regulars. Rotations. Occasional appearances.",
      subtitle: ownsPoolFinding
        ? firstText(poolFinding.observation, poolFinding.claim_contract?.observation, poolFinding.evidence_text)
        : "The pool has layers before any one pattern earns a headline.",
      description: ownsPoolFinding ? [poolFinding.interpretation!] : undefined,
      bands,
      evidence: ownsPoolFinding
        ? findingEvidence(poolFinding)
        : poolEvidence(report, "The structure inside your pool."),
      evidenceRefs: ownsPoolFinding
        ? poolFinding.evidence_refs ?? []
        : ["supporting:portfolio_shape"],
    });
  }

  const timeline = safeTimeline(report);
  if (timeline.length >= 2) {
    const ownsPoolFinding = poolFinding?.semantic_outcome_key === "names_changed_jobs_held";
    const evolution = report.hero_portfolio.evolution;
    pages.push({
      id: "pool-movement",
      chapter: "Structure",
      layout: "split",
      bridge: "A pool can hold its shape and still move.",
      headline: ownsPoolFinding
        ? poolFinding.claim!
        : firstText(evolution?.title, evolution?.body, "The year did not use the same pool all the way through."),
      subtitle: "Early. Middle. Late.",
      description: ownsPoolFinding ? [poolFinding.interpretation!] : undefined,
      timeline,
      evidence: ownsPoolFinding
        ? findingEvidence(poolFinding)
        : poolEvidence(report, "How the pool moved across the year."),
      evidenceRefs: ownsPoolFinding
        ? poolFinding.evidence_refs ?? []
        : report.hero_portfolio.evolution?.evidence_refs ?? ["supporting:portfolio_shape"],
    });
  }

  let findingPageCount = 0;
  for (const family of FAMILY_ORDER) {
    if (findingPageCount === 3) break;
    const finding = findings.find((item) => item.family === family);
    if (!finding) continue;
    const copy = FAMILY_COPY[family];
    pages.push({
      id: copy.id,
      chapter: copy.chapter,
      layout: "split",
      bridge: copy.bridge,
      eyebrow: copy.eyebrow,
      headline: finding.claim!,
      subtitle: copy.subtitle,
      description: [finding.interpretation!],
      evidence: findingEvidence(finding),
      evidenceRefs: finding.evidence_refs ?? [],
    });
    findingPageCount += 1;
  }

  const referencedPages = pages.filter((page) => intersects(page.evidenceRefs, identityRefs));
  if (referencedPages.length >= 2) {
    const supporting = (report.identity_summary.supporting_lines ?? []).filter(Boolean);
    pages.push({
      id: "coherence",
      chapter: "Coherence",
      layout: "split",
      bridge: "Now look at what kept showing up together.",
      headline: "The findings stop looking separate.",
      subtitle: supporting[0],
      description: supporting.slice(1),
      evidence: {
        headline: "Why these findings connect.",
        rows: referencedPages.map((page) => `${page.chapter}: ${page.headline}`),
        alternatives: [],
        limitations: [],
      },
      evidenceRefs: identityRefs,
    });
  }

  const signatureReady = signatureIsReady(report, slots);
  if (signatureReady) {
    pages.push({
      id: "signature-setup",
      chapter: "Signature",
      layout: "center",
      bridge: "The individual findings have finished pretending they’re unrelated.",
      headline: "The pattern underneath the patterns.",
      subtitle: slots.map((slot) => titleCase(slot.kind ?? "")).filter(Boolean).join(". ") + ".",
      evidenceRefs: identityRefs,
    });
    pages.push({
      id: "signature-reveal",
      chapter: "Signature",
      layout: "split",
      eyebrow: "YOUR DOTA SIGNATURE",
      headline: report.identity_summary.headline!,
      description: (report.identity_summary.supporting_lines ?? []).filter(Boolean),
      slots,
      evidence: {
        headline: "Why this Signature landed here.",
        rows: slots.map((slot) => `${titleCase(slot.kind ?? "Signal")}: ${slot.text}`),
        alternatives: [],
        limitations: [],
      },
      evidenceRefs: identityRefs,
    });
  }

  pages.push({
    id: "share",
    chapter: "Share",
    layout: "split",
    bridge: "A report is private right up until you copy the link.",
    headline: "Your Dota DNA, in pieces.",
    subtitle: signatureReady ? report.identity_summary.headline ?? undefined : "The parts that kept showing up.",
    share: {
      displayName: report.identity.display_name?.trim() || "Your Dota",
      signature: signatureReady ? report.identity_summary.headline ?? undefined : undefined,
      heroes: heroes.slice(0, 5).map(heroName),
      findings: pages
        .filter((page) => page.id.startsWith("finding-") || (
          poolFinding && ["pool-layers", "pool-movement"].includes(page.id) && page.headline === poolFinding.claim
        ))
        .map((page) => page.headline),
    },
    evidenceRefs: [],
    kind: "share",
  });

  pages.push({
    id: "end",
    chapter: "End",
    layout: "center",
    headline: "The match history has made its case.",
    subtitle: "Not all of your Dota. The part that kept showing up.",
    evidenceRefs: [],
    kind: "end",
  });

  return pages;
}

function safeHeroes(rows: V6HeroRow[]): V6HeroRow[] {
  return rows.filter((row) => {
    const name = heroName(row);
    return name.length > 0 && !/^\d+$/.test(name) && Number.isFinite(row.match_count) && Number.isFinite(row.share);
  });
}

function safeTimeline(report: V61Report): V6TimelinePoint[] {
  const evolution = report.hero_portfolio.evolution;
  return (evolution?.points ?? evolution?.timeline ?? report.hero_portfolio.timeline ?? []).filter(
    (point) => Boolean(point?.label && (point.summary || point.evidence || point.period)),
  );
}

function isPublishedFinding(finding: V6Finding): boolean {
  return Boolean(
    finding.published &&
    finding.claim?.trim() &&
    finding.interpretation?.trim() &&
    finding.claim_contract &&
    finding.evidence_refs?.length,
  );
}

function availableSlots(report: V61Report): V61IdentitySlot[] {
  const slots = report.identity_summary.slots;
  return [slots?.primary, slots?.twist, slots?.anchor].filter(
    (slot): slot is V61IdentitySlot => Boolean(slot?.text?.trim() && slot.evidence_refs?.length),
  );
}

function signatureIsReady(report: V61Report, slots: V61IdentitySlot[]): boolean {
  const primary = report.identity_summary.slots?.primary;
  return Boolean(
    report.identity_summary.headline?.trim() &&
    primary?.text?.trim() &&
    primary.evidence_refs?.length &&
    ["moderate", "high"].includes(report.identity_summary.confidence ?? "") &&
    slots.length,
  );
}

function elementEvidence(element: V6Element, headline: string): EvidenceModel {
  return {
    headline,
    statement: element.supported_claims?.[0] ?? element.description ?? undefined,
    sampleSize: numberOrUndefined(element.sample_size),
    sessions: numberOrUndefined(element.independent_session_count ?? element.independent_sessions),
    rows: element.zone ? [`Observed range: ${titleCase(element.zone)}`] : [],
    alternatives: [],
    limitations: element.limitations ?? [],
  };
}

function findingEvidence(finding: V6Finding): EvidenceModel {
  const layers = finding.claim_contract ?? finding.layers;
  const rows = comparisonRows(finding.comparison);
  return {
    headline: finding.claim!,
    statement: firstText(layers?.evidence, finding.evidence_text, typeof finding.evidence === "string" ? finding.evidence : undefined),
    sampleSize: numberOrUndefined(finding.sample_size),
    sessions: numberOrUndefined(finding.independent_session_count ?? finding.independent_sessions),
    rows,
    alternatives: layers?.alternatives ?? [],
    limitations: finding.limitations ?? [],
  };
}

function poolEvidence(report: V61Report, headline: string): EvidenceModel {
  const shape = report.supporting_evidence.portfolio_shape ?? {};
  const rows: string[] = [];
  addNumber(rows, shape.match_count, "eligible hero selections", 0);
  addNumber(rows, shape.shannon_effective_heroes, "effective heroes", 1);
  addNumber(rows, shape.shannon_effective_jobs, "mapped jobs", 1);
  if (typeof shape.taxonomy_coverage === "number") rows.push(`${Math.round(shape.taxonomy_coverage * 100)}% taxonomy coverage`);
  return { headline, rows, alternatives: [], limitations: [] };
}

function comparisonRows(comparison: V6Finding["comparison"]): string[] {
  if (!comparison) return [];
  const rows = [
    ...(comparison.contexts ?? []),
    ...(comparison.rows ?? []),
    ...(comparison.positive ?? []),
    ...(comparison.negative ?? []),
    ...(comparison.control ?? []),
  ];
  return rows.map(formatComparisonRow).filter(Boolean);
}

function formatComparisonRow(row: V6ComparisonRow): string {
  const value = row.value ?? row.estimate;
  if (value == null) return row.label;
  return `${row.label}: ${typeof value === "number" ? Number(value.toFixed(2)) : value}${row.unit ? ` ${row.unit}` : ""}`;
}

function breadthHeadline(zone?: string | null): string {
  if (["focused", "low"].includes(zone ?? "")) return "A small group carries most of your year.";
  if (["broad", "high"].includes(zone ?? "")) return "Your year reaches across a wide hero pool.";
  return "Your pool has a center with room around it.";
}

function heroName(row: V6HeroRow): string {
  return firstText(row.display_name, row.hero_name, row.name);
}

function percent(value?: number | null): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function firstText(...values: Array<string | null | undefined>): string {
  return values.find((value) => typeof value === "string" && value.trim())?.trim() ?? "";
}

function titleCase(value: string): string {
  return value.toLowerCase().replace(/(^|_)([a-z])/g, (_match, prefix, letter) => `${prefix ? " " : ""}${letter.toUpperCase()}`);
}

function numberOrUndefined(value?: number | null): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function addNumber(rows: string[], value: unknown, label: string, digits: number): void {
  if (typeof value === "number" && Number.isFinite(value)) rows.push(`${value.toFixed(digits)} ${label}`);
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function intersects(left: string[], right: string[]): boolean {
  const set = new Set(right);
  return left.some((item) => set.has(item));
}
