"""
Clarify endpoint router for handling ambiguous queries.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import query_memory
from ..config import Settings, settings
from .models import QueryRequest, ClarifyResponse, MemoryCandidate, ErrorResponse
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
    summary="Generate clarification for ambiguous queries",
    description="""
    Generate clarification questions when multiple high-confidence candidates exist.
    
    The system will:
    1. Search for memories matching the query (top 5 results)
    2. Analyze similarity scores to detect ambiguity
    3. Generate a clarification question if multiple high-scoring results exist
    4. Return candidates for user selection
    
    Ambiguity is detected when:
    - Multiple results have high similarity scores (>0.7)
    - The difference between top scores is small (<0.1)
    """,
    responses={
        200: {"description": "Clarification generated or no ambiguity detected"},
    }
)
async def clarify_ambiguity_endpoint(
    request: QueryRequest,
    app_settings: Settings = Depends(get_settings)
) -> ClarifyResponse:
    """Generate clarification questions when multiple high-confidence candidates exist."""
    
    # Log the request
    logger.info(
        "Clarification request received",
        extra={
            "query_length": len(request.query)
        }
    )
    
    try:
        # Validate input
        if not request.query.strip():
            raise InvalidInputError("Query cannot be empty", field="query")
        
        # Get more candidates to check for ambiguity
        candidates = query_memory(request.query.strip(), top_k=5)
        
        if len(candidates) < 2:
            logger.info("No ambiguity detected - insufficient candidates")
            return ClarifyResponse(
                clarification_question=None,
                message="No ambiguity detected - single clear result.",
                candidates=[
                    MemoryCandidate(
                        memory_id=c["memory_id"],
                        text=c["text"],
                        similarity_score=c["similarity_score"]
                    ) for c in candidates
                ]
            )
        
        # Check if top candidates have similar high scores (indicating ambiguity)
        top_score = candidates[0]["similarity_score"]
        second_score = candidates[1]["similarity_score"]
        
        if top_score > 0.7 and (top_score - second_score) < 0.1:
            # High ambiguity - generate clarification question
            clarification = "I found multiple similar memories. Do you mean:\n"
            top_candidates = candidates[:3]
            
            for i, candidate in enumerate(top_candidates, 1):
                preview = candidate["text"][:80] + "..." if len(candidate["text"]) > 80 else candidate["text"]
                clarification += f"{i}. {preview}\n"
            clarification += "Please specify which one you're looking for."
            
            logger.info(
                "Ambiguity detected - clarification generated",
                extra={
                    "top_score": top_score,
                    "second_score": second_score,
                    "score_difference": top_score - second_score,
                    "candidates_count": len(top_candidates)
                }
            )
            
            return ClarifyResponse(
                clarification_question=clarification,
                candidates=[
                    MemoryCandidate(
                        memory_id=c["memory_id"],
                        text=c["text"],
                        similarity_score=c["similarity_score"]
                    ) for c in top_candidates
                ]
            )
        else:
            logger.info(
                "No ambiguity detected - clear result found",
                extra={
                    "top_score": top_score,
                    "second_score": second_score,
                    "score_difference": top_score - second_score
                }
            )
            return ClarifyResponse(
                clarification_question=None,
                message="Clear result found - no clarification needed.",
                candidates=[
                    MemoryCandidate(
                        memory_id=c["memory_id"],
                        text=c["text"],
                        similarity_score=c["similarity_score"]
                    ) for c in candidates
                ]
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