"""
Integration tests for agent orchestration.

These tests make REAL API calls - no mocks.
Requires valid API keys in environment variables.
"""

import os
from pathlib import Path

import pytest

from write_assist.agents import (
    DrafterAgent,
    DrafterInput,
    DraftResult,
    EditorAgent,
    EditorInput,
    EditResult,
    JudgeAgent,
    ParallelRunResult,
)


def has_api_key(env_var: str) -> bool:
    """Check if an API key is available."""
    return bool(os.environ.get(env_var))


# Skip markers
skip_no_anthropic = pytest.mark.skipif(
    not has_api_key("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
skip_no_google = pytest.mark.skipif(
    not has_api_key("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)
skip_no_openai = pytest.mark.skipif(
    not has_api_key("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
skip_no_all_keys = pytest.mark.skipif(
    not (
        has_api_key("ANTHROPIC_API_KEY")
        and has_api_key("GOOGLE_API_KEY")
        and has_api_key("OPENAI_API_KEY")
    ),
    reason="Not all API keys are set",
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    # Find the project root by looking for .claude directory
    current = Path(__file__).parent
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current.parent


@pytest.fixture
def sample_drafter_input() -> DrafterInput:
    """Sample input for drafter tests."""
    return DrafterInput(
        topic="The doctrine of consideration in contract law",
        document_type="article",
        section_outline="""
        1. Introduction to consideration
        2. Historical development
        3. Modern applications
        4. Conclusion
        """,
        target_length=500,
    )


@pytest.fixture
def sample_draft_result() -> DraftResult:
    """Sample draft result for editor tests."""
    from write_assist.agents.models import (
        AgentMetadata,
        Citation,
        Draft,
        ResearchNotes,
    )

    return DraftResult(
        draft=Draft(
            title="The Doctrine of Consideration",
            content="This is a sample draft about consideration in contract law...",
            word_count=500,
            citations_used=[
                Citation(
                    id="restatement",
                    full_citation="Restatement (Second) of Contracts § 71 (1981)",
                    source="provided",
                )
            ],
        ),
        research_notes=ResearchNotes(
            sources_consulted=["Restatement", "Farnsworth on Contracts"],
            key_authorities=["Hamer v. Sidway", "Dougherty v. Salt"],
            gaps_identified=["Need more on promissory estoppel"],
        ),
        metadata=AgentMetadata(
            model="test",
            provider="claude",
        ),
    )


# =============================================================================
# Basic Agent Tests (No API calls)
# =============================================================================


class TestAgentBasics:
    """Basic tests that don't require API calls."""

    def test_drafter_agent_init(self, project_root: Path):
        """Should initialize drafter agent."""
        agent = DrafterAgent(project_root=project_root)
        assert agent.agent_name == "Drafter"
        assert agent.spec_file == "drafter-agent.md"

    def test_editor_agent_init(self, project_root: Path):
        """Should initialize editor agent."""
        agent = EditorAgent(project_root=project_root)
        assert agent.agent_name == "Editor"
        assert agent.spec_file == "editor-agent.md"

    def test_judge_agent_init(self, project_root: Path):
        """Should initialize judge agent."""
        agent = JudgeAgent(project_root=project_root)
        assert agent.agent_name == "Judge"
        assert agent.spec_file == "judge-agent.md"

    def test_drafter_loads_spec(self, project_root: Path):
        """Should load spec from markdown file."""
        agent = DrafterAgent(project_root=project_root)
        spec = agent.load_spec()
        assert "Drafter Agent" in spec
        assert "## Purpose" in spec

    def test_drafter_builds_prompt(self, project_root: Path, sample_drafter_input: DrafterInput):
        """Should build prompt from inputs."""
        agent = DrafterAgent(project_root=project_root)
        prompt = agent.build_prompt(sample_drafter_input)
        assert sample_drafter_input.topic in prompt
        assert "article" in prompt
        assert "Academic Bluebook" in prompt

    def test_input_validation(self):
        """Should validate inputs against model."""
        # Valid input
        valid = DrafterInput(
            topic="Test topic",
            document_type="article",
            section_outline="1. Intro\n2. Body\n3. Conclusion",
        )
        assert valid.topic == "Test topic"

        # Invalid document type should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DrafterInput(
                topic="Test",
                document_type="invalid",  # type: ignore
                section_outline="Outline",
            )


# =============================================================================
# Drafter Agent Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestDrafterIntegration:
    """Integration tests for the drafter agent."""

    @skip_no_anthropic
    async def test_drafter_run_claude(self, project_root: Path, sample_drafter_input: DrafterInput):
        """Should run drafter on Claude and return valid result."""
        agent = DrafterAgent(project_root=project_root)
        result = await agent.run(
            inputs=sample_drafter_input,
            provider="claude",
            max_tokens=2000,
        )

        assert isinstance(result, DraftResult)
        assert result.draft.title
        assert result.draft.content
        assert result.draft.word_count > 0
        assert result.metadata.provider == "claude"

    @skip_no_google
    async def test_drafter_run_gemini(self, project_root: Path, sample_drafter_input: DrafterInput):
        """Should run drafter on Gemini and return valid result."""
        agent = DrafterAgent(project_root=project_root)
        result = await agent.run(
            inputs=sample_drafter_input,
            provider="gemini",
            max_tokens=2000,
        )

        assert isinstance(result, DraftResult)
        assert result.draft.title
        assert result.metadata.provider == "gemini"

    @skip_no_openai
    async def test_drafter_run_chatgpt(
        self, project_root: Path, sample_drafter_input: DrafterInput
    ):
        """Should run drafter on ChatGPT and return valid result."""
        agent = DrafterAgent(project_root=project_root)
        result = await agent.run(
            inputs=sample_drafter_input,
            provider="chatgpt",
            max_tokens=2000,
        )

        assert isinstance(result, DraftResult)
        assert result.draft.title
        assert result.metadata.provider == "chatgpt"

    @skip_no_all_keys
    async def test_drafter_run_parallel(
        self, project_root: Path, sample_drafter_input: DrafterInput
    ):
        """Should run drafter on all providers in parallel."""
        agent = DrafterAgent(project_root=project_root)
        result = await agent.run_parallel(
            inputs=sample_drafter_input,
            max_tokens=2000,
        )

        assert isinstance(result, ParallelRunResult)
        assert result.success_count >= 1  # At least one should succeed

        # Check successful results
        for provider, draft_result in result.successful.items():
            assert isinstance(draft_result, DraftResult)
            assert draft_result.metadata.provider == provider
            print(f"\n{provider}: {draft_result.draft.title}")

        # Report any failures
        for provider, error in result.failed.items():
            print(f"\n{provider} FAILED: {error.error_type}: {error.message}")


# =============================================================================
# Editor Agent Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestEditorIntegration:
    """Integration tests for the editor agent."""

    @skip_no_anthropic
    async def test_editor_run_claude(
        self,
        project_root: Path,
        sample_drafter_input: DrafterInput,
        sample_draft_result: DraftResult,
    ):
        """Should run editor on Claude with 3 drafts."""
        agent = EditorAgent(project_root=project_root)

        # Create 3 slightly different drafts
        drafts = [sample_draft_result] * 3  # Simplified for test

        editor_input = EditorInput(
            drafts=drafts,
            original_context=sample_drafter_input,
        )

        result = await agent.run(
            inputs=editor_input,
            provider="claude",
            max_tokens=3000,
        )

        assert isinstance(result, EditResult)
        assert result.integrated_draft.title
        assert result.integrated_draft.content
        assert result.metadata.provider == "claude"


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling."""

    async def test_missing_api_key_captured_in_parallel(self, project_root: Path):
        """Should capture auth errors in parallel run result."""
        # Temporarily unset keys
        original_keys = {
            "ANTHROPIC_API_KEY": os.environ.pop("ANTHROPIC_API_KEY", None),
            "GOOGLE_API_KEY": os.environ.pop("GOOGLE_API_KEY", None),
            "OPENAI_API_KEY": os.environ.pop("OPENAI_API_KEY", None),
        }

        try:
            agent = DrafterAgent(project_root=project_root)
            result = await agent.run_parallel(
                inputs=DrafterInput(
                    topic="Test",
                    document_type="article",
                    section_outline="Test outline",
                ),
            )

            # All should fail due to missing keys
            assert len(result.failed) == 3
            assert result.success_count == 0

            for _provider, error in result.failed.items():
                assert "AuthenticationError" in error.error_type or "not found" in error.message

        finally:
            # Restore keys
            for key, value in original_keys.items():
                if value:
                    os.environ[key] = value
