from collections.abc import Generator
from itertools import islice
from logging import ERROR
from logging import INFO
from logging import Logger
from os import PathLike
from pathlib import Path
from traceback import format_tb
from typing import get_args as get_type_args
from typing import Literal
from typing import overload
from uuid import UUID

from acacore.database import FilesDB
from acacore.database.table import Table
from acacore.exceptions.files import IdentificationError
from acacore.models.event import Event
from acacore.models.file import BaseFile
from acacore.models.file import ConvertedFile
from acacore.models.file import MasterFile
from acacore.models.file import OriginalFile
from acacore.models.reference_files import Action
from acacore.models.reference_files import ActionData
from acacore.models.reference_files import CustomSignature
from acacore.models.reference_files import ManualAction
from acacore.models.reference_files import MasterConvertAction
from acacore.siegfried import Siegfried
from acacore.siegfried.siegfried import SiegfriedFile
from acacore.siegfried.siegfried import TSignaturesProvider
from acacore.utils.click import ctx_params
from acacore.utils.click import end_program
from acacore.utils.click import start_program
from acacore.utils.functions import find_files
from acacore.utils.helpers import ExceptionManager
from click import BadParameter
from click import Choice
from click import Context
from click import group
from click import IntRange
from click import option
from click import pass_context
from click import Path as ClickPath
from click import UsageError
from PIL import UnidentifiedImageError

from digiarch.__version__ import __version__
from digiarch.common import AVID
from digiarch.common import fetch_actions
from digiarch.common import fetch_actions_master
from digiarch.common import fetch_custom_signatures
from digiarch.common import get_avid
from digiarch.common import open_database
from digiarch.common import option_dry_run
from digiarch.query import argument_query
from digiarch.query import query_to_where
from digiarch.query import TQuery


@overload
def identify_requirements(
    target: Literal["original"],
    ctx: Context,
    siegfried_path: str | None,
    siegfried_signature: str,
    siegfried_home: str | None,
    actions_file: str | None,
    custom_signatures_file: str | None,
) -> tuple[Siegfried, dict[str, Action], list[CustomSignature]]: ...


@overload
def identify_requirements(
    target: Literal["master"],
    ctx: Context,
    siegfried_path: str | None,
    siegfried_signature: str,
    siegfried_home: str | None,
    actions_file: str | None,
    custom_signatures_file: str | None,
) -> tuple[Siegfried, dict[str, MasterConvertAction], list[CustomSignature]]: ...


def identify_requirements(
    target: Literal["original", "master"],
    ctx: Context,
    siegfried_path: str | None,
    siegfried_signature: str,
    siegfried_home: str | None,
    actions_file: str | None,
    custom_signatures_file: str | None,
) -> tuple[Siegfried, dict[str, Action] | dict[str, MasterConvertAction], list[CustomSignature]]:
    siegfried = Siegfried(
        siegfried_path or "sf",
        f"{siegfried_signature}.sig",
        siegfried_home,
    )

    try:
        siegfried.run("-version", "-sig", siegfried.signature)
    except IdentificationError as err:
        print(err)
        raise BadParameter("Invalid binary or signature file.", ctx, ctx_params(ctx)["siegfried_path"])

    if target == "original":
        actions = fetch_actions(ctx, "actions_file", actions_file)
    elif target == "master":
        actions = fetch_actions_master(ctx, "actions_file", actions_file)
    else:
        raise UsageError("Unknown target", ctx)

    custom_signatures = fetch_custom_signatures(ctx, "custom_signatures_file", custom_signatures_file)

    return siegfried, actions, custom_signatures


def find_files_query(
    avid: AVID,
    table: Table[BaseFile],
    query: TQuery,
    batch_size: int,
) -> Generator[Path, None, None]:
    where, parameters = query_to_where(query)
    offset: int = 0

    while batch := table.select(
        where,
        parameters,
        order_by=[("lower(relative_path)", "asc")],
        limit=batch_size,
        offset=offset,
    ).fetchall():
        offset += len(batch)
        yield from (avid.path / f.relative_path for f in batch)

    yield from ()


