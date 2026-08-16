from __future__ import annotations


class AppError(Exception):
    """Stable client-facing domain error."""

    code = "ANALYSIS_FAILED"
    status_code = 500

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class InvalidPlayerIdentifier(AppError):
    code = "INVALID_PLAYER_IDENTIFIER"
    status_code = 422


class ProfileUnavailable(AppError):
    code = "PROFILE_PRIVATE_OR_UNAVAILABLE"
    status_code = 404


class InsufficientMatchHistory(AppError):
    code = "INSUFFICIENT_MATCH_HISTORY"
    status_code = 422


class OpenDotaRateLimited(AppError):
    code = "OPENDOTA_RATE_LIMITED"
    status_code = 429


class AnalysisRateLimited(AppError):
    code = "ANALYSIS_RATE_LIMITED"
    status_code = 429


class OpenDotaUnavailable(AppError):
    code = "OPENDOTA_UNAVAILABLE"
    status_code = 503


class SteamIdentityUnavailable(AppError):
    code = "STEAM_IDENTITY_UNAVAILABLE"
    status_code = 503


class ReportNotFound(AppError):
    code = "REPORT_NOT_FOUND"
    status_code = 404


class AnalysisNotFound(AppError):
    code = "ANALYSIS_NOT_FOUND"
    status_code = 404
