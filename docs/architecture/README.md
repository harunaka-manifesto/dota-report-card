# Architecture notes

Read in order:

1. [Free DNA system](free-dna-system.md)
2. [Elements](elements.md)
3. [Patterns](patterns.md)
4. [Pattern presentation](pattern-presentation.md)
5. [Hero relationships](hero-relationships.md)
6. [Hero matchups and synergies](hero-matchups-and-synergies.md)
7. [Hero Portfolio](hero-portfolio.md)
8. [Report flow](report-flow.md)
9. [Data provenance](data-provenance.md)
10. [Hero data sources](hero-data-sources.md)
11. [Hero knowledge](hero-knowledge.md)
12. [Model catalog](model-catalog.md)
13. [v5.2 SSOT and compatibility history](dota-dna-ssot.md)
14. [Free DNA v6 statistics](free-dna-v6-statistics.md)
15. [Deep diagnostics v2](deep-diagnostics-v2.md)
16. [Free DNA V6.1 feature graph](free-dna-v6.1-feature-graph.md)
17. [STRATZ V7 provider contract](stratz-v7-provider-contract.md)
18. [Analytical learnings and gotchas](../../docs/agent/analytical-learnings-and-gotchas.md)

The catalog is generated from production registries. Change a registry first,
then run make dna-catalog and make docs-check.

The V5.2/V6.0 documents describe retained runtime, compatibility, release, and
historical evidence. V7 forward development starts from the
[STRATZ provider contract](stratz-v7-provider-contract.md) and its native data
provenance; it does not inherit V6.1 Finding semantics.
