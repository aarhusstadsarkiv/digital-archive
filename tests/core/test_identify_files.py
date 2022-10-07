# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import json
import os

from pathlib import Path
from threading import Lock
from PIL.Image import DecompressionBombError
from PIL.Image import DecompressionBombWarning
from subprocess import CalledProcessError
from unittest.mock import patch

import pytest
from digiarch.core.ArchiveFileRel import ArchiveFile
from acamodels import Identification
from digiarch.core.identify_files import (
    custom_id,
    is_preservable,
    image_is_preservable,
)
from digiarch.core.identify_files import identify
from digiarch.core.identify_files import sf_id
from digiarch.core.identify_files import is_binary
from digiarch.exceptions import IdentificationError


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


class TestIdentify:
    def test_valid_file(self, docx_info, test_data_dir):
        docx = ArchiveFile(relative_path=docx_info)
        result = identify([docx], test_data_dir)
        assert len(result) == 1
        assert result[0].puid == "fmt/412"
        assert (
            result[0].signature == "Microsoft Word for Windows (2007 onwards)"
        )
        assert result[0].warning is None

    def test_empty_file(self, temp_dir):
        empty_file = temp_dir / "AARS.test" / "mock.empty"
        empty_file.parent.mkdir()
        empty_file.touch()
        empty = ArchiveFile(relative_path=empty_file)
        result = identify([empty], temp_dir)
        assert len(result) == 1
        assert result[0].puid == "aca-error/1"
        assert result[0].signature == "Empty file"
        assert result[0].warning == "Error: File is empty"


class TestSFId:
    def test_valid_input(self, docx_info):
        result = sf_id(docx_info)
        assert result[docx_info].puid == "fmt/412"
        assert (
            result[docx_info].signature
            == "Microsoft Word for Windows (2007 onwards)"
        )
        assert result[docx_info].warning is None

    def test_custom_markup(self, xls_info):
        result = sf_id(xls_info)
        assert result[xls_info].puid == "aca-fmt/3"
        assert result[xls_info].signature == "Microsoft Excel Markup"
        assert result[xls_info].warning is None

    def test_subprocess_error(self, docx_info):
        with pytest.raises(IdentificationError):
            with patch(
                "subprocess.run",
                side_effect=CalledProcessError(
                    returncode=1, cmd="Fail", stderr=b"Fail"
                ),
            ):
                sf_id(docx_info)

    def test_json_error(self, docx_info):
        with pytest.raises(IdentificationError):
            with patch(
                "json.loads",
                side_effect=json.JSONDecodeError,
            ):
                sf_id(docx_info)


