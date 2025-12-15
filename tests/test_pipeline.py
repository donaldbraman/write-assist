"""
Integration tests for the writing pipeline.

These tests make REAL API calls - no mocks.
Requires valid API keys in environment variables.
"""

import os
from pathlib import Path

import pytest

from write_assist.pipeline import (
    PhaseResult,
    PipelineProgress,
    PipelineResult,
    WritingPipeline,
)


def has_api_key(env_var: str) -> bool:
    """Check if an API key is available."""
    return bool(os.environ.get(env_var))


# Skip markers
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
    current = Path(__file__).parent
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current.parent


@pytest.fixture
def pipeline(project_root: Path) -> WritingPipeline:
    """Create a pipeline instance."""
    return WritingPipeline(project_root=project_root)


# =============================================================================
# Basic Pipeline Tests (No API calls)
# =============================================================================


class TestPipelineBasics:
    """Basic tests that don't require API calls."""

    def test_pipeline_init(self, project_root: Path):
        """Should initialize pipeline with agents."""
        pipeline = WritingPipeline(project_root=project_root)
        assert pipeline.drafter is not None
        assert pipeline.editor is not None
        assert pipeline.judge is not None

    def test_phase_result_properties(self):
        """Should calculate phase result properties correctly."""
        result = PhaseResult(
            phase_name="test",
            successful={"claude": "result1", "gemini": "result2"},
            failed={"chatgpt": "error"},
            execution_time_ms=1000,
        )

        assert result.success_count == 2
        assert not result.all_succeeded

    def test_phase_result_all_succeeded(self):
        """Should report all_succeeded when no failures."""
        result = PhaseResult(
            phase_name="test",
            successful={"claude": "r1", "gemini": "r2", "chatgpt": "r3"},
            failed={},
            execution_time_ms=500,
        )

        assert result.all_succeeded
        assert result.success_count == 3

    def test_progress_callback_structure(self):
        """Should have correct progress callback structure."""
        progress = PipelineProgress(
            phase="drafting",
            status="running",
            provider="claude",
            message="Processing...",
            progress_pct=0.5,
        )

        assert progress.phase == "drafting"
        assert progress.status == "running"
        assert progress.provider == "claude"


# =============================================================================
# Pipeline Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestPipelineIntegration:
    """Integration tests for full pipeline execution."""

    @skip_no_all_keys
    async def test_full_pipeline_execution(self, pipeline: WritingPipeline):
        """Should execute full pipeline and return results."""
        # Track progress
        progress_updates: list[PipelineProgress] = []

        def on_progress(p: PipelineProgress) -> None:
            progress_updates.append(p)
            print(f"[{p.phase}] {p.status}: {p.message}")

        result = await pipeline.run(
            topic="The doctrine of promissory estoppel",
            document_type="article",
            section_outline="""
            1. Introduction to promissory estoppel
            2. Elements and requirements
            3. Relationship to consideration
            4. Conclusion
            """,
            target_length=300,  # Short for testing
            max_tokens=2000,
            on_progress=on_progress,
        )

        # Check result structure
        assert isinstance(result, PipelineResult)
        assert result.original_input.topic == "The doctrine of promissory estoppel"

        # Check phases
        assert result.drafting_phase.success_count >= 1
        assert result.editing_phase.success_count >= 1
        assert result.judging_phase.success_count >= 1

        # Check we have results
        assert len(result.draft_results) >= 1
        assert len(result.edit_results) >= 1
        assert len(result.judge_results) >= 1

        # Check consensus ranking
        assert len(result.consensus_ranking) >= 1

        # Check recommended edit
        assert result.recommended_edit is not None
        assert result.recommended_edit.integrated_draft.content

        # Check progress was reported
        assert len(progress_updates) >= 6  # start + complete for each phase

        # Print summary
        print(f"\nPipeline completed in {result.total_execution_time_ms:.0f}ms")
        print(f"Consensus ranking: {result.consensus_ranking}")
        print(f"Recommended draft title: {result.recommended_edit.integrated_draft.title}")

    @skip_no_all_keys
    async def test_pipeline_with_casebook(self, pipeline: WritingPipeline):
        """Should handle casebook document type."""
        result = await pipeline.run(
            topic="Marbury v. Madison and judicial review",
            document_type="casebook_section",
            section_outline="""
            1. Case background
            2. Key holdings
            3. Discussion questions
            """,
            target_length=250,
            max_tokens=2000,
        )

        assert isinstance(result, PipelineResult)
        assert result.has_usable_result


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
class TestPipelineErrorHandling:
    """Tests for error handling in pipeline."""

    async def test_pipeline_with_no_keys(self, project_root: Path):
        """Should handle missing API keys gracefully."""
        # Temporarily unset all keys
        original_keys = {
            "ANTHROPIC_API_KEY": os.environ.pop("ANTHROPIC_API_KEY", None),
            "GOOGLE_API_KEY": os.environ.pop("GOOGLE_API_KEY", None),
            "OPENAI_API_KEY": os.environ.pop("OPENAI_API_KEY", None),
        }

        try:
            pipeline = WritingPipeline(project_root=project_root)
            result = await pipeline.run(
                topic="Test topic",
                document_type="article",
                section_outline="1. Test",
            )

            # Should return a result with all failures
            assert isinstance(result, PipelineResult)
            assert result.drafting_phase.success_count == 0
            assert len(result.drafting_phase.failed) == 3
            assert not result.has_usable_result

        finally:
            # Restore keys
            for key, value in original_keys.items():
                if value:
                    os.environ[key] = value