def identify_original_file(
    ctx: Context,
    avid: AVID,
    db: FilesDB,
    siegfried_file: SiegfriedFile,
    actions: dict[str, Action],
    custom_signatures: list[CustomSignature],
    dry_run: bool,
    update: bool,
    parent: UUID | None,
    original_path: str | PathLike | None,
    *loggers: Logger,
    ignore_lock: bool = False,
):
    errors: list[Event] = []
    existing_file: OriginalFile | None = db.original_files[
        {"relative_path": str(siegfried_file.filename.relative_to(avid.path))}
    ]

    if existing_file and not update:
        Event.from_command(ctx, "skip", (existing_file.uuid, "original"), reason="exists").log(
            INFO,
            *loggers,
            path=existing_file.relative_path,
        )
        return
    if existing_file and existing_file.lock and not ignore_lock:
        Event.from_command(ctx, "skip", (existing_file.uuid, "original"), reason="locked").log(
            INFO,
            *loggers,
            path=existing_file.relative_path,
        )
        return

    file = OriginalFile.from_file(siegfried_file.filename, avid.path, parent=parent)

    with ExceptionManager(Exception, UnidentifiedImageError, allow=[OSError, IOError]) as error:
        file.identify(siegfried_file, custom_signatures, actions)

    if error.exception:
        file.action = "manual"
        file.action_data = ActionData(manual=ManualAction(reason=repr(error.exception), process=""))
        errors.append(
            Event.from_command(
                ctx,
                "error",
                (file.uuid, "original"),
                repr(error.exception),
                "".join(format_tb(error.traceback)).strip() or None,
            )
        )

    file.original_path = Path(original_path).relative_to(file.root) if original_path else file.relative_path

    if existing_file:
        file.uuid = existing_file.uuid
        file.original_path = existing_file.original_path
        file.parent = file.parent or existing_file.parent
        file.processed = (
            False
            if file.action != existing_file.action or file.action_data != existing_file.action_data
            else existing_file.processed
        )
        file.lock = existing_file.lock

    if dry_run:
        pass
    elif existing_file:
        db.original_files.update(file)
        db.log.insert(*errors)
    else:
        db.original_files.insert(file)
        db.log.insert(*errors)

    if update or not existing_file:
        Event.from_command(ctx, "update" if existing_file else "new", (file.uuid, "original")).log(
            INFO,
            *loggers,
            puid=str(file.puid).ljust(10),
            action=str(file.action).ljust(7),
            path=file.relative_path,
        )

        for error in errors:
            error.log(ERROR, show_args=["uuid", "data"])


def identify_original_files(
    ctx: Context,
    avid: AVID,
    db: FilesDB,
    siegfried: Siegfried,
    paths: list[Path],
    actions: dict[str, Action],
    custom_signatures: list[CustomSignature],
    dry_run: bool,
    update: bool,
    parent: UUID | None,
    *loggers: Logger,
    ignore_lock: bool = False,
):
    if not paths:
        return
    for sf_file in siegfried.identify(*paths).files:
        identify_original_file(
            ctx,
            avid,
            db,
            sf_file,
            actions,
            custom_signatures,
            dry_run,
            update,
            parent,
            None,
            *loggers,
            ignore_lock=ignore_lock,
        )


def identify_master_file(
    ctx: Context,
    avid: AVID,
    db: FilesDB,
    siegfried_file: SiegfriedFile,
    custom_signatures: list[CustomSignature],
    actions: dict[str, MasterConvertAction],
    dry_run: bool,
    *loggers: Logger,
):
    file: MasterFile | None = db.master_files[{"relative_path": str(siegfried_file.filename.relative_to(avid.path))}]
    if not file:
        return

    new_file = MasterFile.from_file(
        siegfried_file.filename,
        avid.path,
        file.original_uuid,
        siegfried_file,
        custom_signatures,
        actions,
        file.uuid,
        file.processed,
    )

    if file.relative_path != new_file.relative_path:
        return

    if not dry_run:
        db.master_files.update(new_file)

    Event.from_command(
        ctx,
        "file",
        (file.uuid, "master"),
    ).log(
        INFO,
        *loggers,
        puid=str(new_file.puid).ljust(10),
        access=new_file.convert_access.tool if new_file.convert_access else None,
        statutory=new_file.convert_statutory.tool if new_file.convert_statutory else None,
        path=file.relative_path,
    )


