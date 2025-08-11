"""
Read-only endpoint router for memory retrieval operations.
"""

from fastapi import APIRouter, Depends, status, HTTPException, Query
from typing import List, Dict, Any
import logging

from ..memory import list_memories, list_memories_page, get_memory_by_id
from ..config import Settings, settings
from .exceptions import MemoryServiceError, DatabaseError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["Memory Read-Only Operations"],
    responses={
        404: {"description": "Memory not found"},
        500: {"description": "Internal server error"},
    }
)


def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


@router.get(
    "/memories",
    status_code=status.HTTP_200_OK,
    summary="List memories with pagination",
    description="""
    Retrieve stored memories with pagination support.
    
    Returns a page of memories from the database with their ID and text content.
    Results are ordered by timestamp (newest first).
    
    Query parameters:
    - limit: Number of items per page (1-100, default 20)
    - offset: Number of items to skip (>=0, default 0)
    """,
    responses={
        200: {"description": "Page of memories retrieved successfully"},
        422: {"description": "Invalid pagination parameters"},
    }
)
async def list_memories_endpoint(
    limit: int = Query(20, ge=1, le=100, description="Page size (1..100)"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    app_settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """List stored memories with pagination."""
    
    logger.info(
        "list_memories_request_received",
        limit=limit,
        offset=offset
    )
    
    try:
        # Get page of memories from database
        items, total = list_memories_page(limit=limit, offset=offset)
        
        # Transform to response format (map id -> memory_id, keep text only)
        response_memories = []
        for memory in items:
            response_memory = {
                "memory_id": memory["id"],
                "text": memory["text"]
            }
            response_memories.append(response_memory)
        
        logger.info(
            "list_memories_completed",
            limit=limit,
            offset=offset,
            returned_count=len(response_memories),
            total=total
        )
        
        return {
            "total_memories": total,
            "memories": response_memories
        }
        
    except sqlite3.Error as e:
        logger.error("Database error during list memories", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during list memories", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to list memories", status_code=500)


@router.get(
    "/memories/{memory_id}",
    status_code=status.HTTP_200_OK,
    summary="Get memory by ID",
    description="""
    Retrieve a specific memory by its UUID.
    
    Returns the complete memory details including ID and text content.
    """,
    responses={
        200: {"description": "Memory retrieved successfully"},
        404: {"description": "Memory not found"},
    }
)
async def get_memory_endpoint(
    memory_id: str,
    app_settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """Get a specific memory by its ID."""
    
    logger.info(
        "get_memory_request_received",
        memory_id=memory_id[:8] if len(memory_id) > 8 else memory_id
    )
    
    try:
        # Get memory from database
        memory = get_memory_by_id(memory_id)
        
        if not memory:
            logger.info(
                "get_memory_not_found",
                memory_id=memory_id[:8] if len(memory_id) > 8 else memory_id
            )
            raise HTTPException(
                status_code=404,
                detail="Memory not found"
            )
        
        logger.info(
            "get_memory_completed",
            memory_id=memory_id[:8] if len(memory_id) > 8 else memory_id,
            text_length=len(memory["text"])
        )
        
        return {
            "memory_id": memory["memory_id"],
            "text": memory["text"]
        }
        
    except HTTPException:
        raise
    except sqlite3.Error as e:
        logger.error("Database error during get memory", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during get memory", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to get memory", status_code=500)


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export all memories",
    description="""
    Export complete snapshot of all memories with full metadata.
    
    Returns all memories with complete information including timestamps, 
    language settings, and location data for backup or analysis purposes.
    """,
    responses={
        200: {"description": "Memory export completed successfully"},
    }
)
async def export_memories_endpoint(
    app_settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """Export complete memory snapshot with full metadata."""
    
    logger.info("export_memories_request_received")
    
    try:
        # Get all memories from database
        memories = list_memories()
        
        logger.info(
            "export_memories_completed",
            total_count=len(memories)
        )
        
        return {
            "count": len(memories),
            "items": memories
        }
        
    except sqlite3.Error as e:
        logger.error("Database error during export memories", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during export memories", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to export memories", status_code=500)