"""
Placeholder integration test.

All tests in write-assist are integration tests using real data.
No mocks allowed.
"""

import pytest


def test_placeholder():
    """Placeholder test to verify pytest works."""
    # This test exists to:
    # 1. Verify the test infrastructure works
    # 2. Provide a template for real integration tests
    #
    # Replace with actual integration tests using real LLM calls
    # and real document data.
    assert True


@pytest.mark.asyncio
async def test_async_placeholder():
    """Placeholder async test for LLM integration tests."""
    # Real tests will make actual API calls to Claude, Gemini, and ChatGPT
    # Example structure:
    #
    # from write_assist.llm.client import query_llm
    # response = await query_llm("Test prompt", provider="claude")
    # assert response.content is not None
    assert True
