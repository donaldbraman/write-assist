"""
LLM response caching using diskcache.

Caches LLM responses to avoid repeated API calls during development/testing.
Enabled by default; set WRITE_ASSIST_NO_CACHE=1 to disable.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from diskcache import Cache


def is_cache_enabled() -> bool:
    """Check if caching is enabled (default: True)."""
    return os.environ.get("WRITE_ASSIST_NO_CACHE", "").lower() not in ("1", "true", "yes")


def _find_cache_dir() -> Path:
    """Find the cache directory (project root/.cache/llm)."""
    # Look for project root by finding .claude directory
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent / ".cache" / "llm"
    # Fall back to current directory
    return current / ".cache" / "llm"


class LLMCache:
    """
    File-based cache for LLM responses.

    Uses diskcache for persistent, automatic cache management.
    """

    def __init__(self, cache_dir: Path | None = None):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory for cache storage. Defaults to .cache/llm/
        """
        self._cache_dir = cache_dir or _find_cache_dir()
        self._cache: Cache | None = None

    @property
    def cache(self) -> Cache:
        """Lazy-initialize the cache."""
        if self._cache is None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache = Cache(str(self._cache_dir))
        return self._cache

    def make_key(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Create a cache key from LLM call parameters.

        Args:
            provider: LLM provider name
            model: Model identifier
            prompt: User prompt content
            system_message: System message content
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            SHA-256 hash of the parameters
        """
        key_data = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "system_message": system_message,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> str | None:
        """
        Get a cached response.

        Args:
            key: Cache key from make_key()

        Returns:
            Cached response content, or None if not found
        """
        if not is_cache_enabled():
            return None
        return self.cache.get(key)

    def set(self, key: str, response: str) -> None:
        """
        Store a response in cache.

        Args:
            key: Cache key from make_key()
            response: LLM response content to cache
        """
        if not is_cache_enabled():
            return
        self.cache.set(key, response)

    def clear(self) -> int:
        """
        Clear all cached responses.

        Returns:
            Number of items cleared
        """
        count = len(self.cache)
        self.cache.clear()
        return count

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (count, size, directory)
        """
        return {
            "enabled": is_cache_enabled(),
            "count": len(self.cache),
            "size_bytes": self.cache.volume(),
            "directory": str(self._cache_dir),
        }

    def close(self) -> None:
        """Close the cache connection."""
        if self._cache is not None:
            self._cache.close()
            self._cache = None


# Global cache instance
_llm_cache: LLMCache | None = None


def get_llm_cache() -> LLMCache:
    """Get the global LLM cache instance."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
