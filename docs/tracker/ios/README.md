# iOS client — pointer

The native SwiftUI client lives in a **separate repository**: `~/Documents/dota-tracker-ios` (local path; remote to
be set by the owner). This backend repository remains the single source of product truth: the iOS repo's design
system, screen specs and PRDs cite `docs/tracker/<feature>/SSOT.md` and `DESIGN-REQUIREMENTS.md` and never
redefine a product rule.

What the iOS repo holds (as of 2026-10-07):

- `docs/design-system/` — tokens (`design/tokens/tokens.json`, W3C DTCG), components, states and copy,
  navigation, motion, Figma sync.
- `docs/screens/S1…S9` — one spec per surface, each state from the feature brief's §8 mapped to a treatment.
- `docs/prds/` — the build program: foundation stories F0–F9 and feature PRDs P1–P12, with an agent operating
  contract so an agent can be told "build PRD X".
- `docs/backend-asks.md` — additive API requests raised by the design work (viewer `hero_id` on Match Detail,
  `match_ref` in the READY push, documented ETag/304 and problem+json, display name/avatar on Profile, golden
  fixtures for untested states, and more). None is scheduled until the owner decides.

Owner decisions taken on 2026-10-07 for the client: tabs Home · Matches · Progress · Profile (Settings via the
Profile header); Home default mode bucket Standard; dark-first with a light theme; iOS 26 minimum; English and
Indonesian from day one.