def identify_converted_file(
    ctx: Context,
    avid: AVID,
    table: Table[ConvertedFile],
    file_type: Literal["access", "statutory"],
    siegfried_file: SiegfriedFile,
    dry_run: bool,
    *loggers: Logger,
):
    file: ConvertedFile | None = table[{"relative_path": str(siegfried_file.filename.relative_to(avid.path))}]
    if not file:
        return

    new_file = ConvertedFile.from_file(siegfried_file.filename, avid.path, file.original_uuid, siegfried_file)

    if file.relative_path != new_file.relative_path:
        return

    if not dry_run:
        table.update(new_file)

    Event.from_command(ctx, "file", (file.uuid, file_type)).log(
        INFO,
        *loggers,
        puid=str(new_file.puid).ljust(10),
        path=file.relative_path,
    )


@group("identify", no_args_is_help=True, short_help="Identify files.")
def grp_identify():
    """Identify files in the archive."""


@grp_identify.command("original", short_help="Identify original files.")
@argument_query(False, "uuid", ["uuid", "checksum", "puid", "relative_path", "action", "warning", "processed", "lock"])
@option(
    "--siegfried-path",
    type=ClickPath(exists=True, dir_okay=False, resolve_path=True),
    envvar="SIEGFRIED_PATH",
    default=None,
    required=False,
    show_envvar=True,
    help="The path to the Siegfried executable.",
)
@option(
    "--siegfried-home",
    type=ClickPath(exists=True, file_okay=False, resolve_path=True),
    envvar="SIEGFRIED_HOME",
    required=True,
    show_envvar=True,
    help="The path to the Siegfried home folder.",
)
@option(
    "--siegfried-signature",
    type=Choice(get_type_args(TSignaturesProvider)),
    default="pronom",
    show_default=True,
    help="The signature file to use with Siegfried.",
)
@option(
    "--actions",
    "actions_file",
    type=ClickPath(exists=True, dir_okay=False, file_okay=True, resolve_path=True),
    envvar="DIGIARCH_ACTIONS",
    show_envvar=True,
    default=None,
    help="Path to a YAML file containing file format actions.",
)
@option(
    "--custom-signatures",
    "custom_signatures_file",
    type=ClickPath(exists=True, dir_okay=False, file_okay=True, resolve_path=True),
    envvar="DIGIARCH_CUSTOM_SIGNATURES",
    show_envvar=True,
    default=None,
    help="Path to a YAML file containing custom signature specifications.",
)
@option("--exclude", type=str, multiple=True, help="File and folder names to exclude.  [multiple]")
@option("--batch-size", type=IntRange(1), default=100, show_default=True, help="Amount of files to identify at a time.")
@option("--ignore-lock", is_flag=True, default=False, show_default=True, help="Re-identify locked files.")
@option_dry_run()
@pass_context
def cmd_identify_original(
    ctx: Context,
    query: TQuery,
    siegfried_path: str | None,
    siegfried_signature: str,
    siegfried_home: str | None,
    actions_file: str | None,
    custom_signatures_file: str | None,
    exclude: tuple[str, ...],
    batch_size: int | None,
    ignore_lock: bool,
    dry_run: bool,
):
    """
    Identify files in the OriginalDocuments directory.

    Each file is identified with Siegfried and an action is assigned to it.
    Files that are already in the database are not processed.

    If the QUERY argument is given, then files in the database matching the query will be re-identified.

    For details on the QUERY argument, see the edit command.
    """
    avid = get_avid(ctx)
    siegfried, actions, custom_signatures = identify_requirements(
        "original",
        ctx,
        siegfried_path,
        siegfried_signature,
        siegfried_home,
        actions_file,
        custom_signatures_file,
    )

    with open_database(ctx, avid) as db:
        log_file, log_stdout, _ = start_program(ctx, db, __version__, None, not dry_run, True, dry_run)

        with ExceptionManager(BaseException) as exception:
            if query:
                files = find_files_query(avid, db.original_files, query, batch_size)
            else:
                files = find_files(avid.dirs.original_documents, exclude=[avid.dirs.original_documents / "_metadata"])

            while batch := list(islice(files, batch_size)):
                if exclude:
                    batch = [f for f in batch if not any(p in exclude for p in f.parts)]

                identify_original_files(
                    ctx,
                    avid,
                    db,
                    siegfried,
                    batch,
                    actions,
                    custom_signatures,
                    dry_run,
                    bool(query),
                    None,
                    log_stdout,
                    ignore_lock=ignore_lock,
                )
                if not dry_run:
                    db.commit()

        end_program(ctx, db, exception, dry_run, log_file, log_stdout)


