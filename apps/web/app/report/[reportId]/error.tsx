"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ReportError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="shell report-shell">
      <p className="eyebrow">Report error</p>
      <h1>We could not load this report.</h1>
      <p className="lede">The API may be temporarily unavailable. Retry once, or start a new report if the problem continues.</p>
      <div className="lookup-row">
        <button type="button" onClick={() => reset()}>Retry</button>
        <Link className="back-link" href="/">← New report</Link>
      </div>
    </main>
  );
}
