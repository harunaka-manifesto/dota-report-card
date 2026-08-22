import http from "node:http";
import { spawn } from "node:child_process";

const apiPort = Number(process.env.FIXTURE_API_PORT ?? 8001);
const reportId = "fixture-report";

const elementKeys = [
  "hero_pool_breadth", "hero_pool_stability", "hero_exploration_rate", "toolkit_breadth",
  "post_loss_familiarity_shift", "role_breadth", "combat_involvement", "finisher_orientation",
  "death_exposure", "off_pool_performance", "off_pool_activity_stability", "performance_volatility",
  "recent_form_shift", "recent_activity_shift", "session_length_tendency", "late_session_performance",
  "post_loss_activity_shift", "post_loss_performance_response"
];
const elementLabels = [
  "Breadth", "Stability", "Exploration", "Toolkit", "Familiarity", "Role", "Involvement", "Finishing", "Deaths", "Transfer", "Presence", "Volatility", "Form", "Pace", "Duration", "Drift", "Tempo", "Recovery"
];
const patternKeys = [
  "same_playbook", "comfort_edge", "partial_transfer", "versatile_core", "proven_flexibility", "bounceback", "performance_slide", "controlled_presence", "presence_tax", "session_fade", "session_rise"
];
const patternLabels = [
  "Same Playbook", "Comfort Edge", "Partial Transfer", "Versatile Core", "Proven Flexibility", "Bounceback", "Performance Slide", "Controlled Presence", "Presence Tax", "Session Fade", "Session Rise"
];

