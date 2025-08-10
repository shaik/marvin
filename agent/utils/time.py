"""
Time utilities for Marvin agent.
Provides timezone-aware datetime functions to replace deprecated datetime.utcnow().
"""

from datetime import datetime, UTC


def utc_now_iso_z() -> str:
    """Return ISO8601 UTC with trailing Z (e.g., 2025-08-10T12:34:56.123456Z).
    
    This function replaces the deprecated datetime.utcnow().isoformat() + "Z" pattern
    with a timezone-aware equivalent that produces identical output format.
    
    Returns:
        str: ISO8601 formatted datetime string with UTC timezone as 'Z' suffix
        
    Examples:
        >>> utc_now_iso_z()  # doctest: +SKIP
        '2025-01-27T10:30:45.123456Z'
    """
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")