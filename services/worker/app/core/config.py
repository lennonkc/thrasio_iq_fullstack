"""Configuration management for the worker service."""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum
from dotenv import load_dotenv

# Build the absolute path to the .env file, which is in the parent directory of 'app'
# This makes loading robust, regardless of the current working directory.
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


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


class GoogleCloudConfig(BaseModel):
    """Google Cloud configuration."""
    project_id: str
    bigquery_project_id: str
    region: str = "us-central1"
    credentials_path: Optional[str] = None
    bigquery_dataset: str = "analytics"
    bigquery_location: str = "US"
    bigquery_timeout: int = 60
    bigquery_max_results: int = 10000


class LLMConfig(BaseModel):
    """Large Language Model configuration."""
    provider: str = "vertex-ai"
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.1
    timeout: int = 30
    project_id: str
    vertex_ai_location: str = "us-central1"
    credentials_path: Optional[str] = None

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError("temperature must be between 0 and 2")
        return v


class WorkerConfig(BaseModel):
    """Worker-specific configuration."""
    max_concurrent_tasks: int = 10
    task_timeout: int = 300
    retry_attempts: int = 3
    retry_delay: int = 5
    queue_name: str = "data_analysis"
    dead_letter_queue: str = "data_analysis_dlq"
    workflow_timeout: int = 600
    max_workflow_retries: int = 2


class LangsmithConfig(BaseModel):
    """Langsmith tracing configuration."""
    tracing: bool = False
    api_key: Optional[str] = None
    project: str = "thrasio_iq_backend"

    @field_validator("tracing", mode="before")
    @classmethod
    def parse_tracing(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v


class Settings(BaseSettings):
    """Main application settings."""
    model_config = SettingsConfigDict(env_nested_delimiter='__')

    app_name: str = "Thrasio IQ Worker"
    app_version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "json"

    google_cloud: GoogleCloudConfig
    llm: LLMConfig
    worker: WorkerConfig
    langsmith: LangsmithConfig

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
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    def get_bigquery_client_options(self) -> Dict[str, Any]:
        options = {
            "project": self.google_cloud.bigquery_project_id,
            "location": self.google_cloud.bigquery_location,
        }
        if self.google_cloud.credentials_path:
            options["credentials_path"] = self.google_cloud.credentials_path
        return options

    def get_llm_client_options(self) -> Dict[str, Any]:
        options = {
            "project": self.llm.project_id,
            "location": self.llm.vertex_ai_location,
        }
        if self.llm.credentials_path:
            options["credentials_path"] = self.llm.credentials_path
        return options


# Global settings instance
settings = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings