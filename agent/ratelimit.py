"""
Rate limiting utilities for Marvin Memory Service.
Provides per-API-key rate limiting with configurable thresholds.
"""

from time import time
from threading import Lock
from typing import Optional, Dict, Tuple
from fastapi import Header, HTTPException
from agent.config import settings
import logging
import hashlib

logger = logging.getLogger(__name__)

# In-memory rate limit counters: {(api_key, time_window): count}
_rate_limit_counters: Dict[Tuple[str, int], int] = {}
_rate_limit_lock = Lock()


def _get_key_hash(api_key: str) -> str:
    """Generate a short hash of the API key for logging (privacy)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:8]


def rate_limit_guard(x_api_key: Optional[str] = Header(default=None)) -> None:
    """
    FastAPI dependency that enforces rate limiting per API key.
    
    Behavior:
    - If api_auth_key is None/empty → rate limiting disabled (for local dev)
    - Uses sliding window: current_window = int(time() // window_seconds)
    - Tracks requests per (api_key, window) combination
    - Raises HTTPException(429) when limit exceeded
    
    Thread-safe with internal locking.
    """
    # If authentication is disabled, rate limiting is also disabled
    if not settings.api_auth_key:
        return None
    
    # If no API key provided, this will be caught by api_key_guard later
    # We don't rate limit requests that will be rejected for auth anyway
    if not x_api_key:
        return None
    
    # Calculate current time window
    current_time = time()
    window = int(current_time // settings.rate_limit_window_seconds)
    
    # Create counter key
    counter_key = (x_api_key, window)
    
    # Thread-safe counter update
    with _rate_limit_lock:
        # Get current count for this API key + window
        current_count = _rate_limit_counters.get(counter_key, 0)
        
        # Check if limit would be exceeded
        if current_count >= settings.rate_limit_max_requests:
            # Log rate limit exceeded
            key_hash = _get_key_hash(x_api_key)
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "key_hash": key_hash,
                    "count": current_count,
                    "window": window,
                    "max_requests": settings.rate_limit_max_requests,
                    "window_seconds": settings.rate_limit_window_seconds
                }
            )
            
            # Raise HTTP 429 Too Many Requests
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_max_requests} per {settings.rate_limit_window_seconds}s"
            )
        
        # Increment counter
        _rate_limit_counters[counter_key] = current_count + 1
        new_count = current_count + 1
    
    # Log successful rate limit check
    key_hash = _get_key_hash(x_api_key)
    logger.info(
        "rate_limit_allow",
        extra={
            "key_hash": key_hash,
            "count": new_count,
            "window": window,
            "max_requests": settings.rate_limit_max_requests
        }
    )
    
    return None


def _cleanup_old_windows() -> None:
    """
    Clean up old time windows from the counter dictionary.
    This is a utility function that could be called periodically
    to prevent memory growth (not used in current implementation).
    """
    current_time = time()
    current_window = int(current_time // settings.rate_limit_window_seconds)
    
    with _rate_limit_lock:
        # Remove counters older than 2 windows (for safety margin)
        old_keys = [
            key for key in _rate_limit_counters.keys()
            if key[1] < current_window - 1
        ]
        
        for key in old_keys:
            del _rate_limit_counters[key]
        
        if old_keys:
            logger.debug(
                "rate_limit_cleanup",
                extra={
                    "cleaned_windows": len(old_keys),
                    "current_window": current_window
                }
            )