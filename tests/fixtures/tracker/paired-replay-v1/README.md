# Paired replay capture, version 1

Sanitized real ten-player responses for the same match. The OpenDota source was
first observed without replay statistics, accepted one processing request, then
had statistics at a later read on 2026-09-22. That observation does not establish
the exact processing latency. STRATZ is a retained capture from the September 14
local evidence corpus; no live STRATZ request was made for this fixture.

An allowlist removed accounts, Steam identifiers, names, chat, replay URLs,
rank/MMR, opaque scores and vendor role labels. The match ID is synthetic and
shared by both files. Hero, item, ability and game-unit identifiers remain;
event keys such as attackername contain game-unit names. Missing/null fields,
array lengths and recorded gameplay values are preserved. STRATZ has a positive
`statsDateTime` and replay arrays despite `isStats: false`; the timestamp admits
field-level validation without requiring agreement between those two markers. Do not overwrite
these files when a provider changes shape.

Verified in this specimen: known summary facts agree across all ten players;
net worth, cumulative last hits and cumulative camps stacked agree at 10:00 and
20:00. STRATZ net worth index t means t:00; last-hit entries are interval deltas;
campStack index t is cumulative at (t+1):00. These distinctions are exercised by
the checkpoint tests and agree with the normative insights annex.

Differences are preserved: early net-worth points differ (usually one gold, one
point by 35), one cumulative last-hit boundary differs, and some kill/death event
timestamps differ by up to two seconds. No tolerance or blanket provider parity
is asserted. Conflict tests withhold exact conflicting points. Gold/XP/damage
series and event translation require their own dependency-level verification.

These are backend provider fixtures, not persisted report renderer fixtures.