@grp_identify.command("master", short_help="Identify master files.")
@argument_query(False, "uuid", ["uuid", "checksum", "puid", "relative_path", "action", "warning", "processed", "lock"])
@option(
    "--siegfried-path",
    type=ClickPath(exists=True, dir_okay=False, resolve_path=True),
    envvar="SIEGFRIED_PATH",
    default=None,
    required=False,
    show_envvar=True,
    help="The path to the Siegfried executable.",
)
@option(
    "--siegfried-home",
    type=ClickPath(exists=True, file_okay=False, resolve_path=True),
    envvar="SIEGFRIED_HOME",
    required=True,
    show_envvar=True,
    help="The path to the Siegfried home folder.",
)
@option(
    "--siegfried-signature",
    type=Choice(get_type_args(TSignaturesProvider)),
    default="pronom",
    show_default=True,
    help="The signature file to use with Siegfried.",
)
@option(
    "--actions",
    "actions_file",
    type=ClickPath(exists=True, dir_okay=False, file_okay=True, resolve_path=True),
    envvar="DIGIARCH_MASTER_ACTIONS",
    show_envvar=True,
    default=None,
    help="Path to a YAML file containing master files convert actions.",
)
@option(
    "--custom-signatures",
    "custom_signatures_file",
    type=ClickPath(exists=True, dir_okay=False, file_okay=True, resolve_path=True),
    envvar="DIGIARCH_CUSTOM_SIGNATURES",
    show_envvar=True,
    default=None,
    help="Path to a YAML file containing custom signature specifications.",
)
@option("--batch-size", type=IntRange(1), default=100, show_default=True, help="Amount of files to identify at a time.")
@option_dry_run()
@pass_context
def cmd_identify_master(
    ctx: Context,
    query: TQuery,
    siegfried_path: str | None,
    siegfried_signature: str,
    siegfried_home: str | None,
    actions_file: str | None,
    custom_signatures_file: str | None,
    batch_size: int | None,
    dry_run: bool,
):
    """
    Identify files in the MasterDocuments directory.

    Files are taken from the database, any other file existing in the MasterDocuments directory will be ignored.
    Each file is identified with Siegfried and convert actions for access and statutory files are assigned to it.

    If the QUERY argument is given, then only the files matching the query will be identified or re-identified.

    For details on the QUERY argument, see the edit command.
    """
    avid = get_avid(ctx)
    siegfried, actions, custom_signatures = identify_requirements(
        "master",
        ctx,
        siegfried_path,
        siegfried_signature,
        siegfried_home,
        actions_file,
        custom_signatures_file,
    )

    with open_database(ctx, avid) as db:
        log_file, log_stdout, _ = start_program(ctx, db, __version__, None, not dry_run, True, dry_run)

        with ExceptionManager(BaseException) as exception:
            files = find_files_query(avid, db.master_files, query, batch_size)

            while batch := list(islice(files, batch_size)):
                for sf_file in siegfried.identify(*batch).files:
                    identify_master_file(ctx, avid, db, sf_file, custom_signatures, actions, dry_run, log_stdout)
                if not dry_run:
                    db.commit()

        end_program(ctx, db, exception, dry_run, log_file, log_stdout)


