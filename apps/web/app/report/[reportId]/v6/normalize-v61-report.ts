import type {
  V6ClaimLayers,
  V6Comparison,
  V6ComparisonRow,
  V6Element,
  V6Finding,
  V6HeroPortfolio,
  V6HeroRow,
  V6Story,
  V6StoryBeat,
  V6TimelinePoint,
  V61IdentitySlot,
  V61Report,
} from "./types";

type RecordValue = Record<string, unknown>;

export function normalizeV61StoryReport(rawReport: V61Report): V61Report {
  const source = recordValue(rawReport);
  const identitySummary = recordValue(source.identity_summary);
  const portfolio = recordValue(source.hero_portfolio);

  return {
    ...source,
    identity: recordValue(source.identity),
    metadata: recordValue(source.metadata),
    elements: recordArray(source.elements).map(normalizeElement),
    findings: recordArray(source.findings).map(normalizeFinding),
    identity_summary: {
      ...identitySummary,
      supporting_lines: stringArray(identitySummary.supporting_lines),
      evidence_refs: stringArray(identitySummary.evidence_refs),
      slots: normalizeSlots(identitySummary.slots),
    },
    hero_portfolio: normalizePortfolio(portfolio),
    diagnostic_questions: recordArray(source.diagnostic_questions),
    story: normalizeStory(source.story),
    pages: recordArray(source.pages) as V61Report["pages"],
    share_candidates: recordArray(source.share_candidates),
    supporting_evidence: recordValue(source.supporting_evidence),
    selection_audit: recordValue(source.selection_audit),
    versions: optionalRecord(source.versions) as V61Report["versions"],
    reproducibility: optionalRecord(source.reproducibility) as V61Report["reproducibility"],
    methodology: normalizeMethodology(source.methodology),
    cost: optionalRecord(source.cost) as V61Report["cost"],
  } as V61Report;
}

function normalizeElement(value: RecordValue): V6Element {
  return {
    ...value,
    evidence_refs: stringArray(value.evidence_refs),
    evidence: recordArray(value.evidence),
    limitations: stringArray(value.limitations),
    supported_claims: stringArray(value.supported_claims),
    forbidden_claims: stringArray(value.forbidden_claims),
  } as V6Element;
}

function normalizeFinding(value: RecordValue): V6Finding {
  return {
    ...value,
    evidence_refs: stringArray(value.evidence_refs),
    evidence_items: recordArray(value.evidence_items),
    limitations: stringArray(value.limitations),
    supported_claims: stringArray(value.supported_claims),
    claim_contract: normalizeLayers(value.claim_contract),
    layers: normalizeLayers(value.layers),
    comparison: normalizeComparison(value.comparison),
  } as unknown as V6Finding;
}

function normalizePortfolio(value: RecordValue): V6HeroPortfolio {
  return {
    ...value,
    heroes: recordArray(value.heroes).map(normalizeHero),
    timeline: recordArray(value.timeline),
    evolution: normalizeEvolution(value.evolution),
  } as V6HeroPortfolio;
}

function normalizeHero(value: RecordValue): V6HeroRow {
  return {
    ...value,
    functional_jobs: stringArray(value.functional_jobs),
    jobs: stringArray(value.jobs),
    mapped_jobs: stringArray(value.mapped_jobs),
  } as V6HeroRow;
}

function normalizeEvolution(value: unknown): V6HeroPortfolio["evolution"] {
  if (value === null) return null;
  if (!isRecord(value)) return undefined;
  return {
    ...value,
    points: recordArray(value.points) as V6TimelinePoint[],
    timeline: recordArray(value.timeline) as V6TimelinePoint[],
    evidence_refs: stringArray(value.evidence_refs),
    limitations: stringArray(value.limitations),
  };
}

function normalizeSlots(value: unknown): V61Report["identity_summary"]["slots"] {
  if (value === null) return null;
  if (!isRecord(value)) return undefined;
  const slots: RecordValue = { ...value };
  for (const key of ["primary", "twist", "anchor"] as const) {
    if (key in value) slots[key] = normalizeSlot(value[key]);
  }
  return slots as V61Report["identity_summary"]["slots"];
}

function normalizeSlot(value: unknown): V61IdentitySlot | null | undefined {
  if (value === null) return null;
  if (!isRecord(value)) return undefined;
  return { ...value, evidence_refs: stringArray(value.evidence_refs) } as V61IdentitySlot;
}

function normalizeLayers(value: unknown): V6ClaimLayers | null | undefined {
  if (value === null) return null;
  if (!isRecord(value)) return undefined;
  return { ...value, alternatives: stringArray(value.alternatives) } as V6ClaimLayers;
}

function normalizeComparison(value: unknown): V6Comparison | null | undefined {
  if (value === null) return null;
  if (!isRecord(value)) return undefined;
  return {
    ...value,
    contexts: comparisonRows(value.contexts),
    rows: comparisonRows(value.rows),
    positive: comparisonRows(value.positive),
    negative: comparisonRows(value.negative),
    control: comparisonRows(value.control),
  } as V6Comparison;
}

function comparisonRows(value: unknown): V6ComparisonRow[] {
  return recordArray(value) as V6ComparisonRow[];
}

function normalizeStory(value: unknown): V6Story | V6StoryBeat[] {
  if (Array.isArray(value)) return recordArray(value) as V6StoryBeat[];
  if (!isRecord(value)) return { ordered_beats: [] };
  return {
    ...value,
    ordered_beats: stringArray(value.ordered_beats),
    beats: recordArray(value.beats),
  } as V6Story;
}

function normalizeMethodology(value: unknown): V61Report["methodology"] {
  if (!isRecord(value)) return undefined;
  return { ...value, notes: stringArray(value.notes) };
}

function isRecord(value: unknown): value is RecordValue {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function recordValue(value: unknown): RecordValue {
  return isRecord(value) ? value : {};
}

function optionalRecord(value: unknown): RecordValue | undefined {
  return value === undefined || value === null ? undefined : recordValue(value);
}

function recordArray(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}
