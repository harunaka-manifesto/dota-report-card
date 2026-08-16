import http from "node:http";
import { spawn } from "node:child_process";

const apiPort = Number(process.env.FIXTURE_API_PORT ?? 8001);
const reportId = "fixture-report";

const dimensionKeys = [
  "breadth", "role", "adaptability", "activity",
  "orientation", "resilience", "endurance", "rhythm"
];

const dimensions = dimensionKeys.map((key, index) => ({
  key,
  status: "available",
  score: 0.35 + index * 0.04,
  centered_score: -0.3 + index * 0.08,
  label: `Fixture ${key}`,
  confidence: "moderate",
  confidence_score: 0.72,
  sample_size: 60,
  effective_sample_size: 48,
  coverage: 1,
  evidence: [{ key: "sample", value: 60, unit: "matches", denominator: 60 }],
  confounders: [],
  missing_reasons: [],
  copy: {
    headline_key: `${key}.headline`,
    receipt_key: `${key}.receipt`,
    receipt_params: {},
    left_label: "Lower",
    right_label: "Higher"
  },
  methodology_version: "dna-scoring-1.1.0",
  descriptor_eligible: true
}));

const descriptor = (key, label, dimension) => ({ key, label, dimension });
const hero = {
  hero_id: 1,
  name: "Anti-Mage",
  portrait_url: null,
  score: 0.82,
  component_scores: {},
  matches: 18,
  roles: ["carry"],
  traits: ["mobility"],
  receipts: ["18 observed games"],
  reason_key: "signature_hero",
  confidence: "moderate",
  portrait_asset_version: "fixture-1"
};

const page = (id, kind, section, title, body = null, extra = {}) => ({
  id, kind, section, title, body, evidence_keys: [], ...extra
});

const pages = [
  page("steam-input", "input", "intro", "Enter a player"),
  page("player-found", "player_found", "intro", "Player found"),
  page("analysis", "analysis", "intro", "Reading history"),
  page("report-reveal", "reveal", "intro", "Your Dota DNA", "We found the patterns that only show up when the signals are read together."),
  page("finding-contrast", "finding", "findings", "Your hero pool is wide. Your safety zone is not.", "You explore broadly overall, but your history becomes more concentrated around familiar heroes when results are less stable.", { finding_key: "contrast" }),
  page("finding-strength", "finding", "findings", "Your strongest habit travels across the history.", "A positive pattern with two deterministic receipts.", { finding_key: "strength" }),
  page("experiment-adjacent", "experiment", "findings", "Test the edge of your comfort zone", "In your next 5 post-loss queues, choose one adjacent comfort hero.", { finding_key: "contrast", experiment_key: "adjacent_pick_after_loss" }),
  page("identity-card", "identity_card", "finale", "Your hero pool is wide. Your safety zone is not.", "The Adapter", { finding_key: "contrast" }),
  page("dna-xray", "dna_xray", "dna", "Your full DNA", "All eight dimensions remain available as evidence."),
  page("deep-dive", "deep_dive", "finale", "Explore Deep Dive", "A separate, opt-in product.")
];

