"""Server-to-server App Store Server Notifications V2 endpoint.

Mounted separately from the mobile API so it never appears in the mobile
OpenAPI document. Authenticity comes only from the signed payload's verified
certificate chain; there is no bearer token on this route.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from app.core.config import Settings
from app.storage.database import create_database_engine
from app.tracker.entitlement import AppStoreVerifier, EntitlementError, apply_notification


class NotificationRequest(BaseModel):
    signedPayload: str = Field(min_length=20, max_length=200_000)


def create_store_app(settings: Settings, *, database: Engine | None = None,
                     verifier: AppStoreVerifier | None = None) -> FastAPI:
    app = FastAPI(title="Dota Tracker Store Notifications", version="1.0.0",
                  openapi_url=None, docs_url=None, redoc_url=None)
    app.state.database = database
    app.state.verifier = verifier

    def engine() -> Engine:
        if app.state.database is None:
            app.state.database = create_database_engine(settings)
        return app.state.database

    @app.post("/app-store/notifications")
    async def notification(request: Request, body: NotificationRequest) -> JSONResponse:
        if app.state.verifier is None:
            return JSONResponse(status_code=503, content={"code": "STORE_UNAVAILABLE"})
        try:
            app.state.verifier.verify_notification(body.signedPayload)
        except EntitlementError:
            # Unverifiable input is rejected without touching account state.
            return JSONResponse(status_code=400, content={"code": "NOTIFICATION_INVALID"})
        try:
            apply_notification(engine(), signed_notification=body.signedPayload,
                               verifier=app.state.verifier, now=datetime.now(UTC))
        except EntitlementError:
            # A verified update for an unknown or unavailable account is
            # acknowledged so the store stops retrying; nothing is applied.
            return JSONResponse(status_code=200, content={"applied": False})
        return JSONResponse(status_code=200, content={"applied": True})

    return app
