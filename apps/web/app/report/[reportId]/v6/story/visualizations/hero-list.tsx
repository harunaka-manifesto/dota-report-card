/* eslint-disable @next/next/no-img-element -- portrait URLs are server-owned report data. */

import styles from "./hero-list.module.css";

export type HeroListRow = {
  id: string;
  name: string;
  portraitUrl?: string | null;
  matchCount?: number | null;
  share?: number | null;
  result?: string | null;
  jobs?: readonly string[];
};

export type HeroListPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;

export function HeroList({ heroes, phase = 4 }: { heroes: readonly HeroListRow[]; phase?: HeroListPhase }) {
  const reveal = (at: HeroListPhase) => phase >= at;
  return (
    <ol className={styles.list} data-phase={phase} aria-label="Top heroes">
      {heroes.map((hero) => (
        <li className={styles.row} key={hero.id}>
          <HeroPortrait hero={hero} visible={reveal(5)} />
          <div className={styles.copy}>
            <strong className={reveal(6) ? styles.revealed : styles.hidden}>{hero.name}</strong>
            <span className={reveal(7) ? styles.revealed : styles.hidden}>{formatShare(hero.share, hero.matchCount)}</span>
            <small className={reveal(8) ? styles.revealed : styles.hidden}>{hero.result || "Result not available"}</small>
          </div>
          {reveal(8) && hero.jobs && hero.jobs.length > 0 && <span className={styles.jobs}>{hero.jobs.join(" · ")}</span>}
        </li>
      ))}
      {heroes.length === 0 && <li className={styles.empty}>No hero rows were supplied for this report.</li>}
    </ol>
  );
}

function HeroPortrait({ hero, visible }: { hero: HeroListRow; visible: boolean }) {
  return <span className={`${styles.portrait} ${visible ? styles.portraitVisible : ""}`}>{hero.portraitUrl ? <img src={hero.portraitUrl} alt={`${hero.name} portrait`} /> : <span aria-label={`${hero.name} portrait unavailable`}>{hero.name.slice(0, 2).toUpperCase()}</span>}</span>;
}

function formatShare(share?: number | null, matches?: number | null): string {
  const values = [typeof share === "number" ? `${Math.round(share * 100)}% of pool` : null, typeof matches === "number" ? `${matches} matches` : null].filter(Boolean);
  return values.join(" · ") || "Usage not available";
}
