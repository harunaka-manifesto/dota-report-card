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
      <h1>This report couldn’t load.</h1>
      <div className="state-actions">
        <button className="state-primary-action" type="button" onClick={() => reset()}>
          Try again
        </button>
        <Link className="back-link" href="/">Generate new report</Link>
      </div>
    </main>
  );
}
