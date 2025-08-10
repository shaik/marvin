"""
Marvin's memory engine module.
Handles storage, retrieval, and semantic search of user memories using SQLite and OpenAI embeddings.
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from openai import OpenAI, OpenAIError

from .api.exceptions import DatabaseError

# Configure structured JSON logging
class StructuredLogger:
    """Custom structured logger for JSON output."""
    
    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplication
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler with JSON formatter
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        self.logger.addHandler(handler)
    
    def _log(self, level: str, event: str, **details: Any) -> None:
        """Log structured JSON message."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "event": event,
            "module": "memory",
            **details
        }
        self.logger.info(json.dumps(log_entry))
    
    def info(self, event: str, **details: Any) -> None:
        """Log info level structured message."""
        self._log("INFO", event, **details)
    
    def error(self, event: str, **details: Any) -> None:
        """Log error level structured message."""
        self._log("ERROR", event, **details)
    
    def warning(self, event: str, **details: Any) -> None:
        """Log warning level structured message."""
        self._log("WARNING", event, **details)

# Initialize structured logger
logger = StructuredLogger(__name__)

# Import settings for configuration
from .config import settings

# Initialize OpenAI client with error handling
try:
    client = OpenAI(api_key=settings.openai_api_key)
    logger.info("openai_client_initialized", api_key_present=bool(settings.openai_api_key))
except Exception as e:
    logger.error("openai_client_initialization_failed", error=str(e))
    raise

# Database path from settings
DB_PATH = settings.db_path

# Embedding cache to reduce OpenAI API calls
_embedding_cache: Dict[str, List[float]] = {}

