import type { V6ShareCandidate } from "../../../types";
import { ShareGallery } from "../../cards/share-gallery";
import styles from "../chapters.module.css";

export function ShareChapter(props: {
  candidates: V6ShareCandidate[];
  phase: number;
  selectedId?: string;
  onSelect: (id: string) => void;
  onShare: (candidate: V6ShareCandidate) => void;
  onDownload: (candidate: V6ShareCandidate) => void;
  downloadState?: "idle" | "downloading" | "saved" | "error";
}) {
  return (
    <section className={`${styles.chapter} ${styles.shareChapter}`} data-phase={props.phase} aria-labelledby="story-share-title">
      <div className={styles.chapterHeader}><span>Share</span><span>11 / 11</span></div>
      <h1 id="story-share-title">Your Dota DNA, in pieces.</h1>
      {props.phase === 0 ? <p className={styles.body}>Your report is complete. Choose what leaves with you.</p> : <ShareGallery {...props} />}
    </section>
  );
}
