"""This implements the Command Line Interface which enables the user to
use the functionality implemented in the :mod:`~digiarch` submodules.
The CLI implements several commands with suboptions.
"""  # noqa: D205
# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import asyncio
import logging as log
import os
from collections.abc import Callable
from functools import wraps
from logging import Logger
from pathlib import Path
from typing import Any

import click
from acamodels import ArchiveFile
from click.core import Context

from digiarch import __version__, core
from digiarch.core.identify_files import is_preservable
from digiarch.core.utils import costum_sigs, to_re_identify
from digiarch.exceptions import FileCollectionError, FileParseError, IdentificationError
from digiarch.models import FileData

# -----------------------------------------------------------------------------
# Auxiliary functions
# -----------------------------------------------------------------------------


def coro(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        return asyncio.run(func(*args, **kwargs))

    return wrapper


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


@click.group(invoke_without_command=True, chain=True)
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--reindex", is_flag=True, help="Reindex the current directory.")
@click.version_option(version=__version__)
@click.pass_context
@coro
async def cli(ctx: Context, path: str, reindex: bool) -> None:
    """Used for indexing, reporting on, and identifying files found in PATH."""
    # Initialise
    in_path: Path = Path(path)
    os.environ["ROOTPATH"] = path
    file_data: FileData = FileData(main_dir=in_path, files=[])
    empty: bool = await file_data.db.is_empty()
    warnings: list[str] = []

    # Collect file info and update file_data
    if reindex or empty:
        click.secho("Collecting file information...", bold=True)
        try:
            warnings = await core.explore_dir(file_data)
        except FileCollectionError as error:
            raise click.ClickException(str(error))

    else:
        click.echo("Processing data from ", nl=False)
        click.secho(f"{file_data.db.url}", bold=True)

    for warning in warnings:
        click.secho(warning, bold=True, fg="red")

    try:
        file_data.files = await file_data.db.get_files()
    except FileParseError as error:
        raise click.ClickException(str(error))
    else:
        ctx.obj = file_data
        """_files = file_data.files
        _files = core.generate_checksums(_files)
        try:
            print("Identifying")
            _files = core.identify(_files, file_data.main_dir)
        except IdentificationError as error:
            raise click.ClickException(str(error))
        else:
            click.secho(f"Successfully identified {len(_files)} files.")
            print("Finished identifying")
            file_data.files = _files"""


@cli.command()
@click.pass_obj
def process(file_data: FileData) -> None:
    """Generate checksums and identify files."""
    print("Generate checksums")
    versions: tuple[str, str] = (to_re_identify()[1], costum_sigs()[1])
    print(
        "Using the following versionf from reference files: \n"
        f"to_convert version {versions[0]} \n"
        f"costume_signature version {versions[1]}",
    )
    _files: list[ArchiveFile] = file_data.files
    _files = core.generate_checksums(_files)
    click.secho("Identifying files... ", nl=False)
    try:
        _files = core.identify(_files, file_data.main_dir)
    except IdentificationError as error:
        raise click.ClickException(str(error))
    else:
        click.secho(f"Successfully identified {len(_files)} files.")
        print("Finished identifying")
        file_data.files = _files


# @cli.command()
# @click.pass_context
# @coro
# async def fix(ctx: Context) -> None:
#     """Fix file extensions - files should be identified first."""
#     file_data = ctx.obj
#     fixed = core.fix_extensions(file_data.files)
#     if fixed:
#         click.secho("Rebuilding file information...", bold=True)
#         new_files = core.identify(fixed, file_data.main_dir)
#         await file_data.db.update_files(new_files)
#         file_data.files = await file_data.db.get_files()
#         ctx.obj = file_data
#     else:
#         click.secho("Info: No file extensions to fix.",
#                       bold=True, fg="yellow")


def setup_logger() -> Logger:
    logger: Logger = log.getLogger("image_is_preservable")
    file_handler = log.FileHandler("pillow_decompressionbomb.log", mode="a", encoding="utf-8")
    log_fmt = log.Formatter(
        fmt="%(asctime)s - %(levelname)s: %(message)s",
        datefmt="%D %H:%M:%S",
    )
    file_handler.setFormatter(log_fmt)
    logger.addHandler(file_handler)
    logger.setLevel(log.INFO)
    return logger


def get_preservable_info(file_data: FileData) -> list[dict]:
    log: Logger = setup_logger()
    information = []

    for file in file_data.files:
        preservable_info: dict[str, Any] = {}
        preservable = is_preservable(file, log)
        if preservable[0] is False:
            preservable_info["uuid"] = str(file.uuid)
            preservable_info["ignore reason"] = preservable[1]
            information.append(preservable_info)

    return information


@cli.result_callback()
@coro
async def done(result: Any, **kwargs: Any) -> None:  # noqa: ANN401
    ctx = click.get_current_context()
    file_data: FileData = ctx.obj
    await file_data.db.set_files(file_data.files)

    information = get_preservable_info(file_data)
    await file_data.db.set_preservable_info(information)

    click.secho("Done!", bold=True, fg="green")


if __name__ == "__main__":
    cli()
