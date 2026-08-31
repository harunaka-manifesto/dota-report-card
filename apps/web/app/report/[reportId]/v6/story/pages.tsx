"use client";

/**
 * Page renderers for the thirty-three renderable slots.
 *
 * Rules that hold on every page:
 *  - exactly one `h1`, always beat 0, so navigation focus lands on a real
 *    heading in reading order;
 *  - editorial copy comes from `copy.ts`, never from runtime inference;
 *  - supplied formatted values are rendered as supplied — `formatted_duration`,
 *    `display_value` + `display_unit` — never reformatted from seconds;
 *  - a page without an evidence-gated close ends on the Endstop.
 *
 * Page 25 has no renderer.  It is not reachable, not omitted-with-a-message,
 * and not represented in this file at all.
 */

import type { RefObject } from "react";
import { ArchetypeCard } from "./archetype-card";
import { buildCollageCards, collageSpans } from "./collage";
import { CANONICAL_ELEMENT_KEYS, type ComposedStory, type RenderedPage } from "./compose";
import { COPY, transferClosingLine } from "./copy";
import { formatCount, formatDisplayValue, formatPeriodLabel, formatShare, formatStoryDate } from "./format";
import { HeroEras } from "./hero-eras";
import type { StoryCombatData, StoryFindingContent } from "./payload-types";
import { ShareControl } from "./share";
import {
  Beat,
  ConcealedReveal,
  DominantFact,
  DominantSentence,
  Endstop,
  InlineEvidence,
  OrderedStack,
  Sequence,
  SignalField,
  useBeatPlan,
} from "./story-runtime";
import styles from "./story.module.css";

export type PageProps = {
  story: ComposedStory;
  page: RenderedPage;
  headingRef: RefObject<HTMLHeadingElement>;
  reducedMotion: boolean;
  archetypeRevealed: boolean;
  onRevealArchetype: () => void;
  poolRevealed: boolean;
  onRevealPool: () => void;
  onRunItBack: () => void;
  evidenceOpen: boolean;
  onToggleEvidence: () => void;
  onShared: () => void;
  onCopied: () => void;
  onShareFailed: () => void;
};

export function StoryPageView(props: PageProps) {
  switch (props.page.page) {
    case 1: return <Page1 {...props} />;
    case 2: return <Page2 {...props} />;
    case 3: return <Page3 {...props} />;
    case 4: return <Page4 {...props} />;
    case 5: return <Page5 {...props} />;
    case 6: return <Page6 {...props} />;
    case 7: return <Page7 {...props} />;
    case 8: return <Page8 {...props} />;
    case 9: return <Page9 {...props} />;
    case 10: return <Page10 {...props} />;
    case 11: return <Page11 {...props} />;
    case 12: return <Page12 {...props} />;
    case 13: return <Page13 {...props} />;
    case 14: return <Page14 {...props} />;
    case 15: return <FindingPage {...props} slot="post_loss" />;
    case 16: return <Page16 {...props} />;
    case 17: return <Page17 {...props} />;
    case 18: return <Page18 {...props} />;
    case 19: return <Page19 {...props} />;
    case 20: return <Page20 {...props} />;
    case 21: return <FindingPage {...props} slot="transfer" />;
    case 22: return <CombatPage {...props} module="kills" />;
    case 23: return <CombatPage {...props} module="assists" />;
    case 24: return <CombatPage {...props} module="deaths" />;
    case 26: return <Page26 {...props} />;
    case 27: return <Page27 {...props} />;
    case 29: return <Page29 {...props} />;
    case 30: return <Page30 {...props} />;
    case 32: return <Page32 {...props} />;
    case 33: return <Page33 {...props} />;
    case 34: return <Page34 {...props} />;
    default: return null;
  }
}

/** A page's optional close, plus the Endstop that replaces it when silent. */
function Close({ index, line, dry }: { index: number; line: string | null; dry: boolean }) {
  if (dry && line) {
    return (
      <Beat index={index} className={styles.dryLine} as="p">
        {line}
      </Beat>
    );
  }
  return <Endstop index={index} />;
}

function Page1({ story, headingRef }: PageProps) {
  const data = story.payload.modules.hello.data;
  useBeatPlan({ total: 4 });
  const name = data?.display_name?.trim();
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.display} ref={headingRef} tabIndex={-1}>
          {name ? COPY.page1.greetingNamed(name) : COPY.page1.greetingAnonymous}
        </h1>
      </Beat>
      <Beat index={1} className={styles.lead} as="p">
        {data?.history_materially_short ? COPY.page1.scopeShort : COPY.page1.scopeFull}
      </Beat>
      <Beat index={2} className={styles.support} as="p">
        {COPY.page1.promise}
      </Beat>
      <Endstop index={3} />
    </>
  );
}

