import AnalysisForm from "./components/analysis-form";

const landingSteps = [
  {
    index: "01",
    label: "INPUT",
    title: "Bring a public identifier.",
    body: "A Steam ID, Steam profile URL, or OpenDota profile is enough to start. No login or password.",
  },
  {
    index: "02",
    label: "REPORT",
    title: "Let the year take shape.",
    body: "The history becomes receipts, dates, hero patterns, and findings that clear their evidence gates.",
  },
  {
    index: "03",
    label: "EVIDENCE",
    title: "Keep the receipts close.",
    body: "Supported claims keep an evidence path. Thin or missing history stays an honest omission.",
  },
];

const landingBoundaries = [
  {
    index: "A",
    title: "Public history",
    body: "The read starts with the match history your public profile makes available to the report.",
  },
  {
    index: "B",
    title: "Qualified patterns",
    body: "A pattern earns its place only when the registered signal and its coverage support it.",
  },
  {
    index: "C",
    title: "Evidence in reach",
    body: "The finished report keeps Evidence and Methodology within reach when you want the longer version.",
  },
];

export default function HomePage() {
  return (
    <main className="shell landing-shell">
      <header className="landing-topline" aria-label="Dota Report Card navigation">
        <a className="landing-brand" href="/" aria-label="Dota Report Card home">
          <span className="landing-brand-mark" aria-hidden="true">DR</span>
          <span>Dota Report Card</span>
        </a>
        <nav className="landing-nav" aria-label="Landing page">
          <a href="#how-it-works">How it works</a>
          <a className="landing-nav-cta" href="#start">
            Start a report <span aria-hidden="true">↘</span>
          </a>
        </nav>
      </header>

      <section className="landing-hero" aria-labelledby="landing-title">
        <div className="landing-hero-copy">
          <p className="eyebrow">FREE REPORT / YOUR DOTA YEAR</p>
          <h1 id="landing-title">
            Your Dota history,
            <br />
            <em>with the receipts.</em>
          </h1>
          <p className="lede">
            Give us a public profile. We&apos;ll read the match history available to the report, then
            turn counts, dates, heroes, and qualified findings into a short story.
          </p>

          <div className="landing-form-wrap" id="start">
            <AnalysisForm />
            <p className="landing-quiet-note">
              Public data only. No account connection, no password, and no claim when the history
              cannot support one.
            </p>
          </div>
        </div>

        <div className="landing-preview-column">
          <div className="landing-preview" aria-hidden="true">
            <div className="landing-preview-topline">
              <span>REPORT / PREVIEW</span>
              <span>INPUT <b>→</b> READ</span>
            </div>
            <div className="landing-preview-stage">
              <div className="landing-preview-card landing-preview-card--scope">
                <span className="landing-preview-label">01 / SCOPE</span>
                <strong>
                  Up to
                  <br />
                  365 days
                </strong>
                <span>the window comes first</span>
              </div>
              <div className="landing-preview-card landing-preview-card--shape">
                <span className="landing-preview-label">02 / SHAPE</span>
                <div className="landing-preview-lines">
                  <i />
                  <i />
                  <i />
                  <i />
                </div>
                <span>names move. the record holds.</span>
              </div>
              <div className="landing-preview-card landing-preview-card--receipt">
                <span className="landing-preview-label">03 / RECEIPT</span>
                <strong>Evidence</strong>
                <span>within reach</span>
              </div>
            </div>
          </div>
          <p className="landing-preview-caption">
            <strong>First the receipt.</strong>
            <span>Then the pattern it can honestly support.</span>
          </p>
        </div>
      </section>

      <section className="landing-path" id="how-it-works" aria-labelledby="landing-path-title">
        <div className="landing-section-heading">
          <p className="eyebrow">THE SHORT VERSION</p>
          <h2 id="landing-path-title">One input. Three kinds of clarity.</h2>
          <p>
            The surface stays light. The work underneath keeps its boundaries in view.
          </p>
        </div>
        <ol className="landing-step-list">
          {landingSteps.map((step) => (
            <li className="landing-step" data-landing-step={step.index} key={step.index}>
              <div className="landing-step-heading">
                <span className="landing-step-index">{step.index}</span>
                <span className="landing-step-label">{step.label}</span>
              </div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-boundary" aria-labelledby="landing-boundary-title">
        <div className="landing-boundary-copy">
          <p className="eyebrow">ONSTAGE / BACKSTAGE</p>
          <h2 id="landing-boundary-title">
            Personal on the surface.
            <br />
            <em>Precise underneath.</em>
          </h2>
          <p>
            The report can make a pattern feel close without pretending it knows more than the
            public history. What is missing stays missing; what is supported stays traceable.
          </p>
        </div>
        <div className="landing-boundary-list">
          {landingBoundaries.map((boundary) => (
            <article className="landing-boundary-item" key={boundary.index}>
              <span className="landing-boundary-index">{boundary.index}</span>
              <div>
                <h3>{boundary.title}</h3>
                <p>{boundary.body}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        <span>FREE DOTA REPORT CARD / V6.1</span>
        <span>
          Built from available public history. <a href="#start">Build yours ↗</a>
        </span>
      </footer>
    </main>
  );
}
