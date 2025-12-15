"""
Command-line interface for write-assist.
"""

import click

from write_assist.cli.commands import models_cmd, run_cmd, status_cmd


@click.group()
@click.version_option(package_name="write-assist")
def cli() -> None:
    """write-assist: Multi-LLM legal academic writing assistance."""
    pass


cli.add_command(run_cmd, name="run")
cli.add_command(status_cmd, name="status")
cli.add_command(models_cmd, name="models")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