function Page2({ story, headingRef }: PageProps) {
  const data = story.payload.modules.match_count.data;
  useBeatPlan({ total: 3, holdAfter: 0 });
  if (!data) return null;
  return (
    <>
      <DominantFact
        index={0}
        headingRef={headingRef}
        value={data.match_count === 1 ? "1" : formatCount(data.match_count)}
        unit={data.match_count === 1 ? "match." : "matches."}
      />
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page2.support}
      </Beat>
      <Endstop index={2} />
    </>
  );
}

function Page3({ story, headingRef }: PageProps) {
  const data = story.payload.modules.hours_in_matches.data;
  useBeatPlan({ total: 3, holdAfter: 0 });
  if (!data || data.display_value === null || data.display_value === undefined || !data.display_unit) return null;
  return (
    <>
      <DominantFact
        index={0}
        headingRef={headingRef}
        value={formatDisplayValue(data.display_value)}
        unit={`${data.display_unit}.`}
      />
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page3.support}
      </Beat>
      <Endstop index={2} />
    </>
  );
}

function Page4({ story, headingRef }: PageProps) {
  const data = story.payload.modules.rank_points.data;
  useBeatPlan({ total: 4, holdAfter: 0 });
  if (!data) return null;
  const points = formatCount(data.points_absolute);
  /* Flat monochrome delivery for positive, negative, and zero alike.
     `points_absolute` is `ge=0`: there is no minus sign to lay out. */
  const parts =
    data.direction === "positive"
      ? COPY.page4.positive(points)
      : data.direction === "negative"
        ? COPY.page4.negative(points)
        : null;
  return (
    <>
      {parts ? (
        <DominantSentence index={0} parts={parts} headingRef={headingRef} />
      ) : (
        <Beat index={0}>
          <h1 className={styles.dominantSentence} ref={headingRef} tabIndex={-1}>
            {COPY.page4.zero}
          </h1>
        </Beat>
      )}
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page4.scope(formatCount(data.ranked_matches))}
      </Beat>
      <Beat index={2} className={styles.support} as="p">
        {COPY.page4.split(formatCount(data.ranked_wins), formatCount(data.ranked_losses))}
      </Beat>
      <Endstop index={3} />
    </>
  );
}

function Page5({ story, headingRef }: PageProps) {
  const data = story.payload.modules.busiest_week.data;
  const variant = story.payload.modules.busiest_week.copy_variant;
  useBeatPlan({ total: 4 });
  if (!data) return null;
  const matches = formatCount(data.match_count);
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page5.question}
        </h1>
      </Beat>
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page5.range(formatStoryDate(data.date_start), formatStoryDate(data.date_end))}
      </Beat>
      <Beat index={2} className={styles.support} as="p">
        {variant === "hours" && data.display_value !== null && data.display_value !== undefined && data.display_unit
          ? COPY.page5.withHours(matches, formatDisplayValue(data.display_value), data.display_unit)
          : COPY.page5.matchesOnly(matches)}
      </Beat>
      <Endstop index={3} />
    </>
  );
}

function Page6({ story, headingRef }: PageProps) {
  const data = story.payload.modules.busiest_day.data;
  const variant = story.payload.modules.busiest_day.copy_variant;
  useBeatPlan({ total: 4 });
  if (!data) return null;
  const matches = formatCount(data.match_count);
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {data.inside_busiest_week ? COPY.page6.leadInside : COPY.page6.leadOutside}
        </h1>
      </Beat>
      <Beat index={1} className={styles.lead} as="p">
        {formatStoryDate(data.date)}.
      </Beat>
      <Beat index={2} className={styles.support} as="p">
        {variant === "hours" && data.display_value !== null && data.display_value !== undefined && data.display_unit
          ? COPY.page6.withHours(matches, formatDisplayValue(data.display_value), data.display_unit)
          : COPY.page6.matchesOnly(matches)}
      </Beat>
      <Endstop index={3} />
    </>
  );
}

function Page7({ story, page, headingRef }: PageProps) {
  const data = story.payload.modules.longest_match.data;
  const dry = page.closesWithDryLine;
  useBeatPlan({ total: 5, holdAfter: 1 });
  if (!data) return null;
  const detail =
    typeof data.kills === "number" && typeof data.deaths === "number" && typeof data.assists === "number"
      ? COPY.page7.detail(data.kills, data.deaths, data.assists)
      : null;
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page7.question}
        </h1>
      </Beat>
      {/* `formatted_duration` is supplied.  Never format from seconds. */}
      <DominantFact index={1} value={data.formatted_duration} heading={false} />
      <Beat index={2} className={styles.lead} as="p">
        {COPY.page7.match(data.hero_name, formatStoryDate(data.date))}
        {detail ? <span className={styles.support}> {detail}</span> : null}
      </Beat>
      <Beat index={3} className={styles.support} as="p">
        {data.outcome === "win" ? COPY.page7.win : COPY.page7.loss}
      </Beat>
      <Close index={4} line={COPY.page7.dry} dry={dry} />
    </>
  );
}

