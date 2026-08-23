"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ReportError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="state-shell report-error-state">
      <p className="eyebrow">Free DNA / Report error</p>
      <h1>We couldn&apos;t open that report.</h1>
      <p className="lede">
        Something interrupted the handoff. Try once more, or start a new report if the problem
        keeps happening.
      </p>
      <div className="state-actions">
        <button className="state-primary-action" type="button" onClick={() => reset()}>
          Try again
        </button>
        <Link className="back-link" href="/">Start a new report</Link>
      </div>
    </main>
  );
}
