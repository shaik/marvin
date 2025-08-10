"""
Admin endpoint router for debugging and administrative operations.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import get_cache_stats, clear_embedding_cache
from ..config import Settings, settings
from .models import MemoriesResponse, MemoryCandidate, ErrorResponse
from .exceptions import MemoryServiceError, OpenAIServiceError, DatabaseError
from openai import OpenAIError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    responses={
        503: {"model": ErrorResponse, "description": "OpenAI service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)


def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


@router.get(
    "/memories",
    response_model=MemoriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all stored memories",
    description="""
    Retrieve all stored memories for debugging/admin purposes.
    
    Returns all memories with their similarity scores relative to an empty query.
    This endpoint is intended for administrative use and debugging.
    
    **Warning**: This endpoint may return large amounts of data if many memories are stored.
    """,
    responses={
        200: {"description": "All memories retrieved successfully"},
    }
)
async def get_all_memories(
    app_settings: Settings = Depends(get_settings)
) -> MemoriesResponse:
    """Get all stored memories for debugging/admin purposes."""
    
    logger.info("Admin request to get all memories")
    
    try:
        # Retrieve all memories directly from the database
        conn = sqlite3.connect(app_settings.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, text FROM memories")
            rows = cursor.fetchall()
        finally:
            conn.close()

        # Convert to response models
        memory_candidates = [
            MemoryCandidate(
                memory_id=row[0],
                text=row[1],
                similarity_score=0.0
            )
            for row in rows
        ]
        
        logger.info(
            "All memories retrieved",
            extra={
                "total_memories": len(memory_candidates)
            }
        )
        
        return MemoriesResponse(
            total_memories=len(memory_candidates),
            memories=memory_candidates
        )
        
    except OpenAIError as e:
        logger.error("OpenAI service error during admin memories", extra={"error": str(e)})
        raise OpenAIServiceError(e)
    except sqlite3.Error as e:
        logger.error("Database error during admin memories", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during admin memories", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to get memories", status_code=500)


@router.get(
    "/cache/stats",
    status_code=status.HTTP_200_OK,
    summary="Get embedding cache statistics",
    description="""
    Get statistics about the embedding cache.
    
    Returns information about cache size, memory usage, and performance metrics.
    Useful for monitoring and optimization purposes.
    """,
    responses={
        200: {"description": "Cache statistics retrieved successfully"},
    }
)
async def get_cache_statistics(
    app_settings: Settings = Depends(get_settings)
):
    """Get embedding cache statistics."""
    
    logger.info("Admin request for cache statistics")
    
    try:
        stats = get_cache_stats()
        
        logger.info(
            "Cache statistics retrieved",
            extra=stats
        )
        
        return {
            "cache_statistics": stats,
            "status": "healthy"
        }
        
    except Exception as e:
        logger.error("Unexpected error getting cache stats", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to get cache statistics", status_code=500)


@router.post(
    "/cache/clear",
    status_code=status.HTTP_200_OK,
    summary="Clear embedding cache",
    description="""
    Clear the embedding cache to free up memory.
    
    This will remove all cached embeddings, forcing fresh API calls to OpenAI
    for subsequent requests. Use this for memory management or testing purposes.
    
    **Warning**: Clearing the cache will temporarily increase OpenAI API usage
    until the cache is rebuilt.
    """,
    responses={
        200: {"description": "Cache cleared successfully"},
    }
)
async def clear_cache(
    app_settings: Settings = Depends(get_settings)
):
    """Clear the embedding cache."""
    
    logger.info("Admin request to clear cache")
    
    try:
        items_removed = clear_embedding_cache()
        
        logger.info(
            "Cache cleared",
            extra={
                "items_removed": items_removed
            }
        )
        
        return {
            "message": "Cache cleared successfully",
            "items_removed": items_removed,
            "status": "success"
        }
        
    except Exception as e:
        logger.error("Unexpected error clearing cache", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to clear cache", status_code=500)