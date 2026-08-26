"use client";

import { useMemo } from "react";
import StoryEngine from "./story/story-engine";
import { createStoryModel } from "./story/story-model";
import type { V6StoryReport } from "./types";

/** Route entry point. Data adaptation and interaction state live below this seam. */
export default function ReportStoryV6({ report }: { report: V6StoryReport }) {
  const storyModel = useMemo(() => createStoryModel(report), [report]);
  return <StoryEngine model={storyModel} />;
}

export { StoryEngine } from "./story/story-engine";
export { isFreeDnaReportV6, isFreeDnaReportV61 } from "./types";
export type { V6Report, V61Report, V6StoryReport } from "./types";