function Page8({ story, headingRef }: PageProps) {
  const zero = story.payload.modules.wins_bridge.copy_variant === "zero";
  useBeatPlan({ total: 2 });
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {zero ? COPY.page8.leadZero : COPY.page8.leadWins}
        </h1>
      </Beat>
      <Endstop index={1} />
    </>
  );
}

function Page9({ story, headingRef }: PageProps) {
  const data = story.payload.modules.win_summary.data;
  const variant = story.payload.modules.win_summary.copy_variant;
  const hasDay = Boolean(data?.winningest_day);
  useBeatPlan({ total: variant === "zero" ? 2 : hasDay ? 4 : 3, holdAfter: variant === "zero" ? undefined : 0 });
  if (!data) return null;
  if (variant === "zero") {
    return (
      <>
        <Beat index={0}>
          <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
            {COPY.page9.zero}
          </h1>
        </Beat>
        <Endstop index={1} />
      </>
    );
  }
  return (
    <>
      <DominantFact
        index={0}
        headingRef={headingRef}
        value={data.wins === 1 ? "1" : formatCount(data.wins)}
        unit={data.wins === 1 ? "win." : "wins."}
      />
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page9.support(formatCount(story.payload.universe.match_count))}
      </Beat>
      {data.winningest_day ? (
        <Beat index={2} className={styles.support} as="p">
          {COPY.page9.winningestDay(
            formatStoryDate(data.winningest_day.date),
            formatCount(data.winningest_day.daily_wins),
          )}
        </Beat>
      ) : null}
      <Endstop index={hasDay ? 3 : 2} />
    </>
  );
}

function Page10({ story, page, headingRef }: PageProps) {
  const data = story.payload.modules.winning_streak.data;
  const single = story.payload.modules.winning_streak.copy_variant === "single_win";
  const dry = page.closesWithDryLine;
  useBeatPlan({ total: single ? 3 : 5, holdAfter: single ? undefined : 2 });
  if (!data) return null;
  if (single) {
    return (
      <>
        <Beat index={0}>
          <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
            {COPY.page10.singleLead}
          </h1>
        </Beat>
        <Beat index={1} className={styles.lead} as="p">
          {COPY.page10.singleHeadline}
        </Beat>
        <Endstop index={2} />
      </>
    );
  }
  const length = formatCount(data.length);
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page10.lead}
        </h1>
      </Beat>
      <Sequence
        index={1}
        label={`${length} consecutive wins`}
        blocks={Array.from({ length: Math.min(data.length, 24) }, (_item, position) => ({
          key: `win-${position}`,
          tone: "win" as const,
        }))}
      />
      <DominantFact index={2} value={length} unit="wins in a row." heading={false} />
      <Beat index={3} className={styles.support} as="p">
        {COPY.page10.range(formatStoryDate(data.start_date), formatStoryDate(data.end_date))}
      </Beat>
      <Close index={4} line={COPY.page10.dry(length)} dry={dry} />
    </>
  );
}

function Page11({ story, headingRef }: PageProps) {
  const rows = story.payload.modules.top_win_heroes.data?.rows ?? [];
  useBeatPlan({ total: 3 });
  if (rows.length === 0) return null;
  const headline =
    rows.length >= 3 ? COPY.page11.headlineThree : rows.length === 1 ? COPY.page11.headlineOne : COPY.page11.headlineFew;
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {headline}
        </h1>
      </Beat>
      <OrderedStack
        index={1}
        label="Heroes with the most wins"
        rows={rows.map((row) => ({
          key: `win-hero-${row.hero_id}`,
          ordinal: row.rank,
          name: row.hero_name,
          detail: `${formatCount(row.wins)} ${row.wins === 1 ? "win" : "wins"} · ${formatCount(row.matches)} ${row.matches === 1 ? "match" : "matches"}`,
        }))}
      />
      <Endstop index={2} />
    </>
  );
}

