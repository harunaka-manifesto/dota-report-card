import styles from "./pool-ring.module.css";

export type PoolBand = "core" | "stretch" | "outer" | "unclassified";

export type PoolHero = {
  id: string;
  name: string;
  band?: PoolBand;
  matchCount?: number | null;
  share?: number | null;
};

export type PoolRingPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13;

export function PoolRing({ core, stretch, outer, all, phase = 0 }: { core: readonly PoolHero[]; stretch: readonly PoolHero[]; outer: readonly PoolHero[]; all?: readonly PoolHero[]; phase?: PoolRingPhase }) {
  const heroes = stableHeroes(all ?? [...core, ...stretch, ...outer]);
  const revealBand = (band: PoolBand) => {
    if (phase < 1) return true;
    if (phase < 3) return band !== "outer";
    if (phase < 8) return false;
    if (phase < 9) return band === "core";
    if (phase < 10) return band === "core" || band === "stretch";
    return true;
  };
  return (
    <section className={styles.visual} data-phase={phase} aria-label="Hero pool shape">
      <div className={styles.ring} aria-hidden="true">
        <span className={`${styles.track} ${styles.outerTrack}`} />
        <span className={`${styles.track} ${styles.stretchTrack}`} />
        <span className={`${styles.track} ${styles.coreTrack}`} />
        {heroes.map((hero, index) => {
          const band = hero.band ?? "unclassified";
          const visible = revealBand(band);
          const radius = band === "core" ? 24 : band === "stretch" ? 37 : 49;
          const angle = (index / Math.max(heroes.length, 1)) * Math.PI * 2 - Math.PI / 2;
          const distance = radius / 2;
          return <span className={`${styles.node} ${visible ? styles.nodeVisible : styles.nodeFaded}`} key={hero.id} style={{ left: `${50 + Math.cos(angle) * distance}%`, top: `${50 + Math.sin(angle) * distance}%` }} title={hero.name} />;
        })}
        <span className={styles.center}>POOL</span>
      </div>
      <ul className={styles.legend} aria-label="Heroes by pool band">
        {(["core", "stretch", "outer"] as const).map((band) => <li key={band}><span className={`${styles.legendDot} ${styles[`legend-${band}`]}`} /><strong>{band}</strong><span>{heroes.filter((hero) => hero.band === band).map((hero) => hero.name).join(" · ") || "Not available"}</span></li>)}
      </ul>
    </section>
  );
}

function stableHeroes(heroes: readonly PoolHero[]): PoolHero[] {
  const seen = new Set<string>();
  return heroes.filter((hero) => {
    if (seen.has(hero.id)) return false;
    seen.add(hero.id);
    return true;
  });
}
