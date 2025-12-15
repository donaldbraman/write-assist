"""
Judge agent implementation.

Evaluates and ranks integrated drafts with detailed explanations.
"""

from write_assist.agents.base import BaseAgent
from write_assist.agents.models import JudgeInput, JudgeResult


class JudgeAgent(BaseAgent[JudgeInput, JudgeResult]):
    """
    Judge agent for evaluating and ranking drafts.

    Capabilities:
    - Comparative evaluation across 6 dimensions
    - Rubric-based scoring
    - Reasoned explanations
    - Weakness identification

    Note: Rankings are recommendations - human review required.
    """

    agent_name = "Judge"
    spec_file = "judge-agent.md"
    input_model = JudgeInput
    output_model = JudgeResult

    def build_prompt(self, inputs: JudgeInput) -> str:
        """Build the judge prompt from inputs."""
        # Format the three integrated drafts
        draft_sections = []
        provider_order = ["claude", "gemini", "chatgpt"]

        for i, (provider, edit) in enumerate(zip(provider_order, inputs.integrated_drafts)):
            section = f"""### Integrated Draft {chr(88 + i)} (from {provider.title()} Editor)

**Title:** {edit.integrated_draft.title}

**Content:**
{edit.integrated_draft.content}

**Word Count:** {edit.integrated_draft.word_count}

**Editor's Quality Assessment:**
- Argument Strength: {edit.quality_assessment.argument_strength}
- Citation Accuracy: {edit.quality_assessment.citation_accuracy}
- Prose Quality: {edit.quality_assessment.prose_quality}
- Structural Coherence: {edit.quality_assessment.structural_coherence}

**Integration Notes:**
- From Claude: {len(edit.integration_notes.elements_from_claude)} elements
- From Gemini: {len(edit.integration_notes.elements_from_gemini)} elements
- From ChatGPT: {len(edit.integration_notes.elements_from_chatgpt)} elements
- Original additions: {len(edit.integration_notes.original_additions)}

---"""
            draft_sections.append(section)

        drafts_str = "\n\n".join(draft_sections)

        # Format weights
        weights = inputs.priority_weights or {
            "argument_strength": 0.25,
            "citation_quality": 0.20,
            "prose_clarity": 0.20,
            "structural_coherence": 0.15,
            "academic_rigor": 0.10,
            "originality": 0.10,
        }
        weights_str = "\n".join(
            f"   - **{k.replace('_', ' ').title()}:** {v * 100:.0f}%" for k, v in weights.items()
        )

        # Format specific concerns
        concerns_str = (
            "\n".join(f"- {c}" for c in inputs.specific_concerns)
            if inputs.specific_concerns
            else "None specified - apply standard evaluation"
        )

        return f"""You are an expert evaluator of legal academic writing, tasked with ranking three integrated drafts.

## Your Role

You are one of THREE judges evaluating these drafts. A human will review all three judges' rankings to make the final selection. Your job is to provide:
1. A clear ranking with scores
2. Detailed explanations for your assessments
3. Honest identification of weaknesses
4. Actionable recommendations

## Original Context

**Topic:** {inputs.original_context.topic}
**Document Type:** {inputs.original_context.document_type}
**Requirements:** {inputs.original_context.section_outline}

## The Three Integrated Drafts

{drafts_str}

## Evaluation Rubric

Score each dimension 1-10 with explanation:

{weights_str}

1. **Argument Strength**
   - Logical coherence and validity
   - Persuasiveness of claims
   - Quality of supporting evidence

2. **Citation Quality**
   - Accuracy of Bluebook formatting
   - Appropriateness of sources
   - Effective use of authority

3. **Prose Clarity**
   - Readability and flow
   - Precision of language
   - Appropriate tone for audience

4. **Structural Coherence**
   - Logical organization
   - Effective transitions
   - Balanced section development

5. **Academic Rigor**
   - Depth of analysis
   - Engagement with counterarguments
   - Scholarly contribution

6. **Originality**
   - Fresh perspectives or framings
   - Novel connections
   - Creative but appropriate approach

## Specific Concerns to Address
{concerns_str}

## Judging Principles

- **Be honest:** Don't inflate scores. If all drafts are weak in an area, say so.
- **Be specific:** Point to exact passages when praising or criticizing.
- **Be constructive:** Weaknesses should come with improvement suggestions.
- **Be transparent:** Explain your reasoning so the human can evaluate your judgment.
- **Acknowledge uncertainty:** If a ranking is close, say so.

## Output Format

Return a JSON object with this exact structure:

```json
{{
  "rankings": {{
    "first_place": {{
      "draft_source": "claude | gemini | chatgpt",
      "overall_score": 8.5,
      "summary": "One-paragraph summary of why this draft ranks first"
    }},
    "second_place": {{
      "draft_source": "claude | gemini | chatgpt",
      "overall_score": 7.8,
      "summary": "One-paragraph summary of ranking rationale"
    }},
    "third_place": {{
      "draft_source": "claude | gemini | chatgpt",
      "overall_score": 7.2,
      "summary": "One-paragraph summary of ranking rationale"
    }}
  }},
  "detailed_scores": {{
    "claude_edit": {{
      "argument_strength": {{"score": 8, "explanation": "..."}},
      "citation_quality": {{"score": 9, "explanation": "..."}},
      "prose_clarity": {{"score": 8, "explanation": "..."}},
      "structural_coherence": {{"score": 7, "explanation": "..."}},
      "academic_rigor": {{"score": 8, "explanation": "..."}},
      "originality": {{"score": 7, "explanation": "..."}}
    }},
    "gemini_edit": {{ ... same structure ... }},
    "chatgpt_edit": {{ ... same structure ... }}
  }},
  "comparative_analysis": {{
    "strongest_arguments": "Which draft had the most compelling arguments and why",
    "best_citations": "Which draft used sources most effectively",
    "clearest_prose": "Which draft was most readable and precise",
    "most_original": "Which draft offered the freshest perspective"
  }},
  "recommendations": {{
    "for_human_review": ["Specific passages or issues requiring human judgment"],
    "potential_improvements": ["Suggestions that could enhance any of the drafts"],
    "citation_concerns": ["Any citations that should be verified"]
  }},
  "metadata": {{
    "model": "your model name",
    "timestamp": "ISO-8601 timestamp",
    "version": "1.0.0"
  }}
}}
```

Remember: A human will compare your rankings with two other judges. Provide the reasoning they need to make an informed final decision.

Now evaluate and rank the drafts. Respond ONLY with the JSON object."""
