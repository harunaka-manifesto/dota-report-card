/**
 * Entry point for a persisted V6.1 report.
 *
 * A report that carries `story_payload` renders the thirty-three-page story.
 * A historical report that omits it routes to the explicit legacy
 * compatibility path — old data is never silently reinterpreted through the
 * new composer.
 */

import LegacyStoryV61, { UnsupportedReport } from "./legacy-story-v61";
import { composeStory } from "./story/compose";
import { normalizeStoryPayload } from "./story/normalize-story";
import { StoryShell } from "./story/story-shell";
import { Methodology } from "./story/methodology";
import type { V61Report } from "./types";

type V61ReportWithStory = V61Report & { story_payload?: unknown };

export default function ReportStoryV6({ report }: { report: V61Report }) {
  const raw = (report as V61ReportWithStory).story_payload;
  const normalized = normalizeStoryPayload(raw);

  if (!normalized) {
    return <LegacyStoryV61 report={report} />;
  }

  const story = composeStory(normalized.payload, report.elements ?? [], normalized.diagnostics);
  if (story.pages.length === 0) {
    return <LegacyStoryV61 report={report} />;
  }

  return <StoryShell story={story} methodology={<Methodology report={report} story={story} />} />;
}

export { UnsupportedReport };
export { isFreeDnaReportV6, isFreeDnaReportV61 } from "./types";
export type { V6Report, V61Report, V6StoryReport } from "./types";
