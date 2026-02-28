"""
Configuration management using Pydantic Settings with multi-environment support
"""
import os
import re
from pathlib import Path
from typing import List, Optional, Literal, Union
from pydantic import field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


# Supported environment types
EnvironmentType = Literal["development", "staging", "production", "test"]


class Settings(BaseSettings):
    """Application settings with multi-environment support
    
    Configuration loading priority (highest to lowest):
    1. Environment variables
    2. Environment-specific config file (.env.{ENVIRONMENT})
    3. Base config file (.env)
    4. Default values
    """
    
    # Environment
    ENVIRONMENT: EnvironmentType = "development"
    
    # Database URLs
    DATABASE_URL: str = "postgresql://localhost:5432/kavalan"
    MONGODB_URL: str = "mongodb://localhost:27017/kavalan"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API Keys
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # JWT
    JWT_SECRET: str = "dev_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["*"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate PostgreSQL database URL format"""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        if not v.startswith("postgresql://"):
            raise ValueError(
                f"DATABASE_URL must start with 'postgresql://', got: {v[:20]}..."
            )
        return v
    
    @field_validator("MONGODB_URL")
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL format"""
        if not v:
            raise ValueError("MONGODB_URL cannot be empty")
        if not v.startswith("mongodb://") and not v.startswith("mongodb+srv://"):
            raise ValueError(
                f"MONGODB_URL must start with 'mongodb://' or 'mongodb+srv://', got: {v[:20]}..."
            )
        return v
    
    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format"""
        if not v:
            raise ValueError("REDIS_URL cannot be empty")
        if not v.startswith("redis://") and not v.startswith("rediss://"):
            raise ValueError(
                f"REDIS_URL must start with 'redis://' or 'rediss://', got: {v[:20]}..."
            )
        return v
    
    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Validate JWT secret strength"""
        if not v:
            raise ValueError("JWT_SECRET cannot be empty")
        
        # In production, enforce strong secret
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production":
            if v == "dev_secret_key_change_in_production":
                raise ValueError(
                    "JWT_SECRET must be changed from default value in production environment"
                )
            if len(v) < 32:
                raise ValueError(
                    f"JWT_SECRET must be at least 32 characters in production, got {len(v)} characters"
                )
        
        return v
    
    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm is supported"""
        valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in valid_algorithms:
            raise ValueError(
                f"JWT_ALGORITHM must be one of {valid_algorithms}, got: {v}"
            )
        return v
    
    @field_validator("JWT_EXPIRATION_MINUTES")
    @classmethod
    def validate_jwt_expiration(cls, v: int) -> int:
        """Validate JWT expiration is reasonable"""
        if v <= 0:
            raise ValueError(
                f"JWT_EXPIRATION_MINUTES must be positive, got: {v}"
            )
        if v > 43200:  # 30 days
            raise ValueError(
                f"JWT_EXPIRATION_MINUTES must not exceed 43200 (30 days), got: {v}"
            )
        return v
    
    @field_validator("RATE_LIMIT_PER_MINUTE")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        """Validate rate limit is reasonable"""
        if v <= 0:
            raise ValueError(
                f"RATE_LIMIT_PER_MINUTE must be positive, got: {v}"
            )
        if v > 10000:
            raise ValueError(
                f"RATE_LIMIT_PER_MINUTE must not exceed 10000, got: {v}"
            )
        return v
    
    @field_validator("CELERY_BROKER_URL")
    @classmethod
    def validate_celery_broker_url(cls, v: str) -> str:
        """Validate Celery broker URL format"""
        if not v:
            raise ValueError("CELERY_BROKER_URL cannot be empty")
        if not v.startswith("redis://") and not v.startswith("rediss://"):
            raise ValueError(
                f"CELERY_BROKER_URL must start with 'redis://' or 'rediss://', got: {v[:20]}..."
            )
        return v
    
    @field_validator("CELERY_RESULT_BACKEND")
    @classmethod
    def validate_celery_result_backend(cls, v: str) -> str:
        """Validate Celery result backend URL format"""
        if not v:
            raise ValueError("CELERY_RESULT_BACKEND cannot be empty")
        if not v.startswith("redis://") and not v.startswith("rediss://"):
            raise ValueError(
                f"CELERY_RESULT_BACKEND must start with 'redis://' or 'rediss://', got: {v[:20]}..."
            )
        return v
    
    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_api_key(cls, v: str, info) -> str:
        """Validate Gemini API key in production"""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and not v:
            raise ValueError(
                "GEMINI_API_KEY must be set in production environment"
            )
        return v
    
    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_api_key(cls, v: str, info) -> str:
        """Validate OpenAI API key in production"""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and not v:
            raise ValueError(
                "OPENAI_API_KEY must be set in production environment"
            )
        return v
    
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from .env
        env_file_encoding="utf-8"
    )


def load_settings() -> Settings:
    """Load settings with environment-specific config file support
    
    Loading order:
    1. Load base .env file if it exists
    2. Load environment-specific .env.{ENVIRONMENT} file if it exists
    3. Environment variables override all file-based configs
    
    Returns:
        Settings: Configured settings instance
        
    Raises:
        ValueError: If configuration validation fails with descriptive error message
    """
    # Get environment from env var or default to development
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Determine base directory (where config files are located)
    base_dir = Path(__file__).parent.parent
    
    # Build list of config files to load (in order of priority)
    env_files = []
    
    # Base config file
    base_env_file = base_dir / ".env"
    if base_env_file.exists():
        env_files.append(base_env_file)
    
    # Environment-specific config file
    env_specific_file = base_dir / f".env.{environment}"
    if env_specific_file.exists():
        env_files.append(env_specific_file)
    
    # Load settings with environment-specific config
    # Pydantic will load files in order, with later files overriding earlier ones
    # Environment variables will override all file-based configs
    try:
        if env_files:
            # Create settings with the first file
            settings = Settings(_env_file=str(env_files[0]))
            
            # If there's an environment-specific file, reload with it
            if len(env_files) > 1:
                # Re-create settings to load environment-specific overrides
                settings = Settings(_env_file=str(env_files[1]))
        else:
            # No config files found, use defaults and env vars only
            settings = Settings()
        
        return settings
    
    except ValidationError as e:
        # Format validation errors into a clear message
        error_messages = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"  - {field}: {message}")
        
        error_summary = "\n".join(error_messages)
        raise ValueError(
            f"Configuration validation failed:\n{error_summary}\n\n"
            f"Please check your environment variables and config files."
        ) from e


def get_config_file_path(environment: Optional[str] = None) -> Path:
    """Get the path to the config file for a specific environment
    
    Args:
        environment: Environment name (dev, staging, production, test)
                    If None, uses current ENVIRONMENT setting
    
    Returns:
        Path: Path to the environment-specific config file
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    base_dir = Path(__file__).parent.parent
    return base_dir / f".env.{environment}"


# Global settings instance
settings = load_settings()
