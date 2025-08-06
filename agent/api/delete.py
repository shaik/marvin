"""
Delete endpoint router for memory removal operations.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import delete_memory
from ..config import Settings, settings
from .models import DeleteRequest, DeleteResponse, ErrorResponse
from .exceptions import MemoryServiceError, InvalidInputError, MemoryNotFoundError, DatabaseError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/delete",
    tags=["Memory Management"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        404: {"model": ErrorResponse, "description": "Memory not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)


def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


@router.post(
    "",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a memory",
    description="""
    Delete a memory by its ID.
    
    The system will:
    1. Verify the memory exists
    2. Remove it from the database
    3. Return the deleted text content for confirmation
    
    Used for canceling recently stored memories or removing unwanted entries.
    """,
    responses={
        200: {"description": "Memory deleted successfully"},
    }
)
async def delete_memory_endpoint(
    request: DeleteRequest,
    app_settings: Settings = Depends(get_settings)
) -> DeleteResponse:
    """Delete a memory by ID."""
    
    # Log the request
    logger.info(
        "Delete request received",
        extra={
            "memory_id": request.memory_id[:8] + "..."
        }
    )
    
    try:
        # Validate input
        if not request.memory_id.strip():
            raise InvalidInputError("Memory ID cannot be empty", field="memory_id")
        
        # Delete memory
        result = delete_memory(request.memory_id.strip())
        
        # Check if memory was found
        if not result.get("success", False):
            if "not found" in result.get("error", "").lower():
                raise MemoryNotFoundError(request.memory_id)
            else:
                raise MemoryServiceError(result.get("error", "Delete failed"), status_code=500)
        
        # Log success
        logger.info(
            "Delete operation completed",
            extra={
                "memory_id": request.memory_id,
                "deleted_text_length": len(result.get("deleted_text", ""))
            }
        )
        
        return DeleteResponse(**result)
        
    except (InvalidInputError, MemoryNotFoundError, MemoryServiceError):
        raise
    except sqlite3.Error as e:
        logger.error("Database error during delete", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during delete", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to delete memory", status_code=500)