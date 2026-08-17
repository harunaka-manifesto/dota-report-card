"use client";

import { useMemo, useState } from "react";
import { track } from "../../lib/analytics";

type CardType = "identity" | "exposed" | "strength" | "strongest" | "pattern" | "archetypes" | "dna" | "heroes" | "final";

const CARD_LABELS: Record<CardType, string> = {
  identity: "Identity",
  exposed: "Finding: exposed",
  strength: "Finding: strength",
  strongest: "Strongest supported signal",
  pattern: "Pattern",
  archetypes: "Context archetypes",
  dna: "DNA snapshot",
  heroes: "Hero identity",
  final: "Final fingerprint"
};

export default function ShareControls({ reportId, defaultCardType = "final", findingKind, findingKey, reportSchema }: { reportId: string; defaultCardType?: CardType; findingKind?: string; findingKey?: string; reportSchema?: string }) {
  const [cardType, setCardType] = useState<CardType>(defaultCardType);
  const [showName, setShowName] = useState(true);
  const [showAvatar, setShowAvatar] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const cardLabels = reportSchema === "free-dna-report-3.0.0"
    ? { identity: CARD_LABELS.identity, strongest: CARD_LABELS.strongest, pattern: CARD_LABELS.pattern, archetypes: CARD_LABELS.archetypes }
    : CARD_LABELS;

  const cardUrl = useMemo(() => {
    const params = new URLSearchParams({ show_name: String(showName), show_avatar: String(showAvatar) });
    return `/v1/reports/${encodeURIComponent(reportId)}/share/${cardType}?${params.toString()}`;
  }, [cardType, reportId, showAvatar, showName]);

  const reportPermalink = () => `${window.location.origin}/report/${encodeURIComponent(reportId)}`;

  async function shareLink() {
    const permalink = reportPermalink();
    const canShareFiles = typeof navigator.canShare === "function";
    const shareStartedEvent = findingKind ? "finding.share_started.v1" : "share.initiated.v1";
    track(shareStartedEvent, {
      card_type: cardType,
      finding_key: findingKey ?? null,
      finding_kind: findingKind ?? null,
      report_schema_version: reportSchema ?? null,
      aspect_ratio: "4:5",
      channel: "share",
      show_name: showName,
      show_avatar: showAvatar,
      can_share_files: canShareFiles
    });
    try {
      const response = await fetch(cardUrl);
      if (!response.ok) throw new Error("share-card-failed");
      const rendererVersion = response.headers.get("x-share-renderer") ?? "unknown";
      const blob = await response.blob();
      const file = new File([blob], `dota-dna-${cardType}.svg`, { type: blob.type || "image/svg+xml" });
      if (navigator.share && canShareFiles && navigator.canShare({ files: [file] })) {
        await navigator.share({ title: "My Dota DNA", text: "My Dota DNA report", url: permalink, files: [file] });
        track(findingKind ? "finding.share_completed.v1" : "share.completed.v1", { card_type: cardType, finding_key: findingKey ?? null, finding_kind: findingKind ?? null, report_schema_version: reportSchema ?? null, renderer_version: rendererVersion, channel: "native_file", show_name: showName, show_avatar: showAvatar });
        return;
      }
      if (navigator.share) {
        await navigator.share({ title: "My Dota DNA", text: "My Dota DNA report", url: permalink });
        track(findingKind ? "finding.share_completed.v1" : "share.completed.v1", { card_type: cardType, finding_key: findingKey ?? null, finding_kind: findingKind ?? null, report_schema_version: reportSchema ?? null, renderer_version: rendererVersion, channel: "native_link", show_name: showName, show_avatar: showAvatar });
        return;
      }
      await navigator.clipboard.writeText(permalink);
      setMessage("Report link copied.");
      track(findingKind ? "finding.share_completed.v1" : "share.link_copied.v1", { card_type: cardType, finding_key: findingKey ?? null, finding_kind: findingKind ?? null, report_schema_version: reportSchema ?? null, channel: "clipboard", show_name: showName, show_avatar: showAvatar });
    } catch {
      setMessage("Copy the report link from your browser to share it.");
      track("share.failed.v1", { card_type: cardType, channel: "share", show_name: showName, show_avatar: showAvatar });
    }
  }

  async function downloadCard() {
    try {
      const response = await fetch(cardUrl);
      if (!response.ok) throw new Error("share-card-failed");
      const rendererVersion = response.headers.get("x-share-renderer") ?? "unknown";
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `dota-dna-${cardType}.svg`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      setMessage("Card download started.");
      track(findingKind ? "finding.share_completed.v1" : "share.image_saved.v1", { card_type: cardType, finding_key: findingKey ?? null, finding_kind: findingKind ?? null, report_schema_version: reportSchema ?? null, renderer_version: rendererVersion, aspect_ratio: "4:5", channel: "download", show_name: showName, show_avatar: showAvatar });
    } catch {
      setMessage("The share card could not be generated.");
      track("share.failed.v1", { card_type: cardType, channel: "download", show_name: showName, show_avatar: showAvatar });
    }
  }

  return (
    <div className="share-controls" aria-label="Share your Dota DNA">
      <p className="eyebrow">Share preview</p>
      <label htmlFor="share-card-type">Card</label>
      <select id="share-card-type" value={cardType} onChange={(event) => setCardType(event.target.value as CardType)}>
        {Object.entries(cardLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <div className="share-preview"><img src={cardUrl} alt={`Preview of the privacy-safe ${CARD_LABELS[cardType]} share card`} /></div>
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
