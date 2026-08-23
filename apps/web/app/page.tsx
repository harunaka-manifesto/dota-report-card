import AnalysisForm from "./components/analysis-form";

const landingBeats = [
  {
    index: "01",
    title: "Find your throughline",
    body: "The habits that keep returning, even when the hero changes.",
  },
  {
    index: "02",
    title: "Meet your Elements",
    body: "A compact identity dashboard for the way you move through Dota.",
  },
  {
    index: "03",
    title: "Leave with a test",
    body: "One useful experiment for your next stretch of matches.",
  },
];

export default function HomePage() {
  return (
    <main className="shell landing-shell">
      <header className="landing-topline" aria-label="Free DNA introduction">
        <a href="#start">Free DNA / 01</a>
        <span>A closer look at your play</span>
      </header>

      <section className="landing-hero" aria-labelledby="landing-title">
        <div className="landing-hero-copy">
          <p className="eyebrow">The shape of your play</p>
          <h1 id="landing-title">
            Your Dota habits,
            <br />
            <em>made visible.</em>
          </h1>
          <p className="lede">
            Give us a public profile. We&apos;ll turn the matches into a compact portrait of how
            you move through Dota — the parts you recognize, and the parts that keep sneaking
            back into the draft.
          </p>
          <AnalysisForm />
          <p className="landing-quiet-note">
            Public profile details only. No password, no account connection, and no performance
            theatre required.
          </p>
        </div>

        <div>
          <div className="landing-specimen" aria-hidden="true">
            <div className="landing-specimen-tile"><span>Arrive early</span></div>
            <div className="landing-specimen-tile"><span>Hold the line</span></div>
            <div className="landing-specimen-tile"><span>Change shape</span></div>
            <div className="landing-specimen-tile"><span>Keep pace</span></div>
            <div className="landing-specimen-tile"><span>Find the edge</span></div>
            <div className="landing-specimen-tile"><span>Take the long way</span></div>
            <div className="landing-specimen-tile"><span>Reset</span></div>
            <div className="landing-specimen-tile"><span>Return</span></div>
          </div>
          <p className="landing-specimen-caption">
            <strong>Identity is a pattern, not a rank.</strong>
            <span>Built from the way you actually play.</span>
          </p>
        </div>
      </section>

      <section className="landing-principles" id="start" aria-label="What your report includes">
        {landingBeats.map((beat) => (
          <article className="landing-principle" key={beat.index}>
            <span className="landing-principle-index">{beat.index}</span>
            <h2>{beat.title}</h2>
            <p>{beat.body}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
