# Write-Assist Agents Registry

**Version:** 1.0.0
**Last Updated:** 2025-12-15

## Overview

Role-based agents for the multi-LLM ensemble pipeline. Each agent definition is model-agnostic and runs on Claude, Gemini, and ChatGPT in parallel.

## Pipeline Architecture

```
DRAFTER (×3) → EDITOR (×3) → JUDGE (×3) → Human Review
```

Each phase runs the same agent prompt on all three LLMs simultaneously.

## Available Agents

### Pipeline Agents

| Agent | Version | Purpose | Capabilities |
|-------|---------|---------|--------------|
| [drafter-agent](drafter-agent.md) | 1.0.0 | Create initial draft | File reading, web research, cite-assist queries |
| [editor-agent](editor-agent.md) | 1.0.0 | Integrate multiple drafts | Cross-draft analysis, citation verification |
| [judge-agent](judge-agent.md) | 1.0.0 | Rank and explain | Comparative evaluation, rubric-based scoring |

### Research Agents

| Agent | Version | Purpose | Capabilities |
|-------|---------|---------|--------------|
| [cite-assist-researcher-agent](cite-assist-researcher-agent.md) | 1.0.0 | Academic source retrieval | Semantic search, mode selection, citation prep |

### Utility Agents

| Agent | Version | Purpose | Capabilities |
|-------|---------|---------|--------------|
| [janitor-agent](janitor-agent.md) | 1.0.0 | Repository maintenance | Branch cleanup, issue analysis, code quality |

## Usage Pattern

**Orchestration pseudocode:**

```python
# Phase 1: Parallel drafting
drafts = await asyncio.gather(
    run_agent("drafter", model="claude", context=context),
    run_agent("drafter", model="gemini", context=context),
    run_agent("drafter", model="chatgpt", context=context),
)

# Phase 2: Parallel editing (each editor sees ALL drafts)
edits = await asyncio.gather(
    run_agent("editor", model="claude", drafts=drafts),
    run_agent("editor", model="gemini", drafts=drafts),
    run_agent("editor", model="chatgpt", drafts=drafts),
)

# Phase 3: Parallel judging (each judge sees ALL edits)
rankings = await asyncio.gather(
    run_agent("judge", model="claude", edits=edits),
    run_agent("judge", model="gemini", edits=edits),
    run_agent("judge", model="chatgpt", edits=edits),
)

# Human reviews rankings and selects final output
```

## Future: Drafter Variants

The drafter agent is designed for extensibility. Future variants may include:

- **Formal Academic** - Traditional law review style
- **Accessible** - Plain language, broader audience
- **Interdisciplinary** - Cross-disciplinary framing
- **Doctrinal** - Case law and legal doctrine focus
- **Empirical** - Data-driven, social science methods
- **Theoretical** - Jurisprudential and philosophical

These would be implemented as separate drafter definitions that share core capabilities.

## Agent Design Principles

1. **Model-agnostic prompts** - Same instructions work across Claude, Gemini, ChatGPT
2. **Structured outputs** - JSON or markdown for clean data passing between phases
3. **Tool-enabled** - Drafters have file/web/cite-assist access; editors and judges are evaluation-focused
4. **Academic Bluebook** - All agents reference the bluebook skill for citation standards

## Creating New Agents

Use this template:

```markdown
# [Agent Name]

**Version:** 1.0.0
**Created:** YYYY-MM-DD

## Purpose

One-sentence description.

## Capabilities

- Capability 1
- Capability 2

## Input Contract

**Required:**
- input1: Description

**Optional:**
- input2: Description (default: value)

## Output Contract

Structured output specification.

## Prompt Template

[Complete prompt]

## Version History

### 1.0.0 (YYYY-MM-DD)
- Initial implementation
```

---

*Agents enable ensemble writing by running the same role across multiple LLMs.*
