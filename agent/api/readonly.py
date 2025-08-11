"""
Read-only endpoint router for memory retrieval operations.
"""

from fastapi import APIRouter, Depends, status, HTTPException
from typing import List, Dict, Any
import logging

from ..memory import list_memories, get_memory_by_id
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
    summary="List all memories",
    description="""
    Retrieve all stored memories with basic information.
    
    Returns a list of all memories in the database with their ID and text content.
    Results are ordered by timestamp (newest first).
    """,
    responses={
        200: {"description": "List of memories retrieved successfully"},
    }
)
async def list_memories_endpoint(
    app_settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """List all stored memories."""
    
    logger.info("list_memories_request_received")
    
    try:
        # Get all memories from database
        memories = list_memories()
        
        # Transform to response format (map id -> memory_id, keep text only)
        response_memories = []
        for memory in memories:
            response_memory = {
                "memory_id": memory["id"],
                "text": memory["text"]
            }
            response_memories.append(response_memory)
        
        logger.info(
            "list_memories_completed",
            total_memories=len(response_memories)
        )
        
        return {
            "total_memories": len(response_memories),
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