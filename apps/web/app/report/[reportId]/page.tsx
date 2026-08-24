import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { FreeDnaReportV4 } from "../../../../../packages/api-client/src";
import ReportStoryV4 from "./dna/report-story-v4";
import ReportStoryV6 from "./v6/report-story-v6";
import type { V6Report, V61Report } from "./v6/types";

export const revalidate = 60;

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

type Card = {
  insight_id: string;
  statement: string;
  player_metric: { value: number | null; unit: string };
  cohort_metric: { value: number | null; unit: string } | null;
  denominator: { matches: number; situations: number; parsed_matches: number };
  parse_coverage: { relevant: number };
  confidence: string;
  why_it_matters: string;
  behavior: string;
  target: string;
  practice_window: string;
  limitations: string[];
  effect: { value: number | null; direction: string | null; unit: string };
  role_certainty: { mean_probability: number; threshold: number; below_threshold: boolean };
  selected_cohort: { valid: boolean; level: string | null; sample_size: number } | null;
  evidence_statements: string[];
  source_match_ids: number[];
  provenance: { raw_payload_refs: string[]; normalized_match_refs: string[]; derived_feature_refs: string[] };
};

type DeepScanReport = {
  report_variant: "deep_scan";
  identity: { account_id: number; personaname: string; rank_tier: number | null };
  evidence_scope: {
    processed_matches: number;
    eligible_matches: number;
    normalized_matches: number;
    replay_parse_coverage: number;
    replay_evidence_status: string;
    replay_limitation: string | null;
    published_insight_count: number;
    suppressed_insight_count: number;
  };
  sections: {
    strongest_superpowers: Card[];
    contradictions: Card[];
    highest_value_weaknesses: Card[];
    next_rank: { status: string; reason: string };
  };
};

type Report = FreeDnaReportV4 | V6Report | V61Report | DeepScanReport;

export async function generateMetadata(): Promise<Metadata> {
  return { robots: { index: false, follow: false } };
}

async function getReport(reportId: string): Promise<Report> {
  const response = await fetch(API_BASE_URL + "/v1/reports/" + reportId, { next: { revalidate: 60 } });
  if (response.status === 404) notFound();
  if (!response.ok) {
    let message = "The report could not be loaded.";
    try {
      const body = await response.json();
      if (body?.message) message = body.message;
    } catch {
      // Keep the generic message when the API did not return JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

export default async function ReportPage({ params }: { params: { reportId: string } }) {
  const report = await getReport(params.reportId);
  if (report.report_variant === "free_dna_report") {
    if (report.schema_version === "free-dna-report-6.0.0" || report.schema_version === "free-dna-report-6.1.0") {
      return <ReportStoryV6 report={report} />;
    }
    if (report.schema_version !== "free-dna-report-4.0.0" && report.schema_version !== "free-dna-report-5.0.0" && report.schema_version !== "free-dna-report-5.1.0" && report.schema_version !== "free-dna-report-5.2.0") notFound();
    return <ReportStoryV4 report={report} />;
  }
  return <DeepScanReportPage report={report} />;
}

function DeepScanReportPage({ report }: { report: DeepScanReport }) {
  const sections = report.sections;
  return (
    <main className="shell report-shell">
      <Link className="back-link" href="/">← New report</Link>
      <header className="report-header"><p className="eyebrow">Deep Scan · {report.identity.account_id}</p><h1>{report.identity.personaname || "Anonymous player"}</h1><p className="lede">Evidence scope first. Conclusions only where the data clears the gate.</p></header>
      <section className="scope-card">
        <div><span className="eyebrow">Evidence scope</span><strong>{report.evidence_scope.eligible_matches} eligible matches</strong><p>{report.evidence_scope.normalized_matches} normalized from {report.evidence_scope.processed_matches} history rows.</p></div>
        <div><span className="eyebrow">Replay coverage</span><strong>{Math.round(report.evidence_scope.replay_parse_coverage * 100)}%</strong><p>{report.evidence_scope.replay_evidence_status.replaceAll("_", " ")}</p></div>
        <div><span className="eyebrow">Published</span><strong>{report.evidence_scope.published_insight_count}</strong><p>{report.evidence_scope.suppressed_insight_count} families suppressed or pending.</p></div>
      </section>
      {report.evidence_scope.replay_limitation && <aside className="notice">{report.evidence_scope.replay_limitation}</aside>}
      <ReportSection title="Superpowers" cards={sections.strongest_superpowers} empty="No strength has enough evidence yet." />
      <ReportSection title="Contradictions and context" cards={sections.contradictions} empty="No context split has enough evidence yet." />
      <ReportSection title="Work on next" cards={sections.highest_value_weaknesses} empty="No weakness has enough evidence yet." />
      <section className="deferred"><span className="eyebrow">Next rank</span><h2>Not available in this view</h2><p>{sections.next_rank.reason}</p></section>
    </main>
  );
}

function ReportSection({ title, cards, empty }: { title: string; cards: Card[]; empty: string }) {
  return <section className="report-section"><div className="section-heading"><p className="eyebrow">Report section</p><h2>{title}</h2></div>{cards.length ? <div className="cards">{cards.map((card) => <article className="insight-card" key={card.insight_id}><span className="confidence">{card.confidence} confidence</span><h3>{card.statement}</h3><p>{card.why_it_matters}</p><div className="metric-row"><span>{card.denominator.matches} matches</span><span>{Math.round(card.parse_coverage.relevant * 100)}% coverage</span><span>{card.denominator.situations} situations</span></div><div className="action"><strong>Next: </strong>{card.behavior}<br /><strong>Target: </strong>{card.target} ({card.practice_window})</div><details><summary>Limitations</summary><ul>{card.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details><details><summary>Evidence details</summary><dl className="evidence-details"><div><dt>Measured effect</dt><dd>{formatEffect(card.effect)}</dd></div><div><dt>Role certainty</dt><dd>{Math.round(card.role_certainty.mean_probability * 100)}% ({card.role_certainty.below_threshold ? "below" : "above"} threshold)</dd></div><div><dt>Cohort</dt><dd>{card.selected_cohort?.level ?? "No external cohort"}</dd></div></dl>{card.evidence_statements.length > 0 && <ul>{card.evidence_statements.map((item) => <li key={item}>{item}</li>)}</ul>}<p className="provenance">Provenance: {card.provenance.raw_payload_refs.length} raw payload, {card.provenance.normalized_match_refs.length} normalized, and {card.provenance.derived_feature_refs.length} derived references.</p></details></article>)}</div> : <p className="empty">{empty}</p>}</section>;
}

function formatEffect(effect: Card["effect"]): string {
  if (effect.value === null) return "Not available";
  const value = effect.unit === "rate" || effect.unit === "win rate" ? `${Math.round(effect.value * 100)}%` : effect.value.toFixed(2);
  return `${value}${effect.direction ? ` (${effect.direction})` : ""}`;
}
