"""
Delete endpoint router for memory deletion operations.
"""

from fastapi import APIRouter, Depends, status, HTTPException
import logging

from ..memory import delete_memory
from ..config import Settings, settings
from .models import DeleteRequest, DeleteResponse, ErrorResponse
from .exceptions import MemoryServiceError, InvalidInputError, DatabaseError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/delete",
    tags=["Memory Operations"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
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
    summary="Delete a memory by ID",
    description="""
    Delete a specific memory from the database using its UUID.
    
    The system will:
    1. Validate the memory ID format and existence
    2. Remove the memory from the database
    3. Return confirmation with the deleted text content
    
    This is typically used as the second step in the cancel/undo flow after
    the user confirms the cancellation via the cancel endpoint.
    """,
    responses={
        200: {"description": "Memory deleted successfully"},
        404: {"description": "Memory not found"},
    }
)
async def delete_memory_endpoint(
    request: DeleteRequest,
    app_settings: Settings = Depends(get_settings)
) -> DeleteResponse:
    """Delete a memory by its ID."""
    
    # Log the request
    logger.info(
        "delete_request_received",
        extra={
            "memory_id": request.memory_id[:8] if len(request.memory_id) > 8 else request.memory_id
        }
    )
    
    try:
        # Validate input
        if not request.memory_id.strip():
            raise InvalidInputError("Memory ID cannot be empty", field="memory_id")
        
        # Attempt to delete the memory using existing memory layer function
        result = delete_memory(request.memory_id.strip())
        
        # Check if deletion was successful
        if not result.get("success", False):
            # If the memory was not found or deletion failed
            error_message = result.get("error", "Memory not found")
            
            logger.info(
                "delete_not_found",
                extra={
                    "memory_id": request.memory_id[:8],
                    "error": error_message
                }
            )
            
            raise HTTPException(
                status_code=404,
                detail="Memory not found"
            )
        
        # Log successful deletion
        deleted_text = result.get("deleted_text", "")
        logger.info(
            "delete_success",
            extra={
                "memory_id": request.memory_id[:8],
                "deleted_text_length": len(deleted_text)
            }
        )
        
        return DeleteResponse(
            success=True,
            deleted_text=deleted_text
        )
        
    except HTTPException:
        raise
    except InvalidInputError:
        raise
    except sqlite3.Error as e:
        logger.error("Database error during delete", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during delete", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to delete memory", status_code=500)