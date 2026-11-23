"""Регрессионные тесты: фиксируют проверенное ранее поведение.

Набор запускается в CI при каждом изменении кода (отдельная задача
«regression»), чтобы исправление одного дефекта не изменило корректные
результаты других сценариев.
"""
import json
import os
import subprocess
import sys

import pytest

import mapping
import output_module
import processing_module
import protocol
import textstat

pytestmark = pytest.mark.regression

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

CASES = [
    {
        "name": "два предложения",
        "text": "Привет, мир! Мир текста.",
        "words": 4, "sentences": 2, "unique": 3,
        "longest": "Привет",
        "top": (("мир", 2), ("привет", 1), ("текста", 1)),
    },
    {
        "name": "одно слово",
        "text": "Слово",
        "words": 1, "sentences": 1, "unique": 1,
        "longest": "Слово",
        "top": (("слово", 1),),
    },
    {
        "name": "только знаки",
        "text": "...",
        "words": 0, "sentences": 0, "unique": 0,
        "longest": "",
        "top": (),
    },
    {
        "name": "повторы в разном регистре",
        "text": "Дом дом ДОМ. Домашний дом!",
        "words": 5, "sentences": 2, "unique": 2,
        "longest": "Домашний",
        "top": (("дом", 4), ("домашний", 1)),
    },
    {
        "name": "дефис и апостроф",
        "text": "мама-мама don't",
        "words": 2, "sentences": 1, "unique": 2,
        "longest": "мама-мама",
        "top": (("don't", 1), ("мама-мама", 1)),
    },
    {
        "name": "числа считаются словами",
        "text": "В 2026 году 12 месяцев.",
        "words": 5, "sentences": 1, "unique": 5,
        "longest": "месяцев",
        "top": (("12", 1), ("2026", 1), ("в", 1)),
    },
]


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_known_results_are_stable(case):
    stats = processing_module.analyze(case["text"])
    assert stats.words == case["words"]
    assert stats.sentences == case["sentences"]
    assert stats.unique_words == case["unique"]
    assert stats.longest_word == case["longest"]
    assert stats.top_words == case["top"]
    assert stats.chars == len(case["text"])
    assert stats.chars_no_spaces == sum(
        1 for symbol in case["text"] if not symbol.isspace())


def test_protocol_envelope_is_stable():
    message = protocol.build_request("Текст.")
    assert message == {
        "version": "1.0",
        "type": "text_request",
        "payload": {"text": "Текст."},
    }
    response = processing_module.handle_request(message)
    assert response["version"] == "1.0"
    assert response["type"] == "stats_response"
    assert set(response["payload"]) == {
        "chars", "chars_no_spaces", "words", "sentences", "unique_words",
        "avg_word_length", "longest_word", "top_words",
    }


def test_average_length_rounding_is_stable():
    stats = processing_module.analyze("я яя яяя")
    assert stats.avg_word_length == 2.0


def _runner(request_path, response_path, timeout):
    processing_module.process_files(request_path, response_path)


def test_output_text_is_stable():
    stats = mapping.TextStats(chars=12, chars_no_spaces=11, words=2,
                              sentences=1, unique_words=2,
                              avg_word_length=5.0,
                              longest_word="Привет",
                              top_words=(("привет", 1), ("мир", 1)))
    assert output_module.format_stats(stats) == (
        "Статистика текста\n"
        "Символов: 12\n"
        "Символов без пробелов: 11\n"
        "Слов: 2\n"
        "Предложений: 1\n"
        "Уникальных слов: 2\n"
        "Средняя длина слова: 5.00\n"
        "Самое длинное слово: Привет\n"
        "Самые частые слова:\n"
        "  привет — 1\n  мир — 1"
    )


def test_large_text_result():
    text = " ".join(["слово"] * 1000) + "."
    stats = processing_module.analyze(text)
    assert stats.words == 1000
    assert stats.unique_words == 1
    assert stats.top_words == (("слово", 1000),)
    assert stats.avg_word_length == 5.0


def test_exchange_file_format_is_stable(exchange_dir):
    textstat.integrate("Привет!", exchange_dir, runner=_runner)
    with open(os.path.join(exchange_dir, "request.json"),
              encoding="utf-8") as handle:
        message = json.load(handle)
    assert message["type"] == "text_request"
    assert message["payload"]["text"] == "Привет!"


def test_cli_output_is_stable(tmp_path):
    text = tmp_path / "text.txt"
    text.write_text("Привет, мир!", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, os.path.join(ROOT_DIR, "src", "textstat.py"),
         "--file", str(text)],
        capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0
    assert completed.stdout.split("\n")[0] == "Статистика текста"
    assert "Слов: 2" in completed.stdout
    assert "мир — 1" in completed.stdout
