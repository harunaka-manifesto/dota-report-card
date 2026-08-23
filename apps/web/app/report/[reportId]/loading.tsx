export default function ReportLoading() {
  return (
    <main className="state-shell report-loading-state" aria-busy="true" aria-live="polite">
      <p className="eyebrow">Free DNA / One moment</p>
      <h1>Putting your Dota shape together.</h1>
      <p className="lede">Your report is getting its final pass. The useful parts are almost here.</p>
      <div className="state-progress-track" aria-hidden="true"><span /></div>
    </main>
  );
}
