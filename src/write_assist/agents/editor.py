"""
Editor agent implementation.

Integrates multiple drafts into a single superior version.
"""

from write_assist.agents.base import BaseAgent
from write_assist.agents.models import EditorInput, EditResult


class EditorAgent(BaseAgent[EditorInput, EditResult]):
    """
    Editor agent for integrating drafts.

    Capabilities:
    - Cross-draft analysis
    - Citation verification
    - Synthesis of best elements
    - Gap identification

    Note: Intentionally lacks research capabilities - works only with drafter outputs.
    """

    agent_name = "Editor"
    spec_file = "editor-agent.md"
    input_model = EditorInput
    output_model = EditResult

    def build_prompt(self, inputs: EditorInput) -> str:
        """Build the editor prompt from inputs."""
        # Format the three drafts
        draft_sections = []
        provider_order = ["claude", "gemini", "chatgpt"]

        for i, (provider, draft) in enumerate(zip(provider_order, inputs.drafts)):
            section = f"""### Draft {chr(65 + i)} ({provider.title()})

**Title:** {draft.draft.title}

**Content:**
{draft.draft.content}

**Word Count:** {draft.draft.word_count}

**Citations Used:** {len(draft.draft.citations_used)} citations
{self._format_citations(draft.draft.citations_used)}

**Research Notes:**
- Sources consulted: {len(draft.research_notes.sources_consulted)}
- Key authorities: {", ".join(draft.research_notes.key_authorities[:3])}...
- Gaps identified: {", ".join(draft.research_notes.gaps_identified[:2])}...

---"""
            draft_sections.append(section)

        drafts_str = "\n\n".join(draft_sections)

        # Format focus areas
        focus_areas_str = (
            "\n".join(f"- {area}" for area in inputs.focus_areas)
            if inputs.focus_areas
            else "Balance all quality dimensions equally"
        )

        return f"""You are a legal academic editor integrating multiple drafts into a single superior version.

## Your Task

You have received THREE drafts on the same topic from different AI models. Your job is to:
1. Analyze each draft's strengths and weaknesses
2. Synthesize the best elements into one cohesive draft
3. Ensure consistent voice and style throughout
4. Verify citation accuracy and Bluebook compliance
5. Document your editorial decisions

## Original Context

**Topic:** {inputs.original_context.topic}
**Document Type:** {inputs.original_context.document_type}
**Original Outline:** {inputs.original_context.section_outline}

## The Three Drafts

{drafts_str}

## Editorial Guidelines

1. **Argument Selection**
   - Choose the strongest, most well-reasoned arguments
   - Prefer arguments with better supporting authority
   - Maintain logical flow when combining elements

2. **Prose Quality**
   - Select clearer, more precise language
   - Maintain consistent tone and voice
   - Eliminate redundancy while preserving nuance

3. **Citation Handling**
   - Use the most accurate and complete citations
   - Verify Bluebook format compliance
   - Prefer primary sources over secondary where appropriate
   - Ensure proper signal usage

4. **Structural Coherence**
   - The final draft must read as a unified piece
   - Transitions should be smooth
   - No jarring shifts in style or approach

## Focus Areas
{focus_areas_str}

## Output Format

Return a JSON object with this exact structure:

```json
{{
  "integrated_draft": {{
    "title": "Final section/article title",
    "content": "Full integrated draft with citations",
    "word_count": 1600
  }},
  "integration_notes": {{
    "elements_from_claude": ["List of elements retained from Claude draft"],
    "elements_from_gemini": ["List of elements retained from Gemini draft"],
    "elements_from_chatgpt": ["List of elements retained from ChatGPT draft"],
    "original_additions": ["New elements added by editor"],
    "elements_rejected": ["Elements from drafts that were not used, with reasons"]
  }},
  "quality_assessment": {{
    "argument_strength": "1-10 score with explanation",
    "citation_accuracy": "1-10 score with explanation",
    "prose_quality": "1-10 score with explanation",
    "structural_coherence": "1-10 score with explanation",
    "remaining_weaknesses": ["Issues that still need attention"]
  }},
  "metadata": {{
    "model": "your model name",
    "timestamp": "ISO-8601 timestamp",
    "version": "1.0.0"
  }}
}}
```

Be transparent about which elements came from which draft and why you made your choices.

Now integrate the drafts. Respond ONLY with the JSON object."""

    def _format_citations(self, citations: list) -> str:
        """Format citations for display in prompt."""
        if not citations:
            return "  (no citations)"
        lines = []
        for c in citations[:5]:  # Limit to first 5
            lines.append(f"  - [{c.id}] {c.full_citation[:80]}...")
        if len(citations) > 5:
            lines.append(f"  ... and {len(citations) - 5} more")
        return "\n".join(lines)
