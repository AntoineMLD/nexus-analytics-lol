"""X-API-Key authentication dependency for FastAPI.

Usage:
    @app.get("/protected")
    def endpoint(api_key: str = Security(verify_api_key)):
        ...

The expected key is read from NEXUS_API_KEY environment variable via
pydantic-settings. If NEXUS_API_KEY is empty, all requests are rejected.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from ingestion.utils import settings

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(_header_scheme)) -> str:
    """Raise HTTP 401 if the provided X-API-Key header does not match the expected value.

    Returns the valid key on success so it can be injected into route handlers
    if needed (e.g. for logging).
    """
    expected = settings.nexus_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="NEXUS_API_KEY is not configured on the server.",
        )
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
