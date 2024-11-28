from logging import ERROR
from logging import INFO
from logging import Logger
from os import PathLike
from pathlib import Path
from sqlite3 import connect
from sqlite3 import Connection
from sqlite3 import Row

from acacore.database import FilesDB
from acacore.database.upgrade import is_latest
from acacore.models.event import Event
from acacore.models.file import MasterFile
from acacore.models.file import OriginalFile
from acacore.utils.click import ctx_params
from acacore.utils.click import end_program
from acacore.utils.click import start_program
from acacore.utils.helpers import ExceptionManager
from click import argument
from click import BadParameter
from click import command
from click import Context
from click import option
from click import Parameter
from click import pass_context
from click import Path as ClickPath
from orjson import loads

from digiarch.__version__ import __version__
from digiarch.common import AVID


def root_callback(ctx: Context, param: Parameter, value: str) -> AVID:
    if not AVID.is_avid_dir(value):
        raise BadParameter(f"{value!r} is not a valid AVID directory.", ctx, param)
    return AVID(value)


def import_original_file(avid: AVID, file: Row) -> tuple[OriginalFile, list[MasterFile], list[str]]:
    original_file: OriginalFile = OriginalFile.from_file(
        avid.dirs.original_documents.joinpath(file["relative_path"]),
        avid.path,
        uuid=file["uuid"],
        parent=file["parent"],
        processed=bool(file["processed"]),
        lock=bool(file["lock"]),
    )
    original_file.puid = file["puid"]
    original_file.signature = file["signature"]
    original_file.warning = loads(file["warning"]) if file["warning"] else None
    original_file.action = file["action"]
    original_file.action_data = loads(file["action_data"])
    original_file.original_path = avid.dirs.original_documents.joinpath(file["original_path"]).relative_to(avid.path)

    master_file_paths: list[Path] = [
        avid.dirs.master_documents.joinpath(file["relative_path"]).with_name(n) for n in loads(file["processed_names"])
    ]
    missing_master_files: list[str] = [f.name for f in master_file_paths if not f.is_file()]
    master_files: list[MasterFile] = [
        MasterFile.from_file(f, avid.path, original_file.uuid)
        for f in master_file_paths
        if f.name not in missing_master_files
    ]
    original_file.processed = original_file.processed and not missing_master_files

    return original_file, master_files, missing_master_files


def import_original_files(
    ctx: Context,
    avid: AVID,
    db: FilesDB,
    db_old: Connection,
    *loggers: Logger,
) -> tuple[int, int, int]:
    original_files_cur = db_old.execute("select * from Files")
    original_files_cur.row_factory = Row

    total_imported_original_files: int = 0
    total_imported_master_files: int = 0
    total_missing_master_files: int = 0

    for original_file_row in original_files_cur:
        original_file, master_files, missing_master_files = import_original_file(avid, original_file_row)
        db.original_files.insert(original_file)
        if master_files:
            db.master_files.insert(*master_files)
        Event.from_command(
            ctx,
            "imported",
            (original_file.uuid, "original"),
        ).log(INFO, *loggers, path=original_file.relative_path)
        for master_file in master_files:
            Event.from_command(
                ctx,
                "imported",
                (master_file.uuid, "master"),
            ).log(INFO, *loggers, path=master_file.relative_path)
        for missing_master_file in missing_master_files:
            Event.from_command(ctx, "missing-master", (original_file.uuid, "original")).log(
                ERROR,
                *loggers,
                name=missing_master_file,
            )
        total_imported_original_files += 1
        total_imported_master_files += len(master_files)
        total_missing_master_files += len(missing_master_files)

    return total_imported_original_files, total_imported_master_files, total_missing_master_files


def import_db(
    ctx: Context,
    avid: AVID,
    db: FilesDB,
    import_db_path: str | PathLike,
    *loggers: Logger,
):
    db_old = connect(import_db_path)

    Event.from_command(ctx, "import:start").log(INFO, *loggers)
    new_original_files, new_master_files, missing_master_files = import_original_files(ctx, avid, db, db_old, *loggers)
    Event.from_command(ctx, "import:end").log(
        INFO,
        *loggers,
        original_files=new_original_files,
        master_files=new_master_files,
        missing_master_files=missing_master_files,
    )

    db.log.insert(
        Event.from_command(
            ctx,
            "import",
            None,
            {
                "original_files": new_original_files,
                "master_files": new_master_files,
                "missing_master_files": missing_master_files,
            },
        )
    )
    db.commit()


def check_import_db(ctx: Context, import_db_path: str | PathLike, import_param_name: str):
    db_old: Connection | None = None

    try:
        db_old = connect(import_db_path)

        tables: list[str] = [t.lower() for [t] in db_old.execute("select name from sqlite_master where type = 'table'")]
        if "files" not in tables or "metadata" not in tables:
            raise BadParameter("Invalid database schema.", ctx, ctx_params(ctx)[import_param_name])

        version = db_old.execute("select value from Metadata where key = 'version'").fetchone()
        if not version:
            raise BadParameter("No version information.", ctx, ctx_params(ctx)[import_param_name])
        if version[0] != "3.3.3":
            raise BadParameter(f"Invalid version {version[0]}, must be 3.3.3.", ctx, ctx_params(ctx)[import_param_name])
    finally:
        if db_old:
            db_old.close()


@command("init", no_args_is_help=True, short_help="Initialize the database.")
@argument(
    "avid",
    metavar="AVID_DIR",
    type=ClickPath(exists=True, file_okay=False, writable=True, readable=True, resolve_path=True),
    default=None,
    required=True,
    callback=root_callback,
)
@option(
    "--import",
    "import_db_path",
    type=ClickPath(exists=True, dir_okay=False, readable=True, resolve_path=True),
    default=None,
    required=False,
    help="Import an existing files.db",
)
@pass_context
def cmd_init(ctx: Context, avid: AVID, import_db_path: str | None):
    avid.database_path.parent.mkdir(parents=True, exist_ok=True)

    if import_db_path:
        check_import_db(ctx, import_db_path, "import_db_path")

    with FilesDB(avid.database_path, check_initialisation=False, check_version=False) as db:
        _, log_stdout, event_start = start_program(ctx, db, __version__, None, False, True, True)
        initialized: bool = False

        with ExceptionManager(BaseException) as exception:
            if db.is_initialised():
                is_latest(db.connection, raise_on_difference=True)
                Event.from_command(ctx, "initialized", data=db.version()).log(INFO, log_stdout)
            else:
                db.init()
                db.log.insert(event_start)
                db.commit()

                if avid.dirs.documents.exists() and not avid.dirs.original_documents.exists():
                    avid.dirs.documents.rename(avid.dirs.original_documents)
                    Event.from_command(ctx, "rename", data=["Documents", "OriginalDocuments"]).log(INFO, log_stdout)

                initialized = True
                event = Event.from_command(ctx, "initialized", data=(v := db.version()))
                db.log.insert(event)
                event.log(INFO, log_stdout, show_args=False, version=v)

            if initialized and import_db_path:
                import_db(ctx, avid, db, import_db_path, log_stdout)

        end_program(ctx, db, exception, not initialized, log_stdout)

    if initialized and exception.exception:
        avid.database_path.unlink(missing_ok=True)