function Page12({ story, page, headingRef }: PageProps) {
  const data = story.payload.modules.losing_streak.data;
  const dry = page.closesWithDryLine;
  const single = data?.length === 1;
  const length = data?.length ?? 0;
  const microcopy = single
    ? []
    : [
        // Tied to the second and third revealed loss block.
        ...COPY.page12.microcopy.positional.slice(0, Math.max(0, Math.min(2, length - 1))),
        // Frozen minimum streak, not a frontend threshold.
        ...(length >= COPY.page12.microcopy.longMinimumLength ? [COPY.page12.microcopy.long] : []),
      ];
  const breakerBeats = data?.terminal_state === "broken_by_win" && data?.breaker ? 1 : 0;
  useBeatPlan({
    total: single ? 3 : microcopy.length + 6 + breakerBeats,
    holdAfter: single ? undefined : 2 + microcopy.length,
  });
  if (!data) return null;

  if (single) {
    return (
      <>
        <Beat index={0}>
          <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
            {COPY.page12.singleLead}
          </h1>
        </Beat>
        <Beat index={1} className={styles.lead} as="p">
          {COPY.page12.singleHeadline}
        </Beat>
        <Endstop index={2} />
      </>
    );
  }

  const displayLength = formatCount(data.length);
  const countIndex = 2 + microcopy.length;
  const rangeIndex = countIndex + 1;
  const terminalIndex = rangeIndex + 1;
  // The hero that ended the slide is the most loaded name in the payload.
  // It gets its own beat instead of sharing a sentence with the count.
  const breakerIndex = terminalIndex + 1;
  const hasBreaker = data.terminal_state === "broken_by_win" && Boolean(data.breaker);
  const closeIndex = hasBreaker ? breakerIndex + 1 : terminalIndex + 1;
  const blocks = Array.from({ length: Math.min(data.length, 24) }, (_item, position) => ({
    key: `loss-${position}`,
    tone: "loss" as const,
  }));
  if (data.terminal_state === "broken_by_win") blocks.push({ key: "breaker", tone: "highlight" as never });

  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page12.lead}
        </h1>
      </Beat>
      <Sequence index={1} label={`${displayLength} consecutive losses`} blocks={blocks} />
      {microcopy.map((line, position) => (
        <Beat key={line} index={2 + position} className={styles.microcopy} as="p">
          {line}
        </Beat>
      ))}
      <Beat index={countIndex} className={styles.dominant}>
        <p className={styles.dominantSentence}>
          {COPY.page12.headline(displayLength)[0]}
          <span className={styles.dominantValue}>{COPY.page12.headline(displayLength)[1]}</span>
          {COPY.page12.headline(displayLength)[2]}
        </p>
      </Beat>
      <Beat index={rangeIndex} className={styles.support} as="p">
        {COPY.page12.range(formatStoryDate(data.start_date), formatStoryDate(data.end_date))}
      </Beat>
      <Beat index={terminalIndex} className={styles.lead} as="p">
        {hasBreaker
          ? COPY.page12.brokenLead
          : data.terminal_state === "observation_ended"
            ? COPY.page12.observationEnded
            : COPY.page12.historyBoundary}
      </Beat>
      {hasBreaker && data.breaker ? (
        <Beat index={breakerIndex} className={styles.breaker}>
          <p className={styles.breakerName}>{data.breaker.hero_name}</p>
          {typeof data.breaker.kills === "number" &&
          typeof data.breaker.deaths === "number" &&
          typeof data.breaker.assists === "number" ? (
            <p className={styles.breakerLine}>
              {COPY.page7.detail(data.breaker.kills, data.breaker.deaths, data.breaker.assists)}
              {" · "}
              {formatStoryDate(data.breaker.date)}
            </p>
          ) : (
            <p className={styles.breakerLine}>{formatStoryDate(data.breaker.date)}</p>
          )}
        </Beat>
      ) : null}
      <Close
        index={closeIndex}
        line={data.breaker ? COPY.page12.brokenDry(data.breaker.hero_name) : null}
        dry={dry && Boolean(data.breaker)}
      />
    </>
  );
}

