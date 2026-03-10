"""Custom exception hierarchy for Channex.io API errors.

All exceptions carry the HTTP status code and a human-readable message.
Use these to write precise exception handlers in calling code.

Hierarchy:
    ChannexAPIError (base)
        ChannexAuthError          — 401 Unauthorized
        ChannexNotFoundError      — 404 Not Found
        ChannexRateLimitError     — 429 Too Many Requests
        ChannexValidationError    — 422 Unprocessable Entity
        ChannexServerError        — 5xx Server Errors
    ChannexWebhookSignatureError  — HMAC verification failure (no HTTP code)
"""

from __future__ import annotations


class ChannexAPIError(Exception):
    """Base exception for all Channex API errors.

    Attributes:
        status_code: HTTP status code returned by the API.
        message: Human-readable error message.
        response_body: Raw response body string for debugging.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_body: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.response_body = response_body

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code}, "
            f"message={self.message!r})"
        )


class ChannexAuthError(ChannexAPIError):
    """401 Unauthorized — the API key is missing, invalid, or expired."""


class ChannexNotFoundError(ChannexAPIError):
    """404 Not Found — the requested resource does not exist."""


class ChannexRateLimitError(ChannexAPIError):
    """429 Too Many Requests — the API rate limit has been exceeded.

    The client will automatically retry these with exponential backoff.
    """


class ChannexValidationError(ChannexAPIError):
    """422 Unprocessable Entity — the request payload failed validation."""


class ChannexServerError(ChannexAPIError):
    """5xx Server Error — a transient error on the Channex side.

    The client will automatically retry these with exponential backoff.
    """


class ChannexWebhookSignatureError(Exception):
    """Raised when the HMAC-SHA256 signature on a webhook payload cannot be verified.

    This usually means the payload was tampered with or the wrong webhook secret
    is configured. Requests failing this check should be rejected with HTTP 403.
    """
