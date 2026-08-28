# Free DNA OpenDota Parsed-Data Strategy

## Decision

Use already-parsed OpenDota detail as **background enrichment**, not as a prerequisite for instant Free and not as a replay-parse queue.

The existing one-call history response can identify stored parser-version-22 matches, but its only parsed-derived behavioral fields are lane, lane role, and roaming. That is enough for one cautious Role Shape experiment, not two strong Findings. The useful fields—purchases, wards, minute curves, objectives, kill timing, and fight context—require per-match detail GETs.

## Product flow

```text
one 365-day history call
  → current Free DNA report returns unchanged
  → private parsed-match eligibility list (source_version == "22")
  → optional, owner-approved background detail fetch with a fixed cap
  → cached detail evidence
  → experimental detectors
  → omit unless future support/stability/qualification gates pass
```

The report never waits for enrichment. Missing parsed data means omission, not a thinner report, fabricated evidence, or a parse submission.

## Tier policy

| tier | source | product use |
|---|---|---|
| 1 | history/cached: lane, lane role, roaming | Free-instant context; Role Shape research only |
| 2 | already-parsed match detail | bounded background enrichment; later Free only if latency and qualification pass |
| 3 | new replay parse/raw replay | Deep only |

## Candidate order

1. **Build Adaptation** — purchase sequence versus lineup and game state.
2. **Resource Rhythm** — resource response around fights/objectives.
3. **Fight Clock** — within-match timing only, kept separate from session/result response.
4. **Vision Rhythm** — role-conditional and omitted when opportunity support is absent.

Role Shape remains a Tier-1 descriptive experiment. Roaming Tendency is not a second Finding: it is too close to another role label and too dependent on a parser heuristic.

## Fixed safety rules

- Never submit a parse job in Free.
- Never fetch unparsed detail hoping it becomes parsed.
- Never condition a calibration population on high parsed count.
- Never use fresh sealed validation for candidate search.
- Cache detail by match ID and parser version; invalidate only on verified schema/version drift.
- Keep raw match/account identifiers private and out of tracked evidence.
- Preserve current V6.1 thresholds, estimators, family universe, public contract, and report-generation path.

## Pilot gate

First run only the four-call provider QA in `docs/prompts/free-dna-opendota-parsed-pilot-luna.md`, after explicit owner approval. It verifies live marker semantics, detail availability without parsing, shape, and one-call latency. It does not calibrate a Finding.

Only after that QA passes should a separate analytical plan predeclare a representative development sample, fixed detail cap, candidate formulas, confounder controls, missingness model, stability gates, and a fresh sealed validation. The local audit suggests 30–50 matches may be enough to research Tier-1 context; it establishes no Tier-2 threshold.

## Ship/hold rule

Hold parsed Findings out of instant Free until both conditions are true:

1. at least two Tier-2 candidates show repeatable, distinct player-level signals under hero/role/outcome/time controls; and
2. the bounded fetch path has measured latency/cost compatible with the Free experience.

Otherwise keep enrichment backstage or move it to Deep.
