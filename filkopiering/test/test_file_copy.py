import unittest
import pytest
from pathlib import Path

from filkopiering.main import copy_files


class TestFileCopy(unittest.TestCase):
    def setUp(self) -> None:
        self.destination = Path.cwd() / "dest_dir"
        self.destination.mkdir()
        self.file1 = Path.cwd() / "a.txt"
        self.file2 = Path.cwd() / "b.txt"
        self.file1.touch()

        self.file2.touch()

    def tearDown(self) -> None:
        self.file1.unlink()
        self.file2.unlink()
        self.destination.rmdir()

    def test_file_should_be_copied(self):
        detected_file_names = {
            self.file1.name: [self.file1],
            self.file2.name: [self.file2],
        }
        duplicated_file_names = []
        copy_files(
            self.destination, detected_file_names, duplicated_file_names
        )
        file3 = self.destination / "a.txt"
        file4 = self.destination / "b.txt"
        self.assertTrue(file3.exists())
        self.assertTrue(file3.is_file())
        self.assertTrue(file4.exists())
        self.assertTrue(file4.is_file())
        file3.unlink()
        file4.unlink()


if __name__ == "__main__":
    unittest.main()
