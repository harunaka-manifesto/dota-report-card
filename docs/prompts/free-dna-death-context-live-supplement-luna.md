# Free DNA — Death Context Live Supplement

## Current local result

`LOCAL_REUSE_STATUS = INSUFFICIENT`.

The development summary corpus supplies the deterministic 32-profile/960-ID
panel, but the retained OpenDota raw corpus has only 19 parsed detail bodies
and zero bodies from that frozen panel. The supplement therefore needs up to
960 missing match-detail GETs. It must not request profile history, public
match pages, replay parsing, STRATZ, Steam, or any replacement panel.

## Owner approval gate

Do not make a provider call until the owner explicitly approves this exact
ceiling in the active task:

```text
I approve up to 960 OpenDota match-detail GETs, Rp1,920 and $0.096 pro rata,
384 MiB local storage, zero retries, zero replay parse requests, and immediate
stop on marker, schema, rate-limit, or budget failure.
```

## Execution contract after approval

- Start from base `98e471453b2ea5b6de418ad9ca8d4e5400c913eb` and the frozen local
  panel manifest; do not re-rank after opening a response.
- Request only the missing IDs in the 32×30 panel, using GET `/matches/{id}`.
- Count every physical request in an append-only ledger before interpreting its
  response. Use zero retries and no more than 240 starts per minute.
- Stop on any 429, auth/billing anomaly, schema drift, parse-workflow evidence,
  interrupted request, or budget/storage risk.
- Preserve every body immutably with status, timestamp, bytes, and SHA-256.
- Re-run the registered semantics QA before any outcome analysis. If teamfight
  numerator reconstruction is not reliable, return
  `TEAMFIGHT_SEMANTICS_BLOCKED`.
- Keep the development/tuning lineage only. Do not inspect sealed validation
  or old holdout outcomes.
- Run the frozen Death Context estimand and controls only if the complete panel
  is present. Do not change strata, thresholds, gates, or interpretation.

## Expected outputs

Extend the local Tier-2 manifest and produce the same aggregate diagnostics as
the local-reuse pilot. Keep raw identifiers and the salt local mode `0600`;
tracked evidence may contain aggregates and digests only.
