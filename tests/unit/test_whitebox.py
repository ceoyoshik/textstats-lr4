"""Тесты методов «белого ящика»: покрытие решений и условий.

Вариант 11 требует покрытия решений (каждая ветка if/else хотя бы раз).
Дополнительно проверены условия и комбинации условий для критичных
решений (уровень 3).
"""
import pytest

import input_module
import processing_module
import protocol
from errors import InputDataError, ProtocolError, VersionConflictError

pytestmark = pytest.mark.whitebox


# ------------------------------------------------ решения tokenize/analyze
@pytest.mark.parametrize("text, has_words", [
    ("", False),
    ("   ", False),
    ("...!", False),
    ("слово", True),
    ("два слова", True),
])
def test_tokenize_decision(text, has_words):
    assert bool(processing_module.tokenize(text)) is has_words


@pytest.mark.parametrize("text, count", [
    ("", 0),
    ("!!!", 0),
    ("Одно", 1),
    ("Раз. Два.", 2),
])
def test_split_sentences_decision(text, count):
    assert len(processing_module.split_sentences(text)) == count


@pytest.mark.parametrize("words, limit, expected", [
    ([], 3, ()),
    (["а"], 3, (("а", 1),)),
    (["а", "б"], 1, (("а", 1),)),
    (["а"], 0, ()),
    (["а"], -2, ()),
])
def test_top_words_decisions(words, limit, expected):
    assert processing_module.top_words(words, limit) == expected


# ------------------------------- покрытие решений analyze (пустой/непустой)
def test_analyze_empty_branch():
    stats = processing_module.analyze("...")
    assert stats.words == 0
    assert stats.avg_word_length == 0.0
    assert stats.longest_word == ""


def test_analyze_non_empty_branch():
    stats = processing_module.analyze("Слово")
    assert stats.words == 1
    assert stats.avg_word_length == 5.0
    assert stats.longest_word == "Слово"


# ------------------------------- покрытие решений parse_text (4 исхода)
@pytest.mark.parametrize("text, exception", [
    ("Текст", None),
    (123, InputDataError),
    ("я" * (protocol.MAX_TEXT + 1), InputDataError),
    ("   ", InputDataError),
    ("\x00", InputDataError),
])
def test_parse_text_decisions(text, exception):
    if exception is None:
        assert input_module.parse_text(text) == text
    else:
        with pytest.raises(exception):
            input_module.parse_text(text)


# ------------------------- покрытие решений load_source (файл/поток)
class Stream:
    def read(self):
        return "поток"


def test_load_source_file_branch(tmp_path):
    path = tmp_path / "text.txt"
    path.write_text("файл", encoding="utf-8")
    assert input_module.load_source(str(path)) == "файл"


def test_load_source_stream_branch():
    assert input_module.load_source(None, Stream()) == "поток"


# ---------------------- покрытие решений parse_request (4 проверки)
@pytest.mark.parametrize("text, exception", [
    ("текст", None),
    (42, ProtocolError),
    ("я" * (protocol.MAX_TEXT + 1), InputDataError),
    ("  ", InputDataError),
])
def test_parse_request_decisions(text, exception):
    message = protocol.build_request("x")
    message["payload"]["text"] = text
    if exception is None:
        assert protocol.parse_request(message) == text
    else:
        with pytest.raises(exception):
            protocol.parse_request(message)


# ---------------- комбинаторное покрытие check_version (5 комбинаций)
VERSION_COMBINATIONS = [
    (True, True, True, True, None),
    (True, True, True, False, VersionConflictError),
    (True, True, False, None, ProtocolError),
    (True, False, None, None, ProtocolError),
    (False, None, None, None, ProtocolError),
]


@pytest.mark.parametrize("is_str, two_parts, digits, major, exception",
                         VERSION_COMBINATIONS)
def test_check_version_combinatorial(is_str, two_parts, digits, major,
                                     exception):
    if not is_str:
        version = 1
    elif not two_parts:
        version = "1"
    elif not digits:
        version = "1.a"
    elif major:
        version = "1.0"
    else:
        version = "2.0"
    if exception is None:
        protocol.check_version(version)
    else:
        with pytest.raises(exception):
            protocol.check_version(version)


# ------------------ покрытие решений validate_envelope (6 решений)
ENVELOPE_CASES = [
    ("not a dict", ProtocolError),
    ({"type": "x", "payload": {}}, ProtocolError),
    ({"version": "1.0", "payload": {}}, ProtocolError),
    ({"version": "1.0", "type": "x"}, ProtocolError),
    ({"version": "2.0", "type": "x", "payload": {}}, VersionConflictError),
    ({"version": "1.0", "type": "x", "payload": []}, ProtocolError),
    ({"version": "1.0", "type": "x", "payload": {}}, ProtocolError),
]


@pytest.mark.parametrize("message, exception", ENVELOPE_CASES)
def test_validate_envelope_decisions(message, exception):
    with pytest.raises(exception):
        protocol.validate_envelope(message, protocol.MSG_REQUEST)


# ---------------------- покрытие решений handle_request (4 ветки)
def test_handle_request_success_branch():
    response = processing_module.handle_request(protocol.build_request("да"))
    assert response["type"] == protocol.MSG_RESPONSE


@pytest.mark.parametrize("code", [protocol.ERR_VERSION,
                                  protocol.ERR_INVALID_DATA,
                                  protocol.ERR_PROTOCOL])
def test_handle_request_error_branches(code):
    message = protocol.build_error(code, "причина")
    response = processing_module.handle_request(message)
    assert response["payload"]["code"] == code


# ------------------------- покрытие решений process_files (3 исхода)
def test_process_files_success_branch(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path), protocol.build_request("текст"))
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is True


def test_process_files_error_branch(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path), protocol.build_request(" "))
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is False


def test_process_files_protocol_error_branch(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text("нет json", encoding="utf-8")
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is False


# ------------------ покрытие решений parse_response (5 проверок)
def _payload(**overrides):
    value = {
        "chars": 4, "chars_no_spaces": 4, "words": 1, "sentences": 1,
        "unique_words": 1, "avg_word_length": 4.0,
        "longest_word": "Текст", "top_words": [["текст", 1]],
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize("overrides, exception", [
    ({}, None),
    ({"words": -1}, ProtocolError),
    ({"avg_word_length": float("nan")}, ProtocolError),
    ({"longest_word": 1}, ProtocolError),
    ({"top_words": "нет"}, ProtocolError),
    ({"top_words": [["текст", 9]]}, ProtocolError),
])
def test_parse_response_decisions(overrides, exception):
    message = protocol.build_response(_payload(**overrides))
    if exception is None:
        protocol.parse_response(message)
    else:
        with pytest.raises(exception):
            protocol.parse_response(message)
