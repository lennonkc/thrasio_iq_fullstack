"""Configuration management for the worker service."""

import os
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from enum import Enum


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

    project_id: str = Field(..., env="GCP_PROJECT_ID")
    region: str = Field(default="us-central1", env="GCP_REGION")
    credentials_path: Optional[str] = Field(
        default=None, env="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # BigQuery specific
    bigquery_dataset: str = Field(default="analytics", env="BIGQUERY_DATASET")
    bigquery_location: str = Field(default="US", env="BIGQUERY_LOCATION")
    bigquery_timeout: int = Field(default=60, env="BIGQUERY_TIMEOUT")
    bigquery_max_results: int = Field(default=10000, env="BIGQUERY_MAX_RESULTS")

    class Config:
        env_prefix = "GCP_"


class LookerConfig(BaseSettings):
    """Looker configuration."""

    # base_url: str = Field(..., env="LOOKER_BASE_URL")
    # client_id: str = Field(..., env="LOOKER_CLIENT_ID")
    # client_secret: str = Field(..., env="LOOKER_CLIENT_SECRET")
    # api_version: str = Field(default="4.0", env="LOOKER_API_VERSION")
    # timeout: int = Field(default=30, env="LOOKER_TIMEOUT")
    # verify_ssl: bool = Field(default=True, env="LOOKER_VERIFY_SSL")

    # # Default space and folder IDs
    # default_space_id: Optional[str] = Field(default=None, env="LOOKER_DEFAULT_SPACE_ID")
    # default_folder_id: Optional[str] = Field(
    #     default=None, env="LOOKER_DEFAULT_FOLDER_ID"
    # )

    # @field_validator("base_url")
    # @classmethod
    # def validate_base_url(cls, v):
    #     if not v.startswith(("http://", "https://")):
    #         raise ValueError("base_url must start with http:// or https://")
    #     return v.rstrip("/")

    # class Config:
    #     env_prefix = "LOOKER_"


class LLMConfig(BaseSettings):
    """Large Language Model configuration."""

    provider: str = Field(default="vertex-ai", env="LLM_PROVIDER")
    model_name: str = Field(default="gemini-pro", env="LLM_MODEL_NAME")
    temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=2048, env="LLM_MAX_TOKENS")
    timeout: int = Field(default=30, env="LLM_TIMEOUT")

    # Vertex AI specific
    vertex_ai_location: str = Field(default="us-central1", env="VERTEX_AI_LOCATION")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError("temperature must be between 0 and 2")
        return v

    class Config:
        env_prefix = "LLM_"


class RedisConfig(BaseSettings):
    """Redis configuration for caching and session management."""

    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    ssl: bool = Field(default=False, env="REDIS_SSL")

    # Connection pool settings
    max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    retry_on_timeout: bool = Field(default=True, env="REDIS_RETRY_ON_TIMEOUT")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")

    # Cache settings
    default_ttl: int = Field(default=3600, env="REDIS_DEFAULT_TTL")  # 1 hour
    schema_cache_ttl: int = Field(
        default=86400, env="REDIS_SCHEMA_CACHE_TTL"
    )  # 24 hours

    class Config:
        env_prefix = "REDIS_"


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    # url: str = Field(..., env="DATABASE_URL")
    # pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    # max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    # pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    # pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    # echo: bool = Field(default=False, env="DATABASE_ECHO")

    # class Config:
    #     env_prefix = "DATABASE_"


class SecurityConfig(BaseSettings):
    """Security configuration."""

    # secret_key: str = Field(..., env="SECRET_KEY")
    # jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    # jwt_expiration: int = Field(default=3600, env="JWT_EXPIRATION")  # 1 hour

    # # API rate limiting
    # rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    # rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds

    # # CORS settings
    # cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    # cors_methods: List[str] = Field(
    #     default=["GET", "POST", "PUT", "DELETE"], env="CORS_METHODS"
    # )

    # @field_validator("cors_origins", mode="before")
    # @classmethod
    # def parse_cors_origins(cls, v):
    #     if isinstance(v, str):
    #         return [origin.strip() for origin in v.split(",")]
    #     return v

    # @field_validator("cors_methods", mode="before")
    # @classmethod
    # def parse_cors_methods(cls, v):
    #     if isinstance(v, str):
    #         return [method.strip().upper() for method in v.split(",")]
    #     return v

    # class Config:
    #     env_prefix = "SECURITY_"


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""

    # enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    # enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")
    # enable_profiling: bool = Field(default=False, env="ENABLE_PROFILING")

    # # Prometheus metrics
    # metrics_port: int = Field(default=8080, env="METRICS_PORT")
    # metrics_path: str = Field(default="/metrics", env="METRICS_PATH")

    # # Jaeger tracing
    # jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    # jaeger_service_name: str = Field(
    #     default="thrasio-worker", env="JAEGER_SERVICE_NAME"
    # )

    # # Health check
    # health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")

    # class Config:
    #     env_prefix = "MONITORING_"


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
    workflow_timeout: int = Field(default=600, env="WORKFLOW_TIMEOUT")  # 10 minutes
    max_workflow_retries: int = Field(default=2, env="MAX_WORKFLOW_RETRIES")

    class Config:
        env_prefix = "WORKER_"


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
    google_cloud: GoogleCloudConfig = GoogleCloudConfig()
    looker: LookerConfig = LookerConfig()
    llm: LLMConfig = LLMConfig()
    redis: RedisConfig = RedisConfig()
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    worker: WorkerConfig = WorkerConfig()

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

    def get_database_url(self) -> str:
        """Get the database URL."""
        return self.database.url

    def get_redis_url(self) -> str:
        """Get the Redis URL."""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"

    def get_bigquery_client_options(self) -> Dict[str, Any]:
        """Get BigQuery client options."""
        options = {
            "project": self.google_cloud.project_id,
            "location": self.google_cloud.bigquery_location,
        }

        if self.google_cloud.credentials_path:
            options["credentials_path"] = self.google_cloud.credentials_path

        return options

    def get_looker_client_options(self) -> Dict[str, Any]:
        """Get Looker client options."""
        return {
            "base_url": self.looker.base_url,
            "client_id": self.looker.client_id,
            "client_secret": self.looker.client_secret,
            "api_version": self.looker.api_version,
            "timeout": self.looker.timeout,
            "verify_ssl": self.looker.verify_ssl,
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        Settings instance
    """
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment.

    Returns:
        New Settings instance
    """
    global settings
    settings = Settings()
    return settings
