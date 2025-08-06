"""
Cancel endpoint router for handling cancellation intents.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import query_memory
from ..config import Settings, settings
from .models import CancelRequest, CancelResponse, ErrorResponse
from .exceptions import MemoryServiceError, InvalidInputError, OpenAIServiceError, DatabaseError
from openai import OpenAIError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cancel",
    tags=["Memory Operations"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        503: {"model": ErrorResponse, "description": "OpenAI service unavailable"},
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
    summary="Handle cancellation intent",
    description="""
    Handle user cancellation intent by identifying the target memory.
    
    The system will:
    1. Search for memories similar to the last input text
    2. Find the best matching memory if similarity is high enough (>0.7)
    3. Return a confirmation message for the user to approve cancellation
    
    This is used to identify which memory the user wants to cancel before
    actually deleting it.
    """,
    responses={
        200: {"description": "Cancellation target identified or no match found"},
    }
)
async def handle_cancel_endpoint(
    request: CancelRequest,
    app_settings: Settings = Depends(get_settings)
) -> CancelResponse:
    """Handle cancellation intent by identifying the target memory."""
    
    # Log the request
    logger.info(
        "Cancel request received",
        extra={
            "last_input_length": len(request.last_input)
        }
    )
    
    try:
        # Validate input
        if not request.last_input.strip():
            raise InvalidInputError("Last input cannot be empty", field="last_input")
        
        # Find memories similar to the last input
        candidates = query_memory(request.last_input.strip(), top_k=1)
        
        if not candidates:
            logger.info("No memories found for cancellation")
            return CancelResponse(
                target_memory_id=None,
                confirmation_text=f"No recent memory found matching '{request.last_input}'. Nothing to cancel."
            )
        
        best_match = candidates[0]
        
        # Only suggest cancellation if similarity is high enough
        if best_match["similarity_score"] > 0.7:
            logger.info(
                "Cancellation target identified",
                extra={
                    "target_memory_id": best_match["memory_id"],
                    "similarity_score": best_match["similarity_score"]
                }
            )
            return CancelResponse(
                target_memory_id=best_match["memory_id"],
                confirmation_text=f"Do you mean to cancel '{best_match['text']}'?"
            )
        else:
            logger.info(
                "No clear cancellation target found",
                extra={
                    "best_similarity": best_match["similarity_score"],
                    "threshold": 0.7
                }
            )
            return CancelResponse(
                target_memory_id=None,
                confirmation_text=f"No clear match found for '{request.last_input}'. Please be more specific about what to cancel."
            )
        
    except InvalidInputError:
        raise
    except OpenAIError as e:
        logger.error("OpenAI service error during cancel", extra={"error": str(e)})
        raise OpenAIServiceError(e)
    except sqlite3.Error as e:
        logger.error("Database error during cancel", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during cancel", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to handle cancel request", status_code=500)