"use client";

/**
 * Share is URL-only this cycle.
 *
 * `share_card_available` is `Literal[False]` and no artifact contract exists,
 * so there is no Save path, no downloadable artifact, and no share-image alt
 * text.  Native Web Share falls back to copy-link, which falls back to
 * selectable text.  The control is never dead and never claims a success it
 * did not get.
 *
 * The canonical report URL is origin + pathname: no query string, no
 * fragment, no token, no private identifier.
 */

import { useEffect, useRef, useState } from "react";
import { COPY } from "./copy";
import styles from "./story.module.css";

type ShareStatus = "idle" | "shared" | "copied" | "manual";

export function canonicalReportUrl(): string {
  if (typeof window === "undefined") return "";
  return `${window.location.origin}${window.location.pathname}`;
}

export function ShareControl({
  onShared,
  onCopied,
  onFailed,
}: {
  onShared: () => void;
  onCopied: () => void;
  onFailed: () => void;
}) {
  const [status, setStatus] = useState<ShareStatus>("idle");
  const [url, setUrl] = useState("");
  const fallbackRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (status === "manual") fallbackRef.current?.select();
  }, [status]);

  const share = async () => {
    const target = canonicalReportUrl();
    setUrl(target);
    const navigatorWithShare = navigator as Navigator & { share?: (data: ShareData) => Promise<void> };
    if (typeof navigatorWithShare.share === "function") {
      try {
        await navigatorWithShare.share({ title: "Dota DNA", text: COPY.page33.share, url: target });
        setStatus("shared");
        onShared();
        return;
      } catch (error) {
        // A native cancel is a user choice, not a failure: return silently.
        if (error instanceof DOMException && error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(target);
      setStatus("copied");
      onCopied();
      return;
    } catch {
      setStatus("manual");
      onFailed();
    }
  };

  return (
    <div className={styles.share}>
      {/* The contract label stays the same in both modes: the reader's intent
          is identical and no new string is invented.  See plan section 10. */}
      <button type="button" className={styles.primaryControl} onClick={share}>
        {COPY.page33.share}
      </button>
      <p className={styles.shareStatus} role="status" aria-live="polite">
        {status === "copied" ? COPY.page33.shareCopied : null}
        {status === "manual" ? COPY.page33.shareCopyFailed : null}
      </p>
      {status === "manual" ? (
        <input
          ref={fallbackRef}
          className={styles.shareFallback}
          value={url}
          readOnly
          aria-label={COPY.page33.shareUrlLabel}
        />
      ) : null}
    </div>
  );
}
