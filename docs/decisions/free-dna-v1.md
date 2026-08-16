# Free Dota DNA v1 decisions

These decisions are part of the versioned Free DNA contract.

- Orientation uses the global spectrum convention: `0` is Facilitator, `0.5` is neutral, and `1` is Finisher.
- Share cards use the deterministic `share-svg-1.1.0` renderer. It keeps local, CI, and API output reproducible until a pinned image renderer is introduced.
- The 23 states describe the complete journey payload. A completed report enters at `report-reveal`; the input, player-found, and analysis states are owned by the pre-report flow and are not replayed.
- Summary `lane_role` is used only as a documented role hint: `1=carry`, `2=mid`, `3=offlane`, `4=jungle`, `5=roamer`. A spatial `lane` field alone never manufactures a player role.
