"""
Base class for agent tools.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseTool(ABC):
    """Abstract base class for tools."""

    name: str
    description: str
    input_model: type[BaseModel]

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool."""
        pass

    def to_schema(self) -> dict[str, Any]:
        """Convert tool to JSON schema for the LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_model.model_json_schema(),
        }
