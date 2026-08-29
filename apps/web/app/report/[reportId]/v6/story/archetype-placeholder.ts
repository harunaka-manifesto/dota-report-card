/**
 * THE NARROW EXCEPTION.
 *
 * `modules.archetype` and `modules.final_identity_card` ship as `not_ready`
 * and no backend code path upgrades them.  Left alone, Pages 29-31 and 33
 * cannot render and the report ends on the collage, which has no ending.
 *
 * So the frontend renders exactly those two modules on `not_ready`, supplying
 * the archetype title, description, and anchor bodies from the constant below.
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
  /** Page 30 headline and the Page 33 archetype line. */
  name: "THE RECURRING PLAYER",
  /** One sentence, descriptive, never diagnostic. */
  description:
    "Someone whose year reads back clearly from the outside: the same queues, the same short list of heroes, the same willingness to load in one more time.",
  /**
   * Page 31 anchor bodies.  Anchor MEMBERSHIP is not placeholder — it is
   * gated on which pages actually rendered, in `compose.ts`.  Only this text
   * is frontend-owned.
   */
  anchors: {
    hero_pool: {
      label: "Your hero pool.",
      body: "The heroes you came back to most often across the year.",
    },
    post_loss: {
      label: "After losses.",
      body: "What the next game looked like once a loss was already on the board.",
    },
    transfer: {
      label: "Outside your usual heroes.",
      body: "What stayed the same on the games that were not from your short list.",
    },
  },
} as const;

/**
 * Page 31's scripted close is "Not a personality test. Just a year of Dota
 * leaving fingerprints." — which is false while one constant is shown to
 * every player.  Owner decision (2026-08-29): ship the placeholder live with
 * the line SUPPRESSED rather than replaced, so no new copy is claimed and no
 * false personalization is asserted.  Page 31 closes on the Endstop instead.
 *
 * When the archetype engine lands, restore the scripted line together with
 * the deletion of this exception.
 */
export const ARCHETYPE_PLACEHOLDER_CLOSING_LINE: string | null = null;

export type ArchetypeAnchorKey = keyof typeof ARCHETYPE_PLACEHOLDER.anchors;
