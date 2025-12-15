"""
Placeholder integration test.

All tests in write-assist are integration tests using real data.
No mocks allowed.
"""


def test_placeholder():
    """Placeholder test to verify pytest works."""
    # This test exists to:
    # 1. Verify the test infrastructure works
    # 2. Provide a template for real integration tests
    #
    # Replace with actual integration tests using real LLM calls
    # and real document data.
    assert True


def test_async_infrastructure():
    """Verify async test infrastructure is available."""
    # The actual async tests are in test_llm_integration.py
    # This test verifies pytest-asyncio is configured
    import pytest_asyncio

    assert pytest_asyncio is not None
