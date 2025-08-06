"""
Update endpoint router for memory modification operations.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import update_memory
from ..config import Settings, settings
from .models import UpdateRequest, UpdateResponse, ErrorResponse
from .exceptions import MemoryServiceError, InvalidInputError, MemoryNotFoundError, OpenAIServiceError, DatabaseError
from openai import OpenAIError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/update",
    tags=["Memory Management"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        404: {"model": ErrorResponse, "description": "Memory not found"},
        503: {"model": ErrorResponse, "description": "OpenAI service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)


def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


@router.post(
    "",
    response_model=UpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing memory",
    description="""
    Update an existing memory with new text content.
    
    The system will:
    1. Verify the memory exists
    2. Generate a new embedding for the updated text using OpenAI
    3. Replace the existing memory content and embedding
    4. Return the before/after text for confirmation
    
    Used for resolving duplicates or correcting stored information.
    """,
    responses={
        200: {"description": "Memory updated successfully"},
    }
)
async def update_memory_endpoint(
    request: UpdateRequest,
    app_settings: Settings = Depends(get_settings)
) -> UpdateResponse:
    """Update an existing memory with new text."""
    
    # Log the request
    logger.info(
        "Update request received",
        extra={
            "memory_id": request.memory_id[:8] + "...",
            "new_text_length": len(request.new_text)
        }
    )
    
    try:
        # Validate input
        if not request.memory_id.strip():
            raise InvalidInputError("Memory ID cannot be empty", field="memory_id")
        
        if not request.new_text.strip():
            raise InvalidInputError("New text cannot be empty", field="new_text")
        
        # Update memory
        result = update_memory(request.memory_id.strip(), request.new_text.strip())
        
        # Check if memory was found
        if not result.get("success", False):
            if "not found" in result.get("error", "").lower():
                raise MemoryNotFoundError(request.memory_id)
            else:
                raise MemoryServiceError(result.get("error", "Update failed"), status_code=500)
        
        # Log success
        logger.info(
            "Update operation completed",
            extra={
                "memory_id": request.memory_id,
                "original_length": len(result.get("before", "")),
                "updated_length": len(result.get("after", ""))
            }
        )
        
        return UpdateResponse(**result)
        
    except (InvalidInputError, MemoryNotFoundError, MemoryServiceError):
        raise
    except OpenAIError as e:
        logger.error("OpenAI service error during update", extra={"error": str(e)})
        raise OpenAIServiceError(e)
    except sqlite3.Error as e:
        logger.error("Database error during update", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during update", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to update memory", status_code=500)