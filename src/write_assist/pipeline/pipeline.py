"""
Writing pipeline orchestration.

Chains drafter → editor → judge phases for multi-LLM ensemble writing.
"""

import logging
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
from write_assist.agents.models import DocumentType, LoadedSource, LocalCitation, Provider
from write_assist.artifacts import ArtifactStore
from write_assist.citations import CiteAssistClient, CiteAssistUnavailable
from write_assist.pipeline.models import (
    PhaseResult,
    PipelineProgress,
    PipelineResult,
    ProgressCallback,
)
from write_assist.sources import SourceLoader

logger = logging.getLogger(__name__)


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
        cite_assist_url: str | None = None,
        cite_assist_library_id: int | None = None,
        use_cite_assist: bool = True,
        output_dir: Path | str | None = None,
        save_artifacts: bool = True,
    ):
        """
        Initialize the pipeline.

        Args:
            project_root: Root directory of the project (for agent specs)
            models: Custom models per provider (overrides defaults)
            cite_assist_url: URL for cite-assist API (default: from env or localhost:8000)
            cite_assist_library_id: Zotero library ID for cite-assist queries
            use_cite_assist: Whether to query cite-assist for local citations
            output_dir: Directory to save artifacts (default: ./runs)
            save_artifacts: Whether to save artifacts to disk (default: True)
        """
        self.project_root = project_root
        self.models = models
        self.use_cite_assist = use_cite_assist
        self.cite_assist_url = cite_assist_url
        self.cite_assist_library_id = cite_assist_library_id
        self.output_dir = Path(output_dir) if output_dir else Path("./runs")
        self.save_artifacts = save_artifacts

        # Initialize agents
        self.drafter = DrafterAgent(project_root=project_root, models=models)
        self.editor = EditorAgent(project_root=project_root, models=models)
        self.judge = JudgeAgent(project_root=project_root, models=models)

        # Initialize source loader (uses auth-utils centralized credentials)
        self.source_loader = SourceLoader(
            on_error="warn",  # Log warnings but don't fail pipeline
        )

    async def run(
        self,
        topic: str,
        document_type: DocumentType,
        section_outline: str,
        source_files: list[str] | None = None,
        target_length: int | None = None,
        audience: str = "Legal academics and practitioners",
        max_tokens: int = 8192,
        max_tokens_editing: int | None = None,
        max_tokens_judging: int | None = None,
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
            max_tokens: Maximum tokens for drafting phase
            max_tokens_editing: Maximum tokens for editing phase (default: 2x max_tokens)
            max_tokens_judging: Maximum tokens for judging phase (default: 2x max_tokens)
            temperature: Sampling temperature for LLM calls
            on_progress: Optional callback for progress updates

        Returns:
            PipelineResult with all phase outputs and rankings
        """
        # Editing and judging produce more output (integrated content + metadata)
        # Default to 3x drafting tokens to prevent Gemini truncation
        # Gemini models can truncate around 15-16K chars even with higher limits
        if max_tokens_editing is None:
            max_tokens_editing = max_tokens * 3
        if max_tokens_judging is None:
            max_tokens_judging = max_tokens * 3
        started_at = datetime.now()
        total_start = time.perf_counter()

        # =====================================================================
        # Initialize artifact storage
        # =====================================================================
        artifact_store: ArtifactStore | None = None
        if self.save_artifacts:
            artifact_store = ArtifactStore(
                output_dir=self.output_dir,
                topic=topic,
                started_at=started_at,
            ).initialize()
            self._notify(
                on_progress,
                "artifacts",
                "starting",
                message=f"Saving artifacts to {artifact_store.run_dir}",
            )

        # =====================================================================
        # Pre-Phase 1: Load source documents
        # =====================================================================
        source_documents: list[LoadedSource] = []
        if source_files:
            self._notify(on_progress, "sources", "starting", message="Loading source documents")
            source_documents = self._load_sources(source_files)
            self._notify(
                on_progress,
                "sources",
                "completed",
                message=f"Loaded {len(source_documents)}/{len(source_files)} sources",
            )

        # =====================================================================
        # Pre-Phase 2: Query cite-assist for local citations
        # =====================================================================
        local_citations: list[LocalCitation] = []
        if self.use_cite_assist:
            self._notify(
                on_progress, "research", "starting", message="Querying local citation database"
            )
            local_citations = await self._query_cite_assist(topic)
            self._notify(
                on_progress,
                "research",
                "completed",
                message=f"Found {len(local_citations)} relevant citations",
            )

        # Build drafter input
        drafter_input = DrafterInput(
            topic=topic,
            document_type=document_type,
            section_outline=section_outline,
            source_files=source_files or [],
            source_documents=source_documents,
            target_length=target_length,
            audience=audience,
            local_citations=local_citations,
        )

        # Save input artifacts
        if artifact_store:
            artifact_store.save_input(drafter_input)

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

        # Save draft artifacts
        if artifact_store and draft_parallel_result.successful:
            artifact_store.save_drafts(draft_parallel_result.successful)

        # Save any errors with raw responses for debugging
        if artifact_store and draft_parallel_result.failed:
            raw_responses = {
                p: self.drafter.get_failed_raw_response(p)
                for p in draft_parallel_result.failed
                if self.drafter.get_failed_raw_response(p)
            }
            artifact_store.save_errors("drafting", draft_parallel_result.failed, raw_responses)

        # Check if we have enough drafts to continue
        if drafting_phase.success_count < 1:
            if artifact_store:
                artifact_store.finalize(
                    execution_time_ms=(time.perf_counter() - total_start) * 1000,
                    phase_results={"drafting": "failed"},
                )
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
            max_tokens=max_tokens_editing,
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

        # Save edit artifacts
        if artifact_store and edit_parallel_result.successful:
            artifact_store.save_edits(edit_parallel_result.successful)

        # Save any errors with raw responses for debugging
        if artifact_store and edit_parallel_result.failed:
            raw_responses = {
                p: self.editor.get_failed_raw_response(p)
                for p in edit_parallel_result.failed
                if self.editor.get_failed_raw_response(p)
            }
            artifact_store.save_errors("editing", edit_parallel_result.failed, raw_responses)

        # Check if we have enough edits to continue
        if editing_phase.success_count < 1:
            if artifact_store:
                artifact_store.finalize(
                    execution_time_ms=(time.perf_counter() - total_start) * 1000,
                    phase_results={"drafting": "completed", "editing": "failed"},
                )
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
            max_tokens=max_tokens_judging,
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

        # Save any errors with raw responses for debugging
        if artifact_store and judge_parallel_result.failed:
            raw_responses = {
                p: self.judge.get_failed_raw_response(p)
                for p in judge_parallel_result.failed
                if self.judge.get_failed_raw_response(p)
            }
            artifact_store.save_errors("judging", judge_parallel_result.failed, raw_responses)

        # =====================================================================
        # Aggregate Results
        # =====================================================================
        total_time = (time.perf_counter() - total_start) * 1000

        # Calculate consensus ranking
        consensus = self._calculate_consensus(judge_parallel_result.successful)

        # Get recommended edit (top-ranked by consensus)
        recommended = self._get_recommended_edit(consensus, edit_parallel_result.successful)

        # Save judgment and final artifacts
        final_artifact_path = None
        if artifact_store:
            if judge_parallel_result.successful:
                artifact_store.save_judgments(judge_parallel_result.successful, consensus)
            artifact_store.save_final(recommended, consensus)
            final_artifact_path = artifact_store.finalize(
                execution_time_ms=total_time,
                phase_results={
                    "drafting": "completed",
                    "editing": "completed",
                    "judging": "completed",
                },
            )
            self._notify(
                on_progress,
                "artifacts",
                "completed",
                message=f"Artifacts saved to {final_artifact_path}",
            )

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
            artifact_path=final_artifact_path,
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

    async def _query_cite_assist(
        self,
        topic: str,
        max_results: int = 10,
        min_score: float = 0.3,
    ) -> list[LocalCitation]:
        """
        Query cite-assist for relevant local citations.

        Args:
            topic: The topic to search for
            max_results: Maximum number of citations to return
            min_score: Minimum relevance score threshold

        Returns:
            List of LocalCitation objects
        """
        try:
            async with CiteAssistClient(
                base_url=self.cite_assist_url,
                library_id=self.cite_assist_library_id,
            ) as client:
                response = await client.search(
                    query=topic,
                    max_results=max_results,
                    min_score=min_score,
                    output_mode="chunks",
                )

                # Convert to LocalCitation format
                citations = []
                for result in response.results:
                    citations.append(
                        LocalCitation(
                            id=result.id,
                            title=result.title,
                            authors=result.authors,
                            year=result.year,
                            journal=result.journal,
                            volume=result.volume,
                            pages=result.pages,
                            relevance_score=result.score,
                            relevant_text=result.relevant_text,
                        )
                    )

                return citations

        except CiteAssistUnavailable as e:
            logger.warning(f"cite-assist unavailable: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error querying cite-assist: {e}")
            return []

    def _load_sources(self, source_files: list[str]) -> list[LoadedSource]:
        """
        Load source documents from paths and URLs.

        Args:
            source_files: List of file paths or URLs

        Returns:
            List of LoadedSource objects with content
        """
        loaded = []
        docs = self.source_loader.load_many(source_files)

        for doc in docs:
            loaded.append(
                LoadedSource(
                    path=doc.path,
                    title=doc.title,
                    content=doc.content,
                    source_type=doc.source_type.value,
                )
            )

        return loaded
