# Hero relationships and action provenance

P01 and P02 use a separate, deterministic relationship layer. It does not
assign a global player label or rank heroes by public win rate or patch
popularity.
The active artifacts are `hero-relationships-1.0.0` and
`hero-expressions-1.0.0`, both derived from the reviewed checked-in taxonomy.

## Pool-relative relationship model

The player's established hero history is converted into usage-capped taxonomy
vectors. A single heavily sampled hero can contribute at most 35% of the
weighted pool centroid. The centroid exposes dominant traits and
underrepresented traits, while credible role hints supply role compatibility.

Each candidate relationship records named shared traits, unique traits,
functional similarity, role compatibility, complexity distance, and micro
distance. The finite expression layer explains differences such as reach,
frontline presence, sustain, wave clear, push, save/reset, and repositioning
without inferring spell-level behavior.

## Same Playbook

`deepen` candidates preserve the dominant functional core, remain close enough
to the pool's learning distance, fit credible roles where possible, and vary
secondary expression. `stretch` candidates preserve at least one anchor and
add an underrepresented trait while avoiding both near-duplicates and absurd
functional jumps. Established heroes are excluded. Each card carries the
relationship and expression versions used to produce it, plus plain-language
“what stays familiar” and “what changes” fields.

The action returns up to three candidates per direction. It returns a limited
or unavailable state when evidence cannot support the requested count; the UI
never fills a quota with weak candidates.

## Comfort Edge reliability

P02 ranks all usable rows in the previous-365-day Free window with explicit
recency weighting. Heroes with fewer than 10 usable games are not rankable for the
action. Each rankable hero receives a player-relative reliability estimate
from outcome, observable contribution, death exposure, credible role context,
and sample shrinkage toward the player's own baseline. The top two are the
reference core; ranks three through five are the development side.

P02 action reasons expose expression differences and situations. Teammate and
enemy examples are added only from the versioned aggregate artifacts described
in [Hero matchups and synergies](hero-matchups-and-synergies.md).

## Versioning and review

Changes to taxonomy traits, expression vocabulary, similarity weights,
role-fit rules, learning-distance rules, or overrides must bump an artifact
version and the Free analysis fingerprint. The checked-in implementation is
CPU-only and performs no runtime network call or model inference.
