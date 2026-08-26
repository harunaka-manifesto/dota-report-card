import type {
  V6Element,
  V6Finding,
  V6HeroPortfolio,
  V6ShareCandidate,
  V6StoryBeat,
  V6StoryReport,
} from "../types";
import { reportBeats } from "../types";
import { buildStorySequence, type StoryChapter, type StoryStep } from "./story-sequence";

export type StoryFamilyModel = {
  finding: V6Finding | null;
  evidence?: Record<string, unknown>;
};

export type StoryModel = {
  /** Kept during the migration so existing evidence/persistence behavior is lossless. */
  report: V6StoryReport;
  beats: V6StoryBeat[];
  sequence: StoryStep[];
  player: V6StoryReport["identity"];
  history: V6StoryReport["metadata"];
  heroes: V6HeroPortfolio;
  pool: StoryFamilyModel;
  transfer: StoryFamilyModel;
  postLoss: StoryFamilyModel;
  combat: StoryFamilyModel;
  session: StoryFamilyModel;
  elements: V6Element[];
  identity: V6StoryReport["identity_summary"];
  outcomes: V6Finding[];
  share: V6ShareCandidate[];
  supportingEvidence?: Record<string, Record<string, unknown> | undefined>;
};

export function createStoryModel(report: V6StoryReport): StoryModel {
  const beats = reportBeats(report);
  const supportingEvidence = "supporting_evidence" in report
    ? report.supporting_evidence as Record<string, Record<string, unknown> | undefined>
    : undefined;
  const family = (name: keyof typeof FAMILY_KEYS, evidenceKey?: string): StoryFamilyModel => ({
    finding: findFamily(report.findings, name),
    evidence: evidenceKey ? supportingEvidence?.[evidenceKey] : undefined,
  });

  return {
    report,
    beats,
    sequence: buildStorySequence(report, beats),
    player: report.identity,
    history: report.metadata,
    heroes: report.hero_portfolio,
    pool: family("pool", "portfolio_shape"),
    transfer: family("transfer", "transfer_frontier"),
    postLoss: family("postLoss", "result_response"),
    combat: family("combat", "consistency"),
    session: family("session", "session_curve"),
    elements: report.elements,
    identity: report.identity_summary,
    outcomes: report.findings,
    share: report.share_candidates,
    supportingEvidence,
  };
}

const FAMILY_KEYS = {
  pool: new Set(["pool_shape"]),
  transfer: new Set(["transfer"]),
  postLoss: new Set(["post_loss", "post_loss_response"]),
  combat: new Set(["combat", "combat_expression"]),
  session: new Set(["session", "session_drift"]),
} as const;

function findFamily(findings: V6Finding[], family: keyof typeof FAMILY_KEYS): V6Finding | null {
  return findings.find((finding) => FAMILY_KEYS[family].has(finding.family.trim().toLowerCase() as never)) ?? null;
}

export function chapterForStep(step: StoryStep): StoryChapter {
  return step.chapter;
}
