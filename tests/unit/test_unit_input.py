"""Модульные тесты модуля ввода (эквивалентное разбиение и границы)."""
import pytest

import input_module
import protocol
from errors import InputDataError

pytestmark = pytest.mark.unit

MAX_TEXT = protocol.MAX_TEXT


# ---------------------------------------------------------------- parse_text
def test_parse_text_returns_text():
    assert input_module.parse_text("Привет, мир!") == "Привет, мир!"


def test_parse_text_keeps_control_line_breaks():
    text = "Первая строка\nВторая строка\tс табуляцией"
    assert input_module.parse_text(text) == text


@pytest.mark.parametrize("text, source", [
    (123, "ввод"),
    (None, "ввод"),
    (["текст"], "ввод"),
])
def test_parse_text_requires_string(text, source):
    with pytest.raises(InputDataError):
        input_module.parse_text(text, source)


@pytest.mark.parametrize("text", ["", "   ", "\n\n", "\t \r\n"])
def test_parse_text_rejects_blank(text):
    with pytest.raises(InputDataError):
        input_module.parse_text(text)


@pytest.mark.parametrize("text", [
    "текст\x00с нулём",
    "текст\x01",
    "текст\x1f",
])
def test_parse_text_rejects_control_symbols(text):
    with pytest.raises(InputDataError):
        input_module.parse_text(text)


@pytest.mark.parametrize("length, accepted", [
    (1, True),
    (MAX_TEXT - 1, True),
    (MAX_TEXT, True),
    (MAX_TEXT + 1, False),
])
def test_parse_text_size_boundary(length, accepted):
    text = "я" * length
    if accepted:
        assert len(input_module.parse_text(text)) == length
    else:
        with pytest.raises(InputDataError):
            input_module.parse_text(text)


def test_parse_text_error_mentions_source():
    with pytest.raises(InputDataError) as error:
        input_module.parse_text("", "файл a.txt")
    assert "файл a.txt" in str(error.value)


# ----------------------------------------------------------------- read_file
def test_read_file_utf8(tmp_path):
    path = tmp_path / "text.txt"
    path.write_text("Привет, мир!", encoding="utf-8")
    assert input_module.read_file(str(path)) == "Привет, мир!"


def test_read_file_missing(tmp_path):
    with pytest.raises(InputDataError) as error:
        input_module.read_file(str(tmp_path / "absent.txt"))
    assert "не найден" in str(error.value)


def test_read_file_bad_encoding(tmp_path):
    path = tmp_path / "broken.txt"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(InputDataError):
        input_module.read_file(str(path))


def test_read_file_empty(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("  ", encoding="utf-8")
    with pytest.raises(InputDataError):
        input_module.read_file(str(path))


def test_read_file_directory(tmp_path):
    directory = tmp_path / "dir"
    directory.mkdir()
    with pytest.raises(InputDataError):
        input_module.read_file(str(directory))


# ----------------------------------------------------------------- read_stdin
class Stream:
    def __init__(self, text):
        self.text = text

    def read(self):
        return self.text


def test_read_stdin():
    assert input_module.read_stdin(Stream("текст")) == "текст"


def test_read_stdin_empty():
    with pytest.raises(InputDataError):
        input_module.read_stdin(Stream(""))


def test_read_stdin_bad_encoding():
    class Broken(Stream):
        def read(self):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")

    with pytest.raises(InputDataError):
        input_module.read_stdin(Broken(""))


# --------------------------------------------------------------- load_source
def test_load_source_prefers_file(tmp_path):
    path = tmp_path / "text.txt"
    path.write_text("из файла", encoding="utf-8")
    assert input_module.load_source(str(path)) == "из файла"


def test_load_source_uses_stdin():
    assert input_module.load_source(None, Stream("из потока")) == "из потока"


def test_load_source_default_stdin(monkeypatch):
    class FakeStdin:
        def read(self):
            return "из stdin"

    monkeypatch.setattr(input_module.sys, "stdin", FakeStdin())
    assert input_module.load_source() == "из stdin"
