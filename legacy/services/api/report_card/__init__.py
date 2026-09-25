"""Deprecated-but-live Free DNA / Dota Report Card legacy Python package.

This is the relocation target for legacy report-card modules that used to
live under ``services/api/app``. Tracker code (``app.tracker``) and shared
infrastructure (``app.core``, storage models/engine, the fresh STRATZ path)
remain in ``app``; everything reachable only from the legacy /v1 API and the
persisted-report renderers lives here.
"""
