import type { StoryModel } from "../../story-model";
import { PoolRing, type PoolHero, type PoolRingPhase } from "../../visualizations/pool-ring";
import styles from "./pool-shape-chapter.module.css";

export type PoolShapeData = {
  all: readonly PoolHero[];
  core: readonly PoolHero[];
  stretch: readonly PoolHero[];
  outer: readonly PoolHero[];
  summary?: string | null;
};

export type PoolShapePhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13;

export function createPoolShapeData(model: Pick<StoryModel, "heroes">): PoolShapeData {
  const all = (model.heroes.heroes ?? []).filter((hero) => Boolean(hero.display_name || hero.hero_name || hero.name)).map((hero, index) => {
    const band = poolBand(hero.band ?? hero.layer);
    return { id: String(hero.id ?? hero.hero_id ?? hero.display_name ?? hero.hero_name ?? hero.name ?? index), name: hero.display_name ?? hero.hero_name ?? hero.name ?? "Unknown hero", band, matchCount: hero.match_count, share: hero.share };
  });
  return {
    all,
    core: all.filter((hero) => hero.band === "core"),
    stretch: all.filter((hero) => hero.band === "stretch"),
    outer: all.filter((hero) => hero.band === "outer"),
  };
}

export function PoolShapeChapter({ data, phase = 0, onAdvance }: { data: PoolShapeData; phase?: PoolShapePhase; onAdvance?: () => void }) {
  const reveal = (at: PoolShapePhase) => phase === at;
  return (
    <section className={styles.chapter} data-phase={phase} aria-label="Pool shape">
      <div className={`${styles.state} ${reveal(0) ? styles.visible : ""}`} aria-hidden={!reveal(0)}><span className={styles.eyebrow}>All heroes</span><h1>A hero list is not a hero pool.</h1><p>We look for the part of the field that actually belongs to your Dota.</p></div>
      <div className={`${styles.state} ${reveal(1) ? styles.visible : ""}`} aria-hidden={!reveal(1)}><span className={styles.eyebrow}>Peripheral fade</span><h2>Some names sit farther from the center.</h2></div>
      <div className={`${styles.state} ${reveal(2) ? styles.visible : ""}`} aria-hidden={!reveal(2)}><span className={styles.eyebrow}>Effective pool</span><h2>The effective pool is the field we can read.</h2></div>
      <div className={`${styles.state} ${reveal(3) ? styles.visible : ""}`} aria-hidden={!reveal(3)}><span className={styles.eyebrow}>Concentration question</span><h2>How much of the pool does the core hold?</h2></div>
      <div className={`${styles.state} ${reveal(4) ? styles.visible : ""}`} aria-hidden={!reveal(4)}><span className={styles.eyebrow}>Weighting</span><p>Counts and shares keep the center of gravity visible.</p></div>
      <div className={`${styles.state} ${reveal(5) ? styles.visible : ""}`} aria-hidden={!reveal(5)}><span className={styles.eyebrow}>Top three share</span><h2>{topThreeShare(data.all)}</h2></div>
      <div className={`${styles.state} ${reveal(6) ? styles.visible : ""}`} aria-hidden={!reveal(6)}><span className={styles.eyebrow}>Core question</span><h2>What belongs in the center?</h2></div>
      <div className={`${styles.ringState} ${phase >= 7 && phase <= 10 ? styles.visible : ""}`} aria-hidden={phase < 7 || phase > 10}><PoolRing core={data.core} stretch={data.stretch} outer={data.outer} all={data.all} phase={Math.min(13, Math.max(0, phase)) as PoolRingPhase} /></div>
      <div className={`${styles.state} ${styles.summary} ${reveal(11) ? styles.visible : ""}`} aria-hidden={!reveal(11)}><span className={styles.eyebrow}>Full pool map</span><p>{data.summary || "The pool map keeps heroes and their distances visible without collapsing them into one score."}</p></div>
      <div className={`${styles.state} ${styles.summary} ${reveal(12) ? styles.visible : ""}`} aria-hidden={!reveal(12)}><span className={styles.eyebrow}>Human summary</span><p>{data.summary || "Your pool has a center, a stretch, and an outer edge where the distance becomes visible."}</p></div>
      <div className={`${styles.state} ${reveal(13) ? styles.visible : ""}`} aria-hidden={!reveal(13)}><span className={styles.eyebrow}>Transfer bridge</span><h2>Now we can ask what survives outside the center.</h2></div>
      {onAdvance && <button className={styles.advance} type="button" onClick={onAdvance}>Continue <span aria-hidden="true">→</span></button>}
    </section>
  );
}

function poolBand(value?: string | null): PoolHero["band"] {
  const normalized = value?.toLowerCase();
  if (normalized === "core") return "core";
  if (normalized === "stretch") return "stretch";
  if (normalized === "outer" || normalized === "tail") return "outer";
  return "unclassified";
}

function topThreeShare(heroes: readonly PoolHero[]): string {
  const shares = heroes.map((hero) => hero.share).filter((share): share is number => typeof share === "number").sort((a, b) => b - a).slice(0, 3);
  return shares.length === 0 ? "Top-three share is not available." : `The top three account for ${Math.round(shares.reduce((sum, share) => sum + share, 0) * 100)}% of the observed pool.`;
}
