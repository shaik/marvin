"""
Cancel endpoint router for handling undo/cancellation operations.
"""

from fastapi import APIRouter, Depends, status, HTTPException
import logging

from ..memory import get_most_recent_memory_by_text
from ..config import Settings, settings
from .models import CancelRequest, CancelResponse, ErrorResponse
from .exceptions import MemoryServiceError, InvalidInputError, DatabaseError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cancel",
    tags=["Memory Operations"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "No matching memory found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)


def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


@router.post(
    "",
    response_model=CancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Find memory to cancel by last input text",
    description="""
    Find the most recent memory that exactly matches the provided text for cancellation.
    
    The system will:
    1. Search for the most recent memory with text exactly matching last_input_text
    2. If found, return confirmation text and target memory ID
    3. If not found, return 404 error
    
    This is the first step in the cancel/undo flow - the actual deletion requires
    a separate call to the delete endpoint with the returned memory ID.
    """,
    responses={
        200: {"description": "Memory found for cancellation"},
        404: {"description": "No matching memory found to cancel"},
    }
)
async def cancel_memory_endpoint(
    request: CancelRequest,
    app_settings: Settings = Depends(get_settings)
) -> CancelResponse:
    """Find memory to cancel based on last input text."""
    
    # Log the request
    logger.info(
        "cancel_request_received",
        extra={
            "last_input_text_length": len(request.last_input_text)
        }
    )
    
    try:
        # Validate input
        if not request.last_input_text.strip():
            raise InvalidInputError("Last input text cannot be empty", field="last_input_text")
        
        # Find the most recent memory that matches the text exactly
        matching_memory = get_most_recent_memory_by_text(request.last_input_text.strip())
        
        if not matching_memory:
            logger.info(
                "cancel_no_match",
                extra={
                    "last_input_text": request.last_input_text[:50],
                    "text_length": len(request.last_input_text)
                }
            )
            raise HTTPException(
                status_code=404,
                detail="No matching memory found to cancel"
            )
        
        # Log successful match
        logger.info(
            "cancel_candidate_found",
            extra={
                "target_memory_id": matching_memory["id"][:8],
                "matched_text_length": len(matching_memory["text"])
            }
        )
        
        # Return confirmation response
        confirmation_text = f"Do you mean to cancel '{matching_memory['text']}'?"
        
        return CancelResponse(
            confirmation_text=confirmation_text,
            target_memory_id=matching_memory["id"]
        )
        
    except HTTPException:
        raise
    except InvalidInputError:
        raise
    except sqlite3.Error as e:
        logger.error("Database error during cancel", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during cancel", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to process cancel request", status_code=500)