"""
Pydantic models for request and response schemas.
"""

from pydantic import BaseModel, Field, constr
from typing import List, Optional, Any, Dict, Literal


# Request Models
class StoreRequest(BaseModel):
    """Request model for storing a new memory."""
    text: str = Field(..., description="Memory text to store", min_length=1)
    language: str = Field(default="he", description="Language of the memory text")
    location: Optional[str] = Field(default=None, description="Optional location context")


class QueryRequest(BaseModel):
    """Request model for querying memories."""
    query: str = Field(..., description="Search query text", min_length=1)
    top_k: int = Field(default=3, description="Number of top results to return", ge=1, le=100)


class UpdateRequest(BaseModel):
    """Request model for updating an existing memory."""
    memory_id: str = Field(..., description="UUID of the memory to update")
    new_text: str = Field(..., description="New text content", min_length=1)


class DeleteRequest(BaseModel):
    """Request model for deleting a memory."""
    memory_id: constr(min_length=1) = Field(..., description="UUID of the memory to delete")


class CancelRequest(BaseModel):
    """Request model for handling cancellation intent."""
    last_input_text: constr(min_length=1) = Field(..., description="Last user input text to identify target memory")


class ClarifyRequest(BaseModel):
    """Request model for clarification resolution."""
    session_id: Optional[str] = Field(default=None, description="Session ID linking to prior query candidates")
    query: str = Field(..., description="Original query that needed clarification", min_length=1)
    chosen_memory_id: str = Field(..., description="UUID of the chosen memory from clarification candidates")


class AutoRequest(BaseModel):
    """Request model for LLM-powered auto store/retrieve endpoint."""
    text: str = Field(..., description="User input text for automatic processing", min_length=1)
    force_action: Optional[Literal["store", "retrieve"]] = Field(
        default=None, 
        description="Force a specific action even if LLM would choose clarify"
    )


# Response Models
class StoreResponse(BaseModel):
    """Response model for memory storage operation."""
    duplicate_detected: bool = Field(..., description="Whether a duplicate was found")
    memory_id: str = Field(..., description="UUID of the stored or duplicate memory")
    existing_memory_preview: Optional[str] = Field(default=None, description="Preview of duplicate memory if found")
    similarity_score: Optional[float] = Field(default=None, description="Similarity score if duplicate found")


class MemoryCandidate(BaseModel):
    """Model for a memory search candidate."""
    memory_id: str = Field(..., description="UUID of the memory")
    text: str = Field(..., description="Memory text content")
    similarity_score: float = Field(..., description="Similarity score for this candidate")


class QueryResponse(BaseModel):
    """Response model for memory query operation."""
    session_id: str = Field(..., description="Session ID for tracking follow-up clarifications")
    candidates: List[MemoryCandidate] = Field(..., description="List of matching memory candidates")
    clarification_required: Optional[bool] = Field(default=None, description="Whether clarification is needed due to ambiguous results")
    clarification_question: Optional[str] = Field(default=None, description="Question to help user clarify their intent")


class UpdateResponse(BaseModel):
    """Response model for memory update operation."""
    success: bool = Field(..., description="Whether the update was successful")
    before: Optional[str] = Field(default=None, description="Original text content")
    after: Optional[str] = Field(default=None, description="Updated text content")
    error: Optional[str] = Field(default=None, description="Error message if unsuccessful")


class DeleteResponse(BaseModel):
    """Response model for memory deletion operation."""
    success: bool = Field(..., description="Whether the deletion was successful")
    deleted_text: str = Field(..., description="Text content of deleted memory")


class CancelResponse(BaseModel):
    """Response model for cancellation handling."""
    confirmation_text: str = Field(..., description="Confirmation message for user")
    target_memory_id: Optional[str] = Field(default=None, description="UUID of target memory for cancellation")


class ClarifyResponse(BaseModel):
    """Response model for ambiguity clarification."""
    clarification_question: Optional[str] = Field(default=None, description="Generated clarification question")
    message: Optional[str] = Field(default=None, description="Status message")
    candidates: Optional[List[MemoryCandidate]] = Field(default=None, description="Ambiguous memory candidates")
    clarification_resolved: Optional[bool] = Field(default=None, description="Whether clarification was resolved")
    memory_id: Optional[str] = Field(default=None, description="UUID of the resolved memory")
    text: Optional[str] = Field(default=None, description="Text content of the resolved memory")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")


class MemoriesResponse(BaseModel):
    """Response model for getting all memories."""
    total_memories: int = Field(..., description="Total number of stored memories")
    memories: List[MemoryCandidate] = Field(..., description="All stored memories")


class AutoResponse(BaseModel):
    """Response model for LLM auto endpoint."""
    action: Literal["store", "retrieve", "clarify"] = Field(..., description="Action taken by the system")
    decision: Dict[str, Any] = Field(..., description="LLM decision details including confidence, reason, etc.")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Result of the action (store/retrieve result or None for clarify)")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")