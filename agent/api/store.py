"""
Store endpoint router for memory storage operations.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from ..memory import store_memory
from ..config import Settings, settings
from .models import StoreRequest, StoreResponse, ErrorResponse
from .exceptions import (
    MemoryServiceError,
    InvalidInputError,
    OpenAIServiceError,
    DatabaseError,
)
from openai import OpenAIError
import sqlite3
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/store",
    tags=["Memory Storage"],
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
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a new memory",
    description="""
    Store a new memory with automatic duplicate detection.
    
    The system will:
    1. Generate an embedding for the input text using OpenAI
    2. Check for duplicates using cosine similarity (threshold: 0.85)
    3. Return duplicate information if found, or store the new memory
    
    Returns memory ID and duplicate detection results.
    """,
    responses={
        201: {"description": "Memory stored successfully"},
        409: {"description": "Duplicate memory detected"},
    }
)
async def store_memory_endpoint(
    request: StoreRequest,
    app_settings: Settings = Depends(get_settings)
) -> StoreResponse:
    """Store a new memory with duplicate detection."""
    
    # Log the request
    logger.info(
        "Store request received",
        extra={
            "text_length": len(request.text),
            "language": request.language,
            "has_location": bool(request.location)
        }
    )
    
    try:
        # Validate input
        if not request.text.strip():
            raise InvalidInputError("Memory text cannot be empty", field="text")
        
        # Prepare metadata
        metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "language": request.language,
            "location": request.location
        }
        
        # Store memory
        result = store_memory(request.text.strip(), metadata)
        
        # Log success
        logger.info(
            "Store operation completed",
            extra={
                "memory_id": result.get("memory_id"),
                "duplicate_detected": result.get("duplicate_detected", False),
                "similarity_score": result.get("similarity_score")
            }
        )
        
        # Return appropriate status code with proper response
        status_code = (
            status.HTTP_409_CONFLICT
            if result.get("duplicate_detected")
            else status.HTTP_201_CREATED
        )

        response = StoreResponse(**result)
        return JSONResponse(status_code=status_code, content=response.model_dump())
        
    except InvalidInputError:
        raise
    except OpenAIError as e:
        logger.error("OpenAI service error during store", extra={"error": str(e)})
        raise OpenAIServiceError(e)
    except sqlite3.Error as e:
        logger.error("Database error during store", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during store", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to store memory", status_code=500)