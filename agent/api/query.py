"""
Query endpoint router for memory search operations.
"""

from fastapi import APIRouter, Depends, status
import logging

from ..memory import query_memory
from ..config import Settings, settings
from .models import QueryRequest, QueryResponse, MemoryCandidate, ErrorResponse
from .exceptions import MemoryServiceError, InvalidInputError, OpenAIServiceError, DatabaseError
from openai import OpenAIError
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/query",
    tags=["Memory Search"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        503: {"model": ErrorResponse, "description": "OpenAI service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)


def get_settings() -> Settings:
    """Dependency to get application settings."""
    return settings


def _generate_clarification_question(query: str, top_candidates: list) -> str:
    """Generate a clarification question based on query and candidates.
    
    Args:
        query: The original user query
        top_candidates: List of top memory candidates (at least 2)
        
    Returns:
        A clarification question string
    """
    import re
    
    # Extract words from query (focus on capitalized words as potential proper nouns)
    query_words = query.split()
    capitalized_words = [word.strip('.,!?') for word in query_words if word[0].isupper()]
    
    # Find capitalized words (proper nouns) that appear in multiple candidate texts
    # These are usually the most important disambiguating terms
    proper_noun_subjects = []
    for word in capitalized_words:
        # Skip common question words even if capitalized
        if word.lower() in {"what", "where", "when", "who", "how", "which", "why"}:
            continue
        # Normalize the word by removing possessive forms and punctuation
        normalized_word = word.lower().rstrip("'s").strip(".,!?'\"")
        candidate_matches = sum(1 for candidate in top_candidates if normalized_word in candidate.text.lower())
        if candidate_matches >= 2:
            # Store the original capitalized form for the question
            original_word = word.rstrip("'s").strip(".,!?'\"")
            proper_noun_subjects.append(original_word)
    
    # If we found proper nouns, prioritize them
    if proper_noun_subjects:
        subject = proper_noun_subjects[0]  # Use the first found proper noun
        return f"There are multiple entries mentioning '{subject}'. Which one do you mean?"
    
    # If no proper nouns, check longer words (but avoid common words like "code")
    common_words = {"code", "what", "where", "when", "who", "how", "the", "and", "for", "with"}
    longer_words = [word.strip('.,!?').lower() for word in query_words if len(word) > 3 and word.lower() not in common_words]
    
    ambiguous_subjects = []
    for word in longer_words:
        candidate_matches = sum(1 for candidate in top_candidates if word in candidate.text.lower())
        if candidate_matches >= 2:
            ambiguous_subjects.append(word)
    
    # Generate question based on found ambiguous subjects
    if ambiguous_subjects:
        subject = ambiguous_subjects[0]  # Use the first found ambiguous subject
        return f"There are multiple entries mentioning '{subject}'. Which one do you mean?"
    else:
        return "There are multiple matching entries. Which one do you mean?"


@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Search memories by semantic similarity",
    description="""
    Search stored memories using semantic similarity.
    
    The system will:
    1. Generate an embedding for the query text using OpenAI
    2. Compare against all stored memory embeddings using cosine similarity
    3. Return the top-k most similar memories ranked by score
    
    Higher similarity scores indicate better matches.
    """,
    responses={
        200: {"description": "Search completed successfully"},
    }
)
async def query_memory_endpoint(
    request: QueryRequest,
    app_settings: Settings = Depends(get_settings)
) -> QueryResponse:
    """Query memories using semantic similarity search."""
    
    # Log the request
    logger.info(
        "Query request received",
        extra={
            "query_length": len(request.query),
            "top_k": request.top_k
        }
    )
    
    try:
        # Validate input
        if not request.query.strip():
            raise InvalidInputError("Query cannot be empty", field="query")
        
        if request.top_k <= 0 or request.top_k > 100:
            raise InvalidInputError("top_k must be between 1 and 100", field="top_k")
        
        # Query memories
        candidates = query_memory(request.query.strip(), request.top_k)
        
        # Convert to response models
        memory_candidates = [
            MemoryCandidate(
                memory_id=candidate["memory_id"],
                text=candidate["text"],
                similarity_score=candidate["similarity_score"]
            )
            for candidate in candidates
        ]
        
        # Check if clarification is needed
        clarification_required = False
        clarification_question = None
        
        if (len(memory_candidates) >= app_settings.clarify_min_candidates):
            # Check if top two scores are too close
            top1_score = memory_candidates[0].similarity_score
            top2_score = memory_candidates[1].similarity_score
            score_gap = abs(top1_score - top2_score)
            
            if score_gap <= app_settings.clarify_score_gap:
                clarification_required = True
                
                # Generate clarification question
                clarification_question = _generate_clarification_question(
                    request.query.strip(), 
                    memory_candidates[:2]
                )
                
                # Log clarification trigger
                logger.info(
                    "Clarification triggered due to close scores",
                    extra={
                        "top1_memory_id": memory_candidates[0].memory_id[:8],
                        "top1_score": top1_score,
                        "top2_memory_id": memory_candidates[1].memory_id[:8], 
                        "top2_score": top2_score,
                        "score_gap": score_gap,
                        "clarify_threshold": app_settings.clarify_score_gap
                    }
                )
        
        # Log success
        logger.info(
            "Query operation completed",
            extra={
                "results_count": len(memory_candidates),
                "top_scores": [c.similarity_score for c in memory_candidates[:3]],
                "clarification_required": clarification_required
            }
        )
        
        return QueryResponse(
            candidates=memory_candidates,
            clarification_required=clarification_required,
            clarification_question=clarification_question
        )
        
    except InvalidInputError:
        raise
    except OpenAIError as e:
        logger.error("OpenAI service error during query", extra={"error": str(e)})
        raise OpenAIServiceError(e)
    except sqlite3.Error as e:
        logger.error("Database error during query", extra={"error": str(e)})
        raise DatabaseError(e)
    except Exception as e:
        logger.error("Unexpected error during query", extra={"error": str(e)}, exc_info=True)
        raise MemoryServiceError("Failed to query memories", status_code=500)