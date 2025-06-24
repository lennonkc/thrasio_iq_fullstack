"""Logging configuration for the worker service."""

import sys
import logging
import structlog
from typing import Any, Dict, Optional
from datetime import datetime
import json

from .config import get_settings, LogLevel


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class ContextFilter(logging.Filter):
    """Filter to add context information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize context filter.
        
        Args:
            context: Additional context to add to logs
        """
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            True to include the record
        """
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def setup_logging(
    log_level: Optional[LogLevel] = None,
    log_format: Optional[str] = None,
    service_name: Optional[str] = None,
    service_version: Optional[str] = None
) -> None:
    """Setup logging configuration.
    
    Args:
        log_level: Logging level
        log_format: Log format (json or text)
        service_name: Service name for context
        service_version: Service version for context
    """
    settings = get_settings()
    
    # Use provided values or fall back to settings
    log_level = log_level or settings.log_level
    log_format = log_format or settings.log_format
    service_name = service_name or settings.app_name
    service_version = service_version or settings.app_version
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.value))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.value))
    
    # Set formatter based on format preference
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    
    # Add context filter
    context_filter = ContextFilter({
        "service_name": service_name,
        "service_version": service_version,
        "environment": settings.environment.value
    })
    console_handler.addFilter(context_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Configure structlog
    configure_structlog(log_level, log_format)
    
    # Set specific logger levels
    configure_third_party_loggers(log_level)


def configure_structlog(log_level: LogLevel, log_format: str) -> None:
    """Configure structlog for structured logging.
    
    Args:
        log_level: Logging level
        log_format: Log format preference
    """
    # Determine processors based on format
    if log_format.lower() == "json":
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def configure_third_party_loggers(log_level: LogLevel) -> None:
    """Configure third-party library loggers.
    
    Args:
        log_level: Base logging level
    """
    # Reduce verbosity of third-party libraries
    third_party_loggers = {
        "google.cloud": logging.WARNING,
        "google.auth": logging.WARNING,
        "urllib3": logging.WARNING,
        "requests": logging.WARNING,
        "httpx": logging.WARNING,
        "asyncio": logging.WARNING,
        "aiohttp": logging.WARNING,
        "redis": logging.WARNING,
        "sqlalchemy": logging.WARNING,
        "alembic": logging.WARNING
    }
    
    # Set levels for third-party loggers
    for logger_name, level in third_party_loggers.items():
        logger = logging.getLogger(logger_name)
        # Only set if current level is more verbose
        if logger.level < level:
            logger.setLevel(level)
    
    # In development, allow more verbose logging for our own code
    settings = get_settings()
    if settings.is_development and log_level == LogLevel.DEBUG:
        # Keep our application loggers at DEBUG level
        app_loggers = [
            "app",
            "worker",
            "agents",
            "tools",
            "workflows"
        ]
        
        for logger_name in app_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def add_context(**kwargs: Any) -> None:
    """Add context to all subsequent log messages in this thread.
    
    Args:
        **kwargs: Context key-value pairs
    """
    # This would typically use contextvars in a real implementation
    # For now, we'll use a simple approach
    pass


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class.
        
        Returns:
            Configured logger with class context
        """
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__module__).bind(
                class_name=self.__class__.__name__
            )
        return self._logger


class RequestLogger:
    """Logger for HTTP requests and responses."""
    
    def __init__(self, logger_name: str = "request"):
        """Initialize request logger.
        
        Args:
            logger_name: Name for the logger
        """
        self.logger = get_logger(logger_name)
    
    def log_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log HTTP request.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body (will be truncated if too long)
            user_id: User identifier
            session_id: Session identifier
        """
        log_data = {
            "event": "http_request",
            "method": method,
            "url": url
        }
        
        if headers:
            # Filter sensitive headers
            safe_headers = {k: v for k, v in headers.items() 
                          if k.lower() not in {'authorization', 'cookie', 'x-api-key'}}
            log_data["headers"] = safe_headers
        
        if body:
            # Truncate large bodies
            log_data["body"] = body[:1000] + "..." if len(body) > 1000 else body
        
        if user_id:
            log_data["user_id"] = user_id
        
        if session_id:
            log_data["session_id"] = session_id
        
        self.logger.info("HTTP request", **log_data)
    
    def log_response(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log HTTP response.
        
        Args:
            status_code: HTTP status code
            headers: Response headers
            body: Response body (will be truncated if too long)
            duration_ms: Request duration in milliseconds
            error: Error message if any
        """
        log_data = {
            "event": "http_response",
            "status_code": status_code
        }
        
        if headers:
            log_data["headers"] = headers
        
        if body:
            # Truncate large bodies
            log_data["body"] = body[:1000] + "..." if len(body) > 1000 else body
        
        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms
        
        if error:
            log_data["error"] = error
        
        # Choose log level based on status code
        if status_code >= 500:
            self.logger.error("HTTP response", **log_data)
        elif status_code >= 400:
            self.logger.warning("HTTP response", **log_data)
        else:
            self.logger.info("HTTP response", **log_data)


# Initialize logging on module import
def init_logging() -> None:
    """Initialize logging with default settings."""
    try:
        setup_logging()
    except Exception as e:
        # Fallback to basic logging if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logging.getLogger(__name__).warning(
            f"Failed to setup advanced logging: {e}. Using basic logging."
        )


# Auto-initialize logging
init_logging()