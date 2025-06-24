"""Custom exceptions for the worker service."""

from typing import Any, Dict, Optional, List
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for different types of exceptions."""
    
    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    
    # Authentication and authorization
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    
    # Data and query errors
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    INVALID_QUERY = "INVALID_QUERY"
    QUERY_EXECUTION_ERROR = "QUERY_EXECUTION_ERROR"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    
    # External service errors
    BIGQUERY_ERROR = "BIGQUERY_ERROR"
    LOOKER_ERROR = "LOOKER_ERROR"
    LLM_ERROR = "LLM_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    
    # Workflow and agent errors
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    AGENT_ERROR = "AGENT_ERROR"
    TASK_ERROR = "TASK_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


class BaseWorkerException(Exception):
    """Base exception class for all worker service exceptions."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize base exception.
        
        Args:
            message: Human-readable error message
            error_code: Specific error code
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format.
        
        Returns:
            Dictionary representation of the exception
        """
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details
        }
        
        if self.cause:
            result["cause"] = str(self.cause)
        
        return result
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return f"{self.error_code.value}: {self.message}"


class ValidationError(BaseWorkerException):
    """Exception raised for validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
            details: Additional details
        """
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = str(value)
        
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=error_details
        )
        self.field = field
        self.value = value


class ConfigurationError(BaseWorkerException):
    """Exception raised for configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
            details: Additional details
        """
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            details=error_details
        )
        self.config_key = config_key


class AuthenticationError(BaseWorkerException):
    """Exception raised for authentication errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize authentication error.
        
        Args:
            message: Error message
            details: Additional details
        """
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            details=details
        )


class AuthorizationError(BaseWorkerException):
    """Exception raised for authorization errors."""
    
    def __init__(
        self,
        message: str = "Access denied",
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize authorization error.
        
        Args:
            message: Error message
            resource: Resource being accessed
            action: Action being performed
            details: Additional details
        """
        error_details = details or {}
        if resource:
            error_details["resource"] = resource
        if action:
            error_details["action"] = action
        
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHORIZATION_ERROR,
            details=error_details
        )
        self.resource = resource
        self.action = action


class DataNotFoundError(BaseWorkerException):
    """Exception raised when requested data is not found."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize data not found error.
        
        Args:
            message: Error message
            resource_type: Type of resource not found
            resource_id: ID of resource not found
            details: Additional details
        """
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_NOT_FOUND,
            details=error_details
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class QueryError(BaseWorkerException):
    """Exception raised for query-related errors."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.QUERY_EXECUTION_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize query error.
        
        Args:
            message: Error message
            query: SQL query that caused the error
            error_code: Specific error code
            details: Additional details
        """
        error_details = details or {}
        if query:
            # Truncate long queries for logging
            error_details["query"] = query[:500] + "..." if len(query) > 500 else query
        
        super().__init__(
            message=message,
            error_code=error_code,
            details=error_details
        )
        self.query = query


class BigQueryError(BaseWorkerException):
    """Exception raised for BigQuery-specific errors."""
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        query: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize BigQuery error.
        
        Args:
            message: Error message
            job_id: BigQuery job ID
            query: SQL query
            details: Additional details
            cause: Original exception
        """
        error_details = details or {}
        if job_id:
            error_details["job_id"] = job_id
        if query:
            error_details["query"] = query[:500] + "..." if len(query) > 500 else query
        
        super().__init__(
            message=message,
            error_code=ErrorCode.BIGQUERY_ERROR,
            details=error_details,
            cause=cause
        )
        self.job_id = job_id
        self.query = query


class LookerError(BaseWorkerException):
    """Exception raised for Looker-specific errors."""
    
    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize Looker error.
        
        Args:
            message: Error message
            endpoint: Looker API endpoint
            status_code: HTTP status code
            details: Additional details
            cause: Original exception
        """
        error_details = details or {}
        if endpoint:
            error_details["endpoint"] = endpoint
        if status_code:
            error_details["status_code"] = status_code
        
        super().__init__(
            message=message,
            error_code=ErrorCode.LOOKER_ERROR,
            details=error_details,
            cause=cause
        )
        self.endpoint = endpoint
        self.status_code = status_code


