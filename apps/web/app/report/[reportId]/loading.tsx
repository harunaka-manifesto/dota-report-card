export default function ReportLoading() {
  return (
    <main className="shell report-shell" aria-busy="true" aria-live="polite">
      <p className="eyebrow">Reading your report</p>
      <h1>Putting the Dota back in the numbers.</h1>
      <p className="lede">The report is loading its bounded history and evidence. This usually takes a moment.</p>
      <div className="report-loading-bar" aria-hidden="true"><span /></div>
    </main>
  );
}