function Page13({ story, headingRef }: PageProps) {
  const data = story.payload.modules.top_loss_heroes.data;
  const breaker = story.payload.modules.losing_streak.data?.breaker ?? null;
  const rows = data?.rows ?? [];
  const hasBreakerLead = Boolean(data?.breaker_exists && breaker);
  const hasRoughest = Boolean(data?.roughest_day);
  const base = hasBreakerLead ? 3 : 2;
  useBeatPlan({ total: base + 2 + (hasRoughest ? 1 : 0) });
  if (!data || rows.length === 0) return null;

  const secondIndex = hasBreakerLead ? 1 : 0;
  const rowsHeadlineIndex = hasBreakerLead ? 2 : 1;
  const rowsIndex = rowsHeadlineIndex + 1;
  const roughestIndex = rowsIndex + 1;
  const closeIndex = hasRoughest ? roughestIndex + 1 : roughestIndex;
  const rowsHeadline =
    rows.length >= 3 ? COPY.page13.headlineThree : rows.length === 1 ? COPY.page13.headlineOne : COPY.page13.headlineFew;

  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {hasBreakerLead && breaker ? COPY.page13.breakerLead(breaker.hero_name) : COPY.page13.neutralLead}
        </h1>
      </Beat>
      {hasBreakerLead ? (
        <Beat index={secondIndex} className={styles.lead} as="p">
          {COPY.page13.breakerSecond}
        </Beat>
      ) : null}
      <Beat index={rowsHeadlineIndex} className={styles.lead} as="p">
        {rowsHeadline}
      </Beat>
      <OrderedStack
        index={rowsIndex}
        label="Heroes present for the most losses"
        rows={rows.map((row) => ({
          key: `loss-hero-${row.hero_id}`,
          ordinal: row.rank,
          name: row.hero_name,
          detail: `${formatCount(row.losses)} ${row.losses === 1 ? "loss" : "losses"} · ${formatCount(row.matches)} ${row.matches === 1 ? "match" : "matches"}`,
        }))}
      />
      {data.roughest_day ? (
        <Beat index={roughestIndex} className={styles.support} as="p">
          {COPY.page13.roughestDay(
            formatStoryDate(data.roughest_day.date),
            formatCount(data.roughest_day.daily_losses),
          )}
        </Beat>
      ) : null}
      <Endstop index={closeIndex} />
    </>
  );
}

function Page14({ headingRef }: PageProps) {
  useBeatPlan({ total: 3 });
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page14.lead}
        </h1>
      </Beat>
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page14.second}
      </Beat>
      <Endstop index={2} />
    </>
  );
}

/** Pages 15 and 21 share evidence plumbing but use different reveal order. */
function FindingPage({
  story,
  page,
  headingRef,
  evidenceOpen,
  onToggleEvidence,
  slot,
}: PageProps & { slot: "post_loss" | "transfer" }) {
  const content = story.payload.finding_slots[slot].content ?? null;
  const dry = page.closesWithDryLine;
  const sample = slot === "post_loss" && typeof content?.comparable_opportunities === "number";
  useBeatPlan({ total: 4 + (sample ? 1 : 0) });
  if (!content?.claim || !content.interpretation) return null;
  const interpretationIndex = sample ? 3 : 2;
  const sampleIndex = 2;
  const closeIndex = sample ? 4 : 3;
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {slot === "post_loss" ? COPY.page15.question : COPY.page21.question}
        </h1>
      </Beat>
      <Beat index={1} className={styles.findingClaim} as="p">
        {content.claim}
      </Beat>
      {sample ? (
        <Beat index={sampleIndex} className={styles.support} as="p">
          {COPY.page15.sample(formatCount(content.comparable_opportunities as number))}
        </Beat>
      ) : null}
      <Beat index={interpretationIndex} className={styles.lead} as="p">
        {content.interpretation}
      </Beat>
      {content.claim_contract?.evidence || content.claim_contract?.alternatives?.length ? (
        <FindingEvidence
          id={`finding-${slot}`}
          content={content}
          open={evidenceOpen}
          onToggle={onToggleEvidence}
        />
      ) : null}
      <Close
        index={closeIndex}
        line={slot === "transfer" ? transferClosingLine(content.semantic_outcome_key) : null}
        dry={dry && slot === "transfer"}
      />
    </>
  );
}

function FindingEvidence({
  id,
  content,
  open,
  onToggle,
}: {
  id: string;
  content: StoryFindingContent;
  open: boolean;
  onToggle: () => void;
}) {
  const contract = content.claim_contract;
  const rows: string[] = [];
  if (typeof content.comparable_opportunities === "number") {
    rows.push(`${formatCount(content.comparable_opportunities)} comparable opportunities`);
  }
  rows.push(`Confidence: ${content.confidence}`);
  return (
    <InlineEvidence
      id={id}
      open={open}
      onToggle={onToggle}
      headline={content.claim ?? ""}
      statement={contract?.evidence ?? null}
      rows={rows}
      alternatives={contract?.alternatives ?? []}
      limitations={[]}
    />
  );
}

function Page16({ story, headingRef }: PageProps) {
  const combined = story.heroBridgeCombined;
  useBeatPlan({ total: combined ? 2 : 3 });
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {combined ? COPY.page16.combined : COPY.page16.lead}
        </h1>
      </Beat>
      {combined ? null : (
        <Beat index={1} className={styles.lead} as="p">
          {COPY.page16.second}
        </Beat>
      )}
      <Endstop index={combined ? 1 : 2} />
    </>
  );
}

