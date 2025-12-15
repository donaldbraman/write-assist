"""
LLM client re-exports from auth-utils.

This module provides backwards compatibility - all imports are
re-exported from the shared auth-utils package.
"""

from auth_utils.llm import (
    APIError,
    AuthenticationError,
    LLMClient,
    LLMError,
    LLMResponse,
    Message,
    RateLimitError,
    UsageStats,
)

__all__ = [
    "LLMClient",
    "LLMResponse",
    "Message",
    "UsageStats",
    "LLMError",
    "AuthenticationError",
    "RateLimitError",
    "APIError",
]
