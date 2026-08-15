import AnalysisForm from "./components/analysis-form";

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">OpenDota insight system</p>
        <h1>A report card for how you actually play.</h1>
        <p className="lede">
          Enter a public OpenDota profile or Steam32 ID. The report shows evidence scope first,
          then the patterns that have enough data to earn your attention.
        </p>
        <AnalysisForm />
      </section>
      <section className="principles">
        <div>
          <span>01</span>
          <h2>Auditable</h2>
          <p>Every card keeps its denominator, source matches, cohort, and limitations.</p>
        </div>
        <div>
          <span>02</span>
          <h2>Fail-closed</h2>
          <p>Replay-dependent findings disappear when parsing coverage is not good enough.</p>
        </div>
        <div>
          <span>03</span>
          <h2>Actionable</h2>
          <p>Published evidence ends with a measurable behavior for the next 20 matches.</p>
        </div>
      </section>
    </main>
  );
}

