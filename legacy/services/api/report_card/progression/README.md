# Legacy progression prototype — not the tracker implementation

`role_metrics.py` predates the Dota Tracker SSOTs. It derives roles from STRATZ-native
position labels, uses a **mean** baseline and covers 5 of the 20 V1 metrics, all of which
contradict [App Foundation](../../../../docs/tracker/app_foundation/SSOT.md) §5–§9.

No runtime module imports it; only `tests/unit/test_progression_role_metrics.py` does. The
tracker's correct implementation is `app/tracker/metrics.py` (20 metrics, N/A rules),
`app/tracker/history.py` (previous-20 **median** after a 5-prior gate, PBs) and
`app/tracker/roles.py` (provider-neutral role assignment). Do not extend this package or use it as
a parity target.
