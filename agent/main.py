"""
Marvin's FastAPI backend service.
Provides HTTP API endpoints for storing and querying memories with semantic search.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from openai import OpenAIError
import sqlite3
import os

# Import configuration and dependencies
from .config import settings
from .memory import init_db

# Import API routers
from .api.store import router as store_router
from .api.query import router as query_router
from .api.update import router as update_router
from .api.delete import router as delete_router
from .api.cancel import router as cancel_router
from .api.clarify import router as clarify_router
from .api.admin import router as admin_router

# Import exception handlers
from .api.exceptions import (
    MemoryServiceError,
    memory_service_exception_handler,
    validation_exception_handler,
    openai_exception_handler,
    database_exception_handler,
    generic_exception_handler
)

from .api.models import HealthResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    
    try:
        # Validate settings
        logger.info("Validating configuration...")
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        # Initialize database
        logger.info("Initializing database at %s", settings.db_path)
        init_db()
        logger.info("Database initialized successfully")
        
        # Log configuration
        logger.info("Configuration loaded:")
        logger.info("- Host: %s", settings.host)
        logger.info("- Port: %s", settings.port)
        logger.info("- Database: %s", settings.db_path)
        logger.info("- CORS Origins: %s", settings.cors_origins)
        logger.info("- Log Level: %s", settings.log_level)
        
        logger.info("%s startup completed successfully", settings.app_name)
        
    except Exception as e:
        logger.error("Failed to start %s: %s", settings.app_name, str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down %s", settings.app_name)


# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title=settings.app_name,
    description="""
    Personal memory assistant backend with semantic search capabilities.
    
    ## Features
    - **Semantic Memory Storage**: Store memories with automatic duplicate detection
    - **Intelligent Search**: Query memories using natural language with AI-powered similarity matching
    - **Memory Management**: Update and delete stored memories
    - **Ambiguity Resolution**: Handle unclear queries with clarification prompts
    - **Cancellation Support**: Identify and cancel recent memories
    
    ## Authentication
    Requires OPENAI_API_KEY environment variable for embedding generation.
    
    ## Rate Limits
    API calls are limited by OpenAI's embedding API rate limits.
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(MemoryServiceError, memory_service_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(OpenAIError, openai_exception_handler)
app.add_exception_handler(sqlite3.Error, database_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Check if the service is running and healthy.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"model": ErrorResponse, "description": "Service is unhealthy"},
    }
)
async def health_check() -> HealthResponse:
    """Health check endpoint to verify service status."""
    logger.info("Health check requested")
    
    try:
        # Basic health checks could be added here
        # For now, just return healthy if we can respond
        return HealthResponse(
            status="healthy",
            service=settings.app_name,
            version=settings.app_version
        )
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        raise MemoryServiceError("Service health check failed", status_code=503)

# Include all API routers
app.include_router(store_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")
app.include_router(update_router, prefix="/api/v1")
app.include_router(delete_router, prefix="/api/v1")
app.include_router(cancel_router, prefix="/api/v1")
app.include_router(clarify_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

# Legacy endpoint redirects for backward compatibility
@app.post("/store")
async def legacy_store_redirect(request: Request):
    """Redirect legacy store endpoint to new API version."""
    return {"message": "Please use /api/v1/store endpoint", "new_endpoint": "/api/v1/store"}

@app.post("/query") 
async def legacy_query_redirect(request: Request):
    """Redirect legacy query endpoint to new API version."""
    return {"message": "Please use /api/v1/query endpoint", "new_endpoint": "/api/v1/query"}

@app.post("/update")
async def legacy_update_redirect(request: Request):
    """Redirect legacy update endpoint to new API version."""
    return {"message": "Please use /api/v1/update endpoint", "new_endpoint": "/api/v1/update"}

@app.post("/delete")
async def legacy_delete_redirect(request: Request):
    """Redirect legacy delete endpoint to new API version."""
    return {"message": "Please use /api/v1/delete endpoint", "new_endpoint": "/api/v1/delete"}

@app.post("/cancel")
async def legacy_cancel_redirect(request: Request):
    """Redirect legacy cancel endpoint to new API version."""
    return {"message": "Please use /api/v1/cancel endpoint", "new_endpoint": "/api/v1/cancel"}

@app.post("/clarify")
async def legacy_clarify_redirect(request: Request):
    """Redirect legacy clarify endpoint to new API version."""
    return {"message": "Please use /api/v1/clarify endpoint", "new_endpoint": "/api/v1/clarify"}

@app.get("/memories")
async def legacy_memories_redirect(request: Request):
    """Redirect legacy memories endpoint to new API version."""
    return {"message": "Please use /api/v1/admin/memories endpoint", "new_endpoint": "/api/v1/admin/memories"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agent.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )