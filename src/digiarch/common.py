from collections.abc import Callable
from functools import reduce
from hashlib import sha256
from os import PathLike
from pathlib import Path
from re import match
from sqlite3 import DatabaseError
from tempfile import TemporaryDirectory
from typing import TypeVar

import yaml
from acacore.database import FilesDB
from acacore.models.event import Event
from acacore.models.file import BaseFile
from acacore.models.reference_files import Action
from acacore.models.reference_files import CustomSignature
from acacore.models.reference_files import MasterConvertAction
from acacore.reference_files import get_actions
from acacore.reference_files import get_custom_signatures
from acacore.reference_files import get_master_actions
from acacore.utils.click import ctx_params
from acacore.utils.functions import is_valid_suffix
from click import BadParameter
from click import Command
from click import Context
from click import Group
from click import option
from click import UsageError
from pydantic import TypeAdapter

_invalid_characters: str = '\\/%&${}[]<>*?":|' + bytes(range(32)).decode("ascii") + "\x7f"
T = TypeVar("T")


# noinspection PyPep8Naming
class AVIDIndices:
    def __init__(self, avid_dir: Path) -> None:
        self.avid_dir = avid_dir

    @property
    def path(self):
        return self.avid_dir / "Indices"

    @property
    def archiveIndex(self) -> Path:
        """Indices/archiveIndex.xml"""
        return self.path / "archiveIndex.xml"

    @property
    def contextDocumentationIndex(self) -> Path:
        """Indices/contextDocumentationIndex.xml"""
        return self.path / "contextDocumentationIndex.xml"

    @property
    def docIndex(self) -> Path:
        """Indices/docIndex.xml"""
        return self.path / "docIndex.xml"

    @property
    def fileIndex(self) -> Path:
        """Indices/fileIndex.xml"""
        return self.path / "fileIndex.xml"

    @property
    def tableIndex(self) -> Path:
        """Indices/tableIndex.xml"""
        return self.path / "tableIndex.xml"


# noinspection PyPep8Naming
class AVIDSchemas:
    def __init__(self, avid_dir: Path) -> None:
        self.avid_dir: Path = avid_dir

    @property
    def path(self):
        return self.avid_dir / "Schemas"

    @property
    def archiveIndex(self) -> Path:
        """Schemas/standard/archiveIndex.xsd"""
        return self.path / "standard" / "archiveIndex.xsd"

    @property
    def contextDocumentationIndex(self) -> Path:
        """Schemas/standard/contextDocumentationIndex.xsd"""
        return self.path / "standard" / "contextDocumentationIndex.xsd"

    @property
    def docIndex(self) -> Path:
        """Schemas/standard/docIndex.xsd"""
        return self.path / "standard" / "docIndex.xsd"

    @property
    def fileIndex(self) -> Path:
        """Schemas/standard/fileIndex.xsd"""
        return self.path / "standard" / "fileIndex.xsd"

    @property
    def researchIndex(self) -> Path:
        """Schemas/standard/researchIndex.xsd"""
        return self.path / "standard" / "researchIndex.xsd"

    @property
    def tableIndex(self) -> Path:
        """Schemas/standard/tableIndex.xsd"""
        return self.path / "standard" / "tableIndex.xsd"

    @property
    def XMLSchema(self) -> Path:
        """Schemas/standard/XMLSchema.xsd"""
        return self.path / "standard" / "XMLSchema.xsd"

    @property
    def tables(self) -> dict[int, Path]:
        """Tables/tableN/tableN.xsd"""
        return {
            int(f.name.removeprefix("table")): f.joinpath(f.name).with_suffix(".xsd")
            for f in self.avid_dir.joinpath("Tables").iterdir()
            if f.is_dir() and match(r"table\d+", f.name)
        }


class AVIDDirs:
    def __init__(self, avid_dir: Path) -> None:
        self.dir: Path = avid_dir

    @property
    def original_documents(self):
        return self.dir / "OriginalDocuments"

    @property
    def master_documents(self):
        return self.dir / "MasterDocuments"

    @property
    def access_documents(self):
        return self.dir / "AccessDocuments"

    @property
    def documents(self):
        return self.dir / "Documents"

    @property
    def indices(self) -> AVIDIndices:
        """Indices"""
        return AVIDIndices(self.dir)

    @property
    def schemas(self) -> AVIDSchemas:
        """Schemas"""
        return AVIDSchemas(self.dir)

    @property
    def tables(self) -> dict[int, Path]:
        """Tables"""
        return {
            int(f.name.removeprefix("table")): f.joinpath(f.name).with_suffix(".xml")
            for f in self.dir.joinpath("Tables").iterdir()
            if f.is_dir() and match(r"table\d+", f.name)
        }


class AVID:
    def __init__(self, directory: str | PathLike) -> None:
        if not self.is_avid_dir(directory):
            raise ValueError(f"{directory} is not a valid AVID directory")

        self.path: Path = Path(directory).resolve()
        self.dirs: AVIDDirs = AVIDDirs(self.path)

    def __str__(self) -> str:
        return str(self.path)

    @classmethod
    def is_avid_dir(cls, directory: str | PathLike[str]) -> bool:
        directory = Path(directory)
        if not directory.is_dir():
            return False
        if not (avid_dirs := AVIDDirs(directory)).indices.path.is_dir():
            return False
        if not avid_dirs.schemas.path.is_dir():
            return False
        if not avid_dirs.original_documents.is_dir() and not avid_dirs.documents.is_dir():  # noqa: SIM103
            return False
        return True

    @classmethod
    def find_database_root(cls, directory: str | PathLike[str]) -> Path | None:
        directory = Path(directory)
        if directory.joinpath("_metadata", "avid.db").is_file():
            return directory
        if directory.parent != directory:
            return cls.find_database_root(directory.parent)
        return None

    @property
    def metadata_dir(self):
        return self.path / "_metadata"

    @property
    def database_path(self):
        return self.metadata_dir / "avid.db"


