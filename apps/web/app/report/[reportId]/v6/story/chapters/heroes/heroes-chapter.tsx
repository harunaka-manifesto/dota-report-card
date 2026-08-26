import type { StoryModel } from "../../story-model";
import { HeroList, type HeroListPhase, type HeroListRow } from "../../visualizations/hero-list";
import styles from "./heroes-chapter.module.css";

export type HeroesData = {
  question?: string | null;
  heroName?: string | null;
  portraitUrl?: string | null;
  interpretation?: string | null;
  heroes: readonly HeroListRow[];
};

export type HeroesPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;

export function createHeroesData(model: Pick<StoryModel, "heroes">): HeroesData {
  const rows = (model.heroes.heroes ?? []).filter((hero): hero is typeof hero & { display_name: string } => Boolean(hero.display_name || hero.hero_name || hero.name)).map((hero, index) => ({
    id: String(hero.id ?? hero.hero_id ?? hero.display_name ?? hero.hero_name ?? hero.name ?? index),
    name: hero.display_name ?? hero.hero_name ?? hero.name ?? "Unknown hero",
    matchCount: hero.match_count,
    share: hero.share,
    jobs: hero.functional_jobs ?? hero.jobs,
  }));
  const first = rows[0];
  return {
    question: model.heroes.prediction?.prompt,
    heroName: first?.name,
    heroes: rows.slice(0, 5),
    interpretation: model.heroes.prediction?.reveal,
  };
}

export function HeroesChapter({ data, phase = 0, onAdvance }: { data: HeroesData; phase?: HeroesPhase; onAdvance?: () => void }) {
  const reveal = (at: HeroesPhase) => phase === at;
  return (
    <section className={styles.chapter} data-phase={phase} aria-label="Heroes">
      <div className={`${styles.state} ${reveal(0) ? styles.visible : ""}`} aria-hidden={!reveal(0)}>
        <span className={styles.eyebrow}>Most played hero</span>
        <h1>{data.question || "If we had to start with one hero…"}</h1>
      </div>
      <div className={`${styles.state} ${reveal(1) ? styles.visible : ""}`} aria-hidden={!reveal(1)}>
        <span className={styles.eyebrow}>Hero name reveal</span>
        <h2>{data.heroName || "Hero name not available"}</h2>
      </div>
      <div className={`${styles.state} ${styles.portraitState} ${reveal(2) ? styles.visible : ""}`} aria-hidden={!reveal(2)}>
        <span className={styles.heroSilhouette} aria-hidden="true">{data.heroName?.slice(0, 2).toUpperCase() || "—"}</span>
        <span className={styles.eyebrow}>Portrait reveal</span>
      </div>
      <div className={`${styles.state} ${reveal(3) ? styles.visible : ""}`} aria-hidden={!reveal(3)}>
        <span className={styles.eyebrow}>Human interpretation</span>
        <p>{data.interpretation || "One hero is a useful entry point, not the whole story."}</p>
      </div>
      <div className={`${styles.listState} ${phase >= 4 && phase <= 8 ? styles.visible : ""}`} aria-hidden={phase < 4 || phase > 8}>
        <span className={styles.eyebrow}>{phase >= 5 ? "Top five · portraits" : "Pull back"}</span>
        <HeroList heroes={data.heroes} phase={Math.min(8, Math.max(4, phase)) as HeroListPhase} />
      </div>
      <div className={`${styles.state} ${styles.transition} ${reveal(9) ? styles.visible : ""}`} aria-hidden={!reveal(9)}>
        <span className={styles.eyebrow}>Heroes begin moving</span>
        <p>The names are about to become a pool of jobs.</p>
      </div>
      <div className={`${styles.state} ${styles.transition} ${reveal(10) ? styles.visible : ""}`} aria-hidden={!reveal(10)}>
        <span className={styles.eyebrow}>Pool transition</span>
        <p>The hero list is becoming a map of functional distance.</p>
      </div>
      {onAdvance && <button className={styles.advance} type="button" onClick={onAdvance}>Continue <span aria-hidden="true">→</span></button>}
    </section>
  );
}
