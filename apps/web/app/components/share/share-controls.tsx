"use client";

import { useMemo, useState } from "react";
import { track } from "../../lib/analytics";

export default function ShareControls({ reportId }: { reportId: string }) {
  const [showName, setShowName] = useState(true);
  const [showAvatar, setShowAvatar] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  const cardUrl = useMemo(() => {
    const params = new URLSearchParams({ show_name: String(showName), show_avatar: String(showAvatar) });
    return `/v1/reports/${encodeURIComponent(reportId)}/share/final?${params.toString()}`;
  }, [reportId, showAvatar, showName]);

  const reportPermalink = () => `${window.location.origin}/report/${encodeURIComponent(reportId)}`;

  async function shareLink() {
    const permalink = reportPermalink();
    const canShareFiles = typeof navigator.canShare === "function";
    track("share.initiated.v1", {
      card_type: "final",
      aspect_ratio: "4:5",
      channel: "share",
      show_name: showName,
      show_avatar: showAvatar,
      can_share_files: canShareFiles
    });
    try {
      const response = await fetch(cardUrl);
      if (!response.ok) throw new Error("share-card-failed");
      const blob = await response.blob();
      const file = new File([blob], "dota-dna.svg", { type: blob.type || "image/svg+xml" });
      if (navigator.share && canShareFiles && navigator.canShare({ files: [file] })) {
        await navigator.share({ title: "My Dota DNA", text: "My Dota DNA report", url: permalink, files: [file] });
        track("share.completed.v1", { card_type: "final", channel: "native_file", show_name: showName, show_avatar: showAvatar });
        return;
      }
      if (navigator.share) {
        await navigator.share({ title: "My Dota DNA", text: "My Dota DNA report", url: permalink });
        track("share.completed.v1", { card_type: "final", channel: "native_link", show_name: showName, show_avatar: showAvatar });
        return;
      }
      await navigator.clipboard.writeText(permalink);
      setMessage("Report link copied.");
      track("share.link_copied.v1", { card_type: "final", channel: "clipboard", show_name: showName, show_avatar: showAvatar });
    } catch {
      setMessage("Copy the report link from your browser to share it.");
      track("share.failed.v1", { card_type: "final", channel: "share", show_name: showName, show_avatar: showAvatar });
    }
  }

  async function downloadCard() {
    try {
      const response = await fetch(cardUrl);
      if (!response.ok) throw new Error("share-card-failed");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = "dota-dna.svg";
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      setMessage("Card download started.");
      track("share.image_saved.v1", { card_type: "final", aspect_ratio: "4:5", channel: "download", show_name: showName, show_avatar: showAvatar });
    } catch {
      setMessage("The share card could not be generated.");
      track("share.failed.v1", { card_type: "final", channel: "download", show_name: showName, show_avatar: showAvatar });
    }
  }

  return (
    <div className="share-controls" aria-label="Share your Dota DNA">
      <p className="eyebrow">Share preview</p>
      <div className="share-preview"><img src={cardUrl} alt="Preview of the privacy-safe Dota DNA share card" /></div>
      <label><input type="checkbox" checked={showName} onChange={(event) => setShowName(event.target.checked)} /> Include name</label>
      <label><input type="checkbox" checked={showAvatar} onChange={(event) => setShowAvatar(event.target.checked)} /> Include avatar</label>
      <div className="share-actions">
        <button type="button" onClick={shareLink}>Share report</button>
        <button type="button" onClick={downloadCard}>Download card</button>
      </div>
      {message && <p className="muted" aria-live="polite">{message}</p>}
      <small className="muted">Your account ID is never included in a share card.</small>
    </div>
  );
}
