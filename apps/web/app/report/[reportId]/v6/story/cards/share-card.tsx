import type { V6ShareCandidate } from "../../types";
import styles from "./share-card.module.css";

export type ShareCardType = "identity" | "pool" | "hero" | "finding";

function text(candidate: V6ShareCandidate, key: string): string | null {
  const value = candidate.payload?.[key];
  return typeof value === "string" && value.trim() ? value : null;
}

export function shareCardType(candidate: V6ShareCandidate): ShareCardType | null {
  const kind = candidate.kind?.toLowerCase();
  if (kind === "identity" || kind === "pool" || kind === "hero" || kind === "finding") return kind;
  if (kind === "strongest-finding") return "finding";
  if (kind === "hero-mirror") return "hero";
  return null;
}

export function ShareCard({ candidate, selected = false }: { candidate: V6ShareCandidate; selected?: boolean }) {
  const type = shareCardType(candidate);
  if (!type) return null;
  const title = candidate.title ?? candidate.headline ?? text(candidate, "title") ?? type;
  const body = candidate.body ?? text(candidate, "body") ?? candidate.reason;

  return (
    <article className={styles.card} data-type={type} data-selected={selected} aria-label={`${type} share card`}>
      <p className={styles.meta}>{candidate.title ?? type}</p>
      {candidate.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element -- server-rendered deterministic share asset.
        <img className={styles.image} src={candidate.image_url} alt="" />
      ) : (
        <ShareMark type={type} />
      )}
      <h2>{title}</h2>
      {body && body !== title && <p className={styles.body}>{body}</p>}
    </article>
  );
}

function ShareMark({ type }: { type: ShareCardType }) {
  if (type === "pool") return <span className={styles.poolMark} aria-hidden="true"><i /><i /><i /></span>;
  return <span className={styles.dnaMark} aria-hidden="true">{Array.from({ length: 6 }, (_, index) => <i key={index} />)}</span>;
}
