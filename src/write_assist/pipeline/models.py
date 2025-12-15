"""
Data models for pipeline execution.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from write_assist.agents.models import (
    DrafterInput,
    DraftResult,
    EditResult,
    JudgeResult,
    Provider,
)


@dataclass
class PhaseResult:
    """Result of a single pipeline phase."""

    phase_name: str
    successful: dict[Provider, Any]
    failed: dict[Provider, Any]
    execution_time_ms: float
    tokens_used: int = 0

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed) == 0


@dataclass
class PipelineResult:
    """Complete result of a pipeline execution."""

    # Original input
    original_input: DrafterInput

    # Phase results
    drafting_phase: PhaseResult
    editing_phase: PhaseResult
    judging_phase: PhaseResult

    # Aggregated results
    draft_results: dict[Provider, DraftResult]
    edit_results: dict[Provider, EditResult]
    judge_results: dict[Provider, JudgeResult]

    # Summary
    consensus_ranking: list[Provider] = field(default_factory=list)
    recommended_edit: EditResult | None = None

    # Metadata
    total_tokens_used: int = 0
    total_execution_time_ms: float = 0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    artifact_path: Path | None = None

    @property
    def all_phases_succeeded(self) -> bool:
        """Check if all phases completed successfully."""
        return (
            self.drafting_phase.all_succeeded
            and self.editing_phase.all_succeeded
            and self.judging_phase.all_succeeded
        )

    @property
    def has_usable_result(self) -> bool:
        """Check if there's at least one usable result."""
        return (
            self.drafting_phase.success_count >= 1
            and self.editing_phase.success_count >= 1
            and self.judging_phase.success_count >= 1
        )

    def get_rankings_summary(self) -> dict[Provider, dict[str, Any]]:
        """Get a summary of rankings from all judges."""
        summary: dict[Provider, dict[str, Any]] = {}

        for provider, judge_result in self.judge_results.items():
            summary[provider] = {
                "first": judge_result.rankings.first_place.draft_source,
                "second": judge_result.rankings.second_place.draft_source,
                "third": judge_result.rankings.third_place.draft_source,
                "first_score": judge_result.rankings.first_place.overall_score,
            }

        return summary


@dataclass
class PipelineProgress:
    """Progress update during pipeline execution."""

    phase: str  # "drafting", "editing", "judging"
    status: str  # "starting", "running", "completed", "failed"
    provider: Provider | None = None
    message: str = ""
    progress_pct: float = 0.0


# Type alias for progress callback
ProgressCallback = Callable[[PipelineProgress], None]
