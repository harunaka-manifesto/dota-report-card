/**
 * THE NARROW EXCEPTION.
 *
 * `modules.archetype` and `modules.final_identity_card` ship as `not_ready`
 * and no backend code path upgrades them.  Left alone, Pages 29-30 and 33
 * cannot render and the report ends on the collage, which has no ending.
 *
 * So the frontend renders exactly those two modules on `not_ready`, supplying
 * the neutral report artifact below. It does not present the constant as a
 * personalized archetype.
 *
 * THIS EXCEPTION APPLIES TO `archetype` AND `final_identity_card` AND TO
 * NOTHING ELSE, EVER.  Every other module renders only on `available` or
 * `degraded`.  `compose.ts` implements it as a two-key allowlist, not as a
 * general "render not_ready anyway" branch, and
 * `tests/unit/story-compose.spec.ts` asserts no other module can slip through.
 *
 * When the archetype engine lands and the backend flips these modules to
 * `available`, delete `ARCHETYPE_NOT_READY_RENDER_EXCEPTION` and this file.
 * The payload values then take over with no other change — which is why the
 * placeholder is NEVER written back into payload-shaped state.
 *
 * One placeholder only.  No per-player variation, no rotation, no seeded pick
 * from `story_input_sha256`: fabricated personalization is worse than an
 * honest constant.
 */

import type { StoryModuleKey } from "./payload-types";

export const ARCHETYPE_NOT_READY_RENDER_EXCEPTION: ReadonlySet<StoryModuleKey> = new Set<StoryModuleKey>([
  "archetype",
  "final_identity_card",
]);

export const ARCHETYPE_PLACEHOLDER = {
  /** Neutral Page 30/Page 33 artifact title; never a player classification. */
  name: "THE YEAR IN QUEUE",
  /** One sentence about the report, not the player. */
  description:
    "A report assembled from the matches, results, hero choices, and qualified patterns this history could support.",
} as const;
