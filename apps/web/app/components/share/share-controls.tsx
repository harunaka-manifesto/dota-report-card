"use client";

import { useMemo, useState } from "react";
import { track } from "../../lib/analytics";

type Props = { reportId: string; reportSchema?: string };

export default function ShareControls({ reportId, reportSchema }: Props) {
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
    track("report.share_opened.v1", { card_type: "final", report_schema_version: reportSchema ?? null, channel: "share" });
    try {
      const response = await fetch(cardUrl);
      if (!response.ok) throw new Error("share-card-failed");
      const blob = await response.blob();
      const file = new File([blob], "dota-dna-final.svg", { type: blob.type || "image/svg+xml" });
      const canShareFiles = typeof navigator.canShare === "function" && navigator.canShare({ files: [file] });
      if (navigator.share && canShareFiles) {
        await navigator.share({ title: "My Dota DNA", text: "My Dota DNA report", url: permalink, files: [file] });
        track("share.completed.v1", { card_type: "final", report_schema_version: reportSchema ?? null, channel: "native_file" });
        return;
      }
      if (navigator.share) {
        await navigator.share({ title: "My Dota DNA", text: "My Dota DNA report", url: permalink });
        track("share.completed.v1", { card_type: "final", report_schema_version: reportSchema ?? null, channel: "native_link" });
        return;
      }
      await navigator.clipboard.writeText(permalink);
      setMessage("Report link copied.");
      track("share.link_copied.v1", { card_type: "final", report_schema_version: reportSchema ?? null, channel: "clipboard" });
    } catch {
      setMessage("Copy the report link from your browser to share it.");
      track("share.failed.v1", { card_type: "final", channel: "share" });
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
      anchor.download = "dota-dna-final.svg";
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      setMessage("Card download started.");
      track("share.image_saved.v1", { card_type: "final", report_schema_version: reportSchema ?? null, channel: "download" });
    } catch {
      setMessage("The share card could not be generated.");
      track("share.failed.v1", { card_type: "final", channel: "download" });
    }
  }

  return (
    <div className="share-controls" aria-label="Share your Dota DNA">
      <p className="eyebrow">Share preview</p>
      <div className="share-preview"><img src={cardUrl} alt="Preview of the privacy-safe final share card" /></div>
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
