# V7 surviving Pass-2 integrity verification

Read-only verification date: 2026-09-08. No Pass-2 file was modified and no
provider call was made.

## Durable source

Path: `.local/corpora/stratz/v7-pass2-2026-09-04`

| Layer | Count | Size |
|---|---:|---:|
| canonical documents | 278 | 3.4 GiB |
| canonical rows | 104,982 | included above |
| normalized JSON documents | 13,253 | 3.4 GiB |
| raw files (`.body` plus metadata JSON) | 26,508 | 1.4 GiB |
| request-ledger rows | 13,264 | 39 MiB ledger directory |

Run manifest declares schema `stratz-v7-pass2-runner-1.0.0`, phase
`V7_PASS2_DEEP_ACQUISITION`, split `DISCOVERY`, status `COMPLETE`, 300 planned
accounts, 278 complete, 22 `no_parsed_opportunities`, 500 matches/account,
13,264 physical attempts, zero cache hits, `candidate_test_touched=false`,
`reserved_or_sealed_touched=false`, and `identities_included=false`.

Digests:

- `manifests/run-manifest.json`:
  `237cbb0221cca87973ee5b598be000ccf494dab9f06db8bb5016fb7463e428be`
- `manifests/state.json`:
  `f2b28f58968e433a5117132aced1f88d3f9734437f2a6e40c2c6a83e039e7c6a`
- `hash-manifest.json`:
  `7a2e5f0d23b9f0430321ab33dca26e822b8858b2ba5431295ee0432bf8c4af69`

The canonical reader yields 276 analysis-eligible product-context accounts;
the difference from 278 canonical documents is eligibility, not missing data.

## Estimator compatibility

The surviving rows feed the unchanged `pass2_observations` opportunity builders,
the same categorical projection, blocked-means inference, dependence curve,
population calculation, and ranking functions used by the reviewed Finding
pipeline. A read-only NEW-LINEAGE fit reproduced every committed Pass-2
Finding summary field (`players`, `opportunities`, projection drift, `mu`,
`tau`, `D`, and dependence batch length) for all eight Pass-2 pipeline
dimensions at normal floating-point expectations. The 2.0.0 bundle rebinds
those values without tuning.

Pass-2 is the immutable Pass-2 input to the completed NEW-LINEAGE fit. It was
not recollected or rewritten.
