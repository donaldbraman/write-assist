# Claude Code Instructions for write-assist

Multi-LLM legal academic writing assistance using Claude, Gemini, and ChatGPT.

**Global guides:** `.claude/guides/` (symlinked from cross-repo)

---

## Critical Rules

- NEVER create files outside defined directories
- NEVER use mocks - integration tests with real data only
- NEVER use bare `python` - always `uv run python`
- NEVER commit temporary/debug scripts
- ALL temp scripts go in `temp/` (gitignored)
- ALL tests go in `tests/` as integration tests
- RUN `uv run ruff check . && uv run ruff format .` before commits

---

## Project Overview

**Purpose:** Ensemble writing system that leverages three LLMs (Claude, Gemini, ChatGPT) for legal academic writing.

**Supported Documents:**
- Law review articles
- Casebooks

**Citation System:** Academic Bluebook (law review style)

---

## Multi-LLM Pipeline

```
Phase 1: DRAFTING (parallel)     Phase 2: EDITING (parallel)     Phase 3: JUDGING (parallel)
┌─────────┐                      ┌─────────┐                      ┌─────────┐
│ Claude  │──┐                   │ Claude  │──┐                   │ Claude  │──┐
│ Drafter │  │                   │ Editor  │  │                   │ Judge   │  │
└─────────┘  │  3 Drafts         └─────────┘  │  3 Integrated     └─────────┘  │  3 Rankings
┌─────────┐  ├─────────────►     ┌─────────┐  ├─────────────►     ┌─────────┐  ├─────────►  Human
│ Gemini  │──┤                   │ Gemini  │──┤                   │ Gemini  │──┤            Review
│ Drafter │  │                   │ Editor  │  │                   │ Judge   │  │
└─────────┘  │                   └─────────┘  │                   └─────────┘  │
┌─────────┐  │                   ┌─────────┐  │                   ┌─────────┐  │
│ ChatGPT │──┘                   │ ChatGPT │──┘                   │ ChatGPT │──┘
│ Drafter │                      │ Editor  │                      │ Judge   │
└─────────┘                      └─────────┘                      └─────────┘
```

**Agents:** 3 role-based definitions (drafter, editor, judge) run on each model.

---

## Essential Commands

```bash
# Setup
uv sync                                    # Install dependencies
pre-commit install                         # Install pre-commit hooks

# Worktrees (REQUIRED for development - pre-commit blocks main)
git worktree add ../write-assist-worktrees/feat-name -b feat/feature-name
cd ../write-assist-worktrees/feat-name     # Work in worktree
git worktree list                          # List all worktrees
git worktree remove ../write-assist-worktrees/feat-name  # After merge

# Development
uv run python -m write_assist              # Run main module
uv run pytest                              # Run integration tests

# Quality
uv run ruff check .                        # Lint
uv run ruff format .                       # Format
uv run ruff check . --fix                  # Auto-fix lint issues
```

---

## Just-in-Time Guides

| Topic | Guide | Read When |
|-------|-------|-----------|
| **Worktree Dev Cycle** | [.claude/guides/worktree-dev-cycle.md](.claude/guides/worktree-dev-cycle.md) | **REQUIRED** - Before any development work |
| **Multi-LLM Authentication** | [docs/guides/llm-authentication.md](docs/guides/llm-authentication.md) | Setting up API access |
| **cite-assist Integration** | [docs/guides/cite-assist-integration.md](docs/guides/cite-assist-integration.md) | Querying local citation database |
| **Academic Bluebook** | [.claude/skills/academic-bluebook/SKILL.md](.claude/skills/academic-bluebook/SKILL.md) | Citation formatting |
| **Autonomous Cycle** | [.claude/guides/autonomous-cycle.md](.claude/guides/autonomous-cycle.md) | Development workflow |
| **Git Workflow** | [.claude/guides/git-workflow.md](.claude/guides/git-workflow.md) | Branching and commits |
| **Lint & Hooks** | [.claude/guides/lint-and-hooks.md](.claude/guides/lint-and-hooks.md) | Pre-commit hook issues |
| **PR Guidelines** | [.claude/guides/pr-guidelines.md](.claude/guides/pr-guidelines.md) | Creating pull requests |

---

## Project Structure

```
write-assist/
├── CLAUDE.md                 # This file
├── .claude/
│   ├── agents/               # Drafter, editor, judge definitions
│   ├── commands/             # Slash commands
│   ├── skills/               # Domain expertise (bluebook, article, casebook)
│   └── guides/               # Symlink to cross-repo guides
├── docs/guides/              # Project-specific guides
├── src/write_assist/         # Python package
├── tests/                    # Integration tests (real data only)
└── temp/                     # Temporary scripts (gitignored)
```

---

## Development Guidelines

- **Use git worktrees:** Pre-commit blocks direct commits to main. Create worktrees for all development work. This enables parallel agent work and prevents branch conflicts.
- **Worktree location:** `../write-assist-worktrees/<feature-name>/`
- **Temporary scripts:** Create in `temp/`, never commit
- **Testing:** Integration tests only, use real documents and citations
- **Commits:** Follow cross-repo git workflow, link to issues
- **Pre-commit:** Ruff lint/format runs automatically

### Worktree Workflow

```bash
# 1. Create worktree for new feature
git worktree add ../write-assist-worktrees/my-feature -b feat/my-feature

# 2. Work in worktree
cd ../write-assist-worktrees/my-feature
uv sync  # Install deps in worktree
# ... make changes, commit ...

# 3. Push and create PR
git push -u origin feat/my-feature
gh pr create

# 4. After merge, cleanup
cd /path/to/write-assist
git worktree remove ../write-assist-worktrees/my-feature
git branch -d feat/my-feature
```

**Why worktrees?** Multiple agents can work in parallel without conflicts. Each gets its own directory with its own branch checked out.

---

## Agents

| Agent | Purpose | File |
|-------|---------|------|
| **Drafter** | Create initial draft with research and citations | [.claude/agents/drafter-agent.md](.claude/agents/drafter-agent.md) |
| **Editor** | Review and integrate multiple drafts | [.claude/agents/editor-agent.md](.claude/agents/editor-agent.md) |
| **Judge** | Rank outputs with explanations | [.claude/agents/judge-agent.md](.claude/agents/judge-agent.md) |

**Future:** Drafter variants for different writing styles (stub for later implementation).

---

*Last updated: 2025-12-15 (added worktree workflow)*
