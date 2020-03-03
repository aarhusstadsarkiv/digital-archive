import json
from pathlib import Path
import pytest
from digiarch.internals import FileInfo
from digiarch.identify.checksums import (
    file_checksum,
    checksum_worker,
    generate_checksums,
    check_collisions,
    check_duplicates,
)


@pytest.fixture
def test_file_0(temp_dir):
    test_file = Path(temp_dir).joinpath("test0.txt")
    with test_file.open("w") as file:
        file.write("0")
    return test_file


@pytest.fixture
def test_file_1(temp_dir):
    test_file = Path(temp_dir).joinpath("test1.txt")
    with test_file.open("w") as file:
        file.write("1")
    return test_file


@pytest.fixture
def test_file_info(test_file_0):
    return FileInfo(path=test_file_0)


class TestFileChecksum:
    def test_without_file(self, temp_dir):
        assert file_checksum(Path(temp_dir)) == ""

    def test_with_file(self, test_file_0):
        assert (
            file_checksum(test_file_0)
            == "e9f11462495399c0b8d0d8ec7128df9c0d7269cda23531a352b174bd29c3"
            "b6318a55d3508cb70dad9aaa590185ba0fef4fab46febd46874a103739c10d6"
            "0ebc7"
        )


class TestChecksumWorker:
    def test_without_file(self, temp_dir):
        file_info = FileInfo(path=temp_dir)
        result = checksum_worker(file_info)
        assert result.checksum is None

    def test_with_file(self, test_file_info):
        assert (
            checksum_worker(test_file_info).checksum
            == "e9f11462495399c0b8d0d8ec7128df9c0d7269cda23531a352b174bd29c3"
            "b6318a55d3508cb70dad9aaa590185ba0fef4fab46febd46874a103739c10d6"
            "0ebc7"
        )


class TestGenerateChecksums:
    def test_with_files(self, test_file_0, test_file_1):
        f_info_0 = FileInfo(path=test_file_0, checksum="test0")
        f_info_1 = FileInfo(path=test_file_1, checksum="test1")
        files = [f_info_0, f_info_1]
        result = generate_checksums(files)
        for file in result:
            assert file.checksum == file_checksum(Path(file.path))

    def test_without_files(self):
        assert generate_checksums([]) == []


class TestCheckCollisions:
    def test_with_collisions(self):
        item1 = "collision"
        item2 = "not a collision"
        test_list = [item1, item1, item2]
        result = check_collisions(test_list)
        assert item1 in result
        assert item2 not in result
        assert len(result) == 1

    def test_without_collisions(self):
        item1 = "not a collision"
        item2 = "also not a collision"
        test_list = [item1, item2]
        result = check_collisions(test_list)
        assert item1 not in result
        assert item2 not in result
        assert len(result) == 0


class TestCheckDuplicates:
    def test_with_dups(self, test_file_0, temp_dir):
        f_info_0 = FileInfo(path=test_file_0, checksum="test0")
        f_info_1 = FileInfo(path=test_file_0, checksum="test1")
        files = [f_info_0, f_info_1]
        updated_files = generate_checksums(files)
        print(updated_files)
        check_duplicates(updated_files, temp_dir)
        outfile = Path(temp_dir).joinpath("duplicate_files.json")
        with outfile.open() as file:
            result = json.load(file)
        assert file_checksum(test_file_0) in result
        assert len(result[file_checksum(test_file_0)]) == 2

    def test_without_dups(self, test_file_0, test_file_1, temp_dir):
        f_info_0 = FileInfo(path=test_file_0, checksum="test0")
        f_info_1 = FileInfo(path=test_file_1, checksum="test1")
        files = [f_info_0, f_info_1]
        updated_files = generate_checksums(files)
        check_duplicates(updated_files, temp_dir)
        outfile = Path(temp_dir).joinpath("duplicate_files.json")
        with outfile.open() as file:
            result = json.load(file)
        assert file_checksum(test_file_0) not in result
        assert file_checksum(test_file_1) not in result
        assert result == {}
