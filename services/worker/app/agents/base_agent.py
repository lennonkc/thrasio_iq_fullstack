"""Base Agent class for all agents in the system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from enum import Enum
import structlog
from datetime import datetime
from pydantic import BaseModel, Field


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class AgentState(BaseModel):
    """Agent state model."""
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Base abstract class for all agents."""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Optional configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.logger = structlog.get_logger().bind(agent_id=agent_id)
        self.state = AgentState(agent_id=agent_id)
        
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing results
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent with necessary resources."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources when agent is done."""
        pass
    
    def update_status(self, status: AgentStatus, task: Optional[str] = None, 
                     error: Optional[str] = None) -> None:
        """Update agent status.
        
        Args:
            status: New status
            task: Current task description
            error: Error message if status is ERROR
        """
        self.state.status = status
        self.state.current_task = task
        self.state.error_message = error
        self.state.updated_at = datetime.utcnow()
        
        self.logger.info(
            "Agent status updated",
            status=status.value,
            task=task,
            error=error
        )
    
    def get_state(self) -> AgentState:
        """Get current agent state.
        
        Returns:
            Current agent state
        """
        return self.state
    
    def update_context(self, key: str, value: Any) -> None:
        """Update agent context.
        
        Args:
            key: Context key
            value: Context value
        """
        self.state.context[key] = value
        self.state.updated_at = datetime.utcnow()
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get value from agent context.
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return self.state.context.get(key, default)
    
    async def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle errors during processing.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        error_msg = str(error)
        self.update_status(AgentStatus.ERROR, error=error_msg)
        
        self.logger.error(
            "Agent error occurred",
            error=error_msg,
            error_type=type(error).__name__,
            context=context or {}
        )
    
    def validate_input(self, input_data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate input data has required fields.
        
        Args:
            input_data: Input data to validate
            required_fields: List of required field names
            
        Returns:
            True if all required fields are present
        """
        missing_fields = [field for field in required_fields if field not in input_data]
        
        if missing_fields:
            self.logger.warning(
                "Missing required fields in input",
                missing_fields=missing_fields
            )
            return False
        
        return True