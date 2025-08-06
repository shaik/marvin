"""
Query endpoint router for memory search operations.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import query_memory
from ..config import Settings, settings
from .models import QueryRequest, QueryResponse, MemoryCandidate, ErrorResponse
from .exceptions import MemoryServiceError, InvalidInputError, OpenAIServiceError, DatabaseError
from openai import OpenAIError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/query",
    tags=["Memory Search"],
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
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Search memories by semantic similarity",
    description="""
    Search stored memories using semantic similarity.
    
    The system will:
    1. Generate an embedding for the query text using OpenAI
    2. Compare against all stored memory embeddings using cosine similarity
    3. Return the top-k most similar memories ranked by score
    
    Higher similarity scores indicate better matches.
    """,
    responses={
        200: {"description": "Search completed successfully"},
    }
)
async def query_memory_endpoint(
    request: QueryRequest,
    app_settings: Settings = Depends(get_settings)
) -> QueryResponse:
    """Query memories using semantic similarity search."""
    
    # Log the request
    logger.info(
        "Query request received",
        extra={
            "query_length": len(request.query),
            "top_k": request.top_k
        }
    )
    
    try:
        # Validate input
        if not request.query.strip():
            raise InvalidInputError("Query cannot be empty", field="query")
        
        if request.top_k <= 0 or request.top_k > 100:
            raise InvalidInputError("top_k must be between 1 and 100", field="top_k")
        
        # Query memories
        candidates = query_memory(request.query.strip(), request.top_k)
        
        # Convert to response models
        memory_candidates = [
            MemoryCandidate(
                memory_id=candidate["memory_id"],
                text=candidate["text"],
                similarity_score=candidate["similarity_score"]
            )
            for candidate in candidates
        ]
        
        # Log success
        logger.info(
            "Query operation completed",
            extra={
                "results_count": len(memory_candidates),
                "top_scores": [c.similarity_score for c in memory_candidates[:3]]
            }
        )
        
        return QueryResponse(candidates=memory_candidates)
        
    except InvalidInputError:
        raise
    except OpenAIError as e:
        logger.error("OpenAI service error during query", extra={"error": str(e)})
        raise OpenAIServiceError(e)
    except sqlite3.Error as e:
        logger.error("Database error during query", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during query", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to query memories", status_code=500)