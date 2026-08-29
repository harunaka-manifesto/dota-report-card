/**
 * Presentation-only formatting.  Nothing here derives an analytical value:
 * durations arrive pre-formatted as `formatted_duration`, hours arrive as
 * `display_value` + `display_unit`, and dates arrive as ISO calendar days.
 */

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})/;

/**
 * Formats a supplied ISO calendar day.  Day boundaries are a frozen UTC
 * convention upstream, so the display is pinned to UTC as well — the UI must
 * never imply a player-local "your Saturday".
 */
export function formatStoryDate(value: string | null | undefined): string {
  const match = typeof value === "string" ? DATE_ONLY.exec(value) : null;
  if (!match) return "";
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

/** Short form for tick labels and era captions. */
export function formatStoryMonth(value: string | null | undefined): string {
  const match = typeof value === "string" ? DATE_ONLY.exec(value) : null;
  if (!match) return "";
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "short" }).format(date);
}

/**
 * Renders a supplied period identifier for prose.  A `YYYY-MM` calendar-month
 * id becomes its month name; anything else is passed through untouched, since
 * the producer owns the label.
 */
export function formatPeriodLabel(value: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(value);
  if (!match) return value;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1));
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "long", year: "numeric" }).format(date);
}

/** Groups digits for legibility.  Tabular figures are applied in CSS. */
export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

/**
 * Renders the supplied duration display pair.  Whole values print without a
 * decimal; the producer already chose the unit and the rounding.
 */
export function formatDisplayValue(value: number): string {
  return Number.isInteger(value) ? formatCount(value) : String(value);
}

/** Rounds a supplied share for display only.  The share itself is supplied. */
export function formatShare(share: number): string {
  return `${Math.round(share * 100)}%`;
}

export function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural;
}
