"use client";

/**
 * The archetype card (plan section 9b).
 *
 * Composition family 5 (Artifact): a bordered surface plus type, rules, and
 * blocks from the existing toolkit.  No illustration, photography, imported
 * art, canvas, or decorative SVG.
 *
 * Title and description are in the DOM from mount and are never removed from
 * the accessibility tree — the turn is presentation.  Once turned, the button
 * semantics are removed rather than left behind as a dead control.
 *
 * The content is the single frontend placeholder.  See archetype-placeholder.ts.
 */

import { useRef } from "react";
import { ARCHETYPE_PLACEHOLDER } from "./archetype-placeholder";
import { COPY } from "./copy";
import styles from "./story.module.css";

export function ArchetypeCard({
  title,
  description,
  revealed,
  onReveal,
  reducedMotion,
  scale = "full",
  headingRef,
  heading = true,
  /**
   * The turn belongs to Page 30 and to nothing else.  Page 29 watches the card
   * arrive face-down and Page 33 shows it at rest; neither is a second
   * reveal interaction.
   */
  canTurn = false,
  /** Pages the reader can only reach after the reveal show the resolved face. */
  alwaysFaceUp = false,
}: {
  /** Supplied by `year-shape.ts`, or the neutral constant when it returns null. */
  title: string;
  description: string;
  revealed: boolean;
  onReveal: () => void;
  reducedMotion: boolean;
  scale?: "full" | "compact" | "token";
  headingRef?: React.RefObject<HTMLHeadingElement>;
  heading?: boolean;
  canTurn?: boolean;
  alwaysFaceUp?: boolean;
}) {
  // The compact card rhymes with Page 30 rather than repeating it: the
  // description belongs to the reveal, not to the recap or the final card.
  const showDescription = scale === "full";
  const statusRef = useRef<HTMLParagraphElement>(null);
  // Reduced motion has nothing to trigger: Page 30's card is already face-up.
  const interactive = canTurn && !revealed && !reducedMotion;
  const faceUp = alwaysFaceUp || revealed || (canTurn && reducedMotion);

  const face = (
    <div className={styles.cardFace} data-face={faceUp ? "up" : "down"}>
      <span className={styles.cardRule} aria-hidden="true" />
      {heading ? (
        <h1 className={styles.cardTitle} ref={headingRef} tabIndex={-1}>
          {title}
        </h1>
      ) : (
        <p className={styles.cardTitle}>{title}</p>
      )}
      <span className={styles.cardRule} aria-hidden="true" />
      {showDescription ? (
        <p className={styles.cardDescription}>{description}</p>
      ) : null}
      <span className={styles.cardBackPattern} aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
    </div>
  );

  return (
    <div className={styles.cardShell} data-scale={scale}>
      {interactive ? (
        // The card itself is the control — a real button wrapping the face,
        // not a div with a click handler.  Once turned, the button semantics
        // are removed rather than left behind as a dead interactive element.
        <button type="button" className={styles.cardButton} onClick={onReveal}>
          {face}
          {/* A visible affordance: a face-down card with no cue reads as a
              failed render rather than as something to act on. */}
          <span className={styles.cardPrompt}>{COPY.page30.reveal}</span>
        </button>
      ) : (
        face
      )}
      <p className={styles.visuallyHidden} role="status" aria-live="polite" ref={statusRef}>
        {revealed ? COPY.page30.revealed : ""}
      </p>
    </div>
  );
}