function Page17({ story, headingRef, poolRevealed, onRevealPool }: PageProps) {
  const data = story.payload.modules.hero_pool.data;
  const heroes = data?.heroes ?? [];
  // The supplied order is preserved; the list is only split for presentation
  // so the first name can be called before it resolves.
  const lead = heroes[0];
  const rest = heroes.slice(1);
  const guessable = heroes.length >= 3;
  useBeatPlan({ total: guessable ? 5 : 4 });
  if (!data || heroes.length === 0) return null;

  const row = (hero: (typeof heroes)[number]) => ({
    key: `pool-${hero.hero_id}`,
    ordinal: hero.rank,
    name: hero.hero_name,
    detail: `${formatCount(hero.matches)} ${hero.matches === 1 ? "match" : "matches"} · ${formatShare(hero.share)}`,
  });

  if (!guessable) {
    return (
      <>
        <Beat index={0}>
          <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
            {COPY.page17.headlineFew}
          </h1>
        </Beat>
        <OrderedStack index={1} label="Your most-played heroes" rows={heroes.map(row)} />
        <Beat index={2} className={styles.lead} as="p">
          {COPY.page17.share(formatShare(data.top_five_share))}
        </Beat>
        <Endstop index={3} />
      </>
    );
  }

  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page17.guessLead}
        </h1>
      </Beat>
      {/* Everyone below the top name lands first, so the gap is obvious. */}
      <OrderedStack index={1} label="The rest of your most-played heroes" rows={rest.map(row)} />
      <ConcealedReveal
        index={2}
        prompt={COPY.page17.guessPrompt}
        resolved={poolRevealed}
        onResolve={onRevealPool}
      >
        <span className={styles.concealOrdinal}>{lead.rank}</span>
        <span className={styles.concealName}>{lead.hero_name}</span>
        <span className={styles.concealDetail}>
          {formatCount(lead.matches)} {lead.matches === 1 ? "match" : "matches"} · {formatShare(lead.share)}
        </span>
      </ConcealedReveal>
      <Beat index={3} className={styles.lead} as="p">
        {COPY.page17.share(formatShare(data.top_five_share))}
      </Beat>
      <Endstop index={4} />
    </>
  );
}

function Page18({ story, page, headingRef, reducedMotion }: PageProps) {
  const data = story.payload.modules.hero_eras.data;
  const sparse = story.payload.modules.hero_eras.copy_variant === "sparse_fallback" || data?.sparse_fallback === true;
  const dry = page.closesWithDryLine && !sparse;
  useBeatPlan({ total: sparse ? 3 : 4 });
  if (!data) return null;
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {sparse ? COPY.page18.sparseLead : COPY.page18.lead}
        </h1>
      </Beat>
      {sparse ? null : (
        <Beat index={1} className={styles.lead} as="p">
          {COPY.page18.prompt}
        </Beat>
      )}
      <Beat index={sparse ? 1 : 2}>
        <HeroEras data={data} reducedMotion={reducedMotion} />
      </Beat>
      <Close index={sparse ? 2 : 3} line={COPY.page18.dry} dry={dry} />
    </>
  );
}

function Page19({ story, page, headingRef }: PageProps) {
  const data = story.payload.modules.hero_era_payoff.data;
  const lines: string[] = [];
  if (data?.persistence) {
    lines.push(COPY.page19.persistence(data.persistence.hero.hero_name, formatCount(data.persistence.top_five_periods)));
  }
  if (data?.takeover) lines.push(COPY.page19.takeover(data.takeover.hero.hero_name, formatPeriodLabel(data.takeover.period)));
  if (lines.length === 0 && data?.steady_pool) lines.push(COPY.page19.steady);
  useBeatPlan({ total: 2 + lines.length + (page.transitionLine ? 1 : 0) });
  if (!data || lines.length === 0) return null;
  const closeIndex = 1 + lines.length;
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page19.lead}
        </h1>
      </Beat>
      {lines.map((line, position) => (
        <Beat key={line} index={1 + position} className={styles.lead} as="p">
          {line}
        </Beat>
      ))}
      <Endstop index={closeIndex} />
      <TransitionLine index={closeIndex + 1} line={page.transitionLine} />
    </>
  );
}

/** Fixed transition copy carried by the page before an omitted chapter. */
function TransitionLine({ index, line }: { index: number; line: string | null }) {
  if (!line) return null;
  return (
    <Beat index={index} className={styles.transition} as="p">
      {line}
    </Beat>
  );
}

function Page20({ headingRef }: PageProps) {
  useBeatPlan({ total: 3 });
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page20.lead}
        </h1>
      </Beat>
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page20.second}
      </Beat>
      <Endstop index={2} />
    </>
  );
}

