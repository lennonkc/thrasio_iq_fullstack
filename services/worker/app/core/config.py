"""Configuration management for the worker service."""

import os
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from enum import Enum
from dotenv import load_dotenv


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class GoogleCloudConfig(BaseSettings):
    """Google Cloud configuration."""

    # Default GCP project for most services (AI Agent)
    project_id: str = Field(default="thrasio-dev-ai-agent", env="GCP_PROJECT_ID")
    region: str = Field(default="us-central1", env="GCP_REGION")
    credentials_path: Optional[str] = Field(
        default=None, env="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # BigQuery specific - uses separate project
    bigquery_project_id: str = Field(
        default="thrasio-dev-data-wh-7ee095", env="GCP_BIGQUERY_PROJECT_ID"
    )
    bigquery_dataset: str = Field(default="analytics", env="GCP_BIGQUERY_DATASET")
    bigquery_location: str = Field(default="US", env="GCP_BIGQUERY_LOCATION")
    bigquery_timeout: int = Field(default=60, env="GCP_BIGQUERY_TIMEOUT")
    bigquery_max_results: int = Field(default=10000, env="GCP_BIGQUERY_MAX_RESULTS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class LLMConfig(BaseSettings):
    """Large Language Model configuration."""

    provider: str = Field(default="vertex-ai", env="LLM_PROVIDER")
    model_name: str = Field(default="gemini-2.5-flash", env="LLM_MODEL_NAME")
    temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    # max_tokens: int = Field(default=2048, env="LLM_MAX_TOKENS")
    timeout: int = Field(default=30, env="LLM_TIMEOUT")

    # Vertex AI specific
    project_id: str = Field(default="thrasio-dev-ai-agent", env="LLM_PROJECT_ID")
    vertex_ai_location: str = Field(default="us-central1", env="LLM_VERTEX_AI_LOCATION")
    credentials_path: Optional[str] = Field(
        default=None, env="LLM_GOOGLE_APPLICATION_CREDENTIALS"
    )

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError("temperature must be between 0 and 2")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class WorkerConfig(BaseSettings):
    """Worker-specific configuration."""

    max_concurrent_tasks: int = Field(default=10, env="WORKER_MAX_CONCURRENT_TASKS")
    task_timeout: int = Field(default=300, env="WORKER_TASK_TIMEOUT")  # 5 minutes
    retry_attempts: int = Field(default=3, env="WORKER_RETRY_ATTEMPTS")
    retry_delay: int = Field(default=5, env="WORKER_RETRY_DELAY")  # seconds

    # Queue settings
    queue_name: str = Field(default="data_analysis", env="WORKER_QUEUE_NAME")
    dead_letter_queue: str = Field(
        default="data_analysis_dlq", env="WORKER_DEAD_LETTER_QUEUE"
    )

    # Workflow settings
    workflow_timeout: int = Field(
        default=600, env="WORKER_WORKFLOW_TIMEOUT"
    )  # 10 minutes
    max_workflow_retries: int = Field(default=2, env="WORKER_MAX_WORKFLOW_RETRIES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class LangsmithConfig(BaseSettings):
    """Langsmith tracing configuration."""

    tracing: bool = Field(default=False, env="LANGSMITH_TRACING")
    api_key: Optional[str] = Field(default=None, env="LANGSMITH_API_KEY")
    project: str = Field(default="thrasio_iq_backend", env="LANGSMITH_PROJECT")

    @field_validator("tracing", mode="before")
    @classmethod
    def parse_tracing(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class Settings(BaseSettings):
    """Main application settings."""

    # Basic app settings
    app_name: str = Field(default="Thrasio IQ Worker", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text

    # Service configurations
    google_cloud: GoogleCloudConfig = Field(default_factory=GoogleCloudConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    worker: WorkerConfig = Field(default_factory=WorkerConfig)
    langsmith: LangsmithConfig = Field(default_factory=LangsmithConfig)

    @field_validator("environment", mode="before")
    @classmethod
    def parse_environment(cls, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def parse_log_level(cls, v):
        if isinstance(v, str):
            return LogLevel(v.upper())
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == Environment.TESTING

    def get_bigquery_client_options(self) -> Dict[str, Any]:
        """Get BigQuery client options."""
        options = {
            "project": self.google_cloud.bigquery_project_id,
            "location": self.google_cloud.bigquery_location,
        }

        if self.google_cloud.credentials_path:
            options["credentials_path"] = self.google_cloud.credentials_path

        return options

    def get_llm_client_options(self) -> Dict[str, Any]:
        """Get LLM client options for Vertex AI."""
        options = {
            "project": self.llm.project_id,
            "location": self.llm.vertex_ai_location,
        }

        if self.llm.credentials_path:
            options["credentials_path"] = self.llm.credentials_path

        return options

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True
        extra = "ignore"


# Global settings instance
settings = None


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        Settings instance
    """
    global settings
    if settings is None:
        # Load .env file before creating Settings instance
        load_dotenv()
        settings = Settings()
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment.

    Returns:
        New Settings instance
    """
    global settings
    settings = Settings()
    return settings
