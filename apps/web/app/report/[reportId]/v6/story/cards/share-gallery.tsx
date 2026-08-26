"use client";

import type { V6ShareCandidate } from "../../types";
import { ShareCard, shareCardType, type ShareCardType } from "./share-card";
import styles from "./share-card.module.css";

function candidateId(candidate: V6ShareCandidate, index: number): string {
  return candidate.candidate_id ?? candidate.id ?? `${candidate.kind ?? "card"}-${index}`;
}

export function ShareGallery({
  candidates,
  phase = 5,
  selectedId,
  onSelect,
  onShare,
  onDownload,
  downloadState = "idle",
}: {
  candidates: V6ShareCandidate[];
  phase?: number;
  selectedId?: string;
  onSelect: (id: string) => void;
  onShare: (candidate: V6ShareCandidate) => void;
  onDownload: (candidate: V6ShareCandidate) => void;
  downloadState?: "idle" | "downloading" | "saved" | "error";
}) {
  const cardOrder: Record<ShareCardType, number> = { identity: 0, pool: 1, hero: 2, finding: 3 };
  const eligible = candidates
    .filter((candidate) => candidate.eligible !== false && shareCardType(candidate))
    .map((candidate, index) => ({ candidate, index }))
    .sort((left, right) => cardOrder[shareCardType(left.candidate)!] - cardOrder[shareCardType(right.candidate)!] || left.index - right.index)
    .map(({ candidate }) => candidate);
  const visibleCount = Math.min(eligible.length, Math.max(1, Math.floor(phase)));
  const visible = eligible.slice(0, visibleCount);
  const selectedIndex = Math.max(0, visible.findIndex((candidate, index) => candidateId(candidate, index) === selectedId));
  const selected = visible[selectedIndex];

  if (!selected) return <p className={styles.empty}>No share-ready card was included in this report.</p>;

  return (
    <section className={styles.gallery} aria-label="Share-card gallery">
      <div className={styles.cardStage}>
        {(phase >= 5 ? [selected] : visible).map((candidate, index) => <ShareCard key={candidateId(candidate, index)} candidate={candidate} selected={candidate === selected} />)}
      </div>
      {phase >= 5 && <div className={styles.thumbnails} role="radiogroup" aria-label="Choose a share card">
        {visible.map((candidate, index) => {
          const id = candidateId(candidate, index);
          return <button key={id} type="button" role="radio" aria-checked={candidate === selected} className={styles.thumbnail} data-selected={candidate === selected} onClick={() => onSelect(id)}>{shareCardType(candidate)}</button>;
        })}
      </div>}
      {phase >= 5 && <div className={styles.actions}>
        <button type="button" onClick={() => onShare(selected)}>Share</button>
        <button type="button" onClick={() => onDownload(selected)} disabled={downloadState === "downloading"}>{downloadState === "saved" ? "Saved ✓" : downloadState === "downloading" ? "Saving…" : "Download"}</button>
      </div>}
      {downloadState === "error" && <p className={styles.status} role="status">This card could not be downloaded.</p>}
    </section>
  );
}
