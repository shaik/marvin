"""
Custom exceptions and error handlers for the API.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from openai import OpenAIError
import sqlite3
import logging
from typing import Union

logger = logging.getLogger(__name__)


class MemoryServiceError(Exception):
    """Base exception for memory service errors."""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class MemoryNotFoundError(MemoryServiceError):
    """Exception raised when a memory is not found."""
    def __init__(self, memory_id: str):
        super().__init__(
            message=f"Memory not found: {memory_id[:8]}...",
            status_code=404,
            details={"memory_id": memory_id}
        )


class DuplicateMemoryError(MemoryServiceError):
    """Exception raised when a duplicate memory is detected."""
    def __init__(self, existing_memory_id: str, similarity_score: float):
        super().__init__(
            message="Duplicate memory detected",
            status_code=409,
            details={
                "existing_memory_id": existing_memory_id,
                "similarity_score": similarity_score
            }
        )


class InvalidInputError(MemoryServiceError):
    """Exception raised for invalid input data."""
    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=400,
            details=details
        )


class OpenAIServiceError(MemoryServiceError):
    """Exception raised for OpenAI API errors."""
    def __init__(self, original_error: OpenAIError):
        super().__init__(
            message="OpenAI service error",
            status_code=503,
            details={
                "openai_error_type": type(original_error).__name__,
                "openai_error_message": str(original_error)
            }
        )


class DatabaseError(MemoryServiceError):
    """Exception raised for database errors."""
    def __init__(self, original_error: sqlite3.Error):
        super().__init__(
            message="Database operation failed",
            status_code=500,
            details={
                "database_error_type": type(original_error).__name__,
                "database_error_message": str(original_error)
            }
        )


async def memory_service_exception_handler(request: Request, exc: MemoryServiceError) -> JSONResponse:
    """Handle custom memory service exceptions."""
    logger.error(
        "Memory service error: %s",
        exc.message,
        extra={
            "status_code": exc.status_code,
            "details": exc.details,
            "path": str(request.url.path),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code
        }
    )


async def validation_exception_handler(request: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    """Handle request validation errors."""
    logger.warning(
        "Validation error: %s",
        str(exc),
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "errors": exc.errors() if hasattr(exc, 'errors') else str(exc)
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": {
                "validation_errors": exc.errors() if hasattr(exc, 'errors') else [str(exc)]
            },
            "status_code": 422
        }
    )


async def openai_exception_handler(request: Request, exc: OpenAIError) -> JSONResponse:
    """Handle OpenAI API errors."""
    logger.error(
        "OpenAI API error: %s",
        str(exc),
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "openai_error_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=503,
        content={
            "error": "OpenAIServiceError",
            "message": "External AI service temporarily unavailable",
            "details": {
                "openai_error_type": type(exc).__name__,
                "retry_after": "30 seconds"
            },
            "status_code": 503
        }
    )


async def database_exception_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    """Handle database errors."""
    logger.error(
        "Database error: %s",
        str(exc),
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "database_error_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "DatabaseError",
            "message": "Database operation failed",
            "details": {
                "database_error_type": type(exc).__name__,
                "support_contact": "Check logs for details"
            },
            "status_code": 500
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "Unexpected error: %s",
        str(exc),
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": {
                "exception_type": type(exc).__name__,
                "support_contact": "Check server logs for details"
            },
            "status_code": 500
        }
    )