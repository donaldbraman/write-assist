"""
Drafter agent implementation.

Creates initial drafts of legal academic writing with research and citations.
"""

from write_assist.agents.base import BaseAgent
from write_assist.agents.models import DrafterInput, DraftResult


class DrafterAgent(BaseAgent[DrafterInput, DraftResult]):
    """
    Drafter agent for creating initial drafts.

    Capabilities:
    - File reading for source materials
    - Web research (via prompt instructions)
    - cite-assist queries (via prompt instructions)
    - Academic Bluebook citation formatting
    """

    agent_name = "Drafter"
    spec_file = "drafter-agent.md"
    input_model = DrafterInput
    output_model = DraftResult

    def build_prompt(self, inputs: DrafterInput) -> str:
        """Build the drafter prompt from inputs."""
        # Format source files
        if inputs.source_files:
            source_files_str = "\n".join(f"- {f}" for f in inputs.source_files)
        else:
            source_files_str = "None provided - conduct research"

        # Format target length
        target_length_str = (
            f"{inputs.target_length} words" if inputs.target_length else "Appropriate for section"
        )

        return f"""You are a legal academic writing assistant creating a draft for a {inputs.document_type}.

## Context

**Topic:** {inputs.topic}

**Document Type:** {inputs.document_type}

**Outline:**
{inputs.section_outline}

**Source Materials:**
{source_files_str}

**Target Length:** {target_length_str}

**Audience:** {inputs.audience}

## Instructions

1. **Research Phase**
   - Review any provided source materials
   - Query cite-assist for relevant scholarship on the topic
   - Conduct web research for additional authoritative sources
   - Identify the key authorities and seminal works

2. **Drafting Phase**
   - Follow the provided outline structure
   - Write in formal academic legal prose
   - Integrate sources smoothly with signal phrases
   - Build arguments with proper legal reasoning
   - Use footnotes for citations (law review style)

3. **Citation Phase**
   - Format ALL citations in Academic Bluebook style (law review format)
   - Use proper signals (see, see also, cf., etc.)
   - Include pinpoint citations where referencing specific content
   - Ensure citation sentences vs. citation clauses are correct

## Academic Bluebook Quick Reference

- **Articles:** Author, *Title*, Vol. J. Abbr. First Page, Pincite (Year).
- **Books:** Author, Title Page (ed., Year).
- **Cases:** Case Name, Vol. Reporter First Page, Pincite (Court Year).
- **Subsequent references:** Use *Id.* or *supra* note X appropriately.

## Output Format

Return a JSON object with this exact structure:

```json
{{
  "draft": {{
    "title": "Section/article title",
    "content": "Full markdown draft with citations in footnotes",
    "word_count": 1500,
    "citations_used": [
      {{
        "id": "smith2020",
        "full_citation": "John Smith, Article Title, 100 Harv. L. Rev. 1, 15 (2020)",
        "source": "cite-assist | web | provided"
      }}
    ]
  }},
  "research_notes": {{
    "sources_consulted": ["list of sources reviewed"],
    "key_authorities": ["most important sources for this topic"],
    "gaps_identified": ["areas needing more research"]
  }},
  "metadata": {{
    "model": "your model name",
    "timestamp": "ISO-8601 timestamp",
    "version": "1.0.0"
  }}
}}
```

## Quality Standards

- Arguments should be well-reasoned and supported
- Citations should be accurate and verifiable
- Prose should be clear, precise, and professional
- Structure should follow academic legal writing conventions

Now create the draft. Respond ONLY with the JSON object."""
