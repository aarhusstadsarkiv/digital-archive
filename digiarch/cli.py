"""This implements the Command Line Interface which enables the user to
use the functionality implemented in the `digiarch` submodules.
The CLI implements several commands with suboptions.

"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import click
from pathlib import Path
from digiarch.data import get_fileinfo_list, dump_file
from digiarch.utils import path_utils, group_files
from digiarch.identify import checksums
from digiarch.identify import reports

# -----------------------------------------------------------------------------
# Function Definitions
# -----------------------------------------------------------------------------


@click.group(invoke_without_command=True, chain=True)
@click.argument(
    "path", type=click.Path(exists=True, file_okay=False, resolve_path=True)
)
@click.option(
    "--reindex", is_flag=True, help="Whether to reindex the current directory."
)
@click.pass_context
def cli(ctx: click.core.Context, path: str, reindex: bool) -> None:
    """Command Line Tool for handling Aarhus Digital Archive handins.
    Invoked using digiarch [option] /path/to/handins/ [command]."""
    # Create directories
    main_dir: Path = Path(path, "_digiarch")
    data_dir: Path = Path(main_dir, ".data")
    data_file: Path = Path(data_dir, "data.json")
    path_utils.create_folders(main_dir, data_dir)

    # If we haven't indexed this directory before,
    # or reindex is passed, traverse directory and dump data file.
    # Otherwise, tell the user which file we're processing from.
    if reindex or not data_file.is_file():
        click.secho("Collecting file information...", bold=True)
        empty_subs = path_utils.explore_dir(Path(path), main_dir, data_file)
        if empty_subs:
            for sub in empty_subs:
                click.secho(f"Warning! {sub} is empty!", bold=True, fg="red")
        click.secho("Done!", bold=True, fg="green")
    else:
        click.echo(f"Processing data from ", nl=False)
        click.secho(f"{data_file}", bold=True)

    ctx.obj = {"main_dir": main_dir, "data_file": data_file}


@cli.command()
@click.pass_obj
def report(path_info: dict) -> None:
    """Generate reports on files and directory structure."""
    # TODO: --path should be optional, default to directory where
    # the CLI is called.
    # TODO: Check if path is empty, exit gracefully if so.
    reports.report_results(path_info["data_file"], path_info["main_dir"])


@cli.command()
@click.pass_obj
def group(path_info: dict) -> None:
    """Generate lists of files grouped per file extension."""
    group_files.grouping(path_info["data_file"], path_info["main_dir"])
    click.secho("Done!", bold=True, fg="green")


@cli.command()
@click.pass_obj
def checksum(path_info: dict) -> None:
    """Generate file checksums using BLAKE2."""
    files = get_fileinfo_list(path_info["data_file"])
    updated_files = checksums.generate_checksums(files)
    dump_file(updated_files, path_info["data_file"])
    click.secho("Done!", bold=True, fg="green")


@cli.command()
@click.pass_obj
def dups(path_info: dict) -> None:
    """Check for file duplicates."""
    files = get_fileinfo_list(path_info["data_file"])
    checksums.check_duplicates(files, path_info["main_dir"])
    click.secho("Done!", bold=True, fg="green")