function CombatPage({
  story,
  headingRef,
  module,
}: PageProps & { module: "kills" | "assists" | "deaths" }) {
  const data: StoryCombatData | null | undefined = story.payload.modules[module].data;
  const copy = module === "kills" ? COPY.page22 : module === "assists" ? COPY.page23 : COPY.page24;
  const zero = data?.total === 0;
  const rows = data?.individuals ?? [];
  /*
   * The rows copy names the leading hero, and the producer now projects only
   * that hero's matches into `individuals`.  This check enforces the promise
   * rather than defending against it: a payload that broke it would put a
   * hero in the list that the sentence above never introduced.
   */
  const rowsMatchLeadingHero =
    Boolean(data?.leading_hero) && rows.every((row) => row.hero_id === data?.leading_hero?.hero_id);
  const hasRows = !zero && rows.length > 0 && rowsMatchLeadingHero;
  useBeatPlan({
    total: zero ? 2 : (data?.leading_hero ? 2 : 1) + (hasRows ? 2 : 0) + 1,
    holdAfter: zero ? undefined : 0,
  });
  if (!data) return null;

  if (zero) {
    return (
      <>
        <Beat index={0}>
          <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
            {copy.zero}
          </h1>
        </Beat>
        <Endstop index={1} />
      </>
    );
  }

  const leading = data.leading_hero;
  const rowsHeadlineIndex = leading ? 2 : 1;
  const rowsIndex = rowsHeadlineIndex + 1;
  const closeIndex = hasRows ? rowsIndex + 1 : rowsHeadlineIndex;
  const total = formatCount(data.total);

  return (
    <>
      <DominantSentence index={0} parts={copy.headline(total)} headingRef={headingRef} />
      {leading ? (
        <Beat index={1} className={styles.lead} as="p">
          {copy.leading(leading.hero_name, formatCount(leading.total))}
        </Beat>
      ) : null}
      {hasRows && leading ? (
        <>
          <Beat index={rowsHeadlineIndex} className={styles.support} as="p">
            {rows.length >= 3 ? copy.rowsThree(leading.hero_name) : copy.rowsFew(leading.hero_name)}
          </Beat>
          <OrderedStack
            index={rowsIndex}
            label={`Top ${module} games`}
            rows={rows.map((row) => ({
              key: `${module}-${row.rank}`,
              ordinal: row.rank,
              name: row.hero_name ?? "",
              detail: [
                typeof row.stat_value === "number" ? formatCount(row.stat_value) : null,
                row.date ? formatStoryDate(row.date) : null,
                row.outcome === "win" ? "Win" : row.outcome === "loss" ? "Loss" : null,
              ]
                .filter(Boolean)
                .join(" · "),
            }))}
          />
        </>
      ) : null}
      <Endstop index={closeIndex} />
    </>
  );
}

function Page26({ headingRef }: PageProps) {
  useBeatPlan({ total: 3 });
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page26.lead}
        </h1>
      </Beat>
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page26.second}
      </Beat>
      <Endstop index={2} />
    </>
  );
}

function Page27({ story, headingRef }: PageProps) {
  useBeatPlan({ total: 4 });
  const byKey = new Map(story.elements.map((element) => [element.key, element]));
  const channels = CANONICAL_ELEMENT_KEYS.map((key) => {
    const element = byKey.get(key);
    const zone = typeof element?.zone === "string" && element.zone.trim() ? element.zone : null;
    return {
      key,
      label: element?.label ?? "",
      // An Element that could not be computed is identified in Evidence, never
      // given a fabricated neutral score.
      measured: Boolean(element && ["available", "descriptive", "limited"].includes(String(element.status ?? ""))),
      zone,
    };
  }).filter((channel) => channel.label.length > 0);
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page27.headline}
        </h1>
      </Beat>
      <SignalField index={1} channels={channels} />
      <Beat index={2} className={styles.lead} as="p">
        {COPY.page27.support(channels.length)}
      </Beat>
      <Endstop index={3} />
    </>
  );
}

function Page29({ story, headingRef, archetypeRevealed, onRevealArchetype, reducedMotion }: PageProps) {
  const lines = story.recapLines;
  useBeatPlan({ total: lines.length + 2 });
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {lines[0] ?? COPY.page29.close}
        </h1>
      </Beat>
      {lines.slice(1).map((line, position) => (
        <Beat key={line} index={1 + position} className={styles.recapLine} as="p">
          {line}
        </Beat>
      ))}
      <Beat index={lines.length} className={styles.lead} as="p">
        {COPY.page29.close}
      </Beat>
      {/* The card settles into view here so Page 30 opens on an object the
          reader has already watched arrive. */}
      <Beat index={lines.length + 1} className={styles.cardPreview}>
        <ArchetypeCard
          title={story.shape?.title ?? COPY.page30.neutralTitle}
          description={story.shape?.line ?? COPY.page30.neutralLine}
          revealed={archetypeRevealed}
          onReveal={onRevealArchetype}
          reducedMotion={reducedMotion}
          scale="token"
          heading={false}
        />
      </Beat>
    </>
  );
}

