"""This module implements checksum generation and duplicate detection.

"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import hashlib
from multiprocessing import Pool
from collections import Counter
from pathlib import Path
from typing import List, Set, Dict, ItemsView, Any, Optional
from tqdm import tqdm
from digiarch.internals import FileInfo, to_json, natsort_path

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

    Returns
    -------
    str
        The hex checksum of the input file.

    """

    checksum: str = ""
    hasher: Any = hashlib.blake2b()

    if file.is_file():
        with file.open("rb") as f:
            hasher.update(f.read())
            checksum = hasher.hexdigest()

    return checksum


def checksum_worker(file_info: FileInfo) -> FileInfo:
    """Worker used when multiprocessing checksums of FileInfo objects.

    Parameters
    ----------
    fileinfo : FileInfo
        The FileInfo object that must be updated with a new checksum value.

    Returns
    -------
    FileInfo
        The FileInfo object with an updated checksum value.
    """

    checksum: Optional[str] = file_checksum(file_info.path) or None
    updated_file_info: FileInfo = file_info.replace(checksum=checksum)
    return updated_file_info


def generate_checksums(files: List[FileInfo]) -> List[FileInfo]:
    """Multiprocesses a list of FileInfo object in order to assign
    new checksums.

    Parameters
    ----------
    files : List[FileInfo]
        List of FileInfo objects that need checksums.

    Returns
    -------
    List[FileInfo]
        The updated list of FileInfo objects.
    """

    # Assign variables
    updated_files: List[FileInfo] = []

    # Multiprocess checksum generation
    pool = Pool()
    try:
        updated_files = list(
            tqdm(
                pool.imap_unordered(checksum_worker, files),
                desc="Generating checksums",
                unit=" files",
                total=len(files),
            )
        )
    finally:
        pool.close()
        pool.join()

    return natsort_path(updated_files)


def check_collisions(checksums: List[str]) -> Set[str]:
    """Checks checksum collisions given a list of checksums as strings.
    Returns a set of collisions if any such are found.

    Parameters
    ----------
    checksums : List[str]
        List of checksums that must be checked for collisions.

    Returns
    -------
    Set[str]
        A set of colliding checksums. Empty if none are found.
    """
    checksum_counts: ItemsView[str, int] = Counter(checksums).items()
    collisions: Set[str] = set()

    for checksum, count in checksum_counts:
        if count > 1:
            # We have a collision, boys
            collisions.add(checksum)

    return collisions


def check_duplicates(files: List[FileInfo], save_path: Path) -> None:
    """Generates a file with checksum collisions, indicating that duplicates
    are present.

    Parameters
    ----------
    files : List[FileInfo]
        Files for which duplicates should be checked.
    save_path : Path
        Path to which the checksum collision information should be saved.
    """

    # Initialise variables
    checksums: List[str] = [
        file.checksum for file in files if file.checksum is not None
    ]
    collisions: Set[str] = check_collisions(checksums)
    file_collisions: Dict[str, str] = dict()

    for checksum in tqdm(collisions, desc="Finding duplicates"):
        hits = [
            {"name": file.name, "path": file.path}
            for file in files
            if file.checksum == checksum
        ]
        file_collisions.update({checksum: hits})

    dups_file = Path(save_path).joinpath("duplicate_files.json")
    to_json(file_collisions, dups_file)
