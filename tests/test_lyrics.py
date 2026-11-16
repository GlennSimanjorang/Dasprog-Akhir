"""Unit tests for LRC lyric parser and timestamp handling."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lyrics.lyric_parser import LyricLine, parse_lrc, parse_timestamp


class LyricParserTest(unittest.TestCase):
    """Test parse_lrc and timestamp conversion."""

    def test_parse_timestamp(self) -> None:
        # 01:23.45 -> 1*60 + 23 + 0.45 = 83.45
        self.assertAlmostEqual(parse_timestamp("01", "23", "45"), 83.45)
        # 00:05 -> 5.0
        self.assertAlmostEqual(parse_timestamp("00", "05", None), 5.0)
        # 02:10.500 -> 130.5
        self.assertAlmostEqual(parse_timestamp("02", "10", "500"), 130.5)

    def test_parse_valid_lrc(self) -> None:
        sample_lrc = """[ti:Sample Song]
[ar:Artist Name]
[00:02.00]First line of lyrics
[00:05.50]Second line of lyrics
[00:10.00]Third line of lyrics
"""
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.lrc"
            file_path.write_text(sample_lrc, encoding="utf-8")

            lyrics = parse_lrc(file_path)

            self.assertEqual(len(lyrics), 3)
            self.assertEqual(lyrics[0], LyricLine(2.0, "First line of lyrics"))
            self.assertEqual(lyrics[1], LyricLine(5.5, "Second line of lyrics"))
            self.assertEqual(lyrics[2], LyricLine(10.0, "Third line of lyrics"))

    def test_parse_multi_timestamp_lines(self) -> None:
        sample_lrc = """[00:01.00][00:04.00]Repeated Chorus"""
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.lrc"
            file_path.write_text(sample_lrc, encoding="utf-8")

            lyrics = parse_lrc(file_path)

            self.assertEqual(len(lyrics), 2)
            self.assertEqual(lyrics[0], LyricLine(1.0, "Repeated Chorus"))
            self.assertEqual(lyrics[1], LyricLine(4.0, "Repeated Chorus"))

    def test_parse_unsorted_lrc_is_sorted(self) -> None:
        sample_lrc = """[00:10.00]Later line
[00:01.00]Earlier line
[00:05.00]Middle line"""
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.lrc"
            file_path.write_text(sample_lrc, encoding="utf-8")

            lyrics = parse_lrc(file_path)

            timestamps = [item.timestamp for item in lyrics]
            self.assertEqual(timestamps, [1.0, 5.0, 10.0])

    def test_parse_invalid_lines_gracefully_ignored(self) -> None:
        sample_lrc = """[ar:Random]
Random text without timestamp
[999:999] Invalid format
[00:03.00]Valid line
"""
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.lrc"
            file_path.write_text(sample_lrc, encoding="utf-8")

            lyrics = parse_lrc(file_path)

            self.assertEqual(len(lyrics), 1)
            self.assertEqual(lyrics[0].text, "Valid line")

    def test_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            parse_lrc(Path("non_existent_file.lrc"))


if __name__ == "__main__":
    unittest.main()
