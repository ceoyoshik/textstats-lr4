"""Модульные тесты модуля обработки (границы и классы эквивалентности)."""
import pytest

import processing_module
import protocol
from errors import InputDataError

pytestmark = pytest.mark.unit

SAMPLE = "Привет, мир! Мир текста."


# ------------------------------------------------------------------ tokenize
@pytest.mark.parametrize("text, expected", [
    ("Привет, мир!", ["Привет", "мир"]),
    ("мама-мама и ёж", ["мама-мама", "и", "ёж"]),
    ("don't stop", ["don't", "stop"]),
    ("число 42 в тексте", ["число", "42", "в", "тексте"]),
    ("!!! ??? ...", []),
    ("", []),
    ("   ", []),
])
def test_tokenize(text, expected):
    assert processing_module.tokenize(text) == expected


# ------------------------------------------------------------ split_sentences
@pytest.mark.parametrize("text, expected", [
    ("Привет. Как дела? Хорошо!", 3),
    ("Одно предложение", 1),
    ("Привет... Как дела?", 2),
    ("Вопрос?! Ответ.", 2),
    ("", 0),
    ("!!!", 0),
    ("   ", 0),
])
def test_split_sentences(text, expected):
    assert len(processing_module.split_sentences(text)) == expected


def test_split_sentences_without_space_after_dot():
    """Дефект BUG-1: точка без пробела тоже завершает предложение."""
    assert len(processing_module.split_sentences("Привет.Как дела?")) == 2


def test_split_sentences_strips_parts():
    assert processing_module.split_sentences("  Привет.  Мир.  ") == \
        ["Привет", "Мир"]


# ------------------------------------------------------------------ top_words
def test_top_words_counts_case_insensitive():
    words = ["Мир", "мир", "текст"]
    assert processing_module.top_words(words) == (("мир", 2), ("текст", 1))


def test_top_words_alphabetical_for_equal_counts():
    words = ["б", "а", "в"]
    assert processing_module.top_words(words) == (("а", 1), ("б", 1),
                                                  ("в", 1))


def test_top_words_limit():
    words = ["а", "а", "б", "в", "г"]
    assert processing_module.top_words(words, limit=1) == (("а", 2),)


@pytest.mark.parametrize("limit", [0, -1])
def test_top_words_non_positive_limit(limit):
    assert processing_module.top_words(["а"], limit=limit) == ()


def test_top_words_empty():
    assert processing_module.top_words([]) == ()


def test_top_words_fewer_than_limit():
    result = processing_module.top_words(["а", "б"], limit=5)
    assert result == (("а", 1), ("б", 1))


# -------------------------------------------------------------------- analyze
def test_analyze_sample_text():
    stats = processing_module.analyze(SAMPLE)
    assert stats.chars == len(SAMPLE)
    assert stats.words == 4
    assert stats.sentences == 2
    assert stats.unique_words == 3
    assert stats.avg_word_length == 4.5
    assert stats.longest_word == "Привет"
    assert stats.top_words == (("мир", 2), ("привет", 1), ("текста", 1))


def test_analyze_chars_without_spaces():
    stats = processing_module.analyze("а б\nв\tг")
    assert stats.chars == 7
    assert stats.chars_no_spaces == 4


def test_analyze_single_word():
    stats = processing_module.analyze("Слово")
    assert stats.words == 1
    assert stats.sentences == 1
    assert stats.unique_words == 1
    assert stats.longest_word == "Слово"
    assert stats.avg_word_length == 5.0


def test_analyze_rounds_average_length():
    stats = processing_module.analyze("я я я")
    assert stats.avg_word_length == 1.0


def test_analyze_only_punctuation():
    stats = processing_module.analyze("...")
    assert stats.words == 0
    assert stats.sentences == 0
    assert stats.longest_word == ""
    assert stats.avg_word_length == 0.0
    assert stats.top_words == ()


def test_analyze_longest_word_tie_takes_first():
    stats = processing_module.analyze("кот пёс")
    assert stats.longest_word == "кот"


def test_analyze_hyphenated_word_is_one_token():
    stats = processing_module.analyze("мама-мама")
    assert stats.words == 1
    assert stats.longest_word == "мама-мама"


# ------------------------------------------------------------ handle_request
def test_handle_request_success():
    response = processing_module.handle_request(
        protocol.build_request("Привет, мир!"))
    assert response["type"] == protocol.MSG_RESPONSE
    assert response["payload"]["words"] == 2
    assert response["payload"]["chars"] == 12


def test_handle_request_version_conflict():
    request = protocol.build_request("текст")
    request["version"] = "2.0"
    response = processing_module.handle_request(request)
    assert response["payload"]["code"] == protocol.ERR_VERSION


def test_handle_request_invalid_data():
    response = processing_module.handle_request(
        protocol.build_request("   "))
    assert response["payload"]["code"] == protocol.ERR_INVALID_DATA


def test_handle_request_protocol_error():
    request = protocol.build_request("текст")
    request["type"] = "unknown"
    response = processing_module.handle_request(request)
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL


def test_handle_request_non_object():
    response = processing_module.handle_request("не сообщение")
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL


# -------------------------------------------------------------- process_files
def test_process_files_writes_response(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path), protocol.build_request("Привет!"))
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is True
    response = protocol.load_json(str(response_path))
    assert response["payload"]["words"] == 1


def test_process_files_error_message(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path), protocol.build_request("   "))
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is False


def test_process_files_broken_json(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    request_path.write_text("{broken", encoding="utf-8")
    assert processing_module.process_files(str(request_path),
                                           str(response_path)) is False
    response = protocol.load_json(str(response_path))
    assert response["payload"]["code"] == protocol.ERR_PROTOCOL


# ---------------------------------------------------------------------- main
def test_main_success(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path), protocol.build_request("Текст."))
    code = processing_module.main(["--request", str(request_path),
                                   "--response", str(response_path)])
    assert code == protocol.EXIT_OK


def test_main_reported_error(tmp_path):
    request_path = tmp_path / "request.json"
    response_path = tmp_path / "response.json"
    protocol.dump_json(str(request_path), protocol.build_request("  "))
    code = processing_module.main(["--request", str(request_path),
                                   "--response", str(response_path)])
    assert code == protocol.EXIT_REPORTED_ERROR


def test_main_missing_request_fails(tmp_path, capsys):
    code = processing_module.main([
        "--request", str(tmp_path / "absent.json"),
        "--response", str(tmp_path / "response.json")])
    assert code == protocol.EXIT_FAILURE
    assert "Модуль обработки" in capsys.readouterr().err


def test_main_requires_arguments():
    with pytest.raises(SystemExit):
        processing_module.main([])


def test_handle_request_accepts_max_text_boundary():
    text = "я" * protocol.MAX_TEXT
    response = processing_module.handle_request(protocol.build_request(text))
    assert response["type"] == protocol.MSG_RESPONSE


def test_handle_request_rejects_too_long_text():
    text = "я" * (protocol.MAX_TEXT + 1)
    response = processing_module.handle_request(protocol.build_request(text))
    assert response["payload"]["code"] == protocol.ERR_INVALID_DATA


def test_handle_request_raises_inside_analyze(monkeypatch):
    def broken(_text):
        raise InputDataError("сбой анализа")

    monkeypatch.setattr(processing_module, "analyze", broken)
    response = processing_module.handle_request(protocol.build_request("x"))
    assert response["payload"]["code"] == protocol.ERR_INVALID_DATA
