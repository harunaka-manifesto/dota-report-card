/**
 * Methodology.
 *
 * Analytical caveats live here, not in the story.  The owner-approved mode
 * wording keeps ranked and unranked history combined while limiting rank
 * points to the supplied ranked-match denominator.
 */

import type { ComposedStory } from "./compose";
import { formatCount } from "./format";
import type { V61Report } from "../types";

export function Methodology({ report, story }: { report: V61Report; story: ComposedStory }) {
  const universe = story.payload.universe;
  const provenance = story.payload.provenance;
  // The mode split stays backstage: ranked and unranked are reported as one
  // total.  The ranked denominator is the supplied one, never a frontend sum.
  const rankedMatches = story.payload.modules.rank_points.data?.ranked_matches ?? null;
  return (
    <>
      <section>
        <h3>What we read</h3>
        <p>
          A {universe.requested_window_days}-day summary history covering {formatCount(universe.match_count)} matches
          from {universe.window_start} to {universe.window_end}, observed from {universe.observed_from} to{" "}
          {universe.observed_to}.
        </p>
        <p>
          {provenance.physical_history_requests} history request, {provenance.detail_requests} match-detail requests,{" "}
          {provenance.parse_requests} replay parses.
        </p>
      </section>
      <section>
        <h3>Which matches count</h3>
        <p>
          Yearly totals cover both ranked and unranked matches.{" "}
          {formatCount(universe.excluded_or_unknown_count)} matches were excluded or could not be identified.
        </p>
        {rankedMatches === null ? (
          <p>Rank points cover ranked matches only.</p>
        ) : (
          <p>Rank points cover the {formatCount(rankedMatches)} ranked matches only.</p>
        )}
      </section>
      <section>
        <h3>What rank points are</h3>
        <p>
          Rank points are a modeled figure derived only from the ranked win-loss record at a frozen 25 points per
          ranked match. Dota does not report this number; we compute it here, and it is the only rank-root figure this
          report shows.
        </p>
      </section>
      <section>
        <h3>Duration coverage</h3>
        <p>
          {formatCount(universe.duration_known_count)} of {formatCount(universe.duration_candidate_count)} matches
          reported a duration. Hours mean time inside recorded matches — not queue, draft, lobby, or menu time.
        </p>
        <p>History completeness: {universe.history_completeness.replaceAll("_", " ")}.</p>
      </section>
      <section>
        <h3>Versions</h3>
        <dl>
          <div>
            <dt>Report</dt>
            <dd>{report.schema_version}</dd>
          </div>
          <div>
            <dt>Story payload</dt>
            <dd>{story.payload.version}</dd>
          </div>
          <div>
            <dt>Mode map</dt>
            <dd>{provenance.mode_map_version}</dd>
          </div>
          <div>
            <dt>Hero taxonomy</dt>
            <dd>{provenance.hero_taxonomy_version}</dd>
          </div>
        </dl>
      </section>
      {story.diagnostics.length > 0 ? (
        <section>
          <h3>Omitted modules</h3>
          <ul>
            {story.diagnostics.map((diagnostic) => (
              <li key={`${diagnostic.module}-${diagnostic.code}`}>
                {diagnostic.module}: {diagnostic.code.replaceAll("_", " ")}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  );
}
