# V7 report runtime (legacy staging lineage)

V7 is an earlier STRATZ-native report lineage. It is not the tracker contract.
`research/` is imported by runtime code, including `app/stratz/deep.py` (provider layer), so it
cannot be archived until the used subset is relocated with parity tests (goal R3). The
`data/population-parameters-*.json` files are V7 report artifacts, not the tracker's context
parameter set (see `app/tracker/population_parameters.py`). The eight-row acquisition
arithmetic in `acquisition_policy.py` is legacy-only; tracker historical batches use explicit
page sizes in `app/stratz/queries.py` (`GET_TRACKER_MATCH_BATCH`).
