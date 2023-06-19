"""This module implements checksum generation and duplicate detection."""
# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import hashlib
import os
from collections import Counter
from collections.abc import ItemsView
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Optional

from tqdm import tqdm

from digiarch.core.ArchiveFileRel import ArchiveFile
from digiarch.core.utils import natsort_path

# -----------------------------------------------------------------------------
# Function Definitions
# -----------------------------------------------------------------------------


def file_checksum(file: Path) -> str:
    """Calculate the checksum of an input file using BLAKE2.

    Parameters
    ----------
    file : Path
        The file for which to calculate the checksum. Expects a `pathlib.Path`
        object.

    Returns:
    -------
    str
        The hex checksum of the input file.

    """
    checksum: str = ""
    hasher: Any = hashlib.sha256()

    if file.is_file():
        with file.open("rb") as f:
            hasher.update(f.read())
            checksum = hasher.hexdigest()

    return checksum  # noqa: RET504


def checksum_worker(file_info: ArchiveFile) -> ArchiveFile:
    """Worker used when multiprocessing checksums of FileInfo objects.

    Parameters
    ----------
    fileinfo : ArchiveFile
        The FileInfo object that must be updated with a new checksum value.

    Returns:
    -------
    FileInfo
        The FileInfo object with an updated checksum value.
    """
    checksum: Optional[str] = (
        file_checksum(Path(os.environ["ROOTPATH"], file_info.relative_path)) or None
    )
    updated_file_info: ArchiveFile = file_info.copy(update={"checksum": checksum})
    return updated_file_info


def generate_checksums(files: list[ArchiveFile]) -> list[ArchiveFile]:
    """Multiprocesses a list of FileInfo object in order to assign new checksums.

    Parameters
    ----------
    files : List[FileInfo]
        List of FileInfo objects that need checksums.

    Returns:
    -------
    List[FileInfo]
        The updated list of FileInfo objects.
    """
    # Assign variables
    updated_files: list[ArchiveFile] = []

    # Multiprocess checksum generation
    pool = Pool()
    try:
        updated_files = list(
            tqdm(
                pool.imap_unordered(checksum_worker, files),
                desc="Generating checksums",
                unit=" files",
                total=len(files),
            ),
        )
    except (KeyboardInterrupt, Exception):
        pool.terminate()
        raise
    finally:
        pool.close()
        pool.join()

    return natsort_path(updated_files)


def check_collisions(checksums: list[str]) -> set[str]:
    """Checks checksum collisions given a list of checksums as strings.

    Returns a set of collisions if any such are found.

    Parameters
    ----------
    checksums : List[str]
        List of checksums that must be checked for collisions.

    Returns:
    -------
    Set[str]
        A set of colliding checksums. Empty if none are found.
    """
    checksum_counts: ItemsView[str, int] = Counter(checksums).items()
    collisions: set[str] = set()

    for checksum, count in checksum_counts:
        if count > 1:
            # We have a collision, boys
            collisions.add(checksum)

    return collisions


# def check_duplicates(files: List[ArchiveFile], save_path: Path) -> None:
#     """Generates a file with checksum collisions, indicating that duplicates
#     are present.

#     Parameters
#     ----------
#     files : List[FileInfo]
#         Files for which duplicates should be checked.
#     save_path : Path
#         Path to which the checksum collision information should be saved.
#     """

#     # Initialise variables
#     checksums: List[str] = [
#         file.checksum for file in files if file.checksum is not None
#     ]
#     collisions: Set[str] = check_collisions(checksums)
#     file_collisions: Dict[str, str] = dict()

#     for checksum in tqdm(collisions, desc="Finding duplicates"):
#         hits = [
#             {"name": file.name(), "path": file.path}
#             for file in files
#             if file.checksum == checksum
#         ]
#         file_collisions.update({checksum: hits})

#     dups_file = save_path / "duplicate_files.json"
#     to_json(file_collisions, dups_file)