class LLMError(BaseWorkerException):
    """Exception raised for LLM-specific errors."""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        prompt_length: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize LLM error.
        
        Args:
            message: Error message
            model: LLM model name
            prompt_length: Length of the prompt
            details: Additional details
            cause: Original exception
        """
        error_details = details or {}
        if model:
            error_details["model"] = model
        if prompt_length:
            error_details["prompt_length"] = prompt_length
        
        super().__init__(
            message=message,
            error_code=ErrorCode.LLM_ERROR,
            details=error_details,
            cause=cause
        )
        self.model = model
        self.prompt_length = prompt_length


class WorkflowError(BaseWorkerException):
    """Exception raised for workflow execution errors."""
    
    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize workflow error.
        
        Args:
            message: Error message
            workflow_id: Workflow identifier
            step: Current workflow step
            details: Additional details
            cause: Original exception
        """
        error_details = details or {}
        if workflow_id:
            error_details["workflow_id"] = workflow_id
        if step:
            error_details["step"] = step
        
        super().__init__(
            message=message,
            error_code=ErrorCode.WORKFLOW_ERROR,
            details=error_details,
            cause=cause
        )
        self.workflow_id = workflow_id
        self.step = step


class AgentError(BaseWorkerException):
    """Exception raised for agent-specific errors."""
    
    def __init__(
        self,
        message: str,
        agent_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize agent error.
        
        Args:
            message: Error message
            agent_id: Agent identifier
            agent_type: Type of agent
            details: Additional details
            cause: Original exception
        """
        error_details = details or {}
        if agent_id:
            error_details["agent_id"] = agent_id
        if agent_type:
            error_details["agent_type"] = agent_type
        
        super().__init__(
            message=message,
            error_code=ErrorCode.AGENT_ERROR,
            details=error_details,
            cause=cause
        )
        self.agent_id = agent_id
        self.agent_type = agent_type


class ResourceError(BaseWorkerException):
    """Exception raised for resource-related errors."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize resource error.
        
        Args:
            message: Error message
            resource_type: Type of resource
            resource_id: Resource identifier
            error_code: Specific error code
            details: Additional details
        """
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code=error_code,
            details=error_details
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class TimeoutError(BaseWorkerException):
    """Exception raised for timeout errors."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration
            operation: Operation that timed out
            details: Additional details
        """
        error_details = details or {}
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        if operation:
            error_details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code=ErrorCode.TIMEOUT_ERROR,
            details=error_details
        )
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class RateLimitError(BaseWorkerException):
    """Exception raised for rate limiting errors."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            limit: Rate limit threshold
            details: Additional details
        """
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        if limit:
            error_details["limit"] = limit
        
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_ERROR,
            details=error_details
        )
        self.retry_after = retry_after
        self.limit = limit


def handle_exception(exc: Exception) -> BaseWorkerException:
    """Convert generic exceptions to worker exceptions.
    
    Args:
        exc: Original exception
        
    Returns:
        Converted worker exception
    """
    if isinstance(exc, BaseWorkerException):
        return exc
    
    # Map common exception types
    if isinstance(exc, ValueError):
        return ValidationError(str(exc), cause=exc)
    elif isinstance(exc, KeyError):
        return DataNotFoundError(f"Key not found: {exc}", cause=exc)
    elif isinstance(exc, TimeoutError):
        return TimeoutError(str(exc), cause=exc)
    elif isinstance(exc, ConnectionError):
        return ResourceError(
            "Connection failed",
            error_code=ErrorCode.RESOURCE_UNAVAILABLE,
            cause=exc
        )
    else:
        return BaseWorkerException(
            f"Unexpected error: {str(exc)}",
            error_code=ErrorCode.INTERNAL_ERROR,
            cause=exc
        )


def format_error_response(exc: BaseWorkerException) -> Dict[str, Any]:
    """Format exception as API error response.
    
    Args:
        exc: Worker exception
        
    Returns:
        Formatted error response
    """
    return {
        "error": {
            "code": exc.error_code.value,
            "message": exc.message,
            "details": exc.details
        }
    }