"""
Search tool implementation using Google Custom Search API.
"""

import os
from typing import Any

from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from write_assist.tools.base import BaseTool


class SearchInput(BaseModel):
    """Input for search tool."""

    query: str = Field(..., description="The search query to execute")
    max_results: int = Field(5, description="Maximum number of results to return")


class SearchTool(BaseTool):
    """Tool for searching the web using Google Custom Search."""

    name = "search"
    description = "Search the web for authoritative legal sources and information."
    input_model = SearchInput

    def __init__(self, api_key: str | None = None, cse_id: str | None = None):
        """Initialize the search tool."""
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self._cse_id = cse_id or os.environ.get("GOOGLE_CSE_ID")

    def run(self, query: str, max_results: int = 5) -> str | list[dict[str, Any]]:
        """
        Execute the search.

        Returns:
            Formatted string of search results or string error message.
        """
        if not self._api_key or not self._cse_id:
            return "Error: GOOGLE_API_KEY and GOOGLE_CSE_ID must be set."

        try:
            service = build("customsearch", "v1", developerKey=self._api_key)
            result = (
                service.cse()
                .list(
                    q=query,
                    cx=self._cse_id,
                    num=min(max_results, 10),  # API max is 10
                )
                .execute()
            )

            # Format results into a readable string for the LLM
            output = [f"Search results for: {query}\n"]

            items = result.get("items", [])
            if not items:
                return "No results found."

            for i, item in enumerate(items, 1):
                output.append(f"Source {i}: {item.get('title')}")
                output.append(f"URL: {item.get('link')}")
                snippet = item.get("snippet", "").replace("\n", " ")
                output.append(f"Snippet: {snippet}")
                output.append("")  # Empty line

            return "\n".join(output)

        except Exception as e:
            return f"Error executing search: {str(e)}"
