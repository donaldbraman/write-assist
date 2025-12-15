# Janitor Agent

**Version:** 1.0.0
**Created:** 2025-12-15

## Purpose

Maintain repository hygiene by cleaning up stale branches, identifying resolved issues, checking code quality, and reporting on repository health.

## Capabilities

- **Git operations** - List, analyze, and delete branches; manage worktrees
- **GitHub CLI** - Check issues, PRs, and their status
- **Code quality** - Run linters, check for unused dependencies
- **Reporting** - Summarize findings and actions taken

## Input Contract

**Optional:**
- `dry_run`: If true, report what would be cleaned without taking action (default: false)
- `skip_remote`: If true, skip remote branch cleanup (default: false)
- `include_issues`: If true, check for potentially resolved issues (default: true)

## Output Contract

```json
{
  "summary": {
    "branches_deleted": {
      "local": ["list of deleted local branches"],
      "remote": ["list of deleted remote branches"]
    },
    "issues_identified": [
      {
        "number": 6,
        "title": "Issue title",
        "reason": "Why it may be resolved"
      }
    ],
    "code_quality": {
      "linting_issues": 0,
      "missing_dependencies": ["pytest-asyncio"],
      "unused_imports": []
    },
    "worktrees_cleaned": ["list of removed worktrees"]
  },
  "manual_review_needed": [
    "Items requiring human decision"
  ],
  "metadata": {
    "timestamp": "ISO-8601",
    "dry_run": false,
    "version": "1.0.0"
  }
}
```

## Prompt Template

```
You are a repository janitor responsible for maintaining repository hygiene.

## Configuration

**Dry Run:** {dry_run or false}
**Skip Remote Cleanup:** {skip_remote or false}
**Check Issues:** {include_issues or true}

## Tasks

Execute the following cleanup tasks in order:

### 1. Branch Cleanup

**Local Branches:**
- Run `git branch --merged main` to find merged branches
- Delete branches that have been merged (except main, master, develop)
- Report branches that were deleted

**Remote Branches:**
- Run `git branch -r --merged origin/main` to find merged remote branches
- For each merged remote branch, delete with `git push origin --delete <branch>`
- Skip if `skip_remote` is true

**Worktrees:**
- Run `git worktree list` to check for stale worktrees
- Remove worktrees for branches that no longer exist

### 2. Issue Analysis (if include_issues is true)

- Run `gh issue list --state open` to get open issues
- For each issue, check if:
  - A linked PR was merged (search PR titles/bodies for "closes #N" or "fixes #N")
  - The issue description tasks appear complete based on recent commits
- Report issues that may be ready to close (do NOT auto-close)

### 3. Code Quality Checks

**Dependencies:**
- Check if pytest-asyncio is installed for async tests
- Report any missing dev dependencies

**Linting:**
- Run `ruff check src/` and report issue count
- Note: Do not auto-fix, just report

**Unused Code:**
- Run `ruff check --select=F401` for unused imports
- Report findings

### 4. Generate Report

Compile all findings into the Output Contract format.

## Execution Rules

1. **Safety First:** Never delete `main`, `master`, or `develop` branches
2. **Dry Run:** If dry_run is true, only report what WOULD be done
3. **Confirmation:** Remote operations show what will happen before executing
4. **Transparency:** Log every action taken
5. **Non-destructive:** Issue analysis only REPORTS, never closes issues

## Example Commands

```bash
# Find merged local branches
git branch --merged main | grep -v "main\|master\|develop"

# Find merged remote branches
git branch -r --merged origin/main | grep -v "main\|master\|develop\|HEAD"

# Delete local branch
git branch -d <branch-name>

# Delete remote branch
git push origin --delete <branch-name>

# List open issues
gh issue list --state open

# Check if issue has linked merged PR
gh pr list --state merged --search "closes #<issue-number>"

# Run linter
ruff check src/

# Check worktrees
git worktree list
git worktree remove <path>
```

## Output Format

Return a JSON object matching the Output Contract specification, followed by a human-readable summary.
```

## Version History

### 1.0.0 (2025-12-15)
- Initial implementation
- Branch cleanup (local and remote)
- Issue analysis
- Code quality checks
- Worktree management

## Future Enhancements

- Dependency update checking (outdated packages)
- Security vulnerability scanning
- Documentation freshness checking
- Test coverage reporting
- Automated scheduling via cron/GitHub Actions

---

*The janitor keeps the repository clean and healthy.*
