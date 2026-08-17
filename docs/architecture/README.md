# Architecture notes

These pages describe the implementation currently shipped by the repository.
They keep the useful Dota vocabulary, but the data boundary stays literal:
summary history can show recurring match behavior; it cannot prove a motive,
cause, or replay-level explanation.

## Read in this order

1. [System overview](system-overview.md) for the pipeline and ownership map.
2. [Free DNA model guide](free-dna-model-guide.md) for the complete human-readable explanation of the model.
3. [Model catalog](model-catalog.md) for the compact, generated registry reference.
4. [Root architecture summary](../../ARCHITECTURE.md) for the short version.

The guide explains what the model means. The catalog’s tables are generated
from the production registries and explain what is currently registered. If a
model key changes, update the registry and run `make dna-catalog`; do not
hand-edit the generated block.
