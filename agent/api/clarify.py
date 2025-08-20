"""
Clarify endpoint router for handling ambiguous queries.
"""

from fastapi import APIRouter, Depends, status
import logging
import re

from ..memory import query_memory, get_memory_by_id, embed_text, cosine_similarity
from ..config import Settings, settings
from .models import QueryRequest, ClarifyRequest, ClarifyResponse, MemoryCandidate, ErrorResponse
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
            "query_length": len(request.query),
            "chosen_memory_id": (request.chosen_memory_id or "")[:8],
            "chosen_memory_phrase": request.chosen_memory_phrase
        }
    )

    try:
        # Validate input
        if not request.query.strip():
            raise InvalidInputError("Query cannot be empty", field="query")

        chosen_id = None
        if request.chosen_memory_id and request.chosen_memory_id.strip():
            chosen_id = request.chosen_memory_id.strip()
        elif request.chosen_memory_phrase and request.chosen_memory_phrase.strip():
            phrase = request.chosen_memory_phrase.strip()
            candidates = query_memory(request.query.strip(), app_settings.clarify_min_candidates)
            if not candidates:
                raise InvalidInputError("No candidates available for clarification", field="chosen_memory_phrase")

            phrase_words = set(re.findall(r"\w+", phrase.lower()))
            best_candidate = None
            best_overlap = 0
            for cand in candidates:
                cand_words = set(re.findall(r"\w+", cand["text"].lower()))
                overlap = len(phrase_words & cand_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_candidate = cand

            if best_candidate and best_overlap > 0:
                chosen_id = best_candidate["memory_id"]
            else:
                phrase_embedding = embed_text(phrase)
                best_candidate = max(
                    candidates,
                    key=lambda c: cosine_similarity(phrase_embedding, embed_text(c["text"]))
                )
                chosen_id = best_candidate["memory_id"] if best_candidate else None

        if not chosen_id:
            raise InvalidInputError("Either chosen_memory_id or chosen_memory_phrase must be provided", field="chosen_memory_id")

        # Retrieve the chosen memory by ID
        chosen_memory = get_memory_by_id(chosen_id)

        if not chosen_memory:
            logger.warning(
                "Clarification resolution failed - memory not found",
                extra={
                    "chosen_memory_id": chosen_id[:8],
                    "query": request.query[:50]
                }
            )
            raise InvalidInputError(
                f"Memory with ID {chosen_id[:8]} not found",
                field="chosen_memory_id"
            )

        # Log successful resolution
        logger.info(
            "Clarification resolved successfully",
            extra={
                "chosen_memory_id": chosen_id[:8],
                "resolved_text_length": len(chosen_memory["text"]),
                "query": request.query[:50]
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
