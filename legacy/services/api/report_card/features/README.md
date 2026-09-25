# Legacy report feature extraction

These calculators feed the live report-card analysis. `roles.py` labels classes as
"position N" and relies on a parsed lane signal, so it is not the tracker's role model.
The tracker classifies from summary-class evidence first (`app/tracker/roles.py`,
`app/tracker/role_evidence.py`) and exposes only four public roles. Keep this package for the
legacy product; do not reuse it for tracker work.
