from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: List[BaseMessage]


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, **kwargs: Any):
        # Initialize any common attributes here
        pass

    @abstractmethod
    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        """Run the agent and return the final result."""
        pass

    @abstractmethod
    async def astream(self, **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the agent's intermediate steps and final result."""
        # The 'yield' statement is required for async generators
        if False:
            yield