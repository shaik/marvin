"""
Auto endpoint router for LLM-powered store/retrieve decisions.
"""

import logging
from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from agent.config import settings
from agent.api.models import AutoRequest, AutoResponse
from agent.api.exceptions import InvalidInputError, MemoryServiceError
import openai
import json
from agent.memory import store_memory, query_memory
from agent.utils.time import utc_now_iso_z


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
        # Build simple LLM prompt for decisioning
        client = openai.OpenAI(api_key=app_settings.openai_api_key)

        system_prompt = (
            "You classify a user's input as either 'store' or 'retrieve'. "
            "Always respond with strict JSON like: {\n"
            "  \"action\": \"store|retrieve\",\n"
            "  \"normalized_text\": \"...\",\n"
            "  \"language\": \"he|en|...\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"reason\": \"...\"\n}"
        )

        user_prompt = request.text.strip()

        chat = client.chat.completions.create(
            model=app_settings.llm_decider_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )

        # Parse LLM response JSON
        parsed: dict
        try:
            content = chat.choices[0].message.content if chat and chat.choices else "{}"
            parsed = json.loads(content or "{}")
        except Exception as parse_err:
            logger.debug("auto_decision_parse_error", extra={"error": str(parse_err)})
            parsed = {}

        action = str(parsed.get("action", "")).strip().lower()
        normalized_text = str(parsed.get("normalized_text") or user_prompt)
        language = str(parsed.get("language") or "he")
        try:
            confidence = float(parsed.get("confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0
        reason = str(parsed.get("reason") or "")

        # Apply threshold / force overrides
        chosen_action = action if action in {"store", "retrieve"} else "clarify"
        if request.force_action in {"store", "retrieve"}:
            chosen_action = request.force_action
        elif confidence < app_settings.llm_decider_confidence_min:
            chosen_action = "clarify"

        decision = {
            "action": chosen_action if chosen_action != "clarify" else (action or "clarify"),
            "normalized_text": normalized_text,
            "language": language,
            "confidence": confidence,
            "reason": reason,
        }

        # If clarify, include clarify prompt/options
        if chosen_action == "clarify":
            decision.update({
                "clarify_prompt": f"I need clarification about your request: '{normalized_text}'. What would you like me to do?",
                "clarify_options": ["store", "retrieve"],
            })

        # Log the decision (message contains the token for test visibility)
        logger.info(
            "auto_decision",
            extra={
                "action": chosen_action,
                "confidence": confidence,
                "language": language,
                "raw_action": action,
            }
        )

        # Execute action when not clarifying
        if chosen_action == "store":
            metadata = {
                "timestamp": utc_now_iso_z(),
                "language": language,
                "location": None,
            }
            store_result = store_memory(normalized_text, metadata)
            response = AutoResponse(
                action="store",
                decision=decision,
                result=store_result,
            )
            # 201 for created; 409 for duplicate
            status_code = status.HTTP_201_CREATED if not store_result.get("duplicate_detected") else status.HTTP_409_CONFLICT
            return JSONResponse(status_code=status_code, content=response.model_dump())

        if chosen_action == "retrieve":
            candidates = query_memory(normalized_text)
            response = AutoResponse(
                action="retrieve",
                decision=decision,
                result={"candidates": candidates},
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump())

        # Clarify path (default)
        return JSONResponse(status_code=status.HTTP_200_OK, content=AutoResponse(action="clarify", decision=decision, result=None).model_dump())
        
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

