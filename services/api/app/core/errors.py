from __future__ import annotations


class AppError(Exception):
    """Stable client-facing domain error."""

    code = "ANALYSIS_FAILED"
    status_code = 500

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class ProfileUnavailable(AppError):
    code = "PROFILE_PRIVATE_OR_UNAVAILABLE"
    status_code = 404


class OpenDotaRateLimited(AppError):
    code = "OPENDOTA_RATE_LIMITED"
    status_code = 429


class OpenDotaUnavailable(AppError):
    code = "OPENDOTA_UNAVAILABLE"
    status_code = 503


class StratzProviderError(AppError):
    code = "STRATZ_PROVIDER_ERROR"
    status_code = 503


class StratzRateLimited(StratzProviderError):
    code = "STRATZ_RATE_LIMITED"
    status_code = 429


class StratzUnavailable(StratzProviderError):
    code = "STRATZ_UNAVAILABLE"
    status_code = 503


class StratzForbidden(StratzProviderError):
    code = "STRATZ_FORBIDDEN"
    status_code = 502


class StratzChallengeError(StratzForbidden):
    code = "STRATZ_EDGE_CHALLENGE"


class StratzInvalidResponse(StratzProviderError):
    code = "STRATZ_INVALID_RESPONSE"
    status_code = 502


class StratzGraphQLError(StratzInvalidResponse):
    code = "STRATZ_GRAPHQL_ERROR"


class StratzPartialResponse(StratzGraphQLError):
    code = "STRATZ_PARTIAL_RESPONSE"


class StratzSchemaDrift(StratzInvalidResponse):
    code = "STRATZ_SCHEMA_DRIFT"
