/**
 * Methodology.
 *
 * Analytical caveats live here, not in the story.  Captain's Mode scope is
 * disclosed here too: mode detail matters backstage and distracts onstage.
 *
 * OWNER APPROVAL OUTSTANDING for the scope wording below (plan Risk 10).  It
 * states only values the payload already carries and uses no rank-root
 * vocabulary beyond the fixed "rank points" and "ranked matches" phrases.
 */

import type { ComposedStory } from "./compose";
import { formatCount } from "./format";
import type { V61Report } from "../types";

export function Methodology({ report, story }: { report: V61Report; story: ComposedStory }) {
  const universe = story.payload.universe;
  const provenance = story.payload.provenance;
  const modes = universe.mode_counts;
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
          Yearly totals cover ranked and unranked All Pick plus Captain&rsquo;s Mode:{" "}
          {formatCount(modes.unranked_all_pick)} unranked All Pick, {formatCount(modes.ranked_all_pick)} ranked All
          Pick, {formatCount(modes.unranked_captains_mode)} unranked Captain&rsquo;s Mode, and{" "}
          {formatCount(modes.ranked_captains_mode)} ranked Captain&rsquo;s Mode.{" "}
          {formatCount(universe.excluded_or_unknown_count)} matches were excluded or could not be identified.
        </p>
        <p>Rank points cover ranked All Pick and ranked Captain&rsquo;s Mode only.</p>
      </section>
      <section>
        <h3>What rank points are</h3>
        <p>
          Rank points are a modeled figure derived only from the ranked win-loss record at a frozen 25 points per
          ranked match. They are not a provider-reported rating and not a medal.
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
