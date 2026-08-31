/**
 * Page 32 collage content and geometry.
 *
 * Card membership comes from `card_manifest` mirrored onto
 * `card_collage.data.cards`; the values are read back from the modules those
 * cards reference.  Nothing is recomputed here — if a module was skipped
 * earlier, no card exists for it and none is invented.
 */

import { formatCount, formatDisplayValue, formatPeriodLabel, formatShare, formatStoryDate } from "./format";
import { STORY_MODULE_PAGES, type StoryCard, type StoryCardModuleKey, type StoryPayload } from "./payload-types";

export type CollageCard = {
  id: string;
  module: StoryCardModuleKey;
  label: string;
  value: string;
  detail: string | null;
};

const LABELS: Record<StoryCardModuleKey, string> = {
  hello: "The year",
  match_count: "Matches",
  hours_in_matches: "Time in matches",
  rank_points: "Rank points",
  busiest_week: "Biggest week",
  busiest_day: "Busiest day",
  longest_match: "Longest match",
  wins_bridge: "Wins",
  win_summary: "Wins",
  winning_streak: "Winning streak",
  top_win_heroes: "Most wins",
  losing_streak: "Losing streak",
  top_loss_heroes: "Most losses",
  post_loss: "After a loss",
  hero_pool: "Hero pool",
  hero_eras: "Hero eras",
  hero_era_payoff: "Era standout",
  transfer: "Outside the pool",
  kills: "Kills",
  assists: "Assists",
  deaths: "Deaths",
  element_distinctiveness: "Distinctive shape",
  archetype: "Archetype",
  card_collage: "Your year",
  final_identity_card: "Your Dota DNA",
  deep: "Deeper",
};

export function buildCollageCards(
  payload: StoryPayload,
  cards: StoryCard[],
  renderedPages: ReadonlySet<number>,
): CollageCard[] {
  return cards
    .filter((card) => renderedPages.has(STORY_MODULE_PAGES[card.module]))
    .map((card) => {
      const content = cardContent(payload, card.module);
      if (content === null) return null;
      return { id: card.id, module: card.module, label: LABELS[card.module], ...content };
    })
    .filter((card): card is CollageCard => card !== null);
}

function cardContent(
  payload: StoryPayload,
  module: StoryCardModuleKey,
): { value: string; detail: string | null } | null {
  const modules = payload.modules;
  switch (module) {
    case "hello":
      return { value: "365 days", detail: null };
    case "match_count": {
      const data = modules.match_count.data;
      return data ? { value: formatCount(data.match_count), detail: data.match_count === 1 ? "match" : "matches" } : null;
    }
    case "hours_in_matches": {
      const data = modules.hours_in_matches.data;
      if (!data || data.display_value === null || data.display_value === undefined || !data.display_unit) return null;
      return { value: formatDisplayValue(data.display_value), detail: data.display_unit };
    }
    case "rank_points": {
      const data = modules.rank_points.data;
      return data ? { value: formatCount(data.points_absolute), detail: "rank points" } : null;
    }
    case "busiest_week": {
      const data = modules.busiest_week.data;
      return data
        ? { value: formatCount(data.match_count), detail: `matches · ${formatStoryDate(data.date_start)}` }
        : null;
    }
    case "busiest_day": {
      const data = modules.busiest_day.data;
      return data ? { value: formatCount(data.match_count), detail: `matches · ${formatStoryDate(data.date)}` } : null;
    }
    case "longest_match": {
      const data = modules.longest_match.data;
      return data ? { value: data.formatted_duration, detail: data.hero_name } : null;
    }
    case "wins_bridge":
      // Page 8 shows no number, and this card would repeat the win summary
      // verbatim. A collage card recaps a moment the reader actually saw.
      return null;
    case "win_summary": {
      const data = modules.win_summary.data;
      return data ? { value: formatCount(data.wins), detail: data.wins === 1 ? "win" : "wins" } : null;
    }
    case "winning_streak": {
      const data = modules.winning_streak.data;
      return data ? { value: formatCount(data.length), detail: "in a row" } : null;
    }
    case "top_win_heroes": {
      const row = modules.top_win_heroes.data?.rows[0];
      return row ? { value: row.hero_name, detail: `${formatCount(row.wins)} wins` } : null;
    }
    case "losing_streak": {
      const data = modules.losing_streak.data;
      return data ? { value: formatCount(data.length), detail: "straight losses" } : null;
    }
    case "top_loss_heroes": {
      const row = modules.top_loss_heroes.data?.rows[0];
      return row ? { value: row.hero_name, detail: `${formatCount(row.losses)} losses` } : null;
    }
    case "hero_pool": {
      const data = modules.hero_pool.data;
      return data ? { value: formatShare(data.top_five_share), detail: "of your matches" } : null;
    }
    case "hero_eras": {
      const data = modules.hero_eras.data;
      return data ? { value: formatCount(data.periods.length), detail: "periods" } : null;
    }
    case "hero_era_payoff": {
      const data = modules.hero_era_payoff.data;
      if (data?.takeover)
        return { value: data.takeover.hero.hero_name, detail: formatPeriodLabel(data.takeover.period) };
      if (data?.persistence)
        return {
          value: data.persistence.hero.hero_name,
          detail: `${formatCount(data.persistence.top_five_periods)} periods`,
        };
      return data?.steady_pool ? { value: "Steady", detail: "top heroes" } : null;
    }
    case "kills":
    case "assists":
    case "deaths": {
      const data = modules[module].data;
      return data ? { value: formatCount(data.total), detail: module } : null;
    }
    case "post_loss": {
      const content = payload.finding_slots.post_loss.content;
      return content?.claim ? { value: content.claim, detail: null } : null;
    }
    case "transfer": {
      const content = payload.finding_slots.transfer.content;
      return content?.claim ? { value: content.claim, detail: null } : null;
    }
    default:
      return null;
  }
}

/**
 * Deterministic remainder rules that complete every row without masonry.
 * Phone/tablet run 4 tracks with a normal span of 2; desktop runs 6 tracks
 * with a normal span of 2, a last row of two spanning 3, and a lone last card
 * spanning the full 6.
 */
export function collageSpans(index: number, total: number): { narrow: number; wide: number } {
  const narrow = total % 2 === 1 && index === total - 1 ? 4 : 2;
  const wideRemainder = total % 3;
  let wide = 2;
  if (wideRemainder === 1 && index === total - 1) wide = 6;
  else if (wideRemainder === 2 && index >= total - 2) wide = 3;
  return { narrow, wide };
}