const presentationContracts = {
  same_playbook: { outcome_id: "P01_BROAD_HERO_NARROW_JOB", visual_variant: "hero_job_cluster", recommendation_id: "P01_ADD_MISSING_FUNCTION", deep_dive_id: "P01_DRAFT_SPECIFIC_EXPANSION" },
  comfort_edge: { outcome_id: "P02_RELIABILITY_LADDER", visual_variant: "hero_reliability_ladder", recommendation_id: "P02_FOCUS_DEVELOPMENT_ORDER", deep_dive_id: "P02_HERO_DEMAND_COMPARISON" },
  partial_transfer: { outcome_id: "P03_PRESENCE_HOLDS_RESULT_BENDS", visual_variant: "transfer_split", recommendation_id: "P03_PRACTICE_TRANSFER_DEMAND", deep_dive_id: "P03_ENTRY_HOLD_REENTRY" },
  versatile_core: { outcome_id: "P04_COMPACT_POOL_BROAD_JOBS", visual_variant: "toolkit_orbit", recommendation_id: "P04_ADD_MISSING_FUNCTION", deep_dive_id: "P04_DRAFT_SPECIFIC_EXPANSION" },
  proven_flexibility: { outcome_id: "P05_PROVEN_FLEX_WINDOW", visual_variant: "flex_window_grid", recommendation_id: "P05_PROTECT_RELIABLE_ANCHORS", deep_dive_id: "P05_CONTEXT_TRANSFER" },
  bounceback: { outcome_id: "P06_POST_LOSS_STRONGER", visual_variant: "post_loss_transition", recommendation_id: "P06_REPEAT_POST_LOSS_ANCHOR", deep_dive_id: "P06_POST_LOSS_MECHANISM" },
  performance_slide: { outcome_id: "P07_POST_LOSS_WEAKER", visual_variant: "post_loss_transition", recommendation_id: "P07_CHANGE_ONE_TRANSITION", deep_dive_id: "P07_POST_LOSS_MECHANISM" },
  controlled_presence: { outcome_id: "P08_HIGH_PRESENCE_LOW_COST", visual_variant: "presence_exposure_map", recommendation_id: "P08_PRESERVE_LOW_COST_PRESENCE", deep_dive_id: "P08_FIGHT_CONTEXTS" },
  presence_tax: { outcome_id: "P09_HIGH_PRESENCE_HIGH_COST", visual_variant: "presence_exposure_map", recommendation_id: "P09_INVESTIGATE_PRESENCE_COST", deep_dive_id: "P09_DEATH_VALUE_CONTEXT" },
  session_fade: { outcome_id: "P10_SESSION_FADE", visual_variant: "session_curve", recommendation_id: "P10_CHECKPOINT_AT_BREAKPOINT", deep_dive_id: "P10_SESSION_BREAKPOINT" },
  session_rise: { outcome_id: "P11_SESSION_RISE", visual_variant: "session_curve", recommendation_id: "P11_FRONTLOAD_FAMILIARITY", deep_dive_id: "P11_SESSION_BREAKPOINT" }
};
const presentationCopy = (key, qualified) => {
  const headline = {
    same_playbook: "Broad by hero. Narrow by job.", comfort_edge: "Your pool has a reliability ladder.", partial_transfer: "Your presence travels farther than your results.", versatile_core: "A small pool can cover a lot of Dota.", proven_flexibility: "Your flexibility shows up in the window.", bounceback: "LOSS → NEXT GAME: STRONGER", performance_slide: "LOSS → NEXT GAME: WEAKER", controlled_presence: "You can be involved without paying the full cost.", presence_tax: "Your presence comes with a visible tax.", session_fade: "Your session has a fade point.", session_rise: "You tend to warm into the session."
  }[key];
  return {
    headline,
    subheadline: "A compact visual proof sits below the reveal, followed by one bounded interpretation and next step.",
    interpretation: { title: "What this actually means", body: "This fixture keeps the conclusion tied to the observable summary evidence. It does not claim a cause." },
    recommendation: qualified ? { eyebrow: "DO THIS NEXT", title: "Try one deliberate next step", body: key === "same_playbook" || key === "versatile_core" ? "Use Example bridge hero to add one missing function while keeping a familiar anchor." : "Keep the supported anchor visible while you practice the next demand." } : null,
    deep_dive: qualified ? { title: "Ask the next diagnostic question", body: "Deep Dive can inspect the match-level mechanism behind this supported pattern." } : null,
    fallback: { title: "More evidence needed", body: "The pattern remains visible, but no narrower action is stable enough to call out." }
  };
};
const presentationProof = (key) => ({
  same_playbook: { hero_names: ["Anti-Mage", "Axe", "Rubick"], regular_hero_count: 3, strongest_jobs: ["Fight control", "Fight start"], job_clusters: [{ job: "Fight control", hero_names: ["Axe", "Rubick"], hero_count: 2 }, { job: "Fight start", hero_names: ["Axe"], hero_count: 1 }] },
  comfort_edge: { ranked_heroes: [{ hero_name: "Anti-Mage", rank: 1, band: "Anchor", matches: 18 }, { hero_name: "Axe", rank: 2, band: "Anchor", matches: 16 }, { hero_name: "Rubick", rank: 3, band: "Close", matches: 12 }, { hero_name: "Invoker", rank: 4, band: "Still developing", matches: 8 }] },
  partial_transfer: { familiar_presence: "Shows up often", off_pool_presence: "Shows up often", result_direction: "Weaker than usual", strongest_demand: "Access" },
  versatile_core: { hero_job_maps: [{ hero_name: "Axe", primary_jobs: ["Fight start", "Frontline"] }, { hero_name: "Rubick", primary_jobs: ["Fight control", "Save"] }], coverage: { strongly_covered: ["Fight control"], thin: ["Wave clear"], missing: ["Global reach"] } },
  proven_flexibility: { window_label: "2026-01-01 – 2026-01-07", hero_names: ["Anti-Mage", "Axe", "Rubick"], hero_rows: [{ hero_name: "Anti-Mage", game_count: 5 }, { hero_name: "Axe", game_count: 3 }, { hero_name: "Rubick", game_count: 2 }], total_games: 10, functional_jobs: ["Fight start", "Fight control", "Save"], functional_job_count: 3, repeated_hero_count: 2 },
  bounceback: { transition_label: "LOSS → NEXT GAME: STRONGER", context_label: "Axe", hero_name: "Axe", function_family: "Initiation" },
  performance_slide: { transition_label: "LOSS → NEXT GAME: WEAKER", context_label: "Overall", function_family: "Access" },
  controlled_presence: { contexts: [{ label: "Axe", involvement_label: "Shows up often", death_exposure_label: "Low cost", sample_size: 14 }, { label: "Rubick", involvement_label: "Shows up often", death_exposure_label: "Typical cost", sample_size: 12 }] },
  presence_tax: { contexts: [{ label: "Frontline", involvement_label: "Shows up often", death_exposure_label: "High cost", sample_size: 15 }, { label: "Save", involvement_label: "About usual", death_exposure_label: "Typical cost", sample_size: 11 }] },
  session_fade: { direction: "fade", curve: [{ bucket_label: "Game 1", display_label: "Above usual" }, { bucket_label: "Game 2", display_label: "About usual" }, { bucket_label: "Game 3", display_label: "Below usual" }, { bucket_label: "Game 4", display_label: "Lowest point" }, { bucket_label: "Game 5+", display_label: "Below usual" }], breakpoint_label: "Game 3" },
  session_rise: { direction: "rise", curve: [{ bucket_label: "Game 1", display_label: "Slow start" }, { bucket_label: "Game 2", display_label: "Warming up" }, { bucket_label: "Game 3", display_label: "About usual" }, { bucket_label: "Game 4", display_label: "Above usual" }, { bucket_label: "Game 5+", display_label: "Strongest" }], breakpoint_label: "Game 3" }
}[key]);
const makePresentation = (key, qualified) => {
  const contract = presentationContracts[key];
  const copy = presentationCopy(key, qualified);
  return {
    pattern_id: key,
    outcome_id: contract.outcome_id,
    visual_variant: contract.visual_variant,
    proof_data: { ...presentationProof(key), pattern_status: qualified ? "qualified" : "suppressed", confidence: qualified ? "moderate" : "unavailable" },
    interpretation_id: contract.outcome_id,
    recommendation_id: qualified ? contract.recommendation_id : null,
    recommendation_context: qualified ? { kind: key === "same_playbook" || key === "versatile_core" ? "hero" : "practice", hero_name: key === "same_playbook" || key === "versatile_core" ? "Example bridge hero" : null } : null,
    deep_dive_id: qualified ? contract.deep_dive_id : null,
    evidence_refs: ["fixture.pattern", "fixture.summary"],
    raw_metrics: {},
    confidence: qualified ? "moderate" : "unavailable",
    presentation_version: "pattern-presentation-5.2.0",
    copy
  };
};