class TempDir(TemporaryDirectory):
    prefix: str = ".tmp_digiarch_"

    def __init__(self, parent_dir: str | PathLike) -> None:
        super().__init__(dir=parent_dir, prefix=self.prefix)

    def __enter__(self) -> Path:
        return Path(self.name)


_RH = Callable[[Context, AVID, FilesDB, Event, BaseFile | None], list[Event] | None]


class CommandWithRollback(Command):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rollback: dict[str, _RH] = {}


def rollback(operation: str, handler: _RH) -> Callable[[CommandWithRollback], CommandWithRollback]:
    def inner(cmd: CommandWithRollback) -> CommandWithRollback:
        cmd.rollback[operation] = handler
        return cmd

    return inner


def find_rollback_handlers(app: Command) -> dict[str, Callable]:
    handlers: dict[str, _RH] = {}

    if isinstance(app, Group):
        for name, cmd in app.commands.items():
            handlers |= {f"{app.name}.{n}": h for n, h in find_rollback_handlers(cmd).items()}
    elif isinstance(app, CommandWithRollback):
        handlers |= {f"{app.name}:{op}": h for op, h in app.rollback.items()}

    return handlers


def get_avid(ctx: Context, path: str | PathLike[str] | None = None) -> AVID:
    if path is None and (path := AVID.find_database_root(Path.cwd())) is None:
        raise UsageError(f"No AVID directory found in path {str(Path.cwd())!r}.", ctx)
    if not AVID.is_avid_dir(path):
        raise UsageError(f"Not a valid AVID directory {str(path)!r}.", ctx)
    if not (avid := AVID(path)).database_path.is_file():
        raise UsageError(f"No {avid.database_path.relative_to(avid.path)} present in {str(path)!r}.", ctx)
    return avid


def option_dry_run():
    return option("--dry-run", is_flag=True, default=False, help="Show changes without committing them.")


def open_database(ctx: Context, avid: AVID) -> FilesDB:
    try:
        return FilesDB(avid.database_path, check_initialisation=True, check_version=True)
    except DatabaseError as e:
        raise UsageError(e.args[0], ctx)


def trim_stem(name: str, length: int):
    name_path: Path = Path(name)
    suffixes: str = ""
    for suffix in name_path.suffixes[::-1]:
        if is_valid_suffix(suffix):
            suffixes = suffix + suffixes
        else:
            break
    new_stem: str = name.removesuffix(suffixes)
    trim_length: int = length - len(new_stem)
    return (new_stem[: length - len(suffixes)] if trim_length > 0 else "_") + suffixes


def sanitize_filename(name: str, max_length: int | None = None, unique_trim_prefix: bool = False) -> str:
    new_name: str = reduce(lambda acc, cur: acc.replace(cur, "_"), _invalid_characters, name.strip().replace("/", "_"))
    if max_length and 0 < max_length < len(new_name):
        if unique_trim_prefix:
            new_name = trim_stem(new_name, max_length - 7)
            new_name = sha256(name.encode()).hexdigest()[:7] + (
                new_name if not new_name.startswith("_.") else new_name[1:]
            )
        else:
            new_name = trim_stem(new_name, max_length)
    return new_name


def sanitize_path(path: str | PathLike) -> Path:
    return Path(*[sanitize_filename(p) for p in Path(path).parts])


def fetch_reference_files(
    ctx: Context,
    adapter: type[T],
    file: str | PathLike | None,
    fetcher: Callable[[], T],
    parameter: str,
) -> T:
    if file:
        try:
            data = yaml.load(Path(file).read_text(), yaml.Loader)
        except BaseException:
            raise BadParameter(f"Cannot load file {file}.", ctx, ctx_params(ctx)[parameter])
    else:
        try:
            data = fetcher()
        except BaseException:
            raise BadParameter("Cannot fetch file.", ctx, ctx_params(ctx)[parameter])

    try:
        return TypeAdapter(adapter).validate_python(data)
    except BaseException as err:
        raise BadParameter(f"Invalid data. {''.join(err.args[:1])}", ctx, ctx_params(ctx)[parameter])


def fetch_actions(ctx: Context, parameter: str, file: str | PathLike | None) -> dict[str, Action]:
    return fetch_reference_files(ctx, dict[str, Action], file, get_actions, parameter)


def fetch_actions_master(ctx: Context, parameter: str, file: str | PathLike | None) -> dict[str, MasterConvertAction]:
    return fetch_reference_files(ctx, dict[str, MasterConvertAction], file, get_master_actions, parameter)


def fetch_custom_signatures(ctx: Context, parameter: str, file: str | PathLike | None) -> list[CustomSignature]:
    return fetch_reference_files(ctx, list[CustomSignature], file, get_custom_signatures, parameter)