def _get_text_hash(text: str) -> str:
    """Generate a hash for text to use as cache key.
    
    Args:
        text: Input text to hash.
        
    Returns:
        SHA-256 hash of the text.
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def init_db() -> None:
    """Initialize the SQLite database and create memories table if it doesn't exist.
    
    Creates the memories table with proper schema and handles any database errors.
    Logs the initialization process with structured logging.
    
    Raises:
        sqlite3.Error: If database creation fails.
        OSError: If database file cannot be created.
    """
    logger.info("database_initialization_started", db_path=DB_PATH)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                embedding TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                language TEXT DEFAULT 'he',
                location TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("database_initialization_completed", 
                   db_path=DB_PATH, 
                   table_created="memories")
        
    except sqlite3.Error as e:
        logger.error("database_initialization_failed", 
                    db_path=DB_PATH, 
                    error=str(e), 
                    error_type="sqlite3.Error")
        raise
    except OSError as e:
        logger.error("database_file_creation_failed", 
                    db_path=DB_PATH, 
                    error=str(e), 
                    error_type="OSError")
        raise
    except Exception as e:
        logger.error("database_initialization_unexpected_error", 
                    db_path=DB_PATH, 
                    error=str(e), 
                    error_type=type(e).__name__)
        raise

def embed_text(text: str) -> List[float]:
    """Generate embedding for input text using OpenAI's text-embedding-ada-002 model.
    
    Uses caching to avoid repeated API calls for the same text.
    Handles OpenAI API errors gracefully with structured logging.
    
    Args:
        text: Input text to embed.
        
    Returns:
        List of embedding values as floats.
        
    Raises:
        OpenAIError: If OpenAI API call fails.
        ValueError: If text is empty or invalid.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty or whitespace-only")
    
    # Normalize text for consistent caching
    normalized_text = text.strip()
    text_hash = _get_text_hash(normalized_text)
    
    # Check cache first
    if text_hash in _embedding_cache:
        logger.info("embedding_cache_hit", 
                   text_preview=normalized_text[:50] + "..." if len(normalized_text) > 50 else normalized_text,
                   text_length=len(normalized_text),
                   cache_key=text_hash[:8])
        return _embedding_cache[text_hash]
    
    logger.info("embedding_generation_started", 
               text_preview=normalized_text[:50] + "..." if len(normalized_text) > 50 else normalized_text,
               text_length=len(normalized_text),
               cache_key=text_hash[:8])
    
    try:
        start_time = time.time()
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=normalized_text
        )
        embedding = response.data[0].embedding
        duration = time.time() - start_time
        
        # Cache the embedding
        _embedding_cache[text_hash] = embedding
        
        logger.info("embedding_generation_completed", 
                   text_preview=normalized_text[:50] + "..." if len(normalized_text) > 50 else normalized_text,
                   text_length=len(normalized_text),
                   embedding_dimension=len(embedding),
                   duration_seconds=round(duration, 3),
                   cache_key=text_hash[:8],
                   cache_size=len(_embedding_cache))
        
        return embedding
        
    except OpenAIError as e:
        logger.error("openai_embedding_api_error", 
                    text_preview=normalized_text[:50] + "..." if len(normalized_text) > 50 else normalized_text,
                    error=str(e),
                    error_type=type(e).__name__,
                    cache_key=text_hash[:8])
        raise
    except Exception as e:
        logger.error("embedding_generation_unexpected_error", 
                    text_preview=normalized_text[:50] + "..." if len(normalized_text) > 50 else normalized_text,
                    error=str(e),
                    error_type=type(e).__name__,
                    cache_key=text_hash[:8])
        raise

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two embedding vectors.
    
    Computes the cosine of the angle between two vectors, returning a value
    between -1 and 1, where 1 indicates identical vectors.
    
    Args:
        a: First embedding vector.
        b: Second embedding vector.
        
    Returns:
        Cosine similarity score between -1 and 1.
        
    Raises:
        ValueError: If vectors are empty or have different dimensions.
        TypeError: If inputs are not lists of numbers.
    """
    if not a or not b:
        raise ValueError("Embedding vectors cannot be empty")
    
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: {len(a)} vs {len(b)}")
    
    try:
        a_np = np.array(a, dtype=np.float64)
        b_np = np.array(b, dtype=np.float64)
    except (ValueError, TypeError) as e:
        raise TypeError(f"Embedding vectors must contain numeric values: {str(e)}")
    
    # Calculate norms
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    
    # Handle zero vectors
    if norm_a == 0 or norm_b == 0:
        logger.warning("cosine_similarity_zero_vector", 
                      norm_a=float(norm_a), 
                      norm_b=float(norm_b))
        return 0.0
    
    # Calculate cosine similarity
    dot_product = np.dot(a_np, b_np)
    similarity = dot_product / (norm_a * norm_b)
    
    return float(similarity)

def store_memory(text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Store a new memory with duplicate detection.
    
    Generates embeddings for the input text, checks for duplicates against
    existing memories using cosine similarity, and stores the memory if no
    duplicate is found.
    
    Args:
        text: Memory text to store.
        metadata: Dictionary containing timestamp, language, location.
        
    Returns:
        Dictionary with storage result and duplicate information containing:
        - duplicate_detected: Boolean indicating if duplicate was found
        - memory_id: UUID of the stored or duplicate memory
        - existing_memory_preview: Text of duplicate (if found)
        - similarity_score: Similarity score of duplicate (if found)
        
    Raises:
        ValueError: If text is empty or metadata is invalid.
        sqlite3.Error: If database operations fail.
        OpenAIError: If embedding generation fails.
    """
    if not text or not text.strip():
        raise ValueError("Memory text cannot be empty")
    
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary")
    
    normalized_text = text.strip()
    
    logger.info("memory_store_started", 
               text_preview=normalized_text[:100] + "..." if len(normalized_text) > 100 else normalized_text,
               text_length=len(normalized_text),
               metadata=metadata)
    
    try:
        # Generate embedding for new text
        new_embedding = embed_text(normalized_text)
        
        # Check for duplicates
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, text, embedding FROM memories")
            existing_memories = cursor.fetchall()
            
            logger.info("duplicate_check_started", 
                       existing_memories_count=len(existing_memories))
            
            for memory_id, existing_text, embedding_json in existing_memories:
                try:
                    existing_embedding = json.loads(embedding_json)
                    similarity = cosine_similarity(new_embedding, existing_embedding)
                    
                    logger.info("similarity_calculated", 
                               memory_id=memory_id[:8],
                               similarity_score=round(similarity, 4))
                    
                    if similarity >= 0.85:
                        logger.info("duplicate_detected", 
                                   memory_id=memory_id[:8],
                                   similarity_score=round(similarity, 4),
                                   threshold=0.85)
                        conn.close()
                        return {
                            "duplicate_detected": True,
                            "existing_memory_preview": existing_text,
                            "similarity_score": similarity,
                            "memory_id": memory_id
                        }
                        
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("embedding_parse_error", 
                                  memory_id=memory_id[:8],
                                  error=str(e))
                    continue
            
            # No duplicate found, store new memory
            memory_id = str(uuid.uuid4())
            embedding_json = json.dumps(new_embedding)
            
            cursor.execute("""
                INSERT INTO memories (id, text, embedding, timestamp, language, location)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                normalized_text,
                embedding_json,
                metadata.get("timestamp"),
                metadata.get("language", "he"),
                metadata.get("location")
            ))
            
            conn.commit()
            
            logger.info("memory_stored_successfully", 
                       memory_id=memory_id,
                       text_length=len(normalized_text),
                       embedding_dimension=len(new_embedding))
            
            return {
                "duplicate_detected": False,
                "memory_id": memory_id
            }
            
        finally:
            conn.close()
            
    except sqlite3.Error as e:
        logger.error("database_error_during_store", 
                    error=str(e),
                    error_type="sqlite3.Error")
        raise
    except Exception as e:
        logger.error("memory_store_unexpected_error", 
                    error=str(e),
                    error_type=type(e).__name__)
        raise

def query_memory(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Query memories using semantic similarity search.
    
    Generates an embedding for the query text and compares it against all
    stored memory embeddings to find the most semantically similar memories.
    
    Args:
        query: Search query text.
        top_k: Number of top results to return (must be positive).
        
    Returns:
        List of dictionaries with memory_id, text, and similarity_score,
        sorted by similarity score in descending order.
        
    Raises:
        ValueError: If query is empty or top_k is invalid.
        sqlite3.Error: If database operations fail.
        OpenAIError: If embedding generation fails.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")
    
    normalized_query = query.strip()
    
    logger.info("memory_query_started", 
               query=normalized_query,
               top_k=top_k)
    
    try:
        # Generate embedding for query
        query_embedding = embed_text(normalized_query)
        
        # Get all memories from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id, text, embedding FROM memories")
            memories = cursor.fetchall()
            
            logger.info("memories_retrieved", 
                       memory_count=len(memories))
            
            if not memories:
                logger.info("no_memories_found")
                return []
            
            # Calculate similarities and rank
            results = []
            for memory_id, text, embedding_json in memories:
                try:
                    memory_embedding = json.loads(embedding_json)
                    similarity = cosine_similarity(query_embedding, memory_embedding)
                    
                    results.append({
                        "memory_id": memory_id,
                        "text": text,
                        "similarity_score": similarity
                    })
                    
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("memory_embedding_parse_error", 
                                  memory_id=memory_id[:8],
                                  error=str(e))
                    continue
            
            # Sort by similarity (descending) and take top_k
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_results = results[:top_k]
            
            logger.info("memory_query_completed", 
                       query=normalized_query,
                       results_count=len(top_results),
                       top_scores=[round(r["similarity_score"], 4) for r in top_results[:3]])
            
            return top_results
            
        finally:
            conn.close()
            
    except sqlite3.Error as e:
        logger.error("database_error_during_query", 
                    query=normalized_query,
                    error=str(e),
                    error_type="sqlite3.Error")
        raise
    except Exception as e:
        logger.error("memory_query_unexpected_error", 
                    query=normalized_query,
                    error=str(e),
                    error_type=type(e).__name__)
        raise

def update_memory(memory_id: str, new_text: str) -> Dict[str, Any]:
    """Update an existing memory with new text and regenerate embedding.
    
    Retrieves the existing memory, updates its text content, regenerates
    the embedding, and stores the updated version in the database.
    
    Args:
        memory_id: UUID of the memory to update.
        new_text: New text content to replace existing text.
        
    Returns:
        Dictionary with success status and before/after text containing:
        - success: Boolean indicating if update was successful
        - before: Original text content (if successful)
        - after: New text content (if successful)
        - error: Error message (if unsuccessful)
        
    Raises:
        ValueError: If memory_id or new_text is invalid.
        sqlite3.Error: If database operations fail.
        OpenAIError: If embedding generation fails.
    """
    if not memory_id or not isinstance(memory_id, str):
        raise ValueError("memory_id must be a non-empty string")
    
    if not new_text or not new_text.strip():
        raise ValueError("new_text cannot be empty")
    
    normalized_text = new_text.strip()
    
    logger.info("memory_update_started", 
               memory_id=memory_id[:8],
               new_text_length=len(normalized_text))
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Get original text
            cursor.execute("SELECT text FROM memories WHERE id = ?", (memory_id,))
            result = cursor.fetchone()
            
            if not result:
                logger.warning("memory_not_found_for_update", 
                              memory_id=memory_id[:8])
                return {"success": False, "error": "Memory not found"}
            
            original_text = result[0]
            
            # Generate new embedding
            new_embedding = embed_text(normalized_text)
            embedding_json = json.dumps(new_embedding)
            
            # Update memory
            cursor.execute("""
                UPDATE memories 
                SET text = ?, embedding = ? 
                WHERE id = ?
            """, (normalized_text, embedding_json, memory_id))
            
            conn.commit()
            
            logger.info("memory_update_completed", 
                       memory_id=memory_id,
                       original_text_length=len(original_text),
                       new_text_length=len(normalized_text),
                       embedding_dimension=len(new_embedding))
            
            return {
                "success": True,
                "before": original_text,
                "after": normalized_text
            }
            
        finally:
            conn.close()
            
    except sqlite3.Error as e:
        logger.error("database_error_during_update", 
                    memory_id=memory_id[:8],
                    error=str(e),
                    error_type="sqlite3.Error")
        raise
    except Exception as e:
        logger.error("memory_update_unexpected_error", 
                    memory_id=memory_id[:8],
                    error=str(e),
                    error_type=type(e).__name__)
        raise

def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Delete a memory by ID.
    
    Removes the specified memory from the database and returns the deleted text
    for confirmation purposes.
    
    Args:
        memory_id: UUID of the memory to delete.
        
    Returns:
        Dictionary with success status and deleted text containing:
        - success: Boolean indicating if deletion was successful
        - deleted_text: Text content of deleted memory (if successful)
        - error: Error message (if unsuccessful)
        
    Raises:
        ValueError: If memory_id is invalid.
        sqlite3.Error: If database operations fail.
    """
    if not memory_id or not isinstance(memory_id, str):
        raise ValueError("memory_id must be a non-empty string")
    
    logger.info("memory_deletion_started", 
               memory_id=memory_id[:8])
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Get text before deletion for logging
            cursor.execute("SELECT text FROM memories WHERE id = ?", (memory_id,))
            result = cursor.fetchone()
            
            if not result:
                logger.warning("memory_not_found_for_deletion", 
                              memory_id=memory_id[:8])
                return {"success": False, "error": "Memory not found"}
            
            deleted_text = result[0]
            
            # Delete memory
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            
            logger.info("memory_deletion_completed", 
                       memory_id=memory_id,
                       deleted_text_length=len(deleted_text),
                       deleted_text_preview=deleted_text[:50] + "..." if len(deleted_text) > 50 else deleted_text)
            
            return {
                "success": True,
                "deleted_text": deleted_text
            }
            
        finally:
            conn.close()
            
    except sqlite3.Error as e:
        logger.error("database_error_during_deletion", 
                    memory_id=memory_id[:8],
                    error=str(e),
                    error_type="sqlite3.Error")
        raise
    except Exception as e:
        logger.error("memory_deletion_unexpected_error", 
                    memory_id=memory_id[:8],
                    error=str(e),
                    error_type=type(e).__name__)
        raise


def clear_embedding_cache() -> int:
    """Clear the embedding cache and return number of cached items removed.
    
    Useful for memory management or testing purposes.
    
    Returns:
        Number of cached embeddings that were cleared.
    """
    global _embedding_cache
    cache_size = len(_embedding_cache)
    _embedding_cache.clear()
    
    logger.info("embedding_cache_cleared", 
               items_removed=cache_size)
    
    return cache_size


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about the embedding cache.
    
    Returns:
        Dictionary with cache statistics including size and memory usage.
    """
    cache_size = len(_embedding_cache)
    
    # Estimate memory usage (rough calculation)
    total_embeddings = sum(len(embedding) for embedding in _embedding_cache.values())
    estimated_memory_mb = (total_embeddings * 8) / (1024 * 1024)  # 8 bytes per float64
    
    stats = {
        "cache_size": cache_size,
        "total_embeddings": total_embeddings,
        "estimated_memory_mb": round(estimated_memory_mb, 2)
    }
    
    logger.info("cache_stats_requested", **stats)
    
    return stats


def get_memory_by_id(memory_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific memory by its ID.
    
    Args:
        memory_id: UUID of the memory to retrieve
        
    Returns:
        Dictionary with memory details if found, None if not found
        
    Raises:
        ValueError: If memory_id is empty
        DatabaseError: If database operation fails
    """
    if not memory_id or not memory_id.strip():
        raise ValueError("Memory ID cannot be empty")
    
    try:
        with sqlite3.connect(settings.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, timestamp, language, location
                FROM memories 
                WHERE id = ?
            """, (memory_id.strip(),))
            
            row = cursor.fetchone()
            if not row:
                logger.info("memory_not_found", memory_id=memory_id[:8])
                return None
                
            memory_data = {
                "memory_id": row[0],
                "text": row[1], 
                "timestamp": row[2],
                "language": row[3],
                "location": row[4]
            }
            
            logger.info(
                "memory_retrieved_by_id",
                memory_id=memory_id[:8],
                text_length=len(memory_data["text"])
            )
            
            return memory_data
            
    except sqlite3.Error as e:
        logger.error("database_error_get_memory", memory_id=memory_id[:8], error=str(e))
        raise DatabaseError(f"Failed to retrieve memory: {e}")