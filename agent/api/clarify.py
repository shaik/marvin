"""
Clarify endpoint router for handling ambiguous queries.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import query_memory, get_memory_by_id
from ..config import Settings, settings
from .models import QueryRequest, ClarifyRequest, ClarifyResponse, MemoryCandidate, ErrorResponse
from .session_store import get_session_candidates
from .exceptions import MemoryServiceError, InvalidInputError, OpenAIServiceError, DatabaseError
from openai import OpenAIError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/clarify",
    tags=["Memory Operations"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        503: {"model": ErrorResponse, "description": "OpenAI service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)


def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


@router.post(
    "",
    response_model=ClarifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve clarification by selecting a specific memory",
    description="""
    Resolve user clarification by selecting a specific memory from ambiguous candidates.
    
    The system will:
    1. Validate that the chosen memory ID exists in the database
    2. Retrieve the complete memory details for the chosen ID
    3. Return confirmation of the clarification resolution
    
    This endpoint is used after a query returned clarification_required=true,
    and the user has selected one of the candidate memories.
    """,
    responses={
        200: {"description": "Clarification resolved successfully"},
        404: {"description": "Chosen memory ID not found"},
        422: {"description": "Invalid request parameters"},
    }
)
async def clarify_resolution_endpoint(
    request: ClarifyRequest,
    app_settings: Settings = Depends(get_settings)
) -> ClarifyResponse:
    """Resolve clarification by selecting a specific memory from ambiguous candidates."""
    
    # Log the request
    logger.info(
        "Clarification resolution request received",
        extra={
            "session_id": (request.session_id or "")[:8],
            "query_length": len(request.query) if request.query else None,
            "chosen_memory_id": request.chosen_memory_id[:8]
        }
    )
    
    try:
        # Validate input
        if request.session_id:
            candidates = get_session_candidates(request.session_id.strip())
            if not candidates:
                raise InvalidInputError("Session ID not found or expired", field="session_id")

            if not any(c.memory_id == request.chosen_memory_id.strip() for c in candidates):
                raise InvalidInputError("Chosen memory ID not found in session candidates", field="chosen_memory_id")

            # Retrieve chosen memory
            chosen_memory = get_memory_by_id(request.chosen_memory_id.strip())
        else:
            # Fallback to legacy behavior requiring query
            if not request.query or not request.query.strip():
                raise InvalidInputError("Query cannot be empty", field="query")

            if not request.chosen_memory_id.strip():
                raise InvalidInputError("Chosen memory ID cannot be empty", field="chosen_memory_id")

            chosen_memory = get_memory_by_id(request.chosen_memory_id.strip())

            if not chosen_memory:
                logger.warning(
                    "Clarification resolution failed - memory not found",
                    extra={
                        "chosen_memory_id": request.chosen_memory_id[:8],
                        "query": request.query[:50] if request.query else None
                    }
                )
                raise InvalidInputError(
                    f"Memory with ID {request.chosen_memory_id[:8]} not found",
                    field="chosen_memory_id"
                )
        
        # Log successful resolution
        logger.info(
            "Clarification resolved successfully",
            extra={
                "chosen_memory_id": request.chosen_memory_id[:8],
                "resolved_text_length": len(chosen_memory["text"]),
                "session_id": (request.session_id or "")[:8],
                "query": request.query[:50] if request.query else None
            }
        )
        
        # Return resolution confirmation
        return ClarifyResponse(
            clarification_resolved=True,
            memory_id=chosen_memory["memory_id"],
            text=chosen_memory["text"],
            message=f"Clarification resolved. Selected memory: {chosen_memory['text'][:100]}{'...' if len(chosen_memory['text']) > 100 else ''}"
        )
        
    except InvalidInputError:
        raise
    except OpenAIError as e:
        logger.error("OpenAI service error during clarify", extra={"error": str(e)})
        raise OpenAIServiceError(e)
    except sqlite3.Error as e:
        logger.error("Database error during clarify", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during clarify", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to generate clarification", status_code=500)