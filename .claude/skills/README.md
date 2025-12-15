# Write-Assist Skills Registry

**Version:** 1.0.0
**Last Updated:** 2025-12-15

## Overview

Skills provide domain expertise for legal academic writing. They follow a progressive disclosure pattern:

1. **Level 1 - Metadata** (~100 tokens) - Loaded at startup via YAML frontmatter
2. **Level 2 - Instructions** (<5k tokens) - Full SKILL.md loaded when triggered
3. **Level 3 - Resources** (on-demand) - Workflows and reference materials

## Available Skills

| Skill | Version | Purpose | Directory |
|-------|---------|---------|-----------|
| [Academic Bluebook](academic-bluebook/SKILL.md) | 1.0.0 | Citation formatting for law reviews | `academic-bluebook/` |
| [Article Writing](article-writing/SKILL.md) | 1.0.0 | Law review article structure and style | `article-writing/` |
| [Casebook Editing](casebook-editing/SKILL.md) | 1.0.0 | Casebook development and case editing | `casebook-editing/` |
| [Cite-Assist Research](cite-assist/SKILL.md) | 1.0.0 | Semantic search via cite-assist v3 API | `cite-assist/` |

## Skill Structure

```
skill-name/
├── SKILL.md              # Main skill file with YAML frontmatter
└── workflows/            # Task-specific workflows
    ├── workflow-1.md
    └── workflow-2.md
```

## Usage

Skills are referenced by agents during execution:

```
See `.claude/skills/academic-bluebook/SKILL.md` for citation rules.
```

The drafter, editor, and judge agents all reference the Academic Bluebook skill for consistent citation handling.

## Integration with Agents

- **Drafter** - Uses all three skills depending on document type
- **Editor** - Primarily uses Academic Bluebook for citation verification
- **Judge** - References skills when evaluating domain-specific quality

## Creating New Skills

1. Create directory: `.claude/skills/skill-name/`
2. Create `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: Skill Name
   description: Brief description
   version: 1.0.0
   ---
   ```
3. Add workflows in `workflows/` subdirectory
4. Update this README

---

*Skills encapsulate domain expertise for reuse across agents and conversations.*