const receipt = (key, value = 60) => ({ key, value, unit: "matches", denominator: 60, coverage: 1, confidence_score: .78, comparison: "Fixture evidence" });
const elements = elementKeys.map((key, index) => ({
  key,
  label: elementLabels[index],
  dimension_key: "summary",
  status: "available",
  score: .28 + index * .035,
  centered_score: -.44 + index * .07,
  axis: { left: "Lower", right: "Higher" },
  zone: ["Focused", "Selective", "Mixed", "Varied", "Wide"][Math.min(4, Math.floor(index / 4))],
  confidence: "moderate",
  confidence_score: .78,
  sample_size: 60,
  effective_sample_size: 48,
  coverage: 1,
  receipts: [receipt(key)],
  confounders: [],
  missing_reasons: [],
  methodology_version: "element-5.1.0"
}));
const patterns = patternKeys.map((key, index) => ({
  key,
  label: patternLabels[index],
  kind: index % 2 ? "contradiction" : "style",
  status: index < 5 ? "qualified" : "suppressed",
  direction: index < 5 ? "fixture_direction" : null,
  strength: index < 5 ? .76 - index * .04 : 0,
  relationship_strength: index < 5 ? .82 : 0,
  confidence: index < 5 ? "moderate" : "low",
  confidence_score: index < 5 ? .76 : 0,
  evidence_coverage: index < 5 ? .9 : 0,
  qualification_quality: index < 5 ? .8 : 0,
  element_keys: [elementKeys[index % elementKeys.length], elementKeys[(index + 1) % elementKeys.length]],
  modifier_element_keys: [],
  family: index % 2 ? "breadth_transfer" : "session_drift",
  tier: index < 6 ? "A" : "B",
  receipts: [receipt(key)],
  confounders: [],
  story_eligibility: "eligible",
  story_blockers: [],
  suppression_reasons: index < 5 ? [] : ["relationship_threshold_not_met"],
  methodology_version: "free-patterns-5.1.0",
  action: null,
  presentation: makePresentation(key, index < 5)
}));
const optionFeedback = {
  mobility: "Yes — Mobility is the strongest recurring way of helping across the established pool.",
  durability: "Durability shows up in the pool, but Mobility has the stronger cross-hero coverage.",
  range: "Range shows up in the pool, but Mobility has the stronger cross-hero coverage.",
  setup: "Setup shows up in the pool, but Mobility has the stronger cross-hero coverage.",
  "hero:1": "Yes — Anti-Mage stands apart from the pool most clearly.",
  "hero:2": "Axe fits the pool more closely. Anti-Mage stands apart more clearly.",
  "hero:3": "Invoker fits the pool more closely. Anti-Mage stands apart more clearly.",
  "hero:4": "Rubick fits the pool more closely. Anti-Mage stands apart more clearly."
};
const option = (key, label, hero_id = null) => ({ key, label, hero_id, feedback: optionFeedback[key] ?? null });
const pages = [
  { id: "element-scan", kind: "element_scan", section: "elements", title: "The pieces of your Dota pattern", body: "Eighteen observable Elements make the report legible.", content: { scanning_body: "Reconstructing the signals we found. The strongest three get a closer look next.", ready_body: "Eighteen observable Elements make the report legible. The strongest three get a closer look next." }, evidence_keys: elementKeys, options: [] },
  ...elements.slice(0, 3).map((item) => ({ id: `element-${item.key}`, kind: "element_highlight", section: "elements", title: item.label, body: `${item.zone} signal · moderate confidence.`, content: { observation: `${item.label} landed in the ${item.zone} zone across the bounded summary history.`, why_highlight: "It was selected as one of the clearest signals in this report.", evidence: "The receipt below shows the summary fields supporting this signal.", what_to_notice: "Notice the zone and the sample together; neither is a verdict.", guardrail: "This describes an observed pattern, not why it happened." }, evidence_keys: [item.key], element_key: item.key, options: [] })),
  ...patterns.slice(0, 5).map((item) => ({ id: `pattern-${item.key}`, kind: "pattern_highlight", section: "patterns", title: item.label, body: "A qualified relationship between Elements.", content: { meaning: "A qualified relationship between Elements.", observations: ["Breadth reads Focused.", "Stability reads Focused."], worth_noticing: "The relationship is visible in the Element zones below.", player_read: "This relationship describes how the signals moved together; it does not claim a cause.", takeaway: "Keep an eye on whether the same relationship appears in another window.", guardrail: "The result is bounded by the summary fields and the required Element evidence.", presentation_copy: item.presentation.copy }, presentation: item.presentation, evidence_keys: item.element_keys, pattern_key: item.key, options: [] })),
  { id: "hero-common-thread", kind: "hero_common_thread_question", section: "hero_portfolio", title: "What keeps showing up across your established heroes?", body: "Choose the way of helping you think keeps recurring, then compare it with the evidence-backed read.", content: { boundary: "This describes what the heroes tend to offer; it does not prove those tools were used correctly in every match.", correct_label: "You got it.", incorrect_label: "Not quite." }, evidence_keys: [], portfolio_key: "common_thread", options: [option("mobility", "Mobility"), option("durability", "Durability"), option("range", "Range"), option("setup", "Setup")] },
  { id: "hero-exception", kind: "hero_exception_question", section: "hero_portfolio", title: "Which hero gives your pool a different kind of Dota?", body: "Pick the hero you expect to feel most different from the rest of the pool.", content: { boundary: "Different does not mean better or worse.", correct_label: "Yep.", incorrect_label: "Good guess — but not this one." }, evidence_keys: [], portfolio_key: "exception", options: [option("hero:1", "Anti-Mage", 1), option("hero:2", "Axe", 2), option("hero:3", "Invoker", 3), option("hero:4", "Rubick", 4)] },
  { id: "pool-evolution-question", kind: "pool_evolution_question", section: "hero_portfolio", title: "How do you think your hero pool has changed recently?", body: "Choose the description that feels closest. This is a self-assessment, not a score.", content: { locked_copy: "Complete the self-assessment above to see the report read." }, evidence_keys: [], portfolio_key: "evolution", options: [option("more_experimental", "I’ve become more experimental"), option("same_style", "My heroes changed, but my style didn’t"), option("different_kind", "I’ve shifted toward a different kind of hero"), option("not_changed", "It hasn’t changed much")] },
  { id: "pool-evolution-reveal", kind: "pool_evolution_reveal", section: "hero_portfolio", title: "Pool Evolution", body: "New heroes. Same taste. Your recent picks look different, but the ways you ask your heroes to help barely moved.", content: { copy: "New heroes. Same taste. Your recent picks look different, but the ways you ask your heroes to help barely moved.", locked_copy: "Complete the self-assessment above to see the report read." }, evidence_keys: [], portfolio_key: "evolution", options: [] },
  { id: "hero-mirror", kind: "hero_mirror_reveal", section: "finale", title: "Your Hero Mirror", body: "One last comparison: your observable behavior against a hero-shaped reference.", content: { closed: "One last comparison: your observable behavior against a hero-shaped reference.", available: "Of the heroes you've played enough for us to trust, Anti-Mage is where your usual Dota shows up most clearly.", qualifier: "Not your best hero. Not necessarily your most played.", guardrail: "This is not a personality test. We're not saying you are Anti-Mage. We're saying your games on Anti-Mage most closely resemble the way you usually play Dota." }, evidence_keys: [], portfolio_key: "hero_mirror", options: [] },
  { id: "final-card", kind: "final_card", section: "finale", title: "The part worth sharing", body: "Your strongest Elements, Patterns, Hero Portfolio, and Mirror in one bounded report.", evidence_keys: [], options: [] },
  { id: "deep-dive", kind: "deep_dive", section: "finale", title: "Tell me more", body: "Selected match-detail analysis can investigate mechanisms behind summary-level discoveries.", evidence_keys: [], options: [] }
];