function Page30({ story, headingRef, archetypeRevealed, onRevealArchetype, reducedMotion }: PageProps) {
  useBeatPlan({ total: 2, identityHoldAfter: 0 });
  return (
    <>
      <Beat index={0}>
        <ArchetypeCard
          title={story.shape?.title ?? COPY.page30.neutralTitle}
          description={story.shape?.line ?? COPY.page30.neutralLine}
          revealed={archetypeRevealed}
          onReveal={onRevealArchetype}
          reducedMotion={reducedMotion}
          headingRef={headingRef}
          canTurn
        />
      </Beat>
      {/* Page 30 always closes without a dry line. */}
      <Endstop index={1} />
    </>
  );
}

function Page32({ story, headingRef, reducedMotion }: PageProps) {
  const cards = buildCollageCards(
    story.payload,
    story.payload.modules.card_collage.data?.cards ?? [],
    new Set(story.pages.map((item) => item.page)),
  );
  useBeatPlan({ total: 3 });
  return (
    <>
      <Beat index={0} className={styles.collage} as="ul">
        {cards.map((card, position) => {
          const spans = collageSpans(position, cards.length);
          return (
            <li
              key={card.id}
              className={styles.collageCard}
              data-module={card.module}
              style={{
                ["--span-narrow" as string]: spans.narrow,
                ["--span-wide" as string]: spans.wide,
                ...(reducedMotion ? {} : { transitionDelay: `${collageDelay(position)}ms` }),
              }}
            >
              <span className={styles.collageLabel}>{card.label}</span>
              <span className={styles.collageValue}>{card.value}</span>
              {card.detail ? <span className={styles.collageDetail}>{card.detail}</span> : null}
            </li>
          );
        })}
      </Beat>
      <Beat index={1}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page32.close}
        </h1>
      </Beat>
      <Endstop index={2} />
    </>
  );
}

/** Eight individual steps, then waves of four. */
function collageDelay(position: number): number {
  return position < 8 ? position * 90 : (8 + Math.floor((position - 8) / 4)) * 90;
}

function Page33({
  story,
  headingRef,
  archetypeRevealed,
  onRevealArchetype,
  reducedMotion,
  onRunItBack,
  onShared,
  onCopied,
  onShareFailed,
}: PageProps) {
  const identity = story.finalIdentity;
  const name = identity?.displayName?.trim() || null;
  useBeatPlan({ total: name ? 5 : 4 });
  if (!identity) return null;
  const offset = name ? 1 : 0;
  return (
    <>
      <div className={styles.finalCard}>
        {name ? (
          <Beat index={0}>
            <h1 className={styles.cardName} ref={headingRef} tabIndex={-1}>
              {name}
            </h1>
          </Beat>
        ) : null}
        <Beat index={offset}>
          <ArchetypeCard
            title={story.shape?.title ?? COPY.page30.neutralTitle}
            description={story.shape?.line ?? COPY.page30.neutralLine}
            revealed={archetypeRevealed}
            onReveal={onRevealArchetype}
            reducedMotion={reducedMotion}
            scale="compact"
            heading={!name}
            headingRef={name ? undefined : headingRef}
            alwaysFaceUp
          />
        </Beat>
        <Beat index={offset + 1} className={styles.lead} as="p">
          {COPY.page33.matches(formatCount(identity.storyMatchCount))}
        </Beat>
        <Beat index={offset + 2} className={styles.support} as="p">
          {COPY.page33.lookback(
            formatCount(identity.lookbackDays),
            story.payload.universe.history_completeness === "complete" &&
              story.payload.modules.hello.data?.history_materially_short !== true,
          )}
        </Beat>
      </div>
      <Beat index={offset + 3} className={styles.finalActions}>
        <ShareControl onShared={onShared} onCopied={onCopied} onFailed={onShareFailed} />
        <button type="button" className={styles.textControl} onClick={onRunItBack}>
          {COPY.page33.runItBack}
        </button>
      </Beat>
    </>
  );
}

function Page34({ story, headingRef }: PageProps) {
  useBeatPlan({ total: 4 });
  // Composition already removed this page when there is no destination, so a
  // dead CTA cannot reach the reader.
  if (!story.deepDestination) return null;
  return (
    <>
      <Beat index={0}>
        <h1 className={styles.chapterType} ref={headingRef} tabIndex={-1}>
          {COPY.page34.lead}
        </h1>
      </Beat>
      <Beat index={1} className={styles.lead} as="p">
        {COPY.page34.second}
      </Beat>
      <Beat index={2}>
        <a className={styles.primaryControl} href={story.deepDestination}>
          {COPY.page34.cta}
        </a>
      </Beat>
      <Endstop index={3} />
    </>
  );
}
