"""Identify files using
`siegfried <https://github.com/richardlehane/siegfried>`
"""
import json
import re
import subprocess
import os
import warnings
import logging as log
from logging import Logger
from functools import partial
from pathlib import Path
from threading import Lock
import PIL
from PIL import Image
from typing import Any, Tuple
from typing import Dict
from typing import List
from multiprocessing import Pool

from acamodels import Identification

from digiarch.core.ArchiveFileRel import ArchiveFile
from digiarch.core.utils import natsort_path
from digiarch.exceptions import IdentificationError


warnings.filterwarnings("error", category=Image.DecompressionBombWarning)


# formats that we test against our own formats, no matter that Siegfried
# already identified them.
RERUN_FORMATS = [
    "fmt/111",  # why do we re-run these?
    "x-fmt/111",  # .TAB-files related to GIS is identified as plaintext
    "fmt/1600",  # Both fmt/1600 and fmt/1630 identify .dat-files in extension
    "fmt/1730",  # only, which is a bad idea. They are sometimes winmail.dat
]
SIZE_OF_KILO_BYTE = 1024


def update_file_id(
    path: Path, file_id: Identification, signature: Dict[str, str]
) -> None:
    file_id.puid = signature["puid"]
    file_id.signature = signature["signature"]
    if path.suffix.lower() != signature["extension"].lower():
        file_id.warning = "Extension mismatch"
    else:
        file_id.warning = None


def custom_id(path: Path, file_id: Identification) -> Identification:
    sig_file = Path(__file__).parent / "custom_sigs.json"
    signatures: List[Dict] = json.load(sig_file.open(encoding="utf-8"))

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
            elif sig["operator"] == "AND":
                if bof_pattern.search(bof) and eof_pattern.search(eof):
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


def sf_id(path: Path) -> Dict[Path, Identification]:
    """Identify files using
    `siegfried <https://github.com/richardlehane/siegfried>`_ and update
    FileInfo with obtained PUID, signature name, and warning if applicable.

    Parameters
    ----------
    path : pathlib.Path
        Path in which to identify files.

    Returns
    -------
    Dict[Path, Identification]
        Dictionary containing file path and associated identification
        information obtained from siegfried's stdout.

    Raises
    ------
    IdentificationError
        If running siegfried or loading of the resulting JSON output fails,
        an IdentificationError is thrown.
    """

    id_dict: Dict[Path, Identification] = {}

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

    for file_result in id_result.get("files", []):
        match: Dict[str, Any] = {}
        for id_match in file_result.get("matches"):
            if id_match.get("ns") == "pronom":
                match = id_match
        if match:
            file_identification: Identification
            file_path: Path = Path(file_result["filename"])

            if match.get("id", "").lower() == "unknown":
                puid = None
            else:
                puid = match.get("id")

            signature_and_version = None
            signature = match.get("format")
            version = match["version"]
            if signature:
                signature_and_version = f"{signature} ({version})"
            warning = match.get("warning", "").capitalize()
            file_identification = Identification(
                puid=puid,
                signature=signature_and_version or None,
                warning=warning or None,
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
    """
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

    if b"\x00" in bytes_of_file:
        return True
    elif pdf_signature in bytes_of_file.hex():
        return True
    elif file.puid == word_markup_puid:
        return True
    else:
        return False


def is_preservable(file: ArchiveFile, log: Logger) -> Tuple[bool, Any]:
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


def getPixelAmount(file_path: Path) -> int:
    with Image.open(file_path) as im:
        width, height = im.size
        pixelAmount: int = width * height
        return pixelAmount


def isImagePreservable(file_path: Path) -> bool:
    pixel_amount = getPixelAmount(file_path)
    if pixel_amount < 20000:
        return False
    else:
        return True


def image_is_preservable(
    file: ArchiveFile, lock: Lock, logger: Logger
) -> bool:

    lock.acquire()
    result: bool = False

    if "ROOTPATH" in os.environ:
        file_path: Path = Path(os.environ["ROOTPATH"], file.relative_path)
    else:
        file_path = file.relative_path
    try:
        result = isImagePreservable(file_path)
    except PIL.UnidentifiedImageError:
        print(f"PIL could not open the file: {file.relative_path}")
        result = True
    except Image.DecompressionBombWarning:
        logger.warning(
            "The file {} threw a decompresionbomb warning".format(
                file.relative_path
            )
        )
        result = True
    except Image.DecompressionBombError:
        logger.error(
            "The file {} threw a decompresionbomb error".format(
                file.relative_path
            )
        )
        result = True
    finally:
        lock.release()
        return result


def update_file_info(
    file_info: ArchiveFile, id_info: Dict[Path, Identification]
) -> ArchiveFile:
    no_id: Identification = Identification(
        puid=None,
        signature=None,
        warning="No identification information obtained.",
    )
    file_path = Path(os.environ["ROOTPATH"], file_info.relative_path)
    new_id: Identification = id_info.get(file_path) or no_id

    if file_path.stat().st_size == 0:
        new_id = Identification(
            puid="aca-error/1",
            signature="Empty file",
            warning="Error: File is empty",
        )
    file_info = file_info.copy(update=new_id.dict())
    file_info.is_binary = is_binary(file_info)
    file_info.file_size_in_bytes = file_path.stat().st_size
    return file_info


def identify(files: List[ArchiveFile], path: Path) -> List[ArchiveFile]:
    """Identify all files in a list, and return the updated list.

    Parameters
    ----------
    files : List[FileInfo]
        Files to identify.

    Returns
    -------
    List[FileInfo]
        Input files with updated Identification information.

    """

    id_info: Dict[Path, Identification] = sf_id(path)
    # functools.partial: Return a new partial object
    # which when called will behave like func called with the
    # positional arguments args and keyword arguments keywords.

    # Create a partial function of update_file_info
    # so that we can use map on it.
    # map cannot be used on update_file_info itself since id_info
    # can be shorter than files.
    _update = partial(update_file_info, id_info=id_info)
    with Pool(5) as p:
        updated_files: List[ArchiveFile] = p.map(_update, files, 10000)

    return natsort_path(updated_files)