const report = {
  report_id: reportId,
  schema_version: "free-dna-report-5.2.0",
  report_variant: "free_dna_report",
  noindex: true,
  identity: { display_name: "Fixture player", avatar_url: null, rank_tier: null },
  metadata: { created_at: "2026-01-01T00:00:00+00:00", expires_at: null, data_from: null, data_to: null, processed_matches: 60, eligible_matches: 60, history_limit: null, raw_history_hash: "fixture-history", history_tier: "normal" },
  versions: { eligibility: "summary-eligibility-1.0.0", sessions: "sessions-5.0.0", features: "dna-features-5.0.0", behavior_model: "behavior-model-5.2.0", element_registry: "free-elements-5.1.0", pattern_registry: "free-patterns-5.1.0", pattern_ranking: "free-pattern-ranking-5.0.0", pattern_actions: "pattern-actions-5.0.0", presentation: "pattern-presentation-5.2.0", hero_taxonomy: "fixture-taxonomy", hero_knowledge: "hero-knowledge-fixture", hero_relationships: "hero-relationships-1.0.0", hero_expressions: "hero-expressions-1.0.0", hero_reliability: "hero-reliability-1.0.0", hero_matchups: "hero-matchups-1.0.0", hero_synergies: "hero-synergies-1.0.0", hero_situations: "hero-situations-1.0.0", hero_portfolio: "hero-portfolio-1.2.0+hero-portfolio-config-1.0.0", hero_mirror: "hero-mirror-1.2.0", story: "free-story-5.2.0", copy: "free-dna-copy-5.2.0", model: "fixture-model", template: "templates-1.0.0", share_renderer: "share-svg-4.1.0", analysis_version_fingerprint: "fixture-fingerprint", performance_proxy: "performance-proxy-5.0.0", recency_weighting: "recency-weighting-5.0.0", sessionization: "sessions-5.0.0" },
  reproducibility: { model_version: "free-dna-model-5.2.0", element_registry_version: "free-elements-5.1.0", pattern_registry_version: "free-patterns-5.1.0", hero_taxonomy_version: "fixture-taxonomy", hero_knowledge_version: "hero-knowledge-fixture", performance_proxy_version: "performance-proxy-5.0.0", sessionization_version: "sessions-5.0.0", recency_weighting_version: "recency-weighting-5.0.0", generated_at: "2026-01-01T00:00:00+00:00", window_start: null, window_end: null, input_snapshot_hash: "fixture-history", raw_match_count: 60, usable_match_count: 60, deduplicated_match_count: 60, session_count: 12, completed_session_count: 10, left_censored_session_count: 1, right_censored_session_count: 1, role_hint_coverage: 1, hero_taxonomy_coverage: 1, effective_sample_size: 48, recency_config: { half_life_days: 180, version: "recency-weighting-5.0.0" }, session_gap_config: { gap_minutes: 90, clock_tolerance_seconds: 300 } },
  quality: { overall_confidence: "moderate", history_tier: "normal", missing_data_flags: [], partial: false, warnings: [], available_elements: 18, limited_elements: 0, unavailable_elements: 0, qualified_patterns: 5 },
  elements,
  patterns,
  highlights: { element_keys: elementKeys.slice(0, 3), pattern_keys: patternKeys.slice(0, 5) },
  hero_portfolio: {
    common_thread: { status: "available", trait_key: "mobility", trait_label: "Mobility", weighted_coverage: .74, hero_count: 5, denominator: 5, secondary_traits: ["Range", "Setup"], options: [option("mobility", "Mobility"), option("durability", "Durability"), option("range", "Range"), option("setup", "Setup")], correct_option_key: "mobility", confidence_score: .76, limitations: [] },
    exception: { status: "available", hero_id: 1, hero_name: "Anti-Mage", pool_traits: ["Mobility", "Range"], exception_traits: ["Mobility"], options: [option("hero:1", "Anti-Mage", 1), option("hero:2", "Axe", 2), option("hero:3", "Invoker", 3), option("hero:4", "Rubick", 4)], correct_option_key: "hero:1", distance: .62, margin: .18, confidence_score: .74, limitations: ["Different does not mean better or worse."] },
    evolution: { status: "available", variant: "new_heroes_same_toolkit", earlier_hero_ids: [1, 2], recent_hero_ids: [1, 2, 3], earlier_traits: ["Mobility", "Range"], recent_traits: ["Mobility", "Range", "Setup"], hero_distribution_shift: .34, toolkit_distribution_shift: .08, confidence_score: .72, earlier_sample_size: 24, recent_sample_size: 24, earlier_taxonomy_coverage: 1, recent_taxonomy_coverage: 1, limitations: [] },
    hero_mirror: { status: "available", hero_id: 1, hero_name: "Anti-Mage", similarity_score: .81, runner_up_hero_id: 2, margin: .09, player_behavior: { involvement: "Active", finishing: "Closer", deaths: "Mixed", role_context: "Carry-heavy" }, hero_behavior: { involvement: "Active", finishing: "Closer", deaths: "Safe", role_context: "Carry-heavy" }, confidence_score: .66, limitations: ["This is not a personality test."] },
    version: "hero-portfolio-1.2.0+hero-portfolio-config-1.0.0"
  },
  story: { version: "free-story-5.2.0", ordered_pages: pages.map((item) => item.id) },
  pages,
  shares: { final: { display_name: "Fixture player", strongest_elements: elements.slice(0, 3).map((item) => ({ key: item.key, label: item.label, zone: item.zone })), strongest_patterns: patterns.slice(0, 5).map((item) => ({ key: item.key, label: item.label })), hero_portfolio: { common_thread: "Mobility", exception_hero: "Anti-Mage", pool_direction: "New heroes. Same taste." }, hero_mirror: { hero_id: 1, hero_name: "Anti-Mage" } }, privacy_defaults: { show_name: true, show_avatar: true, show_raw_id: false } },
  deep_dive: { available: true, cta_label: "Tell me more", href: "/?mode=deep_scan", copy: "Opt-in detail analysis." },
  methodology: { free_summary_only: true, session_gap_minutes: 90, session_policy_version: "sessions-5.0.0", notes: ["Summary-only fixture."] },
  cost: { history_requests: 1, detail_requests: 0, parse_requests: 0, parse_status_requests: 0, cache_hits: 0, estimated_cost_units: 1 }
};

