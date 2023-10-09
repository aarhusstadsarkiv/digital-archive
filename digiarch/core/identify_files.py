"""Identify files using siegfried <https://github.com/richardlehane/siegfried>`."""
import json
import os
import re
import subprocess
import warnings
from functools import partial
from logging import Logger
from multiprocessing import Pool
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import PIL
from acamodels import Identification
from PIL import Image

from digiarch.core.ArchiveFileRel import ArchiveFile
from digiarch.core.utils import costum_sigs, natsort_path, to_re_identify
from digiarch.exceptions import IdentificationError

warnings.filterwarnings("error", category=Image.DecompressionBombWarning)


# formats that we test against our own formats, no matter that Siegfried
# already identified them.
RERUN_FORMATS = to_re_identify()
SIZE_OF_KILO_BYTE = 1024


def update_file_id(path: Path, file_id: Identification, signature: dict[str, str]) -> None:
    file_id.puid = signature["puid"]
    file_id.signature = signature["signature"]
    if path.suffix.lower() != signature["extension"].lower():
        file_id.warning = "Extension mismatch"
    else:
        file_id.warning = None


def custom_id(path: Path, file_id: Identification) -> Identification:
    signatures: list[dict] = costum_sigs()

    with path.open("rb") as file_bytes:
        # BOF
        bof = file_bytes.read(SIZE_OF_KILO_BYTE * 2).hex()
        # Navigate to EOF
        try:
            file_bytes.seek(-1024, 2)
        except OSError:
            # File too small :)
            file_bytes.seek(-file_bytes.tell(), 2)
        eof = file_bytes.read(SIZE_OF_KILO_BYTE).hex()

    for sig in signatures:
        if "bof" in sig and "eof" in sig:
            bof_pattern = re.compile(sig["bof"])
            eof_pattern = re.compile(sig["eof"])
            if sig["operator"] == "OR":
                if bof_pattern.search(bof) or eof_pattern.search(eof):
                    update_file_id(path, file_id, sig)
                    break
            elif sig["operator"] == "AND" and bof_pattern.search(bof) and eof_pattern.search(eof):
                update_file_id(path, file_id, sig)
                break
        elif "bof" in sig:
            bof_pattern = re.compile(sig["bof"])
            if bof_pattern.search(bof):
                update_file_id(path, file_id, sig)
                break
        elif "eof" in sig:
            eof_pattern = re.compile(sig["eof"])
            if eof_pattern.search(eof):
                update_file_id(path, file_id, sig)
                break
    return file_id


def sf_id(path: Path, log: Optional[Logger] = None) -> dict[Path, Identification]:
    """Identify files using `siegfried <https://github.com/richardlehane/siegfried>`.

    Also updates FileInfo with obtained PUID, signature name, and warning if applicable.

    Parameters
    ----------
    path : pathlib.Path
        Path in which to identify files.

    Returns:
    -------
    Dict[Path, Identification]
        Dictionary containing file path and associated identification
        information obtained from siegfried's stdout.

    Raises:
    ------
    IdentificationError
        While siegfried or loading of the resulting JSON output fails,
        an IdentificationError is thrown.
    """
    id_dict: dict[Path, Identification] = {}

    try:
        sf_proc = subprocess.run(
            ["sf", "-json", "-multi", "1024", str(path)],
            check=True,
            capture_output=True,
        )
    except Exception as error:
        raise IdentificationError(error)

    try:
        id_result = json.loads(sf_proc.stdout)
    except Exception as error:
        raise IdentificationError(error)

    # We get identifiers as a list containing the ditionary,
    # soo we have to get the one element our of it
    results_dict: Optional[dict] = id_result.get("identifiers", None)[0]
    if results_dict and log:
        DROID_file_version: Optional[str] = results_dict.get("details")
        log.info(
            "Running sf with the following version of DROID: " + DROID_file_version
            if DROID_file_version
            else ""
        )
    for file_result in id_result.get("files", []):
        match: dict[str, Any] = {}
        for id_match in file_result.get("matches"):
            if id_match.get("ns") == "pronom":
                match = id_match
        if match:
            file_identification: Identification
            file_path: Path = Path(file_result["filename"])

            puid = None if match.get("id", "").lower() == "unknown" else match.get("id")

            signature_and_version = None
            signature = match.get("format")
            version = match.get("version")
            if signature:
                signature_and_version = f"{signature} ({version})"
            warning: str = match.get("warning", "").capitalize()
            file_size: int = file_result.get("filesize")
            file_errors: Optional[str] = file_result.get("errors", None)
            if file_errors:
                warning = warning + " ; Errors: " + file_errors
            file_identification = Identification(
                puid=puid,
                signature=signature_and_version or None,
                warning=warning or None,
                size=file_size,
            )

            # unindentified files
            if puid is None:
                file_identification = custom_id(file_path, file_identification)

            # re-identify files, warnings or not!
            if puid in RERUN_FORMATS:
                file_identification = custom_id(file_path, file_identification)

            # Possible MS Office files identified as markup (XML, HTML etc.)
            if (
                puid in ["fmt/96", "fmt/101", "fmt/583", "x-fmt/263"]
                and "Extension mismatch" in warning
            ):
                file_identification = custom_id(file_path, file_identification)

            id_dict.update({file_path: file_identification})

    return id_dict


