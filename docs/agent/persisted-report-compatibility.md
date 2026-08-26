# Persisted Report Compatibility

Read the [root agent operating contract](../../AGENTS.md) first. This is the
primary compatibility manual for report producers, API consumers, and
frontend renderers.

## Core contract

Persisted report JSON is effectively a historical API contract. It is
production data written by an earlier report producer and read by code that
may be much newer. The current TypeScript or Pydantic model is not proof that
every valid historical payload contains every currently known field.

The compatibility requirement is:

    a valid persisted report
        → remains readable by the supported renderer
        → without report regeneration
        → without changing its analytical meaning

A new report renderer MUST support:

- the newest/current report fixture; and
- at least one sanitized production-shaped historical fixture from a previous
  production implementation.

If a payload version truly cannot be rendered by the current implementation,
route it to an explicit versioned renderer or an intentional unsupported state.
Do not let an absent optional field become a runtime crash.

## Additive evolution

Prefer additive public report evolution:

1. Preserve existing analytical fields and their semantics.
2. Add a presentation-only field as optional.
3. Make the new renderer use it only when it is present and valid.
4. Define the omission behavior for old reports.
5. Add a new fixture for the new shape; never overwrite the historical one.

A new field is not automatically presentation-only. If it changes a finding,
confidence, evidence, significance, cohort, identity qualification, or
publication decision, it changes analytical semantics or the public report
contract and requires the applicable release authorization.

If a new semantic field is mandatory for a new report version, use an explicit
schema version and perform a backward compatibility and consumer audit. Do
not silently make all existing persisted JSON conform by mutating it.

## TypeScript types versus runtime JSON

TypeScript types describe developer expectations at compile time. The API
response and persisted JSON are runtime values. They can contain:

- an older schema version;
- a missing field;
- an explicit null;
- an empty array;
- a partially populated nested object; or
- a historical field shape.

The renderer MUST validate or normalize untrusted runtime structure before
using it. A non-optional property, type assertion, non-null assertion, or
current fixture does not establish historical presence.

Keep these states meaningful:

- missing presentation data → omit or suppress the dependent presentation;
- null data → follow the contract's explicit null behavior;
- empty collection → render the empty state only when that state is truthful;
- invalid structure → reject or degrade the affected section, not the entire
  report, unless the report's versioned contract makes the root invalid.

Do not use a default that turns “no evidence” into a positive analytical
claim.

## Compatibility boundary

Report rendering should use this boundary:

    raw persisted JSON
            ↓
    runtime validation / normalization
            ↓
    presentation-safe model
            ↓
    story composer
            ↓
    renderer

### What runtime normalization MAY do

Normalization may repair STRUCTURE:

- confirm the root value is an object before reading properties;
- validate primitive types and discard malformed collection entries;
- turn an absent optional collection into an empty collection when that means
  “there are no items to display”;
- preserve explicit null where null has contract meaning;
- accept a documented historical alias when the schema version supports it;
- isolate a malformed optional section so other valid sections can render; and
- produce an explicit unavailable state for a missing presentation input.

Normalization may make a safe structural representation. It must not make a
new analytical conclusion.

### What runtime normalization MUST NOT do

Normalization must not fabricate ANALYTICAL MEANING. It must not derive or
invent:

- findings;
- confidence;
- evidence;
- evidence references;
- statistical significance;
- semantic outcomes;
- identity slots;
- causal explanations;
- cohort membership;
- analytical classifications;
- publication eligibility; or
- a new threshold-based interpretation.

If an analytical input is missing, the story composer must suppress or
degrade the dependent story. It must not replace the input with a plausible
default.

## Degradation rules

| Missing or invalid input | Allowed behavior | Forbidden behavior |
| --- | --- | --- |
| story_band | Omit the band-specific story or render rows without bands if that is already supported by the contract. | Infer a band from match counts, shares, or new frontend thresholds. |
| chronology | Omit chronology UI and its navigation step. | Reconstruct a timeline from display order or guessed dates. |
| identity slots | Omit Signature UI and continue with other supported pages. | Create PRIMARY, TWIST, or ANCHOR slots from hero or finding data. |
| comparison rows | Render only existing evidence or omit the comparison section. | Create a baseline, cohort row, or direction from unrelated metrics. |
| limitations | Omit optional limitation copy or use only contractually supplied generic UI. | Claim that limitations do not exist. |
| optional supporting evidence | Omit the evidence block or show an explicit unavailable state. | Convert the headline or finding into evidence. |

The entire report must not crash because presentation-only information is
unavailable. If the missing value is required for a supported analytical
claim, suppress that claim rather than populating a placeholder that looks
like evidence.

## Compatibility example: hero portfolio

OLD REPORT:

    hero_portfolio.heroes:
    - display_name
    - match_count
    - share

NEW REPORT:

    hero_portfolio.heroes:
    - display_name
    - match_count
    - share
    - story_band

The new UI may use story_band when it is present and has the expected value.
The new UI must not crash when story_band is absent. It may omit the
band-specific story and still render the supported hero rows.

It may NOT invent a story_band using arbitrary new frontend thresholds. A
frontend heuristic would create analytical meaning that the old report never
published. If the band is important enough to be analytical, it belongs in a
versioned producer contract and analytical release, not in compatibility
normalization.

## Other historical absence cases

### Missing chronology

Render the report's non-chronological pages and remove the chronology page
from the story sequence. Recalculate total pages, progress indicators, and
navigation bounds after omission. Do not create dates or order from array
positions.

### Missing identity slots

Render the identity summary only from the fields it actually contains. Omit
Signature UI when the relevant slots are absent or invalid. Do not copy a
headline into a slot or infer a slot kind.

### Missing comparison data

Show the player's available evidence without a comparison section, or show an
explicit unavailable state. Do not construct a cohort, baseline, or
statistical contrast from a different field.

### Missing limitations

Omit optional limitation copy if the persisted report has none. Do not replace
missing limitations with a claim that the analysis is unlimited, causal, or
more certain than the stored report says.

### Missing optional supporting evidence

Keep only the supported headline, measurement, or story content. Omit
supporting evidence UI when its evidence items or references are unavailable.
Never turn a copy string into an evidence reference.

## Schema versions and public contracts

Schema versions are routing and compatibility signals. When a contract
evolves:

- keep old schema versions readable by their existing renderer or by a
  deliberately compatible new renderer;
- add, rather than replace, historical fixtures;
- document whether a field is analytical, presentation-only, or internal;
- audit all API and frontend consumers before making a field required;
- preserve private identifier handling across versions; and
- record a new analytical release only when analytical semantics actually
  change.

Changing a TypeScript type is not a migration. Changing a Pydantic schema is
not evidence that persisted rows were rewritten. Treat storage, API output,
and frontend rendering as separate compatibility surfaces.

## Production-shaped historical fixtures

At least one historical fixture must be derived from the structural shape of a
real persisted production report. It must be sanitized:

- account IDs;
- Steam IDs;
- report IDs;
- match IDs;
- session IDs;
- access tokens;
- protected cohort references; and
- other private identifiers.

Sanitization must preserve the cases that expose compatibility bugs:

- missing fields;
- explicit nulls;
- nesting;
- array shapes;
- optional states;
- published and suppressed structure;
- hero portfolio structure;
- identity structure; and
- supporting evidence structure.

Store compatibility fixtures in the recommended directory:

    apps/web/tests/fixtures/persisted-reports/

The directory is a convention for future fixture work. A current fixture and a
historical fixture are separate artifacts. When the contract evolves, add a
new fixture and keep the old fixture unchanged.

Do not rebuild a historical fixture solely from current TypeScript types.
Doing so removes the very absence and nesting cases the fixture is meant to
protect.

## No report regeneration requirement

Presentation validation should read an existing persisted report or a
sanitized fixture. A presentation change must not require generating a new
report. Do not spend OpenDota calls to validate layout, traversal, optional
fields, or browser compatibility.

If the only way to make the new UI render is to regenerate reports, change the
server projection, or change analytical output, STOP. Report the requested
cross-layer change and its compatibility risk.

## Analytical meaning stays authoritative

The persisted report's analytical content remains authoritative for that
report. A renderer can choose how much of it to disclose, but it cannot change:

- whether a finding qualified;
- its confidence or significance;
- its evidence or evidence references;
- its semantic outcome;
- its cohort membership;
- its identity qualification; or
- its causal limits.

Presentation may omit content. It may not upgrade, downgrade, or reinterpret
analytical semantics to fill a visual gap.

## Compatibility release checklist

Before calling a report renderer change safe:

- [ ] Current fixture renders.
- [ ] A production-shaped historical fixture renders.
- [ ] Missing optional fields degrade by omission.
- [ ] Progress and navigation reflect omitted pages.
- [ ] No analytical information is fabricated.
- [ ] Existing persisted data does not need regeneration.
- [ ] Public contract changes, if any, are classified and audited.
- [ ] Private identifiers remain protected.
- [ ] Browser checks pass in the applicable environments.
- [ ] The Vercel Preview smoke test uses an existing persisted report when
      possible.

If any item is uncertain, follow the root contract's STOP conditions.
