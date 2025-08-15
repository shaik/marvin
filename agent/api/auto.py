"""
Auto endpoint router for LLM-powered store/retrieve decisions.
"""

import json
import logging
from datetime import datetime, UTC
from typing import Dict, Any
from fastapi import APIRouter, status, Depends, Response
from openai import OpenAI, OpenAIError
from agent.config import settings
from agent.api.models import AutoRequest, AutoResponse
from agent.api.exceptions import InvalidInputError, MemoryServiceError, OpenAIServiceError
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


async def classify_user_intent(text: str, app_settings) -> Dict[str, Any]:
    """
    Use LLM to classify user intent as store, retrieve, or clarify.
    
    Args:
        text: User input text to classify
        app_settings: Application settings with LLM configuration
        
    Returns:
        Dict with action, confidence, language, and reason
        
    Raises:
        OpenAIError: If LLM API call fails
    """
    # Import the OpenAI client from memory module to use the same mocked instance
    from agent.memory import client
    
    # Design system prompt with few-shot examples
    system_prompt = """You are a classifier that decides if a message is:
- store: save new information (statements, notes, facts, tasks, lists)
- retrieve: get existing information (questions, commands to recall)
- clarify: when not sure

Return only valid JSON: {"action": "store|retrieve|clarify", "confidence": 0.0-1.0, "language": "en|he|mixed", "reason": "brief explanation"}

Examples:

User: "I bought milk from the store today"
{"action": "store", "confidence": 0.95, "language": "en", "reason": "stating a fact to remember"}

User: "קניתי חלב היום"
{"action": "store", "confidence": 0.95, "language": "he", "reason": "stating a fact to remember in Hebrew"}

User: "When did I buy milk?"
{"action": "retrieve", "confidence": 0.90, "language": "en", "reason": "asking about past information"}

User: "מתי קניתי חלב?"
{"action": "retrieve", "confidence": 0.90, "language": "he", "reason": "asking about past information in Hebrew"}

User: "What should I do with this milk?"
{"action": "clarify", "confidence": 0.30, "language": "en", "reason": "unclear intent - could be asking for advice"}

User: "milk"
{"action": "clarify", "confidence": 0.20, "language": "en", "reason": "too vague - need more context"}

User: "Remember: doctor appointment Tuesday 3pm"
{"action": "store", "confidence": 0.98, "language": "en", "reason": "explicit instruction to remember information"}

User: "Find my doctor appointment"
{"action": "retrieve", "confidence": 0.92, "language": "en", "reason": "asking to find stored information"}

User: "My password is ABC123"
{"action": "store", "confidence": 0.85, "language": "en", "reason": "sharing information to store"}

User: "What's my password?"
{"action": "retrieve", "confidence": 0.88, "language": "en", "reason": "asking for stored information"}"""

    try:
        # Make LLM API call
        response = client.chat.completions.create(
            model=app_settings.llm_decider_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=150,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        # Parse response
        llm_response = response.choices[0].message.content.strip()
        decision = json.loads(llm_response)
        
        # Validate required fields
        required_fields = ["action", "confidence", "language", "reason"]
        for field in required_fields:
            if field not in decision:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate action value
        if decision["action"] not in ["store", "retrieve", "clarify"]:
            raise ValueError(f"Invalid action: {decision['action']}")
        
        # Ensure confidence is a float between 0 and 1
        confidence = float(decision["confidence"])
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Invalid confidence: {confidence}")
        decision["confidence"] = confidence
        
        # Add normalized text
        decision["normalized_text"] = text.strip()
        
        return decision
        
    except json.JSONDecodeError as e:
        logger.warning(
            "LLM returned invalid JSON",
            extra={
                "event": "llm_json_parse_error",
                "error": str(e),
                "llm_response": llm_response[:200] if 'llm_response' in locals() else "unknown",
                "text_preview": text[:50]
            }
        )
        # Return clarify decision for invalid JSON
        return {
            "action": "clarify",
            "confidence": 0.0,
            "language": "en",  # Default
            "reason": "LLM returned invalid JSON format",
            "normalized_text": text.strip()
        }
        
    except (ValueError, KeyError) as e:
        logger.warning(
            "LLM returned invalid decision format",
            extra={
                "event": "llm_decision_validation_error",
                "error": str(e),
                "llm_response": llm_response[:200] if 'llm_response' in locals() else "unknown",
                "text_preview": text[:50]
            }
        )
        # Return clarify decision for invalid format
        return {
            "action": "clarify",
            "confidence": 0.0,
            "language": "en",  # Default
            "reason": "LLM decision format validation failed",
            "normalized_text": text.strip()
        }
        
    except OpenAIError as e:
        logger.error(
            "OpenAI API error during classification",
            extra={
                "event": "llm_api_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "text_preview": text[:50]
            }
        )
        raise  # Re-raise to be handled by caller


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
    response: Response,
    app_settings = Depends(get_settings)
) -> AutoResponse:
    """
    LLM-powered auto endpoint that decides between store/retrieve actions.
    
    Uses LLM to classify user intent and execute the appropriate action.
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
        # Step 1: Check for force_action override
        if request.force_action:
            # Force action override - skip LLM decision
            final_action = request.force_action
            decision = {
                "action": final_action,
                "normalized_text": request.text.strip(),
                "language": "unknown",  # Not determined by LLM
                "confidence": 1.0,  # Forced actions have max confidence
                "reason": f"User forced action: {final_action}"
            }
            
            logger.info(
                "Force action override applied",
                extra={
                    "event": "auto_decision",
                    "action": final_action,
                    "confidence": 1.0,
                    "language": "unknown",
                    "reason": "force_action_override"
                }
            )
        else:
            # Step 2: Get LLM classification
            decision = await classify_user_intent(request.text, app_settings)
            
            # Step 3: Apply confidence threshold
            if decision["confidence"] < app_settings.llm_decider_confidence_min:
                final_action = "clarify"
                decision["action"] = "clarify"
                decision["reason"] = f"Low confidence ({decision['confidence']:.2f} < {app_settings.llm_decider_confidence_min})"
            else:
                final_action = decision["action"]
            
            # Log the LLM decision
            logger.info(
                "LLM auto decision completed",
                extra={
                    "event": "auto_decision",
                    "action": final_action,
                    "confidence": decision["confidence"],
                    "language": decision["language"],
                    "reason": decision["reason"]
                }
            )
        
        # Step 4: Execute the decided action
        result = None
        
        if final_action == "store":
            # Execute store action
            try:
                # Determine language for metadata (use LLM detected or default)
                language = decision.get("language", "en") if decision.get("language") != "unknown" else "en"
                if language == "mixed":
                    language = "en"  # Default for mixed language
                
                metadata = {
                    "timestamp": utc_now_iso_z(),
                    "language": language,
                    "location": None
                }
                
                store_result = store_memory(decision["normalized_text"], metadata)
                
                # Convert store result to expected format
                result = {
                    "duplicate_detected": store_result.get("duplicate_detected", False),
                    "memory_id": store_result.get("memory_id"),
                    "existing_memory_preview": store_result.get("existing_memory_preview"),
                    "similarity_score": store_result.get("similarity_score")
                }
                
                # Set status code for store
                response.status_code = status.HTTP_201_CREATED
                
            except Exception as e:
                logger.error(
                    "Store action failed",
                    extra={
                        "event": "auto_store_error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "text_preview": request.text[:50]
                    }
                )
                raise MemoryServiceError("Failed to store memory", status_code=500)
                
        elif final_action == "retrieve":
            # Execute retrieve action
            try:
                query_result = query_memory(decision["normalized_text"], top_k=5)
                
                # Convert query result to expected format
                result = {
                    "candidates": [
                        {
                            "memory_id": candidate["memory_id"],
                            "text": candidate["text"],
                            "similarity_score": candidate["similarity_score"]
                        }
                        for candidate in query_result
                    ]
                }
                
                # Set status code for retrieve
                response.status_code = status.HTTP_200_OK
                
            except Exception as e:
                logger.error(
                    "Retrieve action failed",
                    extra={
                        "event": "auto_retrieve_error",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "text_preview": request.text[:50]
                    }
                )
                raise MemoryServiceError("Failed to retrieve memories", status_code=500)
                
        else:  # final_action == "clarify"
            # Return clarification request
            decision["clarify_prompt"] = f"I'm not sure what you want me to do with: '{decision['normalized_text']}'. Would you like me to store this information or help you find something?"
            decision["clarify_options"] = ["store", "retrieve"]
            
            # Set status code for clarify
            response.status_code = status.HTTP_200_OK
        
        # Return response
        return AutoResponse(
            action=final_action,
            decision=decision,
            result=result
        )
        
    except OpenAIError as e:
        logger.error(
            "OpenAI service error during auto decision",
            extra={
                "event": "auto_openai_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "text_preview": request.text[:50]
            }
        )
        raise OpenAIServiceError(e)
        
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
