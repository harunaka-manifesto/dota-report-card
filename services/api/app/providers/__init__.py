"""Provider protocol package for the isolated V7 canonical boundary.

``app.providers.base`` holds the shared dataclasses/protocol that both the
fresh STRATZ path (``app.stratz``) and the legacy V7 provider factory
(``report_card.providers.build_v7_provider``) depend on. The provider
*factory* itself is legacy-only (only ``app.main``, the deploy composition
root, calls it) and lives in ``report_card.providers``.
"""
