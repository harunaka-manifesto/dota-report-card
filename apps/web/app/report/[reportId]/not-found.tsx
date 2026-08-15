import Link from "next/link";

export default function ReportNotFound() {
  return (
    <main className="shell report-shell">
      <p className="eyebrow">Report unavailable</p>
      <h1>This report has expired.</h1>
      <p className="lede">Reports are retained for a limited time in this experiment. Build a new report to continue.</p>
      <Link className="back-link" href="/">← Build a new report</Link>
    </main>
  );
}
