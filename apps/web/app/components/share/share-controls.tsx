"use client";

import { useState } from "react";
import { track } from "../../lib/analytics";

export default function ShareControls({ reportId }: { reportId: string }) {
  const [showName, setShowName] = useState(true);
  const [showAvatar, setShowAvatar] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  const cardUrl = (card: string) => {
    const params = new URLSearchParams({ show_name: String(showName), show_avatar: String(showAvatar) });
    return `/v1/reports/${encodeURIComponent(reportId)}/share/${card}?${params.toString()}`;
  };

  async function shareLink() {
    const url = window.location.origin + cardUrl("final");
    track("share.initiated.v1", { card_type: "final", aspect_ratio: "4:5", channel: "link" });
    try {
      if (navigator.share) {
        await navigator.share({ title: "My Dota DNA", url });
        track("share.completed.v1", { card_type: "final", channel: "native_link" });
        return;
      }
      await navigator.clipboard.writeText(url);
      setMessage("Share link copied.");
      track("share.link_copied.v1", { card_type: "final", channel: "clipboard" });
    } catch {
      setMessage("Copy the link from your browser to share it.");
      track("share.failed.v1", { card_type: "final", channel: "link" });
    }
  }

  function downloadCard() {
    const anchor = document.createElement("a");
    anchor.href = cardUrl("final");
    anchor.download = "dota-dna.svg";
    anchor.click();
    setMessage("Card download started.");
    track("share.image_saved.v1", { card_type: "final", aspect_ratio: "4:5", channel: "download" });
  }

  return (
    <div className="share-controls" aria-label="Share your Dota DNA">
      <p className="eyebrow">Share preview</p>
      <label><input type="checkbox" checked={showName} onChange={(event) => setShowName(event.target.checked)} /> Include name</label>
      <label><input type="checkbox" checked={showAvatar} onChange={(event) => setShowAvatar(event.target.checked)} /> Include avatar</label>
      <div className="share-actions">
        <button type="button" onClick={shareLink}>Share link</button>
        <button type="button" onClick={downloadCard}>Download card</button>
      </div>
      {message && <p className="muted" aria-live="polite">{message}</p>}
      <small className="muted">Your account ID is never included in a share card.</small>
    </div>
  );
}