const report = {
  report_id: reportId,
  schema_version: "free-dna-report-2.0.0",
  report_variant: "free_dna_report",
  noindex: true,
  identity: { display_name: "Fixture player", avatar_url: null, rank_tier: null },
  metadata: {
    created_at: "2026-01-01T00:00:00+00:00",
    expires_at: null,
    data_from: null,
    data_to: null,
    processed_matches: 60,
    eligible_matches: 60,
    history_limit: 500,
    raw_history_hash: "fixture-history",
    history_tier: "normal"
  },
  versions: {
    eligibility: "summary-eligibility-1.1.0",
    sessions: "sessions-1.1.0",
    features: "dna-features-1.1.0",
    dna_scoring: "dna-scoring-1.1.0",
    baselines: "baselines-1.0.0",
    archetype: "archetypes-1.1.0",
    hero_identity: "hero-identity-1.1.0",
    hero_taxonomy: "fixture-taxonomy",
    recommendations: "hero-recommendations-1.1.0",
    findings: "free-findings-1.0.0",
    finding_ranking: "free-finding-ranking-1.0.0",
    story: "free-story-2.0.0",
    copy: "copy-1.0.0",
    model: "fixture-model",
    template: "free-dna-template-1.0.0",
    share_renderer: "share-svg-1.1.0",
    analysis_version_fingerprint: "fixture-fingerprint"
  },
  quality: {
    overall_confidence: "moderate",
    history_tier: "normal",
    missing_data_flags: [],
    partial: false,
    warnings: []
  },
  dimensions,
  archetype: {
    key: "adapter",
    label: "The Adapter",
    fit: 0.81,
    runner_up: null,
    descriptors: [
      descriptor("breadth", "Exploratory", "breadth"),
      descriptor("adaptability", "Adaptable", "adaptability"),
      descriptor("rhythm", "Grinder", "rhythm")
    ],
    contributing_dimensions: [],
    confidence: "moderate",
    explanation_evidence: ["Fixture evidence"],
    classifier_version: "archetypes-1.1.0"
  },
  heroes: {
    signature: hero,
    comfort_picks: [hero],
    patterns: [{ key: "explorer", label: "Explorer", copy_key: "explorer", traits: ["mobility"], role_traits: ["carry"], contributors: ["Anti-Mage"] }],
    recommendations: [],
    taxonomy_version: "fixture-taxonomy",
    limitations: [],
    identity_version: "hero-identity-1.1.0"
  },
  findings: [
    {
      key: "contrast",
      kind: "contradiction",
      headline: "Your hero pool is wide. Your safety zone is not.",
      body: "You explore broadly overall, but your history becomes more concentrated around familiar heroes when results are less stable.",
      interpretation: "You do not avoid experimentation. You appear to rely on familiarity more selectively.",
      confidence: "high",
      receipts: [
        { key: "pool", label: "Hero pool", value: "31 heroes · n=60", context: "dna_feature", confidence: "high" },
        { key: "trust", label: "Familiar picks after losses", value: "61% vs 43% after wins", context: "derived_summary", confidence: "moderate" }
      ],
      related_dimensions: ["breadth", "resilience"],
      related_heroes: [],
      experiment: {
        key: "adjacent_pick_after_loss",
        title: "Test the edge of your comfort zone",
        instruction: "In your next 5 post-loss queues, choose one adjacent comfort hero.",
        hypothesis: "Your playable pool may be wider than the first familiar pick after a loss.",
        measurement: "Notice whether activity and result quality stay close to your normal comfort games.",
        window: "5 matches"
      },
      share_copy: "My hero pool is wide. Apparently my safety zone is not."
    },
    {
      key: "strength",
      kind: "strength",
      headline: "Your strongest habit travels across the history.",
      body: "Activity and role evidence stay visible across the bounded sample.",
      interpretation: "This is the clearest positive pattern available in the fixture history.",
      confidence: "moderate",
      receipts: [
        { key: "activity", label: "Typical activity", value: "18.2 involvement/min · n=60", context: "dna_feature", confidence: "moderate" },
        { key: "role", label: "Dominant role share", value: "62% · n=60", context: "dimension", confidence: "moderate" }
      ],
      related_dimensions: ["activity", "role"],
      related_heroes: [],
      experiment: null,
      share_copy: "One of my strongest Dota habits holds up."
    }
  ],
  story: {
    version: "free-story-2.0.0",
    thesis_key: "contrast",
    strength_key: "strength",
    contradiction_key: null,
    edge_key: null,
    leak_key: null,
    experiment_key: "adjacent_pick_after_loss",
    ordered_pages: pages.map((item) => item.id)
  },
  pages,
  shares: {
    identity: { finding_key: "contrast", headline: "Your hero pool is wide. Your safety zone is not.", archetype: "The Adapter", receipts: ["31 heroes · n=60", "61% vs 43% after wins"] },
    exposed: { finding_key: "contrast", headline: "My hero pool is wide. Apparently my safety zone is not.", archetype: "The Adapter", receipts: ["31 heroes · n=60", "61% vs 43% after wins"] },
    strength: { finding_key: "strength", headline: "One of my strongest Dota habits holds up.", archetype: "The Adapter", receipts: ["18.2 involvement/min · n=60", "62% · n=60"] },
    dna: { archetype: "The Adapter", descriptors: [], match_count: 60, spectra: [] },
    heroes: { signature: hero, comfort: [hero], pattern: null, recommendations: [] },
    final: { archetype: "The Adapter", descriptors: [], match_count: 60, display_name: "Fixture player", signature: "Anti-Mage", pattern: "Explorer", rhythm: "Grinder" },
    privacy_defaults: { show_name: true, show_avatar: true, show_raw_id: false }
  },
  deep_dive: { available: true, cta_label: "Explore Deep Dive", href: "/?mode=deep_scan", copy: "Opt-in detail analysis." },
  methodology: { free_summary_only: true, session_gap_minutes: 90, session_policy_version: "sessions-1.1.0", notes: ["Summary-only fixture."] },
  cost: { history_requests: 1, detail_requests: 0, parse_requests: 0, parse_status_requests: 0, cache_hits: 0, estimated_cost_units: 1 }
};

function sendJson(response, status, value) {
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(value));
}

const api = http.createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${apiPort}`);
  if (request.method === "GET" && url.pathname === `/v1/reports/${reportId}`) {
    sendJson(response, 200, report);
    return;
  }
  if (request.method === "GET" && url.pathname.startsWith(`/v1/reports/${reportId}/share/`)) {
    response.writeHead(200, { "Content-Type": "image/svg+xml", "X-Robots-Tag": "noindex" });
    response.end(`<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350"><text>${url.pathname}</text></svg>`);
    return;
  }
  if (request.method === "POST" && url.pathname === "/v1/analyses") {
    sendJson(response, 202, { job_id: "fixture-job", status: "queued", reused: false, events_url: "/v1/analyses/fixture-job/events" });
    return;
  }
  if (request.method === "GET" && url.pathname === "/v1/analyses/fixture-job") {
    sendJson(response, 200, { job_id: "fixture-job", status: "completed", stage: "completed", warnings: [], report_id: reportId, message: null, failure_code: null });
    return;
  }
  if (request.method === "GET" && url.pathname === "/v1/analyses/fixture-job/events") {
    response.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
    response.end("data: {\"stage\":\"completed\",\"status\":\"completed\"}\n\n");
    return;
  }
  sendJson(response, 404, { message: "Not found" });
});

await new Promise((resolve) => api.listen(apiPort, "127.0.0.1", resolve));
const next = spawn("npm", ["run", "dev", "--", "--hostname", "127.0.0.1"], {
  env: { ...process.env, API_BASE_URL: `http://127.0.0.1:${apiPort}` },
  stdio: "inherit"
});

function shutdown() {
  next.kill("SIGTERM");
  api.close();
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
next.on("exit", (code) => {
  api.close();
  process.exit(code ?? 0);
});
