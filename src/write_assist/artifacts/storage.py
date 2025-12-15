"""
Artifact storage for pipeline runs.

Provides organized, human-readable storage of all pipeline outputs
with obfuscated provider names to prevent bias.
"""

import json
import re
import shutil
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
from write_assist.artifacts.obfuscation import (
    Alias,
    ProviderMapping,
    obfuscate_provider_in_text,
)


def slugify(text: str, max_length: int = 40) -> str:
    """Convert text to URL-safe slug."""
    # Lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:max_length].rstrip("-")


def format_datetime(dt: datetime) -> str:
    """Format datetime as YY-MM-DD-HH-MM."""
    return dt.strftime("%y-%m-%d-%H-%M")


class ArtifactStore:
    """
    Manages artifact storage for a single pipeline run.

    Creates a structured directory with all inputs, outputs, and metadata.
    Provider names are obfuscated to prevent bias during review.
    """

    def __init__(
        self,
        output_dir: Path | str,
        topic: str,
        started_at: datetime | None = None,
        mapping: ProviderMapping | None = None,
    ):
        """
        Initialize artifact store for a new run.

        Args:
            output_dir: Base directory for all runs
            topic: Topic being written about (used in directory name)
            started_at: Run start time (default: now)
            mapping: Provider mapping (default: random)
        """
        self.started_at = started_at or datetime.now()
        self.mapping = mapping or ProviderMapping.create_random()

        # Create run directory name
        time_str = format_datetime(self.started_at)
        topic_slug = slugify(topic)
        self.run_id = f"{time_str}_{topic_slug}"

        # Set up paths
        self.base_dir = Path(output_dir)
        self.run_dir = self.base_dir / self.run_id

        # Initialize manifest data
        self._manifest: dict[str, Any] = {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": None,
            "provider_mapping": self.mapping.to_dict(),
            "topic": topic,
        }

    def initialize(self) -> "ArtifactStore":
        """Create directory structure."""
        # Create all directories
        (self.run_dir / "input" / "sources").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "drafts").mkdir(exist_ok=True)
        (self.run_dir / "edits").mkdir(exist_ok=True)
        (self.run_dir / "judgments").mkdir(exist_ok=True)
        (self.run_dir / "final").mkdir(exist_ok=True)

        return self

    # =========================================================================
    # Input Saving
    # =========================================================================

    def save_input(self, drafter_input: DrafterInput) -> None:
        """Save the original input parameters."""
        input_dir = self.run_dir / "input"

        # Save topic
        (input_dir / "topic.md").write_text(drafter_input.topic)

        # Save outline
        (input_dir / "outline.md").write_text(drafter_input.section_outline)

        # Save source documents
        for doc in drafter_input.source_documents:
            safe_name = slugify(doc.title) + ".md"
            source_path = input_dir / "sources" / safe_name
            source_path.write_text(f"# {doc.title}\n\n{doc.content}")

        # Update manifest
        self._manifest.update(
            {
                "document_type": drafter_input.document_type,
                "target_length": drafter_input.target_length,
                "audience": drafter_input.audience,
                "source_count": len(drafter_input.source_documents),
                "citation_count": len(drafter_input.local_citations),
            }
        )

    # =========================================================================
    # Draft Saving
    # =========================================================================

    def save_drafts(self, drafts: dict[Provider, DraftResult]) -> None:
        """Save all drafts with obfuscated names."""
        drafts_dir = self.run_dir / "drafts"
        research_notes: dict[str, Any] = {}

        for provider, draft_result in drafts.items():
            alias = self.mapping.get_alias(provider)

            # Save draft content (obfuscated)
            content = self._format_draft_markdown(draft_result, alias)
            (drafts_dir / f"{alias}-draft.md").write_text(content)

            # Collect research notes
            research_notes[alias] = {
                "sources_consulted": draft_result.research_notes.sources_consulted,
                "key_authorities": draft_result.research_notes.key_authorities,
                "gaps_identified": draft_result.research_notes.gaps_identified,
                "citations_used": [
                    {"id": c.id, "citation": c.full_citation, "source": c.source}
                    for c in draft_result.draft.citations_used
                ],
                "word_count": draft_result.draft.word_count,
            }

        # Save combined research notes
        (drafts_dir / "research-notes.json").write_text(json.dumps(research_notes, indent=2))

    def _format_draft_markdown(self, draft_result: DraftResult, alias: Alias) -> str:
        """Format draft as markdown with metadata header."""
        draft = draft_result.draft
        return f"""# {draft.title}

> **Source:** {alias.title()}
> **Word Count:** {draft.word_count}

---

{draft.content}
"""

    # =========================================================================
    # Edit Saving
    # =========================================================================

    def save_edits(self, edits: dict[Provider, EditResult]) -> None:
        """Save all edits with obfuscated names."""
        edits_dir = self.run_dir / "edits"
        integration_notes: dict[str, Any] = {}

        for provider, edit_result in edits.items():
            alias = self.mapping.get_alias(provider)

            # Save edit content (obfuscated)
            content = self._format_edit_markdown(edit_result, alias)
            (edits_dir / f"{alias}-edit.md").write_text(content)

            # Collect integration notes (obfuscated)
            integration_notes[alias] = self._obfuscate_integration_notes(edit_result, alias)

        # Save combined integration notes
        (edits_dir / "integration-notes.json").write_text(json.dumps(integration_notes, indent=2))

    def _format_edit_markdown(self, edit_result: EditResult, alias: Alias) -> str:
        """Format edit as markdown with metadata header."""
        edit = edit_result.integrated_draft
        qa = edit_result.quality_assessment

        return f"""# {edit.title}

> **Editor:** {alias.title()}
> **Word Count:** {edit.word_count}

## Quality Assessment

- **Argument Strength:** {qa.argument_strength}
- **Citation Accuracy:** {qa.citation_accuracy}
- **Prose Quality:** {qa.prose_quality}
- **Structural Coherence:** {qa.structural_coherence}

### Remaining Weaknesses
{self._format_list(qa.remaining_weaknesses)}

---

{edit.content}
"""

    def _obfuscate_integration_notes(
        self, edit_result: EditResult, editor_alias: Alias
    ) -> dict[str, Any]:
        """Convert integration notes to use aliases."""
        notes = edit_result.integration_notes
        return {
            "editor": editor_alias,
            "elements_from": {
                self.mapping.get_alias("claude"): notes.elements_from_claude,  # type: ignore
                self.mapping.get_alias("gemini"): notes.elements_from_gemini,  # type: ignore
                self.mapping.get_alias("chatgpt"): notes.elements_from_chatgpt,  # type: ignore
            },
            "original_additions": notes.original_additions,
            "elements_rejected": notes.elements_rejected,
        }

    # =========================================================================
    # Judgment Saving
    # =========================================================================

    def save_judgments(
        self,
        judgments: dict[Provider, JudgeResult],
        consensus_ranking: list[Provider],
    ) -> None:
        """Save all judgments with obfuscated names."""
        judgments_dir = self.run_dir / "judgments"

        for provider, judge_result in judgments.items():
            alias = self.mapping.get_alias(provider)

            # Save judgment (obfuscated)
            judgment_data = self._obfuscate_judgment(judge_result, alias)
            (judgments_dir / f"{alias}-judgment.json").write_text(
                json.dumps(judgment_data, indent=2)
            )

        # Save consensus summary
        consensus_aliases = [self.mapping.get_alias(p) for p in consensus_ranking]
        consensus_md = self._format_consensus_markdown(judgments, consensus_aliases)
        (judgments_dir / "consensus.md").write_text(consensus_md)

        # Update manifest
        self._manifest["consensus_ranking"] = consensus_aliases

    def _obfuscate_judgment(self, judge_result: JudgeResult, judge_alias: Alias) -> dict[str, Any]:
        """Convert judgment to use aliases."""
        rankings = judge_result.rankings

        # Map draft sources to aliases
        def rank_to_dict(entry: Any) -> dict[str, Any]:
            return {
                "draft": self.mapping.get_alias(entry.draft_source),
                "score": entry.overall_score,
                "summary": obfuscate_provider_in_text(entry.summary, self.mapping),
            }

        # Map detailed scores
        detailed = {}
        for alias in ["aleph", "bet", "gimel"]:
            provider = self.mapping.get_provider(alias)  # type: ignore
            provider_scores = getattr(judge_result.detailed_scores, f"{provider}_edit", None)
            if provider_scores:
                detailed[alias] = {
                    "argument_strength": {
                        "score": provider_scores.argument_strength.score,
                        "explanation": provider_scores.argument_strength.explanation,
                    },
                    "citation_quality": {
                        "score": provider_scores.citation_quality.score,
                        "explanation": provider_scores.citation_quality.explanation,
                    },
                    "prose_clarity": {
                        "score": provider_scores.prose_clarity.score,
                        "explanation": provider_scores.prose_clarity.explanation,
                    },
                    "structural_coherence": {
                        "score": provider_scores.structural_coherence.score,
                        "explanation": provider_scores.structural_coherence.explanation,
                    },
                    "academic_rigor": {
                        "score": provider_scores.academic_rigor.score,
                        "explanation": provider_scores.academic_rigor.explanation,
                    },
                    "originality": {
                        "score": provider_scores.originality.score,
                        "explanation": provider_scores.originality.explanation,
                    },
                }

        return {
            "judge": judge_alias,
            "rankings": {
                "first": rank_to_dict(rankings.first_place),
                "second": rank_to_dict(rankings.second_place),
                "third": rank_to_dict(rankings.third_place),
            },
            "detailed_scores": detailed,
            "comparative_analysis": {
                "strongest_arguments": obfuscate_provider_in_text(
                    judge_result.comparative_analysis.strongest_arguments, self.mapping
                ),
                "best_citations": obfuscate_provider_in_text(
                    judge_result.comparative_analysis.best_citations, self.mapping
                ),
                "clearest_prose": obfuscate_provider_in_text(
                    judge_result.comparative_analysis.clearest_prose, self.mapping
                ),
                "most_original": obfuscate_provider_in_text(
                    judge_result.comparative_analysis.most_original, self.mapping
                ),
            },
            "recommendations": {
                "for_human_review": judge_result.recommendations.for_human_review,
                "potential_improvements": judge_result.recommendations.potential_improvements,
                "citation_concerns": judge_result.recommendations.citation_concerns,
            },
        }

    def _format_consensus_markdown(
        self,
        judgments: dict[Provider, JudgeResult],
        consensus_aliases: list[Alias],
    ) -> str:
        """Format consensus summary as markdown."""
        lines = ["# Consensus Rankings", ""]

        # Overall ranking
        lines.append("## Final Ranking")
        lines.append("")
        for i, alias in enumerate(consensus_aliases, 1):
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
            lines.append(f"{medal} **{alias.title()}**")
        lines.append("")

        # Per-judge rankings
        lines.append("## Individual Judge Rankings")
        lines.append("")
        lines.append("| Judge | 1st | 2nd | 3rd |")
        lines.append("|-------|-----|-----|-----|")

        for provider, result in judgments.items():
            judge_alias = self.mapping.get_alias(provider)
            r = result.rankings
            first = self.mapping.get_alias(r.first_place.draft_source)
            second = self.mapping.get_alias(r.second_place.draft_source)
            third = self.mapping.get_alias(r.third_place.draft_source)
            lines.append(
                f"| {judge_alias.title()} | {first.title()} ({r.first_place.overall_score:.1f}) "
                f"| {second.title()} ({r.second_place.overall_score:.1f}) "
                f"| {third.title()} ({r.third_place.overall_score:.1f}) |"
            )

        return "\n".join(lines)

    # =========================================================================
    # Final Output
    # =========================================================================

    def save_final(
        self,
        recommended_edit: EditResult | None,
        consensus_ranking: list[Provider],
    ) -> None:
        """Save final recommended output and reveal document."""
        final_dir = self.run_dir / "final"

        if recommended_edit:
            # Save recommended draft (still obfuscated for initial review)
            winner_provider = consensus_ranking[0] if consensus_ranking else None
            winner_alias = self.mapping.get_alias(winner_provider) if winner_provider else "unknown"

            content = f"""# {recommended_edit.integrated_draft.title}

> **Winner:** {winner_alias.title()}
> **Word Count:** {recommended_edit.integrated_draft.word_count}

---

{recommended_edit.integrated_draft.content}
"""
            (final_dir / "recommended.md").write_text(content)

        # Save provider reveal
        reveal = self._format_reveal_markdown(consensus_ranking)
        (final_dir / "provider-reveal.md").write_text(reveal)

    def _format_reveal_markdown(self, consensus_ranking: list[Provider]) -> str:
        """Format the unblinded reveal document."""
        lines = [
            "# Provider Reveal",
            "",
            "This document reveals the true identities behind the aliases.",
            "",
            "## Alias Mapping",
            "",
            "| Alias | Provider |",
            "|-------|----------|",
        ]

        for alias in ["aleph", "bet", "gimel"]:
            provider = self.mapping.get_provider(alias)  # type: ignore
            lines.append(f"| {alias.title()} | {provider.title()} |")

        lines.extend(
            [
                "",
                "## Final Rankings (Unblinded)",
                "",
            ]
        )

        for i, provider in enumerate(consensus_ranking, 1):
            alias = self.mapping.get_alias(provider)
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
            lines.append(f"{medal} **{provider.title()}** (was {alias.title()})")

        return "\n".join(lines)

    # =========================================================================
    # Manifest
    # =========================================================================

    def finalize(
        self,
        completed_at: datetime | None = None,
        execution_time_ms: float = 0,
        phase_results: dict[str, Any] | None = None,
    ) -> Path:
        """Write final manifest and return run directory path."""
        self._manifest["completed_at"] = (completed_at or datetime.now()).isoformat()
        self._manifest["execution_time_ms"] = execution_time_ms

        if phase_results:
            self._manifest["phase_results"] = phase_results

        # Write manifest
        manifest_path = self.run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(self._manifest, indent=2, default=str))

        return self.run_dir

    # =========================================================================
    # Utilities
    # =========================================================================

    def _format_list(self, items: list[str]) -> str:
        """Format a list as markdown bullets."""
        if not items:
            return "_None identified_"
        return "\n".join(f"- {item}" for item in items)

    def delete(self) -> None:
        """Delete the run directory (for cleanup on failure)."""
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    @property
    def path(self) -> Path:
        """Get the run directory path."""
        return self.run_dir
