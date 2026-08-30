"use client";

/**
 * Page 18 — Hero Eras.
 *
 * A styled native `<input type="range">` gives discrete snapping, pointer and
 * touch behaviour, and keyboard semantics with no dependency.  Ordering is
 * always the supplied `top_heroes` order; an empty period clears every row
 * before showing the contracted empty message.
 */

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { COPY } from "./copy";
import { formatCount, formatStoryMonth } from "./format";
import { initialHeroEraIndex } from "./hero-eras-selection";
import type { StoryHeroEra, StoryHeroErasData } from "./payload-types";
import styles from "./story.module.css";

export function HeroEras({ data, reducedMotion }: { data: StoryHeroErasData; reducedMotion: boolean }) {
  const periods = data.periods;
  const [index, setIndex] = useState(() => initialHeroEraIndex(periods));
  const controlId = useId();
  const statusRef = useRef<HTMLParagraphElement>(null);
  const period = periods[Math.min(index, periods.length - 1)];

  useEffect(() => {
    setIndex(initialHeroEraIndex(periods));
  }, [periods]);

  const label = useMemo(() => periodLabel(period), [period]);

  // Fewer than two valid periods cannot be navigated; the supplied static
  // sequence takes over rather than leaving a disabled thumb behind.
  if (data.sparse_fallback || periods.length < 2) {
    return <HeroEraSequence periods={periods} />;
  }

  return (
    <div className={styles.eras}>
      <div className={styles.eraControl}>
        <input
          id={controlId}
          className={styles.eraRange}
          type="range"
          min={0}
          max={periods.length - 1}
          step={1}
          value={index}
          aria-label={COPY.page18.control}
          aria-valuetext={label}
          onChange={(event) => setIndex(Number(event.currentTarget.value))}
          onKeyDown={(event) => {
            // Arrow and Page keys are native.  Home/End are not handled
            // consistently across engines for a range, so they are supplied
            // here to keep the contracted keyboard behaviour identical
            // everywhere.  Story navigation stays suppressed while focused.
            if (event.key !== "Home" && event.key !== "End") return;
            event.preventDefault();
            setIndex(event.key === "Home" ? 0 : periods.length - 1);
          }}
        />
        <ol className={styles.eraTicks} aria-hidden="true">
          {periods.map((item, position) => (
            <li key={item.id} className={styles.eraTick} data-active={position === index} data-empty={item.empty}>
              <span className={styles.eraTickMark} />
              <span className={styles.eraTickLabel}>{formatStoryMonth(item.date_start)}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className={styles.eraRows} data-reduced={reducedMotion}>
        {period.empty || period.top_heroes.length === 0 ? (
          <p className={styles.eraEmpty}>{COPY.page18.emptyPeriod}</p>
        ) : (
          <ol className={styles.stack}>
            {period.top_heroes.map((hero) => (
              <li key={`${period.id}-${hero.hero_id}`} className={styles.stackRow} data-revealed="true">
                <span className={styles.stackOrdinal}>{hero.rank}</span>
                <span className={styles.stackName}>{hero.hero_name}</span>
                <span className={styles.stackDetail}>
                  {formatCount(hero.matches)} {hero.matches === 1 ? "match" : "matches"}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>

      <p className={styles.visuallyHidden} role="status" aria-live="polite" ref={statusRef}>
        {period.empty
          ? `${label}. ${COPY.page18.emptyPeriod}`
          : `${label}. ${period.top_heroes.length} ${period.top_heroes.length === 1 ? "hero" : "heroes"}.`}
      </p>
    </div>
  );
}

/** The static sparse-volume fallback: no slider, no drag hint, no dead thumb. */
function HeroEraSequence({ periods }: { periods: readonly StoryHeroEra[] }) {
  return (
    <div className={styles.eraSequence}>
      {periods.map((period) => (
        <section key={period.id} className={styles.eraSequenceGroup}>
          <h2 className={styles.eraSequenceLabel}>{periodLabel(period)}</h2>
          {period.empty || period.top_heroes.length === 0 ? (
            <p className={styles.eraEmpty}>{COPY.page18.emptyPeriod}</p>
          ) : (
            <ol className={styles.stack}>
              {period.top_heroes.map((hero) => (
                <li key={`${period.id}-${hero.hero_id}`} className={styles.stackRow} data-revealed="true">
                  <span className={styles.stackOrdinal}>{hero.rank}</span>
                  <span className={styles.stackName}>{hero.hero_name}</span>
                  <span className={styles.stackDetail}>{formatCount(hero.matches)}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      ))}
    </div>
  );
}

function periodLabel(period: StoryHeroEra | undefined): string {
  if (!period) return "";
  const start = formatStoryMonth(period.date_start);
  const end = formatStoryMonth(period.date_end);
  return period.period_kind === "calendar_month" || start === end ? start : `${start} – ${end}`;
}

export { initialHeroEraIndex };
