"""
Tests for research capabilities in DrafterAgent.
"""

from unittest.mock import AsyncMock, patch

import pytest

from write_assist.agents import DrafterAgent, DrafterInput
from write_assist.llm import LLMResponse


@pytest.fixture
def mock_search_tool():
    """Mock the search tool to avoid real API calls."""
    # We patch the class where it is DEFINED, not where it is imported locally
    with patch("write_assist.tools.search.SearchTool") as MockTool:
        tool_instance = MockTool.return_value
        tool_instance.run.return_value = "Mock search result content about AI copyright."
        yield tool_instance


@pytest.fixture
def mock_llm_client():
    """Mock the LLM client to simulate ReAct conversation."""
    with patch("write_assist.llm.LLMClient") as MockClient:
        instance = MockClient.return_value

        # Responses to return in sequence
        responses = [
            LLMResponse(
                content="I need to check recent cases. Tool: search(query='AI copyright cases 2024')",
                model="test-model",
                provider="claude",
            ),
            LLMResponse(
                content="I have enough information now. FINAL ANSWER",
                model="test-model",
                provider="claude",
            ),
        ]

        # AsyncMock's side_effect can be an iterable of return values,
        # and it will return them one by one when awaited.
        instance.chat = AsyncMock(side_effect=responses)

        yield instance


@pytest.mark.asyncio
async def test_research_loop_execution(mock_search_tool, mock_llm_client):  # noqa: ARG001
    """Test that the research loop executes and calls the tool."""
    agent = DrafterAgent(project_root=None)

    inputs = DrafterInput(
        topic="AI Copyright",
        document_type="article",
        section_outline="1. Intro",
        max_research_steps=2,
    )

    # We only test the _research_loop method here to isolate it from the full run
    await agent._research_loop(inputs, provider="claude")

    # Verify tool was called
    mock_search_tool.run.assert_called_once_with(query="AI copyright cases 2024")

    # Verify input context was updated
    assert len(inputs.research_context) == 1
    assert "Mock search result" in inputs.research_context[0]


@pytest.mark.asyncio
async def test_research_integration_in_prompt(mock_search_tool):  # noqa: ARG001
    """Test that research context is actually included in the final prompt."""
    agent = DrafterAgent(project_root=None)

    inputs = DrafterInput(
        topic="AI Copyright",
        document_type="article",
        section_outline="1. Intro",
        research_context=[
            "### Research on 'query'\nResult 1",
            "### Research on 'query2'\nResult 2",
        ],
    )

    prompt = agent.build_prompt(inputs)

    assert "## Research Findings" in prompt
    assert "Result 1" in prompt
    assert "Result 2" in prompt
    assert "Integrate these latest developments" in prompt
