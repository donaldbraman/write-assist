"""
Agent orchestration for multi-LLM execution.

This module provides agents that run prompts against Claude, Gemini, and ChatGPT
in parallel, parsing and validating structured outputs.
"""

from write_assist.agents.base import BaseAgent
from write_assist.agents.drafter import DrafterAgent
from write_assist.agents.editor import EditorAgent
from write_assist.agents.judge import JudgeAgent
from write_assist.agents.models import (
    AgentError,
    AgentMetadata,
    Citation,
    ComparativeAnalysis,
    DetailedScore,
    DetailedScores,
    Draft,
    DrafterInput,
    DraftResult,
    EditorInput,
    EditResult,
    IntegratedDraft,
    IntegrationNotes,
    JudgeInput,
    JudgeResult,
    ParallelRunResult,
    QualityAssessment,
    RankingEntry,
    Rankings,
    Recommendations,
    ResearchNotes,
    ScoreExplanation,
)

__all__ = [
    # Agents
    "BaseAgent",
    "DrafterAgent",
    "EditorAgent",
    "JudgeAgent",
    # Input Models
    "DrafterInput",
    "EditorInput",
    "JudgeInput",
    # Output Models
    "DraftResult",
    "EditResult",
    "JudgeResult",
    # Supporting Models
    "AgentError",
    "AgentMetadata",
    "Citation",
    "ComparativeAnalysis",
    "DetailedScore",
    "DetailedScores",
    "Draft",
    "IntegratedDraft",
    "IntegrationNotes",
    "ParallelRunResult",
    "QualityAssessment",
    "RankingEntry",
    "Rankings",
    "Recommendations",
    "ResearchNotes",
    "ScoreExplanation",
]
