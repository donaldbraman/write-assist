"""
Writing pipeline orchestration.

Chains drafter → editor → judge phases for multi-LLM ensemble writing.
"""

import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from write_assist.agents import (
    DrafterAgent,
    DrafterInput,
    DraftResult,
    EditorAgent,
    EditorInput,
    EditResult,
    JudgeAgent,
    JudgeInput,
    JudgeResult,
)
from write_assist.agents.models import DocumentType, Provider
from write_assist.pipeline.models import (
    PhaseResult,
    PipelineProgress,
    PipelineResult,
    ProgressCallback,
)


class WritingPipeline:
    """
    Orchestrates the multi-LLM writing pipeline.

    The pipeline runs three phases:
    1. Drafting: 3 drafters create initial drafts in parallel
    2. Editing: 3 editors each see all drafts, integrate into superior versions
    3. Judging: 3 judges each see all edits, provide rankings

    Human review of judge rankings produces the final selection.

    Example:
        >>> pipeline = WritingPipeline()
        >>> result = await pipeline.run(
        ...     topic="The doctrine of consideration",
        ...     document_type="article",
        ...     section_outline="1. Introduction\\n2. History\\n3. Conclusion"
        ... )
        >>> print(result.consensus_ranking)  # ['claude', 'gemini', 'chatgpt']
        >>> print(result.recommended_edit.integrated_draft.content)
    """

    def __init__(
        self,
        project_root: Path | None = None,
        models: dict[Provider, str] | None = None,
    ):
        """
        Initialize the pipeline.

        Args:
            project_root: Root directory of the project (for agent specs)
            models: Custom models per provider (overrides defaults)
        """
        self.project_root = project_root
        self.models = models

        # Initialize agents
        self.drafter = DrafterAgent(project_root=project_root, models=models)
        self.editor = EditorAgent(project_root=project_root, models=models)
        self.judge = JudgeAgent(project_root=project_root, models=models)

    async def run(
        self,
        topic: str,
        document_type: DocumentType,
        section_outline: str,
        source_files: list[str] | None = None,
        target_length: int | None = None,
        audience: str = "Legal academics and practitioners",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        """
        Run the full writing pipeline.

        Args:
            topic: The subject matter or thesis to address
            document_type: "article" or "casebook_section"
            section_outline: Structure or outline to follow
            source_files: Optional list of file paths to reference materials
            target_length: Approximate word count target
            audience: Target readership description
            max_tokens: Maximum tokens per LLM response
            temperature: Sampling temperature for LLM calls
            on_progress: Optional callback for progress updates

        Returns:
            PipelineResult with all phase outputs and rankings
        """
        started_at = datetime.now()
        total_start = time.perf_counter()

        # Build drafter input
        drafter_input = DrafterInput(
            topic=topic,
            document_type=document_type,
            section_outline=section_outline,
            source_files=source_files or [],
            target_length=target_length,
            audience=audience,
        )

        # =====================================================================
        # Phase 1: Drafting
        # =====================================================================
        self._notify(on_progress, "drafting", "starting", message="Starting drafting phase")

        phase1_start = time.perf_counter()
        draft_parallel_result = await self.drafter.run_parallel(
            inputs=drafter_input,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        phase1_time = (time.perf_counter() - phase1_start) * 1000

        drafting_phase = PhaseResult(
            phase_name="drafting",
            successful=draft_parallel_result.successful,
            failed=draft_parallel_result.failed,
            execution_time_ms=phase1_time,
        )

        self._notify(
            on_progress,
            "drafting",
            "completed",
            message=f"Drafting complete: {drafting_phase.success_count}/3 succeeded",
        )

        # Check if we have enough drafts to continue
        if drafting_phase.success_count < 1:
            return self._create_failed_result(
                drafter_input, drafting_phase, started_at, total_start
            )

        # =====================================================================
        # Phase 2: Editing
        # =====================================================================
        self._notify(on_progress, "editing", "starting", message="Starting editing phase")

        # Build editor input with all successful drafts
        # If we have fewer than 3 drafts, duplicate the best one to fill gaps
        drafts_list = self._prepare_drafts_for_editing(draft_parallel_result.successful)

        editor_input = EditorInput(
            drafts=drafts_list,
            original_context=drafter_input,
        )

        phase2_start = time.perf_counter()
        edit_parallel_result = await self.editor.run_parallel(
            inputs=editor_input,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        phase2_time = (time.perf_counter() - phase2_start) * 1000

        editing_phase = PhaseResult(
            phase_name="editing",
            successful=edit_parallel_result.successful,
            failed=edit_parallel_result.failed,
            execution_time_ms=phase2_time,
        )

        self._notify(
            on_progress,
            "editing",
            "completed",
            message=f"Editing complete: {editing_phase.success_count}/3 succeeded",
        )

        # Check if we have enough edits to continue
        if editing_phase.success_count < 1:
            return self._create_partial_result(
                drafter_input,
                drafting_phase,
                editing_phase,
                draft_parallel_result.successful,
                started_at,
                total_start,
            )

        # =====================================================================
        # Phase 3: Judging
        # =====================================================================
        self._notify(on_progress, "judging", "starting", message="Starting judging phase")

        # Build judge input with all successful edits
        edits_list = self._prepare_edits_for_judging(edit_parallel_result.successful)

        judge_input = JudgeInput(
            integrated_drafts=edits_list,
            original_context=drafter_input,
        )

        phase3_start = time.perf_counter()
        judge_parallel_result = await self.judge.run_parallel(
            inputs=judge_input,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        phase3_time = (time.perf_counter() - phase3_start) * 1000

        judging_phase = PhaseResult(
            phase_name="judging",
            successful=judge_parallel_result.successful,
            failed=judge_parallel_result.failed,
            execution_time_ms=phase3_time,
        )

        self._notify(
            on_progress,
            "judging",
            "completed",
            message=f"Judging complete: {judging_phase.success_count}/3 succeeded",
        )

        # =====================================================================
        # Aggregate Results
        # =====================================================================
        total_time = (time.perf_counter() - total_start) * 1000

        # Calculate consensus ranking
        consensus = self._calculate_consensus(judge_parallel_result.successful)

        # Get recommended edit (top-ranked by consensus)
        recommended = self._get_recommended_edit(consensus, edit_parallel_result.successful)

        return PipelineResult(
            original_input=drafter_input,
            drafting_phase=drafting_phase,
            editing_phase=editing_phase,
            judging_phase=judging_phase,
            draft_results=draft_parallel_result.successful,
            edit_results=edit_parallel_result.successful,
            judge_results=judge_parallel_result.successful,
            consensus_ranking=consensus,
            recommended_edit=recommended,
            total_execution_time_ms=total_time,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    def _notify(
        self,
        callback: ProgressCallback | None,
        phase: str,
        status: str,
        provider: Provider | None = None,
        message: str = "",
    ) -> None:
        """Send progress notification if callback is set."""
        if callback:
            callback(
                PipelineProgress(
                    phase=phase,
                    status=status,
                    provider=provider,
                    message=message,
                )
            )

    def _prepare_drafts_for_editing(
        self, successful_drafts: dict[Provider, DraftResult]
    ) -> list[DraftResult]:
        """
        Prepare drafts list for editor input.

        Ensures we always have 3 drafts by duplicating if needed.
        """
        drafts = list(successful_drafts.values())

        # If we have fewer than 3, duplicate to fill
        while len(drafts) < 3:
            drafts.append(drafts[0])  # Duplicate first draft

        return drafts[:3]

    def _prepare_edits_for_judging(
        self, successful_edits: dict[Provider, EditResult]
    ) -> list[EditResult]:
        """
        Prepare edits list for judge input.

        Ensures we always have 3 edits by duplicating if needed.
        """
        edits = list(successful_edits.values())

        # If we have fewer than 3, duplicate to fill
        while len(edits) < 3:
            edits.append(edits[0])  # Duplicate first edit

        return edits[:3]

    def _calculate_consensus(self, judge_results: dict[Provider, JudgeResult]) -> list[Provider]:
        """
        Calculate consensus ranking from all judges.

        Uses Borda count: 1st place = 3 points, 2nd = 2, 3rd = 1
        """
        if not judge_results:
            return []

        scores: Counter[Provider] = Counter()

        for judge_result in judge_results.values():
            rankings = judge_result.rankings
            scores[rankings.first_place.draft_source] += 3
            scores[rankings.second_place.draft_source] += 2
            scores[rankings.third_place.draft_source] += 1

        # Return sorted by score (highest first)
        return [provider for provider, _ in scores.most_common()]

    def _get_recommended_edit(
        self,
        consensus: list[Provider],
        edits: dict[Provider, EditResult],
    ) -> EditResult | None:
        """Get the edit from the top-ranked provider."""
        if not consensus or not edits:
            return None

        # Return the edit from the consensus winner
        for provider in consensus:
            if provider in edits:
                return edits[provider]

        # Fall back to any available edit
        return next(iter(edits.values()), None)

    def _create_failed_result(
        self,
        drafter_input: DrafterInput,
        drafting_phase: PhaseResult,
        started_at: datetime,
        total_start: float,
    ) -> PipelineResult:
        """Create a result for when drafting phase fails completely."""
        total_time = (time.perf_counter() - total_start) * 1000

        return PipelineResult(
            original_input=drafter_input,
            drafting_phase=drafting_phase,
            editing_phase=PhaseResult(
                phase_name="editing",
                successful={},
                failed={},
                execution_time_ms=0,
            ),
            judging_phase=PhaseResult(
                phase_name="judging",
                successful={},
                failed={},
                execution_time_ms=0,
            ),
            draft_results={},
            edit_results={},
            judge_results={},
            total_execution_time_ms=total_time,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    def _create_partial_result(
        self,
        drafter_input: DrafterInput,
        drafting_phase: PhaseResult,
        editing_phase: PhaseResult,
        draft_results: dict[Provider, DraftResult],
        started_at: datetime,
        total_start: float,
    ) -> PipelineResult:
        """Create a result for when editing phase fails completely."""
        total_time = (time.perf_counter() - total_start) * 1000

        return PipelineResult(
            original_input=drafter_input,
            drafting_phase=drafting_phase,
            editing_phase=editing_phase,
            judging_phase=PhaseResult(
                phase_name="judging",
                successful={},
                failed={},
                execution_time_ms=0,
            ),
            draft_results=draft_results,
            edit_results={},
            judge_results={},
            total_execution_time_ms=total_time,
            started_at=started_at,
            completed_at=datetime.now(),
        )