class TestCustomId:
    def test_lwp(self, temp_dir):
        lwp_file = temp_dir / "mock.lwp"
        lwp_file.write_bytes(
            bytes.fromhex(
                "576F726450726F0DFB000000000000"
                "000005985C8172030040CCC1BFFFBDF970"
            )
        )
        lwp_id = Identification(
            puid=None, signature=None, warning="this is a warning"
        )
        new_id = custom_id(lwp_file, lwp_id)
        assert new_id.puid == "x-fmt/340"
        assert new_id.signature == "Lotus WordPro Document"
        assert new_id.warning is None
        fail_lwp_file = lwp_file.rename(lwp_file.with_suffix(".fail"))
        fail_id = custom_id(fail_lwp_file, lwp_id)
        assert fail_id.puid == "x-fmt/340"
        assert fail_id.signature == "Lotus WordPro Document"
        assert fail_id.warning == "Extension mismatch"

    def test_123(self, temp_dir):
        _123_file = temp_dir / "mock.123"
        _123_file.write_bytes(bytes.fromhex("00001A000310040000000000"))
        _123_id = Identification(
            puid=None, signature=None, warning="this is a warning"
        )
        new_id = custom_id(_123_file, _123_id)
        assert new_id.puid == "aca-fmt/1"
        assert new_id.signature == "Lotus 1-2-3 Spreadsheet"
        assert new_id.warning is None
        fail_123_file = _123_file.rename(_123_file.with_suffix(".fail"))
        fail_id = custom_id(fail_123_file, _123_id)
        assert fail_id.puid == "aca-fmt/1"
        assert fail_id.signature == "Lotus 1-2-3 Spreadsheet"
        assert fail_id.warning == "Extension mismatch"

    def test_word_markup(self, temp_dir):
        word_markup = temp_dir / "mock.doc"
        word_markup.write_bytes(
            bytes.fromhex(
                "6e2070726f6769643d22576f72642e446f"
                "63756d656e74223f3e3c773a776f726444"
            )
        )
        word_markup_id = Identification(
            puid="fmt/96",
            signature="Hypertext Markup Language",
            warning="Extension mismatch",
        )
        new_id = custom_id(word_markup, word_markup_id)
        assert new_id.puid == "aca-fmt/2"
        assert new_id.signature == "Microsoft Word Markup"
        assert new_id.warning is None
        word_markup_wrong_suffix = word_markup.rename(
            word_markup.with_suffix(".fail")
        )
        new_id_wrong_suffix = custom_id(
            word_markup_wrong_suffix, word_markup_id
        )
        assert new_id_wrong_suffix.puid == new_id.puid
        assert new_id_wrong_suffix.signature == new_id.signature
        assert new_id_wrong_suffix.warning == "Extension mismatch"

    def test_excel_markup(self, temp_dir):
        excel_markup = temp_dir / "mock.xls"
        excel_markup.write_bytes(
            bytes.fromhex(
                "6d657461206e616d653d50726f67496420636f6e74656e"
                "743d457863656c2e53686565743e0d0a3c6d657461206e"
            )
        )
        excel_markup_id = Identification(
            puid="fmt/583",
            signature="Vector Markup Language",
            warning="Extension mismatch",
        )
        new_id = custom_id(excel_markup, excel_markup_id)
        assert new_id.puid == "aca-fmt/3"
        assert new_id.signature == "Microsoft Excel Markup"
        assert new_id.warning is None
        excel_markup_wrong_suffix = excel_markup.rename(
            excel_markup.with_suffix(".test")
        )
        new_id_wrong_suffix = custom_id(
            excel_markup_wrong_suffix, excel_markup_id
        )
        assert new_id_wrong_suffix.puid == new_id.puid
        assert new_id_wrong_suffix.signature == new_id.signature
        assert new_id_wrong_suffix.warning == "Extension mismatch"

    def test_mmap(self, temp_dir):
        mmap_markup = temp_dir / "mock.mmap"
        mmap_markup.write_bytes(bytes.fromhex("4D696E644d616E61676572"))
        mmap_markup_id = Identification(
            puid="x-fmt/263",
            signature="ZIP Archive",
            warning="Extension mismatch",
        )
        new_id = custom_id(mmap_markup, mmap_markup_id)
        assert new_id.puid == "aca-fmt/4"
        assert new_id.signature == "MindManager Mind Map"
        assert new_id.warning is None
        mmap_markup_wrong_suffix = mmap_markup.rename(
            mmap_markup.with_suffix(".test")
        )
        new_id_wrong_suffix = custom_id(
            mmap_markup_wrong_suffix, mmap_markup_id
        )
        assert new_id_wrong_suffix.puid == new_id.puid
        assert new_id_wrong_suffix.signature == new_id.signature
        assert new_id_wrong_suffix.warning == "Extension mismatch"

    def test_gif(self, temp_dir):
        gif_file = temp_dir / "mock.gif"
        gif_file.write_bytes(bytes.fromhex("4749463839613B"))

        new_id_dict = sf_id(gif_file)
        assert new_id_dict[gif_file].puid == "fmt/4"
        assert (
            new_id_dict[gif_file].signature
            == "Graphics Interchange Format (89a)"
        )
        assert new_id_dict[gif_file].warning is None
        fail_gif_file = gif_file.rename(gif_file.with_suffix(".fail"))
        fail_id_dict = sf_id(fail_gif_file)
        assert fail_id_dict[fail_gif_file].puid == "fmt/4"
        assert (
            fail_id_dict[fail_gif_file].signature
            == "Graphics Interchange Format (89a)"
        )
        assert fail_id_dict[fail_gif_file].warning == "Extension mismatch"

    def test_nsf(self, temp_dir):
        nsf_file = temp_dir / "mock.nsf"
        nsf_file.write_bytes(
            bytes.fromhex(
                "1a000004000029000000bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            )
        )
        nsf_id = Identification(puid=None, signature=None, warning="fail")
        new_id = custom_id(nsf_file, nsf_id)
        assert new_id.puid == "aca-fmt/8"
        assert new_id.signature == "Lotus Notes Database"
        assert new_id.warning is None
        fail_nsf_file = nsf_file.rename(nsf_file.with_suffix(".fail"))
        fail_id = custom_id(fail_nsf_file, nsf_id)
        assert fail_id.puid == "aca-fmt/8"
        assert fail_id.signature == "Lotus Notes Database"
        assert fail_id.warning == "Extension mismatch"

    def test_id(self, temp_dir):
        id_file = temp_dir / "mock.id"
        id_file.write_bytes(bytes.fromhex("010000002E01000043000000"))
        id_id = Identification(puid=None, signature=None, warning="fail")
        new_id = custom_id(id_file, id_id)
        assert new_id.puid == "aca-fmt/7"
        assert new_id.signature == "ID File"
        # assert new_id.warning == "Match on extension only"

    def test_is_binary_false(self, non_binary_file):
        assert is_binary(non_binary_file) is False

    def test_is_binary_true(self, binary_file):
        assert is_binary(binary_file) is True


class TestIsPreservable:
    def test_is_preservable_image_true(self, binary_file):
        assert is_preservable(binary_file)[0] is True

    def test_is_preservable_image_false(self, small_binary_file):
        assert is_preservable(small_binary_file)[0] is False

    def test_is_preservable_binary_file_true(
        self, python_wiki_binary_file: ArchiveFile
    ):
        assert is_preservable(python_wiki_binary_file)[0] is True

    def test_is_preservable_binary_file_false(
        self, very_small_binary_file: ArchiveFile
    ):
        assert is_preservable(very_small_binary_file)[0] is False

    # All non binary (i.e. text) files are considered as preservable
    def test_is_preservable_non_binary_file(
        self, non_binary_file: ArchiveFile
    ):
        assert is_preservable(non_binary_file)[0] is True

    def test_image_is_preservable_on_pillow_exception(
        self, very_small_binary_file
    ):
        # If pillow cannot parse an image file, it should
        # still be marked as preservable
        # but looked at manually at some point.
        lock: Lock = Lock()
        assert image_is_preservable(very_small_binary_file, lock) is True

    # GIVEN a too large file (mimmicked by a monkeypatch)
    # WHEN a decompressionbomberror is thrown
    # THEN a log file should be created and contain info about it
    def test_decrompresionbomb_log_error(
        self, binary_file, monkeypatch, lock, log
    ):

        pathToFile: Path = Path("pillow_decompressionbomb.log")

        def mock_open(*args, **kwargs):
            raise DecompressionBombError

        monkeypatch.setattr(
            "digiarch.core.identify_files.isImagePreservable", mock_open
        )
        image_is_preservable(binary_file, lock, logger=log)
        assert os.path.exists(pathToFile)
        with open(pathToFile, mode="r", encoding="utf-8") as file:
            line = file.readline()
            assert (
                "ERROR: The file image_file.png threw "
                "a decompresionbomb error\n" in line
            )
        file.close()

    def test_decrompresionbomb_log_warning(
        self, binary_file, monkeypatch, lock, log
    ):

        pathToFile: Path = Path("pillow_decompressionbomb.log")

        def mock_open(*args, **kwargs):
            raise DecompressionBombWarning

        monkeypatch.setattr(
            "digiarch.core.identify_files.isImagePreservable", mock_open
        )

        image_is_preservable(binary_file, lock, logger=log)
        # The assertions are ugly and not best practice. They are used to
        # check multiple lines of the file, and if one of them contains the
        # warning then the test should assert True
        with open(pathToFile, mode="r", encoding="utf-8") as file:
            for line in file.readlines():
                if (
                    "WARNING: The file image_file.png threw a "
                    "decompresionbomb warning\n" in line
                ):
                    assert True
                    return
                else:
                    continue
            assert False
