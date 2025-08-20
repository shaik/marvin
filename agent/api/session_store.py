import time
from typing import List, Dict, Optional
from uuid import uuid4

from .models import MemoryCandidate

SESSION_TTL_SECONDS = 300  # 5 minutes

# Internal store mapping session_id -> {"expires": float, "candidates": List[dict]}
_session_store: Dict[str, Dict[str, object]] = {}

def create_session(candidates: List[MemoryCandidate]) -> str:
    """Create a session storing candidates and return session ID."""
    session_id = str(uuid4())
    _session_store[session_id] = {
        "expires": time.time() + SESSION_TTL_SECONDS,
        "candidates": [c.model_dump() for c in candidates],
    }
    return session_id

def get_session_candidates(session_id: str) -> Optional[List[MemoryCandidate]]:
    """Retrieve stored candidates for a session if not expired."""
    data = _session_store.get(session_id)
    if not data:
        return None
    if time.time() > data["expires"]:
        # Session expired - remove and return None
        del _session_store[session_id]
        return None
    return [MemoryCandidate(**c) for c in data["candidates"]]
