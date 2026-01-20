"""API authentication module.

Provides simple API key authentication for securing endpoints.
"""

import os
import secrets
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# API key header configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Load valid API keys from environment
# Format: comma-separated list of keys
_VALID_API_KEYS = set()


def _load_api_keys() -> set:
    """Load valid API keys from environment."""
    keys_str = os.environ.get("SITEABLE_API_KEYS", "")
    if keys_str:
        return {k.strip() for k in keys_str.split(",") if k.strip()}
    return set()


def get_api_keys() -> set:
    """Get the set of valid API keys."""
    global _VALID_API_KEYS
    if not _VALID_API_KEYS:
        _VALID_API_KEYS = _load_api_keys()
    return _VALID_API_KEYS


def is_auth_enabled() -> bool:
    """Check if API authentication is enabled."""
    return bool(get_api_keys())


async def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Optional[str]:
    """Verify API key from request header.

    If no API keys are configured, authentication is disabled.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If authentication is enabled and key is invalid
    """
    # If no API keys configured, skip authentication
    if not is_auth_enabled():
        return None

    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API key is required. Provide it in the X-API-Key header.",
        )

    if api_key not in get_api_keys():
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return api_key


def generate_api_key() -> str:
    """Generate a new random API key.

    Returns:
        A secure random API key (32 characters)
    """
    return secrets.token_urlsafe(24)


def require_auth(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Dependency that requires authentication.

    Use this for endpoints that must be protected.

    Args:
        api_key: API key from header

    Returns:
        The validated API key

    Raises:
        HTTPException: If key is missing or invalid
    """
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API key is required.",
        )

    if api_key not in get_api_keys():
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return api_key


class OptionalAuth:
    """Dependency for optional authentication.

    Validates the API key if provided, but doesn't require it
    when authentication is disabled.
    """

    async def __call__(
        self,
        api_key: Optional[str] = Security(API_KEY_HEADER),
    ) -> Optional[str]:
        """Check authentication if enabled."""
        if not is_auth_enabled():
            return None

        return await verify_api_key(api_key)
