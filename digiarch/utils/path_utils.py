"""Utilities for handling files, paths, etc.

"""
# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import os
from tqdm import tqdm
from digiarch.data import FileInfo, dump_file
from typing import List, Tuple

# -----------------------------------------------------------------------------
# Function Definitions
# -----------------------------------------------------------------------------


def create_folders(folder_paths: Tuple[str, ...]) -> None:
    """Creates given folders, and passes on FileExistsException.

    Parameters
    ----------
    folder_paths : Tuple[str, ...]
        Paths of folders to create.

    """
    for folder in folder_paths:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass


def explore_dir(path: str, main_dir: str, save_file: str) -> None:
    """Finds files and empty directories in the given path,
    and collects them into a list of FileInfo objects.

    Parameters
    ----------
    path : str
        The path in which to find files.

    """
    # Type declarations
    dir_info: List[FileInfo] = []
    info: FileInfo
    ext: str
    main_dir_name: str = os.path.basename(os.path.normpath(main_dir))
    main_folders: List[str] = [
        folder for folder in os.listdir(path) if folder != main_dir_name
    ]

    if not main_folders:
        # Path is empty, write empty file and return
        dump_file(data="", file=save_file)
        return

    # Traverse given path, collect results.
    # tqdm is used to show progress of os.walk
    for root, dirs, files in tqdm(
        os.walk(path, topdown=True), unit=" folders", desc="Processed"
    ):
        # Don't walk the processing directory
        if main_dir_name in dirs:
            dirs.remove(main_dir_name)
        if not dirs and not files:
            # We found an empty subdirectory.
            info = FileInfo(is_empty_sub=True, path=root)
            dir_info.append(info)
        for file in files:
            cur_file = str(file)
            ext = os.path.splitext(cur_file)[1].lower()
            info = FileInfo(name=cur_file, ext=ext, path=root)
            dir_info.append(info)

    # Save results
    dump_file(data=dir_info, file=save_file)
