"""Shared testing fixtures.

"""
# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
from typing import Tuple, Union
from digiarch.core.ArchiveFileRel import ArchiveFile
from pathlib import Path
import pytest
import os
import png

# -----------------------------------------------------------------------------
# Function Definitions
# -----------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio


@pytest.fixture
def temp_dir(tmpdir_factory):
    t_dir: str = tmpdir_factory.mktemp("temp_dir")
    temp_dir: Path = Path(t_dir, "AARS.TEST")
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


@pytest.fixture
def main_dir(temp_dir):
    main_dir: Path = temp_dir / "_metadata"
    main_dir.mkdir(exist_ok=True)
    return main_dir


@pytest.fixture
def data_file(main_dir):
    data_dir: Path = main_dir / ".data"
    data_dir.mkdir(exist_ok=True)
    data_file: Path = data_dir / "data.json"
    return data_file


@pytest.fixture
def test_data_dir():
    return Path(__file__).parent.parent / "tests" / "_data" / "AARS.test_data"


@pytest.fixture
def docx_info(test_data_dir):
    docx_file: Path = test_data_dir / "docx_test.docx"
    return docx_file


@pytest.fixture
def xls_info(test_data_dir):
    xls_file: Path = test_data_dir / "xls_test.xls"
    return xls_file


@pytest.fixture
def adx_info(test_data_dir):
    adx_file: Path = test_data_dir / "adx_test.adx"
    return adx_file


@pytest.fixture
def file_data(temp_dir):
    from digiarch.models import FileData

    return FileData(main_dir=temp_dir, files=[])


@pytest.fixture
def non_binary_file():
    os.environ["ROOTPATH"] = str(Path.cwd())
    text_file_relative_path = Path("text_file.txt")
    text_file_path = Path(os.environ["ROOTPATH"], text_file_relative_path)
    text_file_path.touch()
    text_file_path.write_text("Non binary file test.")
    non_binary_file = ArchiveFile(relative_path=text_file_relative_path)
    yield non_binary_file
    text_file_path.unlink()


@pytest.fixture
def binary_file():
    os.environ["ROOTPATH"] = str(Path.cwd())
    image_file_relative_path = Path("image_file.png")
    image_file_path = Path(os.environ["ROOTPATH"], image_file_relative_path)

    # Creating a png image of 255 by 255.
    width = 255
    height = 255
    img = []
    for y in range(height):
        row: Union[Tuple[int, int, int], Tuple] = ()
        for x in range(width):
            row = row + (x, max(0, 255 - x - y), y)
        img.append(row)
    with open(image_file_path, "wb") as f:
        w = png.Writer(width, height, greyscale=False)
        w.write(f, img)
    png_file = ArchiveFile(
        relative_path=image_file_relative_path,
        puid="fmt/11",
        signature="PNG file",
    )
    yield png_file
    image_file_path.unlink()


@pytest.fixture
def small_binary_file():
    os.environ["ROOTPATH"] = str(Path.cwd())
    image_file_relative_path = Path("image_file.png")
    image_file_path = Path(os.environ["ROOTPATH"], image_file_relative_path)

    # Creating a png image of 255 by 255.
    width = 50
    height = 50
    img = []
    for y in range(height):
        row: Union[Tuple[int, int, int], Tuple] = ()
        for x in range(width):
            row = row + (x, max(0, 255 - x - y), y)
        img.append(row)
    with open(image_file_path, "wb") as f:
        w = png.Writer(width, height, greyscale=False)
        w.write(f, img)
    png_file = ArchiveFile(
        relative_path=image_file_relative_path,
        puid="fmt/11",
        signature="PNG file",
    )
    yield png_file
    image_file_path.unlink()
