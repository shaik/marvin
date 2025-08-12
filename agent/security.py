"""
Security utilities for Marvin Memory Service.
Provides authentication and authorization mechanisms.
"""

import logging
from typing import Union
from fastapi import Header, HTTPException
from .config import settings

logger = logging.getLogger(__name__)


def api_key_guard(x_api_key: Union[str, None] = Header(default=None)) -> None:
    """
    FastAPI dependency that enforces API key authentication when enabled.
    
    Args:
        x_api_key: API key from X-API-KEY header
        
    Raises:
        HTTPException: 401 error if API key is invalid or missing when auth is enabled
        
    Returns:
        None: Authentication passed or disabled
        
    Behavior:
        - If settings.api_auth_key is None/empty: authentication is disabled, always pass
        - If settings.api_auth_key is set: supports comma-separated keys, require matching X-API-KEY header
        - If header is missing or doesn't match: raise 401 error with structured logging
    """
    # Check if authentication is enabled
    raw = settings.api_auth_key
    
    # If no API key is configured, authentication is disabled
    if not raw:
        return None
    
    # Build set of allowed keys from comma-separated string
    allowed = {k.strip() for k in raw.split(",") if k.strip()}
    
    # Authentication is enabled, check the provided key
    if not x_api_key or x_api_key not in allowed:
        # Log authentication failure
        logger.warning(
            "API key authentication failed",
            extra={
                "provided_key_present": bool(x_api_key),
                "configured_key_present": bool(raw)
            }
        )
        
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    
    # Authentication successful - no logging needed for success case
    return None