def is_binary(file: ArchiveFile) -> bool:
    """Check if a ArchiveFile is binary.

    Description:
    ----------------
    Checks if an ArchiveFile is a txt file or binary.
    This is done by looking for the null byte
    (text files wont include null bytes, since they are null terminated,
    i.e. the text in the text file stops at the null byte).
    We also check if the hexadecimal pdf signature is in the file
    since some pdf files might not include the null byte.
    """
    pdf_signature = "25504446"
    word_markup_puid = "aca-fmt/2"
    bytes_of_file = file.read_bytes()

    if b"\x00" in bytes_of_file or (pdf_signature in bytes_of_file.hex()):
        return True
    return str(file.puid) == word_markup_puid


def is_preservable(file: ArchiveFile, log: Logger) -> tuple[bool, Any]:
    lock: Lock = Lock()  # Used by image_is_preservable
    image_format_codes = [
        "fmt/3",
        "fmt/4",
        "fmt/11",
        "fmt/13",
        "fmt/41",
        "fmt/42",
        "fmt/43",
        "fmt/44",
        "fmt/115",
        "fmt/116",
        "fmt/124",
        "fmt/353",
        "fmt/645",
        "x-fmt/390",
        "x-fmt/391",
    ]
    if file.puid in image_format_codes:
        if image_is_preservable(file, lock, log):
            return (True, None)
        else:
            return (False, "Image contains less than 20000 pixels.")
    elif file.is_binary:
        if file.size_as_int() > 1024:
            return (True, None)
        else:
            return (False, "Binary file is less than 1 kb.")
    else:
        return (True, None)


def get_pixel_amount(file_path: Path) -> int:
    with Image.open(file_path) as im:
        width, height = im.size
        pixelAmount: int = width * height
        return pixelAmount


def check_if_preservable(file_path: Path) -> bool:
    pixel_amount = get_pixel_amount(file_path)
    return pixel_amount > 20000


def image_is_preservable(file: ArchiveFile, lock: Lock, logger: Logger) -> bool:

    lock.acquire()
    result: bool = False

    if "ROOTPATH" in os.environ:
        file_path: Path = Path(os.environ["ROOTPATH"], file.relative_path)
    else:
        file_path = file.relative_path
    try:
        result = check_if_preservable(file_path)
    except PIL.UnidentifiedImageError:
        print(f"PIL could not open the file: {file.relative_path}")
        result = True
    except Image.DecompressionBombWarning:
        logger.warning(f"The file {file.relative_path} threw a decompresionbomb warning")
        result = True
    except Image.DecompressionBombError:
        logger.error(f"The file {file.relative_path} threw a decompresionbomb error")
        result = True
    finally:
        lock.release()
        return result


def update_file_info(file_info: ArchiveFile, id_info: dict[Path, Identification]) -> ArchiveFile:
    no_id: Identification = Identification(
        puid=None,
        signature=None,
        warning="No identification information obtained.",
    )
    file_path = Path(os.environ["ROOTPATH"], file_info.relative_path)
    new_id: Identification = id_info.get(file_path) or no_id
    file_size = new_id.size

    if file_size == 0:
        new_id = Identification(
            puid="aca-error/1",
            signature="Empty file",
            warning="Error: File is empty",
        )
    file_info = file_info.copy(update=new_id.dict())
    file_info.is_binary = is_binary(file_info)
    file_info.size = file_size
    return file_info


def identify(
    files: list[ArchiveFile], path: Path, log: Optional[Logger] = None
) -> list[ArchiveFile]:
    """Identify all files in a list, and return the updated list.

    Args:
        files (list[ArchiveFile]): Files to identify
        path (Path): _description_
        log (Logger): Log to be used to write to. If none is given, nothing is added to the log.

    Returns:
        list[ArchiveFile]: Input files with updated Identification information.
    """
    id_info: dict[Path, Identification] = sf_id(path, log)
    # functools.partial: Return a new partial object
    # which when called will behave like func called with the
    # positional arguments args and keyword arguments keywords.

    # Create a partial function of update_file_info
    # so that we can use map on it.
    # map cannot be used on update_file_info itself since id_info
    # can be shorter than files.
    _update = partial(update_file_info, id_info=id_info)
    with Pool(5) as p:
        updated_files: list[ArchiveFile] = p.map(_update, files, 10000)

    return natsort_path(updated_files)