function sendJson(response, status, value) {
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(value));
}

const api = http.createServer((request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${apiPort}`);
  if (request.method === "GET" && url.pathname === `/v1/reports/${reportId}`) return sendJson(response, 200, report);
  if (request.method === "GET" && url.pathname.startsWith(`/v1/reports/${reportId}/share/`)) {
    response.writeHead(200, { "Content-Type": "image/svg+xml", "X-Robots-Tag": "noindex" });
    return response.end(`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350"><text>Dota DNA final</text></svg>`);
  }
  if (request.method === "POST" && url.pathname === "/v1/analyses") return sendJson(response, 202, { job_id: "fixture-job", status: "queued", reused: false, events_url: "/v1/analyses/fixture-job/events" });
  if (request.method === "GET" && url.pathname === "/v1/analyses/fixture-job") return sendJson(response, 200, { job_id: "fixture-job", status: "completed", stage: "completed", warnings: [], report_id: reportId, message: null, failure_code: null });
  if (request.method === "GET" && url.pathname === "/v1/analyses/fixture-job/events") {
    response.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
    return response.end("data: {\"stage\":\"completed\",\"status\":\"completed\"}\n\n");
  }
  return sendJson(response, 404, { message: "Not found" });
});

await new Promise((resolve) => api.listen(apiPort, "127.0.0.1", resolve));
const next = spawn("npm", ["run", "dev", "--", "--hostname", "127.0.0.1"], { env: { ...process.env, API_BASE_URL: `http://127.0.0.1:${apiPort}` }, stdio: "inherit" });
function shutdown() { next.kill("SIGTERM"); api.close(); }
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
next.on("exit", (code) => { api.close(); process.exit(code ?? 0); });
