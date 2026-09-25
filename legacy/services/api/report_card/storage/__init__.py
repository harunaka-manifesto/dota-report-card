"""Legacy report-card persistence: the repository the deprecated /v1 API and
worker use. Shared database engine/models (``app.storage.database`` and
``app.storage.models``) stay in ``app`` because migrations and the tracker
depend on them.
"""