# noinspection DuplicatedCode
@grp_identify.command("access", short_help="Identify access files.")
@argument_query(False, "uuid", ["uuid", "checksum", "puid", "relative_path", "action", "warning"])
@option(
    "--siegfried-path",
    type=ClickPath(exists=True, dir_okay=False, resolve_path=True),
    envvar="SIEGFRIED_PATH",
    default=None,
    required=False,
    show_envvar=True,
    help="The path to the Siegfried executable.",
)
@option(
    "--siegfried-home",
    type=ClickPath(exists=True, file_okay=False, resolve_path=True),
    envvar="SIEGFRIED_HOME",
    required=True,
    show_envvar=True,
    help="The path to the Siegfried home folder.",
)
@option(
    "--siegfried-signature",
    type=Choice(get_type_args(TSignaturesProvider)),
    default="pronom",
    show_default=True,
    help="The signature file to use with Siegfried.",
)
@option("--batch-size", type=IntRange(1), default=100, show_default=True, help="Amount of files to identify at a time.")
@option_dry_run()
@pass_context
def cmd_identify_access(
    ctx: Context,
    query: TQuery,
    siegfried_path: str | None,
    siegfried_signature: str,
    siegfried_home: str | None,
    batch_size: int | None,
    dry_run: bool,
):
    """
    Identify files in the AccessDocuments directory.

    Files are taken from the database, any other file existing in the AccessDocuments directory will be ignored.
    Each file is identified with Siegfried.

    If the QUERY argument is given, then only the files matching the query will be identified or re-identified.

    For details on the QUERY argument, see the edit command.
    """
    avid = get_avid(ctx)
    siegfried = Siegfried(
        siegfried_path or "sf",
        f"{siegfried_signature}.sig",
        siegfried_home,
    )

    try:
        siegfried.run("-version", "-sig", siegfried.signature)
    except IdentificationError as err:
        print(err)
        raise BadParameter("Invalid binary or signature file.", ctx, ctx_params(ctx)["siegfried_path"])

    with open_database(ctx, avid) as db:
        log_file, log_stdout, _ = start_program(ctx, db, __version__, None, not dry_run, True, dry_run)

        with ExceptionManager(BaseException) as exception:
            files = find_files_query(avid, db.access_files, query, batch_size)

            while batch := list(islice(files, batch_size)):
                for sf_file in siegfried.identify(*batch).files:
                    identify_converted_file(ctx, avid, db.access_files, "access", sf_file, dry_run, log_stdout)
                if not dry_run:
                    db.commit()

        end_program(ctx, db, exception, dry_run, log_file, log_stdout)


# noinspection DuplicatedCode
@grp_identify.command("statutory", short_help="Identify statutory files.")
@argument_query(False, "uuid", ["uuid", "checksum", "puid", "relative_path", "action", "warning"])
@option(
    "--siegfried-path",
    type=ClickPath(exists=True, dir_okay=False, resolve_path=True),
    envvar="SIEGFRIED_PATH",
    default=None,
    required=False,
    show_envvar=True,
    help="The path to the Siegfried executable.",
)
@option(
    "--siegfried-home",
    type=ClickPath(exists=True, file_okay=False, resolve_path=True),
    envvar="SIEGFRIED_HOME",
    required=True,
    show_envvar=True,
    help="The path to the Siegfried home folder.",
)
@option(
    "--siegfried-signature",
    type=Choice(get_type_args(TSignaturesProvider)),
    default="pronom",
    show_default=True,
    help="The signature file to use with Siegfried.",
)
@option("--batch-size", type=IntRange(1), default=100, show_default=True, help="Amount of files to identify at a time.")
@option_dry_run()
@pass_context
def cmd_identify_statutory(
    ctx: Context,
    query: TQuery,
    siegfried_path: str | None,
    siegfried_signature: str,
    siegfried_home: str | None,
    batch_size: int | None,
    dry_run: bool,
):
    """
    Identify files in the Documents directory.

    Files are taken from the database, any other file existing in the Documents directory will be ignored.
    Each file is identified with Siegfried.

    If the QUERY argument is given, then only the files matching the query will be identified or re-identified.

    For details on the QUERY argument, see the edit command.
    """
    avid = get_avid(ctx)
    siegfried = Siegfried(
        siegfried_path or "sf",
        f"{siegfried_signature}.sig",
        siegfried_home,
    )

    try:
        siegfried.run("-version", "-sig", siegfried.signature)
    except IdentificationError as err:
        print(err)
        raise BadParameter("Invalid binary or signature file.", ctx, ctx_params(ctx)["siegfried_path"])

    with open_database(ctx, avid) as db:
        log_file, log_stdout, _ = start_program(ctx, db, __version__, None, not dry_run, True, dry_run)

        with ExceptionManager(BaseException) as exception:
            files = find_files_query(avid, db.statutory_files, query, batch_size)

            while batch := list(islice(files, batch_size)):
                for sf_file in siegfried.identify(*batch).files:
                    identify_converted_file(ctx, avid, db.statutory_files, "statutory", sf_file, dry_run, log_stdout)
                if not dry_run:
                    db.commit()

        end_program(ctx, db, exception, dry_run, log_file, log_stdout)


grp_identify.list_commands = lambda _ctx: list(grp_identify.commands)
