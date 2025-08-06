"""
Pydantic models for request and response schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict


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
    memory_id: str = Field(..., description="UUID of the memory to delete")


class CancelRequest(BaseModel):
    """Request model for handling cancellation intent."""
    last_input: str = Field(..., description="Last user input to identify target memory")


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
    candidates: List[MemoryCandidate] = Field(..., description="List of matching memory candidates")


class UpdateResponse(BaseModel):
    """Response model for memory update operation."""
    success: bool = Field(..., description="Whether the update was successful")
    before: Optional[str] = Field(default=None, description="Original text content")
    after: Optional[str] = Field(default=None, description="Updated text content")
    error: Optional[str] = Field(default=None, description="Error message if unsuccessful")


class DeleteResponse(BaseModel):
    """Response model for memory deletion operation."""
    success: bool = Field(..., description="Whether the deletion was successful")
    deleted_text: Optional[str] = Field(default=None, description="Text content of deleted memory")
    error: Optional[str] = Field(default=None, description="Error message if unsuccessful")


class CancelResponse(BaseModel):
    """Response model for cancellation handling."""
    target_memory_id: Optional[str] = Field(default=None, description="UUID of target memory for cancellation")
    confirmation_text: str = Field(..., description="Confirmation message for user")


class ClarifyResponse(BaseModel):
    """Response model for ambiguity clarification."""
    clarification_question: Optional[str] = Field(default=None, description="Generated clarification question")
    message: Optional[str] = Field(default=None, description="Status message")
    candidates: Optional[List[MemoryCandidate]] = Field(default=None, description="Ambiguous memory candidates")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")


class MemoriesResponse(BaseModel):
    """Response model for getting all memories."""
    total_memories: int = Field(..., description="Total number of stored memories")
    memories: List[MemoryCandidate] = Field(..., description="All stored memories")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    status_code: int = Field(..., description="HTTP status code")