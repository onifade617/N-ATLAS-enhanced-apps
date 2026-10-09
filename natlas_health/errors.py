"""Errors raised by NatlasClient. Catch ``NatlasError`` to handle every failure in one place."""


class NatlasError(Exception):
    """Base class for every N-ATLaS client error."""

    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


class NotConfiguredError(NatlasError):
    """No gateway URL was given (argument or NATLAS_BASE_URL)."""


class AuthenticationError(NatlasError):
    """401/403: the API key is missing or not one of the gateway's NATLAS_API_KEYS."""


class UnavailableError(NatlasError):
    """The gateway or one of its upstreams (LLM, ASR, TTS) is down, cold-starting or timed out.

    Modal deployments scale to zero; the first request after idle can take minutes. Retry or fall back.
    """


class FeatureNotEnabledError(NatlasError):
    """501: the gateway does not serve this route (e.g. speech synthesis is switched off)."""


class BadRequestError(NatlasError):
    """4xx other than auth: the request was malformed (empty input, unsupported language, file too large)."""


class InvalidResponseError(NatlasError):
    """The gateway answered 2xx but the body was not what the API documents."""
