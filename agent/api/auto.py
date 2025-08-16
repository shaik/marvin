"""
Auto endpoint router for LLM-powered store/retrieve decisions.
"""

import logging
from fastapi import APIRouter, status, Depends
from agent.config import settings
from agent.api.models import AutoRequest, AutoResponse
from agent.api.exceptions import InvalidInputError, MemoryServiceError


# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    tags=["auto"],
    responses={
        401: {"description": "Authentication required"},
        422: {"description": "Invalid request parameters"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    }
)


def get_settings():
    """Dependency to get application settings."""
    return settings


@router.post(
    "/auto",
    response_model=AutoResponse,
    status_code=status.HTTP_200_OK,  # Default; will change based on action
    summary="LLM-powered auto store or retrieve decision",
    description="""
    Automatically decide whether to store or retrieve memories using LLM.
    
    The system will:
    1. Send the user text to an LLM to determine intent (store vs retrieve)
    2. If confidence is high enough, execute the chosen action
    3. If confidence is low or invalid, return clarification request
    4. Support force_action to override clarification decisions
    
    Returns different status codes based on action:
    - 201: Memory stored successfully  
    - 200: Memory retrieved or clarification needed
    """,
    responses={
        200: {"description": "Retrieve completed or clarification needed"},
        201: {"description": "Memory stored successfully"},
    }
)
async def auto_endpoint(
    request: AutoRequest,
    app_settings = Depends(get_settings)
) -> AutoResponse:
    """
    LLM-powered auto endpoint that decides between store/retrieve actions.
    
    This is a STUB implementation that always returns clarify until Step 3.
    """
    
    # Input validation
    if not request.text.strip():
        raise InvalidInputError("Text cannot be empty", field="text")
    
    # Log the auto decision request
    logger.info(
        "Auto decision request received",
        extra={
            "event": "auto_decision_request",
            "text_length": len(request.text),
            "force_action": request.force_action,
            "text_preview": request.text[:50] + "..." if len(request.text) > 50 else request.text
        }
    )
    
    try:
        # STUB: Always return clarify for now
        # In Step 3, this will be replaced with actual LLM logic
        
        decision = {
            "normalized_text": request.text.strip(),
            "language": "en",  # Default assumption for stub
            "confidence": 0.0,  # Low confidence to trigger clarify
            "reason": "STUB: Implementation not complete - always triggers clarification",
            "clarify_prompt": f"I need clarification about your request: '{request.text.strip()}'. What would you like me to do?",
            "clarify_options": ["store", "retrieve"]
        }
        
        # Log the stubbed decision
        logger.info(
            "Auto decision completed (STUB)",
            extra={
                "event": "auto_decision",
                "action": "clarify",
                "confidence": 0.0,
                "language": "en",
                "reason": "stub_implementation"
            }
        )
        
        # Return clarify response (HTTP 200)
        return AutoResponse(
            action="clarify",
            decision=decision,
            result=None
        )
        
    except Exception as e:
        logger.error(
            "Auto decision failed",
            extra={
                "event": "auto_decision_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "text_preview": request.text[:50] + "..." if len(request.text) > 50 else request.text
            }
        )
        raise MemoryServiceError("Auto decision processing failed", status_code=500)
