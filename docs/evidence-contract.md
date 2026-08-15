# Evidence contract

Every evaluated insight is persisted as an evidence object, whether it is published or suppressed. The object contains stable insight and concept IDs, report scope, player and cohort metrics, unit, match/situation/parsed-match denominators, parse coverage, role certainty, selected cohort fallback, interval, confidence, confounders, action target, source match IDs, and feature/cohort/model/template versions.

The provenance map links the same source match IDs to the raw OpenDota payload endpoint, normalized match record, and derived feature record. A published card is a projection of this object; it does not recalculate metrics.

Templates may choose approved phrasing, but may not add findings, modify values or denominators, omit material confounders, or upgrade confidence.

