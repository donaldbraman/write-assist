"""
Pydantic models for agent inputs and outputs.

These models match the contracts defined in .claude/agents/*.md
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Provider = Literal["claude", "gemini", "chatgpt"]
DocumentType = Literal["article", "casebook_section"]


# =============================================================================
# Common Models
# =============================================================================


class AgentMetadata(BaseModel):
    """Metadata attached to every agent output."""

    model: str
    provider: Provider
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"


class Citation(BaseModel):
    """A citation used in a draft."""

    id: str
    full_citation: str
    source: Literal["cite-assist", "web", "provided"]


# =============================================================================
# Drafter Agent Models
# =============================================================================


class DrafterInput(BaseModel):
    """Input contract for the drafter agent."""

    topic: str
    document_type: DocumentType
    section_outline: str
    source_files: list[str] = Field(default_factory=list)
    target_length: int | None = None
    audience: str = "Legal academics and practitioners"
    style_variant: str = "standard"


class Draft(BaseModel):
    """The draft content produced by the drafter."""

    title: str
    content: str
    word_count: int
    citations_used: list[Citation] = Field(default_factory=list)


class ResearchNotes(BaseModel):
    """Research notes from the drafting process."""

    sources_consulted: list[str] = Field(default_factory=list)
    key_authorities: list[str] = Field(default_factory=list)
    gaps_identified: list[str] = Field(default_factory=list)


class DraftResult(BaseModel):
    """Output contract for the drafter agent."""

    draft: Draft
    research_notes: ResearchNotes
    metadata: AgentMetadata


# =============================================================================
# Editor Agent Models
# =============================================================================


class EditorInput(BaseModel):
    """Input contract for the editor agent."""

    drafts: list[DraftResult]  # Expects 3 drafts from different providers
    original_context: DrafterInput
    focus_areas: list[str] = Field(default_factory=list)
    style_preference: str | None = None


class IntegratedDraft(BaseModel):
    """The integrated draft produced by the editor."""

    title: str
    content: str
    word_count: int


class IntegrationNotes(BaseModel):
    """Notes on how drafts were integrated."""

    elements_from_claude: list[str] = Field(default_factory=list)
    elements_from_gemini: list[str] = Field(default_factory=list)
    elements_from_chatgpt: list[str] = Field(default_factory=list)
    original_additions: list[str] = Field(default_factory=list)
    elements_rejected: list[str] = Field(default_factory=list)


class QualityAssessment(BaseModel):
    """Editor's quality assessment of the integrated draft."""

    argument_strength: str
    citation_accuracy: str
    prose_quality: str
    structural_coherence: str
    remaining_weaknesses: list[str] = Field(default_factory=list)


class EditResult(BaseModel):
    """Output contract for the editor agent."""

    integrated_draft: IntegratedDraft
    integration_notes: IntegrationNotes
    quality_assessment: QualityAssessment
    metadata: AgentMetadata


# =============================================================================
# Judge Agent Models
# =============================================================================


class JudgeInput(BaseModel):
    """Input contract for the judge agent."""

    integrated_drafts: list[EditResult]  # Expects 3 edits from different providers
    original_context: DrafterInput
    evaluation_criteria: dict[str, float] | None = None  # Custom weights
    priority_weights: dict[str, float] | None = None
    specific_concerns: list[str] = Field(default_factory=list)


class RankingEntry(BaseModel):
    """A single ranking entry."""

    draft_source: Provider
    overall_score: float
    summary: str


class Rankings(BaseModel):
    """Rankings from the judge."""

    first_place: RankingEntry
    second_place: RankingEntry
    third_place: RankingEntry


class ScoreExplanation(BaseModel):
    """A score with explanation."""

    score: float
    explanation: str


class DetailedScore(BaseModel):
    """Detailed scores for a single draft."""

    argument_strength: ScoreExplanation
    citation_quality: ScoreExplanation
    prose_clarity: ScoreExplanation
    structural_coherence: ScoreExplanation
    academic_rigor: ScoreExplanation
    originality: ScoreExplanation


class DetailedScores(BaseModel):
    """Detailed scores for all three drafts."""

    claude_edit: DetailedScore
    gemini_edit: DetailedScore
    chatgpt_edit: DetailedScore


class ComparativeAnalysis(BaseModel):
    """Comparative analysis across drafts."""

    strongest_arguments: str
    best_citations: str
    clearest_prose: str
    most_original: str


class Recommendations(BaseModel):
    """Recommendations from the judge."""

    for_human_review: list[str] = Field(default_factory=list)
    potential_improvements: list[str] = Field(default_factory=list)
    citation_concerns: list[str] = Field(default_factory=list)


class JudgeResult(BaseModel):
    """Output contract for the judge agent."""

    rankings: Rankings
    detailed_scores: DetailedScores
    comparative_analysis: ComparativeAnalysis
    recommendations: Recommendations
    metadata: AgentMetadata


# =============================================================================
# Agent Run Results (with error handling)
# =============================================================================


class AgentError(BaseModel):
    """Represents an error from an agent run."""

    provider: Provider
    error_type: str
    message: str
    original_error: Any = None


class ParallelRunResult(BaseModel):
    """Result of running an agent across all providers in parallel."""

    successful: dict[Provider, Any]  # Provider -> result (type depends on agent)
    failed: dict[Provider, AgentError]

    @property
    def all_succeeded(self) -> bool:
        """Check if all providers succeeded."""
        return len(self.failed) == 0

    @property
    def success_count(self) -> int:
        """Number of successful runs."""
        return len(self.successful)
