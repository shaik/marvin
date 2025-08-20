"""
Configuration settings for Marvin Memory Service using Pydantic BaseSettings.
"""

try:
    from pydantic_settings import BaseSettings
except ModuleNotFoundError:  # Fallback when pydantic-settings isn't installed
    from pydantic import BaseModel as BaseSettings
from pydantic import Field
from typing import Optional, Union


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        ...,
        env="OPENAI_API_KEY",
        description="OpenAI API key for embedding generation"
    )
    
    # Database Configuration
    db_path: str = Field(
        default="agent/marvin_memory.db",
        env="DB_PATH",
        description="Path to SQLite database file"
    )
    
    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Server host address"
    )
    
    port: int = Field(
        default=5000,
        env="PORT",
        description="Server port number"
    )
    
    # Authentication Configuration
    api_auth_key: Union[str, None] = Field(
        default=None,
        env="API_AUTH_KEY",
        description="API key for authenticating requests to /api/v1/* endpoints. If None/unset, authentication is disabled for local development."
    )
    
    # CORS Configuration
    cors_origins: list = Field(
        default=[
            "http://localhost:19006",  # React Native default
            "http://localhost:3000",   # Common React dev server
            "http://127.0.0.1:19006",
            "http://127.0.0.1:3000",
        ],
        env="CORS_ORIGINS",
        description="Allowed CORS origins for frontend clients"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # Application Configuration
    app_name: str = Field(
        default="Marvin Memory Service",
        env="APP_NAME",
        description="Application name"
    )
    
    app_version: str = Field(
        default="1.0.0",
        env="APP_VERSION",
        description="Application version"
    )
    
    # Clarification Configuration
    clarify_score_gap: float = Field(
        default=0.05,
        env="CLARIFY_SCORE_GAP",
        description="Maximum allowed score gap between top-1 and top-2 to trigger clarification"
    )
    
    clarify_min_candidates: int = Field(
        default=2,
        env="CLARIFY_MIN_CANDIDATES", 
        description="Minimum number of candidates required to trigger clarification"
    )
    
    # Rate Limiting Configuration
    rate_limit_max_requests: int = Field(
        default=10,
        env="RATE_LIMIT_MAX_REQUESTS",
        description="Maximum number of requests per API key per time window"
    )
    
    rate_limit_window_seconds: int = Field(
        default=60,
        env="RATE_LIMIT_WINDOW_SECONDS",
        description="Time window in seconds for rate limiting"
    )
    
    # LLM Auto Decision Configuration
    llm_decider_model: str = Field(
        default="gpt-4o-mini",
        env="LLM_DECIDER_MODEL",
        description="OpenAI model used for auto store/retrieve decisions"
    )
    
    llm_decider_confidence_min: float = Field(
        default=0.70,
        env="LLM_DECIDER_CONFIDENCE_MIN",
        description="Minimum confidence threshold for LLM decisions (below triggers clarification)"
    )
    # LLM Answer Generation Configuration
    llm_answer_model: str = Field(
        default="gpt-4o-mini",
        env="LLM_ANSWER_MODEL",
        description="OpenAI model used to generate natural language answers from memories",
    )

    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
# Provide a safe fallback when required environment variables are missing
try:
    settings = Settings()
except Exception:
    settings = Settings(openai_api_key="")
