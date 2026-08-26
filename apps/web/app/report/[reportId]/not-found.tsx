import Link from "next/link";

export default function ReportNotFound() {
  return (
    <main className="state-shell report-not-found-state">
      <h1>This report isn’t here.</h1>
      <div className="state-actions">
        <Link className="state-primary-action" href="/">Generate new report</Link>
      </div>
    </main>
  );
}
