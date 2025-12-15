"""
Output formatters for CLI results.
"""

import json

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from write_assist.pipeline import PipelineProgress, PipelineResult

console = Console()


def create_progress_display() -> Progress:
    """Create a rich progress display for pipeline execution."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def format_progress_update(progress: PipelineProgress) -> str:
    """Format a progress update for display."""
    status_icons = {
        "starting": "🚀",
        "running": "⏳",
        "completed": "✅",
        "failed": "❌",
    }
    icon = status_icons.get(progress.status, "•")
    return f"{icon} [{progress.phase}] {progress.message}"


def output_json(result: PipelineResult) -> None:
    """Output result as JSON."""
    output = {
        "original_input": {
            "topic": result.original_input.topic,
            "document_type": result.original_input.document_type,
            "section_outline": result.original_input.section_outline,
        },
        "phases": {
            "drafting": {
                "success_count": result.drafting_phase.success_count,
                "execution_time_ms": result.drafting_phase.execution_time_ms,
            },
            "editing": {
                "success_count": result.editing_phase.success_count,
                "execution_time_ms": result.editing_phase.execution_time_ms,
            },
            "judging": {
                "success_count": result.judging_phase.success_count,
                "execution_time_ms": result.judging_phase.execution_time_ms,
            },
        },
        "consensus_ranking": result.consensus_ranking,
        "total_execution_time_ms": result.total_execution_time_ms,
    }

    if result.recommended_edit:
        output["recommended_draft"] = {
            "title": result.recommended_edit.integrated_draft.title,
            "content": result.recommended_edit.integrated_draft.content,
            "word_count": result.recommended_edit.integrated_draft.word_count,
        }

    console.print_json(json.dumps(output, indent=2, default=str))


def output_markdown(result: PipelineResult) -> None:
    """Output result as markdown."""
    if not result.recommended_edit:
        console.print("[red]No usable result generated.[/red]")
        return

    edit = result.recommended_edit

    md = f"""# {edit.integrated_draft.title}

{edit.integrated_draft.content}

---

**Word Count:** {edit.integrated_draft.word_count}
**Consensus Ranking:** {" > ".join(result.consensus_ranking)}
**Execution Time:** {result.total_execution_time_ms:.0f}ms
"""

    console.print(Markdown(md))


def output_interactive(result: PipelineResult) -> None:
    """Output result in interactive format with panels."""
    # Summary panel
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value")

    summary_table.add_row("Total Time", f"{result.total_execution_time_ms:.0f}ms")
    summary_table.add_row("Consensus Ranking", " → ".join(result.consensus_ranking))
    summary_table.add_row("Drafting Phase", f"{result.drafting_phase.success_count}/3 succeeded")
    summary_table.add_row("Editing Phase", f"{result.editing_phase.success_count}/3 succeeded")
    summary_table.add_row("Judging Phase", f"{result.judging_phase.success_count}/3 succeeded")

    console.print(Panel(summary_table, title="Pipeline Summary", border_style="green"))

    # Rankings table
    if result.judge_results:
        rankings_table = Table(title="Judge Rankings")
        rankings_table.add_column("Judge", style="cyan")
        rankings_table.add_column("1st Place")
        rankings_table.add_column("2nd Place")
        rankings_table.add_column("3rd Place")

        for provider, judge_result in result.judge_results.items():
            rankings_table.add_row(
                provider.title(),
                f"{judge_result.rankings.first_place.draft_source} ({judge_result.rankings.first_place.overall_score:.1f})",
                f"{judge_result.rankings.second_place.draft_source} ({judge_result.rankings.second_place.overall_score:.1f})",
                f"{judge_result.rankings.third_place.draft_source} ({judge_result.rankings.third_place.overall_score:.1f})",
            )

        console.print(rankings_table)

    # Recommended draft
    if result.recommended_edit:
        edit = result.recommended_edit
        console.print()
        console.print(
            Panel(
                Markdown(edit.integrated_draft.content[:2000] + "..."),
                title=f"[bold]{edit.integrated_draft.title}[/bold] (Preview)",
                subtitle=f"Word count: {edit.integrated_draft.word_count}",
                border_style="blue",
            )
        )


def output_result(result: PipelineResult, format: str) -> None:
    """Output result in the specified format."""
    formatters = {
        "json": output_json,
        "markdown": output_markdown,
        "interactive": output_interactive,
    }

    formatter = formatters.get(format, output_interactive)
    formatter(result)


def print_status_table(api_status: dict[str, bool]) -> None:
    """Print API key status table."""
    table = Table(title="API Key Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("Environment Variable")

    env_vars = {
        "Claude": "ANTHROPIC_API_KEY",
        "Gemini": "GOOGLE_API_KEY",
        "ChatGPT": "OPENAI_API_KEY",
    }

    for provider, status in api_status.items():
        status_str = "[green]✓ Set[/green]" if status else "[red]✗ Not set[/red]"
        table.add_row(provider, status_str, env_vars.get(provider, ""))

    console.print(table)


def print_models_table(models: dict[str, str]) -> None:
    """Print available models table."""
    table = Table(title="Default Models")
    table.add_column("Provider", style="cyan")
    table.add_column("Default Model")

    for provider, model in models.items():
        table.add_row(provider.title(), model)

    console.print(table)
