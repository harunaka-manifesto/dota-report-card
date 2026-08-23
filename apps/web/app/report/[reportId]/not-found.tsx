import Link from "next/link";

export default function ReportNotFound() {
  return (
    <main className="state-shell report-not-found-state">
      <p className="eyebrow">Free DNA / Report unavailable</p>
      <h1>That report is no longer available.</h1>
      <p className="lede">
        Reports are temporary by design. Build a new one when you&apos;re ready to look again.
      </p>
      <div className="state-actions">
        <Link className="state-primary-action" href="/">Build a new report</Link>
      </div>
    </main>
  );
}
