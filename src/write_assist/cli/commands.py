"""
CLI command implementations.
"""

import asyncio
from pathlib import Path

import click

from write_assist.agents.base import DEFAULT_MODELS
from write_assist.agents.models import Provider
from write_assist.cli.output import (
    console,
    format_progress_update,
    output_result,
    print_models_table,
    print_status_table,
)
from write_assist.llm import LLMClient
from write_assist.pipeline import PipelineProgress, WritingPipeline

# =============================================================================
# Run Command
# =============================================================================


@click.command()
@click.option(
    "--topic",
    "-t",
    help="Topic or thesis to address",
)
@click.option(
    "--topic-file",
    "-T",
    type=click.Path(exists=True),
    help="Read topic from file",
)
@click.option(
    "--type",
    "-y",
    "doc_type",
    type=click.Choice(["article", "casebook_section"]),
    default="article",
    help="Document type",
)
@click.option(
    "--outline",
    "-o",
    help="Section outline",
)
@click.option(
    "--outline-file",
    "-O",
    type=click.Path(exists=True),
    help="Read outline from file",
)
@click.option(
    "--length",
    "-l",
    type=int,
    help="Target word count",
)
@click.option(
    "--output",
    "-f",
    type=click.Path(),
    help="Write result to file",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown", "interactive"]),
    default="interactive",
    help="Output format",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed progress",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Minimal output",
)
@click.option(
    "--model-claude",
    help="Override Claude model",
)
@click.option(
    "--model-gemini",
    help="Override Gemini model",
)
@click.option(
    "--model-chatgpt",
    help="Override ChatGPT model",
)
@click.option(
    "--source",
    "-s",
    "sources",
    multiple=True,
    help="Source document (local path or Google Docs URL). Can be repeated.",
)
@click.option(
    "--no-cite-assist",
    is_flag=True,
    help="Disable cite-assist citation lookup",
)
@click.option(
    "--output-dir",
    "-d",
    type=click.Path(),
    default="./runs",
    help="Directory for artifact storage (default: ./runs)",
)
@click.option(
    "--no-artifacts",
    is_flag=True,
    help="Disable artifact storage",
)
def run_cmd(
    topic: str | None,
    topic_file: str | None,
    doc_type: str,
    outline: str | None,
    outline_file: str | None,
    length: int | None,
    output: str | None,
    output_format: str,
    verbose: bool,
    quiet: bool,
    model_claude: str | None,
    model_gemini: str | None,
    model_chatgpt: str | None,
    sources: tuple[str, ...],
    no_cite_assist: bool,
    output_dir: str,
    no_artifacts: bool,
) -> None:
    """Run the full writing pipeline."""
    # Resolve topic
    if topic_file:
        topic = Path(topic_file).read_text().strip()
    if not topic:
        raise click.UsageError("Either --topic or --topic-file is required")

    # Resolve outline
    if outline_file:
        outline = Path(outline_file).read_text().strip()
    if not outline:
        outline = "1. Introduction\n2. Main content\n3. Conclusion"

    # Build models dict
    models: dict[Provider, str] = DEFAULT_MODELS.copy()
    if model_claude:
        models["claude"] = model_claude
    if model_gemini:
        models["gemini"] = model_gemini
    if model_chatgpt:
        models["chatgpt"] = model_chatgpt

    # Create pipeline
    pipeline = WritingPipeline(
        models=models,
        use_cite_assist=not no_cite_assist,
        output_dir=output_dir,
        save_artifacts=not no_artifacts,
    )

    # Progress callback
    def on_progress(p: PipelineProgress) -> None:
        if not quiet:
            console.print(format_progress_update(p))

    # Run pipeline
    if not quiet:
        console.print(f"\n[bold]Starting pipeline for:[/bold] {topic[:50]}...")
        if sources:
            console.print(f"[dim]Sources: {len(sources)} document(s)[/dim]")
        console.print()

    try:
        result = asyncio.run(
            pipeline.run(
                topic=topic,
                document_type=doc_type,  # type: ignore
                section_outline=outline,
                source_files=list(sources) if sources else None,
                target_length=length,
                on_progress=on_progress if verbose else None,
            )
        )
    except Exception as e:
        console.print(f"[red]Pipeline failed:[/red] {e}")
        raise click.Abort() from e

    # Output result
    if not quiet:
        console.print()
        if result.artifact_path:
            console.print(f"[dim]Artifacts saved to:[/dim] {result.artifact_path}")
            console.print()

    if output:
        # Write to file
        output_path = Path(output)
        if output_format == "json":
            import json

            with open(output_path, "w") as f:
                json.dump(
                    {
                        "topic": topic,
                        "consensus_ranking": result.consensus_ranking,
                        "recommended_title": result.recommended_edit.integrated_draft.title
                        if result.recommended_edit
                        else None,
                        "recommended_content": result.recommended_edit.integrated_draft.content
                        if result.recommended_edit
                        else None,
                    },
                    f,
                    indent=2,
                )
        else:
            with open(output_path, "w") as f:
                if result.recommended_edit:
                    f.write(f"# {result.recommended_edit.integrated_draft.title}\n\n")
                    f.write(result.recommended_edit.integrated_draft.content)
        console.print(f"[green]Result written to:[/green] {output_path}")
    else:
        output_result(result, output_format)


# =============================================================================
# Status Command
# =============================================================================


@click.command()
def status_cmd() -> None:
    """Check API key status."""
    # Use auth-utils to check provider configuration
    configured = LLMClient.get_configured_providers()

    api_status = {
        "Claude": configured.get("claude", False),
        "Gemini": configured.get("gemini", False),
        "ChatGPT": configured.get("chatgpt", False),
    }

    print_status_table(api_status)

    # Summary
    set_count = sum(1 for v in api_status.values() if v)
    if set_count == 3:
        console.print("\n[green]All API keys are configured![/green]")
    elif set_count > 0:
        console.print(
            f"\n[yellow]{set_count}/3 API keys configured. "
            "Pipeline may still work with partial results.[/yellow]"
        )
    else:
        console.print(
            "\n[red]No API keys configured. Set at least one key to use write-assist.[/red]"
        )


# =============================================================================
# Models Command
# =============================================================================


@click.command()
def models_cmd() -> None:
    """Show available models."""
    print_models_table(DEFAULT_MODELS)

    console.print("\n[dim]Override with --model-claude, --model-gemini, --model-chatgpt[/dim]")
