import type { V6StoryBeat, V6StoryReport } from "../types";
import { LEGACY_BEAT_IDS, type LegacyBeatId } from "./story-navigation";

export type StoryChapter =
  | "arrival" | "heroes" | "pool-shape" | "transfer" | "post-loss"
  | "combat-expression" | "session-drift" | "synthesis" | "identity"
  | "premium" | "share";

export type StoryStep = {
  id: string;
  chapter: StoryChapter;
  phase: number;
  phaseCount: number;
  progressIndex: number;
  legacyBeatIndex: number;
  legacyBeatId: LegacyBeatId;
  beat?: V6StoryBeat;
  skippable: boolean;
};

type ChapterDefinition = { chapter: StoryChapter; count: number; progressIndex: number; legacyBeatIndex: number };

export const STORY_CHAPTERS: readonly ChapterDefinition[] = [
  { chapter: "arrival", count: 12, progressIndex: 0, legacyBeatIndex: 0 },
  { chapter: "heroes", count: 11, progressIndex: 1, legacyBeatIndex: 0 },
  { chapter: "pool-shape", count: 14, progressIndex: 2, legacyBeatIndex: 2 },
  { chapter: "transfer", count: 9, progressIndex: 3, legacyBeatIndex: 3 },
  { chapter: "post-loss", count: 9, progressIndex: 4, legacyBeatIndex: 4 },
  { chapter: "combat-expression", count: 10, progressIndex: 5, legacyBeatIndex: 5 },
  { chapter: "session-drift", count: 9, progressIndex: 6, legacyBeatIndex: 6 },
  { chapter: "synthesis", count: 7, progressIndex: 7, legacyBeatIndex: 7 },
  { chapter: "identity", count: 9, progressIndex: 8, legacyBeatIndex: 7 },
  { chapter: "premium", count: 4, progressIndex: 9, legacyBeatIndex: 8 },
  { chapter: "share", count: 9, progressIndex: 10, legacyBeatIndex: 8 },
];

const OPTIONAL_FAMILY_ALIASES: Record<StoryChapter, readonly string[] | null> = {
  arrival: null, heroes: null, "pool-shape": ["pool_shape"], transfer: ["transfer"],
  "post-loss": ["post_loss", "post_loss_response"], "combat-expression": ["combat", "combat_expression"], "session-drift": ["session", "session_drift"],
  synthesis: null, identity: null, premium: null, share: null,
};

/** Build the complete narrative while omitting only genuinely absent families. */
export function buildStorySequence(report: V6StoryReport, beats: V6StoryBeat[]): StoryStep[] {
  const result: StoryStep[] = [];
  for (const definition of STORY_CHAPTERS) {
    const familyAliases = OPTIONAL_FAMILY_ALIASES[definition.chapter];
    if (familyAliases && !hasFamily(report, familyAliases)) continue;
    const legacyBeatId = LEGACY_BEAT_IDS[definition.legacyBeatIndex];
    for (let phase = 0; phase < definition.count; phase += 1) {
      result.push({
        id: `${definition.chapter}.${phase}`,
        chapter: definition.chapter,
        phase,
        phaseCount: definition.count,
        progressIndex: shareProgress(definition.chapter, phase, definition.progressIndex),
        legacyBeatIndex: definition.legacyBeatIndex,
        legacyBeatId,
        beat: beats[definition.legacyBeatIndex],
        skippable: true,
      });
    }
  }
  return result;
}

function hasFamily(report: V6StoryReport, aliases: readonly string[]): boolean {
  return report.findings.some((finding) => aliases.includes(finding.family.toLowerCase()));
}

function shareProgress(chapter: StoryChapter, phase: number, fallback: number): number {
  if (chapter !== "share") return fallback;
  if (phase === 0) return 10;
  if (phase <= 2) return 11;
  if (phase <= 5) return 12;
  return 13;
}
