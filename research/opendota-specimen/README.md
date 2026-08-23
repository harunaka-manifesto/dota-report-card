# OpenDota parsed-match specimen

- Endpoint: `GET https://api.opendota.com/api/matches/8431600692`
- Acquisition date: 2026-08-23 (Asia/Jakarta)
- OpenDota requests made for this research: exactly one
- Raw response: `match_8431600692.raw.json`
- Payload size: 288,313 bytes
- SHA-256: `7c0f73a8af1abd3e015a806a8b10289d801046cfca4a8b113a93e7409525edd5`
- Parse proof: `version = 22`, `od_data.has_parsed = true`
- Match: Team Falcons 35–12 Team Spirit, 36:25, Captains Mode, FISSURE Universe Episode 6
- Roster completeness: 10/10 non-null account IDs and persona names
- Parsed structures present: 37-point team gold/XP curves, 10 × 37 player economy/XP/CS curves, 450 purchase events, 47 kill events, 5 buybacks, 46 rune pickups, 96 ward placements, 2 parser-defined teamfights, and 29 objectives.

The JSON is preserved byte-for-byte as returned. All inspection after acquisition was performed against this local file; no second OpenDota API request was made.

The specimen is a professional match rather than an ordinary ranked pub. It was selected because its parsed status and telemetry richness could be independently established before spending the single permitted API request. That improves acquisition certainty but makes the specimen unsuitable as a pub-behavior baseline; the research document treats it only as a schema specimen.
